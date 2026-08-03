#!/usr/bin/env python3
"""Train Kronos on NSE weekly data. Single GPU, standalone script."""
import sys, os, json, pickle, time
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "kronos"))
from model import Kronos, KronosTokenizer

WORKSPACE = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(WORKSPACE, "kronos", "data", "nse_weekly")
SAVE_DIR = os.path.join(WORKSPACE, "models", "kronos_finetuned")
os.makedirs(SAVE_DIR, exist_ok=True)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
LOOKBACK = 90
PREDICT = 10
WINDOW = LOOKBACK + PREDICT + 1
BATCH_SIZE = 16
EPOCHS_TOKENIZER = 10
EPOCHS_PREDICTOR = 15
LR_TOKENIZER = 2e-4
LR_PREDICTOR = 4e-5
ACCUMULATE = 2


class NseDataset(Dataset):
    def __init__(self, path, window, n_samples=5000):
        with open(path, 'rb') as f:
            data = pickle.load(f)
        self.window = window
        self.indices = []
        for symbol, df in data.items():
            df = df[['open', 'high', 'low', 'close', 'vol', 'amt']].copy()
            # Add time features: minute=0, hour=0, weekday, day, month
            df['minute'] = 0
            df['hour'] = 0
            df['weekday'] = pd.to_datetime(df.index).weekday if hasattr(df.index, 'weekday') else 0
            df['day'] = pd.to_datetime(df.index).day if hasattr(df.index, 'day') else 1
            df['month'] = pd.to_datetime(df.index).month if hasattr(df.index, 'month') else 1

            if len(df) >= window:
                for i in range(len(df) - window + 1):
                    self.indices.append((df.iloc[i:i+window].copy(), i))
        self.n_samples = min(n_samples, len(self.indices))
        print(f"  {len(data)} symbols, {len(self.indices)} samples, using {self.n_samples}")

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        df, _ = self.indices[idx % len(self.indices)]
        x = df[['open', 'high', 'low', 'close', 'vol', 'amt']].values.astype(np.float32)
        s = df[['minute', 'hour', 'weekday', 'day', 'month']].values.astype(np.float32)
        return torch.FloatTensor(x), torch.FloatTensor(s)


def train_tokenizer(tokenizer, train_loader, val_loader):
    print("\n=== Training Tokenizer ===")
    tokenizer.train().to(DEVICE)
    opt = torch.optim.AdamW(tokenizer.parameters(), lr=LR_TOKENIZER, weight_decay=0.01)
    best_loss = float('inf')

    for epoch in range(EPOCHS_TOKENIZER):
        tokenizer.train()
        total_loss = 0
        for batch_x, _ in tqdm(train_loader, desc=f"Tokenizer E{epoch+1}"):
            batch_x = batch_x.to(DEVICE)
            (z_pre, z_full), bsq_loss, quantized, z_indices = tokenizer(batch_x)
            recon_loss = F.mse_loss(z_full, batch_x)
            loss = recon_loss + bsq_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(tokenizer.parameters(), 5.0)
            opt.step()
            opt.zero_grad()
            total_loss += loss.item()

        tokenizer.eval()
        val_loss = 0
        with torch.no_grad():
            for batch_x, _ in val_loader:
                batch_x = batch_x.to(DEVICE)
                (z_pre, z_full), bsq_loss, _, _ = tokenizer(batch_x)
                val_loss += F.mse_loss(z_full, batch_x).item()

        avg_train = total_loss / len(train_loader)
        avg_val = val_loss / len(val_loader)
        print(f"  Epoch {epoch+1}: train={avg_train:.4f} val={avg_val:.4f}")

        if avg_val < best_loss:
            best_loss = avg_val
            tokenizer.save_pretrained(os.path.join(SAVE_DIR, "tokenizer_best"))
            print(f"  -> Saved best (val_loss={avg_val:.4f})")
    
    tokenizer.save_pretrained(os.path.join(SAVE_DIR, "tokenizer_final"))
    return tokenizer


def train_predictor(model, tokenizer, train_loader, val_loader):
    print("\n=== Training Predictor ===")
    tokenizer.eval().to(DEVICE)
    model.train().to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=LR_PREDICTOR, weight_decay=0.01)
    best_loss = float('inf')
    step = 0

    for epoch in range(EPOCHS_PREDICTOR):
        model.train()
        total_loss = 0
        for batch_x, batch_s in tqdm(train_loader, desc=f"Predictor E{epoch+1}"):
            batch_x = batch_x.to(DEVICE, non_blocking=True)
            batch_s = batch_s.to(DEVICE, non_blocking=True)

            with torch.no_grad():
                s1, s2 = tokenizer.encode(batch_x, half=True)

            # Shift for next-token prediction
            s1_in, s1_out = s1[:, :-1], s1[:, 1:]
            s2_in, s2_out = s2[:, :-1], s2[:, 1:]
            stamp = batch_s[:, :-1, :]

            s1_logits, s2_logits = model(s1_in, s2_in, stamp)
            loss, s1_loss, s2_loss = model.head.compute_loss(s1_logits, s2_logits, s1_out, s2_out)

            loss = loss / ACCUMULATE
            loss.backward()

            if (step + 1) % ACCUMULATE == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
                opt.step()
                opt.zero_grad()
            step += 1
            total_loss += loss.item() * ACCUMULATE

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch_x, batch_s in val_loader:
                batch_x = batch_x.to(DEVICE, non_blocking=True)
                batch_s = batch_s.to(DEVICE, non_blocking=True)
                s1, s2 = tokenizer.encode(batch_x, half=True)
                s1_logits, s2_logits = model(s1[:, :-1], s2[:, :-1], batch_s[:, :-1, :])
                loss, _, _ = model.head.compute_loss(s1_logits, s2_logits, s1[:, 1:], s2[:, 1:])
                val_loss += loss.item()

        avg_train = total_loss / len(train_loader)
        avg_val = val_loss / len(val_loader)
        print(f"  Epoch {epoch+1}: train={avg_train:.4f} val={avg_val:.4f}")

        if avg_val < best_loss:
            best_loss = avg_val
            model.save_pretrained(os.path.join(SAVE_DIR, "predictor_best"))
            torch.save(model.state_dict(), os.path.join(SAVE_DIR, "predictor_best.pt"))
            print(f"  -> Saved best (val_loss={avg_val:.4f})")

    model.save_pretrained(os.path.join(SAVE_DIR, "predictor_final"))
    return model


def main():
    print(f"Device: {DEVICE}")
    print(f"Config: lookback={LOOKBACK}, predict={PREDICT}, batch={BATCH_SIZE}")

    if not os.path.exists(os.path.join(DATA_DIR, "train_data.pkl")):
        print("Data not found. Run scripts/prepare_nse_data.py first.")
        return

    train_ds = NseDataset(os.path.join(DATA_DIR, "train_data.pkl"), WINDOW, n_samples=3000)
    val_ds = NseDataset(os.path.join(DATA_DIR, "val_data.pkl"), WINDOW, n_samples=500)
    train_loader = DataLoader(train_ds, BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_ds, BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True)

    print("\nLoading pre-trained Kronos...")
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
    print(f"Tokenizer: {sum(p.numel() for p in tokenizer.parameters())/1e6:.1f}M")
    print(f"Predictor: {sum(p.numel() for p in model.parameters())/1e6:.1f}M")

    train_tokenizer(tokenizer, train_loader, val_loader)
    tokenizer = KronosTokenizer.from_pretrained(os.path.join(SAVE_DIR, "tokenizer_best"))
    train_predictor(model, tokenizer, train_loader, val_loader)

    print(f"\nDone! Models saved to {SAVE_DIR}")


if __name__ == "__main__":
    main()
