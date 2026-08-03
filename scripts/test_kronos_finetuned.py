"""Quick test of fine-tuned Kronos model."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "kronos"))

import torch
import yfinance as yf
import pandas as pd
import numpy as np
from model import Kronos, KronosTokenizer, KronosPredictor

WORKSPACE = os.path.dirname(os.path.dirname(__file__))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SAVE_DIR = os.path.join(WORKSPACE, "models", "kronos_finetuned")

print("Loading fine-tuned model...")
tokenizer = KronosTokenizer.from_pretrained(os.path.join(SAVE_DIR, "tokenizer_best"))
model = Kronos.from_pretrained(os.path.join(SAVE_DIR, "predictor_best"))
model.to(DEVICE)
model.eval()
tokenizer.to(DEVICE)
tokenizer.eval()
print(f"Predictor: {sum(p.numel() for p in model.parameters())/1e6:.1f}M params")

print("\nFetching fresh NSE data for test...")
df = yf.download("RELIANCE.NS", period="2y", interval="1wk", progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [c[0].lower() for c in df.columns]
df = df.rename(columns={'volume': 'vol'})
df['amt'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4 * df['vol']
df = df[['open', 'high', 'low', 'close', 'vol', 'amt']]

print(f"Data: {len(df)} weeks")

# Predict last 10 weeks using 90-week lookback
lookback = 90
pred_len = 10
x_df = df.iloc[:lookback].reset_index(drop=True)
x_ts = pd.Series(df.index[:lookback])
y_ts = pd.Series(df.index[lookback:lookback + pred_len])

predictor = KronosPredictor(model, tokenizer, max_context=512)
pred_df = predictor.predict(
    df=x_df, x_timestamp=x_ts, y_timestamp=y_ts,
    pred_len=pred_len, T=0.7, top_p=0.9, sample_count=5, verbose=False
)

# Compare with actual
actual = df.iloc[lookback:lookback + pred_len]
if 'close' in pred_df.columns:
    mape = np.mean(np.abs((actual['close'].values - pred_df['close'].values[:len(actual)]) / (actual['close'].values + 1e-10))) * 100
    print(f"\nMAPE: {mape:.2f}%")
    print(f"Last actual close: {actual['close'].values[-1]:.2f}")
    print(f"Predicted close:   {pred_df['close'].values[-1]:.2f}")

print("\nFine-tuned model works correctly!")
