"""Download Kronos model and NSE stock data, verify inference works."""
import sys, os
WORKSPACE = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(WORKSPACE, "kronos"))
os.environ["HF_TOKEN"] = "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"

import torch
import yfinance as yf
import pandas as pd
import numpy as np
from model import Kronos, KronosTokenizer, KronosPredictor

MODELS_DIR = os.path.join(WORKSPACE, "models")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

print(f"Device: {DEVICE}")
print(f"CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB" if DEVICE == "cuda" else "")

# 1. Download model from HuggingFace
print("\n=== Downloading Kronos-small model ===")
tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
model.to(DEVICE)
model.eval()
print(f"Model loaded: {sum(p.numel() for p in model.parameters())/1e6:.1f}M params")

# 2. Download NSE weekly data
print("\n=== Fetching NSE stock data ===")
nse_tickers = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]
all_data = {}
for ticker in nse_tickers:
    print(f"  Fetching {ticker}...")
    df = yf.download(ticker, period="2y", interval="1wk", progress=False)
    if df.empty:
        print(f"  No data for {ticker}, trying without suffix...")
        df = yf.download(ticker.replace(".NS", ""), period="2y", interval="1wk", progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [str(c).lower() for c in df.columns]
        all_data[ticker] = df
        print(f"  {ticker}: {len(df)} weeks ({df.index[0].date()} to {df.index[-1].date()})")

if not all_data:
    print("No NSE data fetched, using synthetic data for demonstration")
    print("ERROR: No data available")
    sys.exit(1)

# 3. Test inference on one stock
print("\n=== Testing Kronos Inference ===")
ticker = list(all_data.keys())[0]
df = all_data[ticker]

# Prepare data - use OHLCV columns
cols = [c for c in ['open', 'high', 'low', 'close', 'volume', 'amount'] if c in df.columns]
print(f"Using columns: {cols}")
print(f"Data shape: {df[cols].shape}")

# Use latest data
lookback = min(400, len(df) - 10)
pred_len = min(52, len(df) - lookback)  # predict ~1 year ahead weekly

if lookback < 10:
    print(f"Not enough data for {ticker}, need at least 10 weeks")
    sys.exit(1)

x_df = df.iloc[:lookback][cols].reset_index(drop=True)
x_timestamp = df.index[:lookback]
y_timestamp = df.index[lookback:lookback + pred_len]

print(f"Lookback: {lookback} weeks, Predict: {pred_len} weeks")
print(f"X range: {x_timestamp[0].date()} to {x_timestamp[-1].date()}")
print(f"Y range: {y_timestamp[0].date()} to {y_timestamp[-1].date()}")

# Run prediction
predictor = KronosPredictor(model, tokenizer, max_context=512)
pred_df = predictor.predict(
    df=x_df, x_timestamp=pd.Series(x_timestamp),
    y_timestamp=pd.Series(y_timestamp),
    pred_len=pred_len, T=0.8, top_p=0.9, sample_count=5,
)

print(f"\nPrediction shape: {pred_df.shape}")
print("Prediction head:")
print(pred_df.head())

# Compare with actual
actual = df.iloc[lookback:lookback + pred_len]
if 'close' in pred_df.columns and 'close' in actual.columns:
    actual_close = actual['close'].values[:len(pred_df)]
    pred_close = pred_df['close'].values
    mape = np.mean(np.abs((actual_close - pred_close) / (actual_close + 1e-10))) * 100
    print(f"\nMAPE on close prices: {mape:.2f}%")
    print(f"Actual close range: {actual_close.min():.2f} - {actual_close.max():.2f}")
    print(f"Pred close range: {pred_close.min():.2f} - {pred_close.max():.2f}")

# Save a sample result
result = {
    "ticker": ticker,
    "model": "Kronos-small",
    "lookback_weeks": lookback,
    "prediction_weeks": pred_len,
    "actual_close": actual_close.tolist() if 'close' in actual.columns else [],
    "predicted_close": pred_close.tolist() if 'close' in pred_df.columns else [],
    "dates": [str(d.date()) for d in y_timestamp[:len(pred_df)]],
}
import json
os.makedirs(MODELS_DIR, exist_ok=True)
with open(os.path.join(MODELS_DIR, "kronos_first_run.json"), "w") as f:
    json.dump(result, f, indent=2)

print("\n=== Kronos inference verified! ===")
print(f"Model ready for fine-tuning on all {len(all_data)} NSE stocks")
print(f"Results saved to models/kronos_first_run.json")
