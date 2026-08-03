#!/usr/bin/env python3
"""Prepare NSE stock data for Kronos fine-tuning (yfinance instead of Qlib)."""
import sys, os, pickle
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "kronos"))

import yfinance as yf
import pandas as pd
import numpy as np
from tqdm import tqdm

NSE_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "BAJFINANCE.NS",
    "KOTAKBANK.NS", "LT.NS", "WIPRO.NS", "AXISBANK.NS", "TITAN.NS",
    "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "NTPC.NS",
    "M&M.NS", "POWERGRID.NS", "JSWSTEEL.NS", "TRENT.NS", "BAJAJFINSV.NS",
    "HCLTECH.NS", "ADANIPORTS.NS", "TATASTEEL.NS", "TATAMOTORS.NS", "COALINDIA.NS",
    "NESTLEIND.NS", "ONGC.NS", "DMART.NS", "SBILIFE.NS", "EICHERMOT.NS",
    "GODREJCP.NS", "BRITANNIA.NS", "HDFCLIFE.NS", "DIVISLAB.NS", "CIPLA.NS",
    "SHRIRAMFIN.NS", "DRREDDY.NS", "GRASIM.NS", "HAL.NS", "ADANIENT.NS",
    "HEROMOTOCO.NS", "BPCL.NS", "BAJAJ-AUTO.NS", "TECHM.NS", "INDUSINDBK.NS",
]

def fetch_nse_data(period="5y", interval="1wk"):
    """Fetch NSE stock data from Yahoo Finance."""
    all_data = {}
    for ticker in tqdm(NSE_TICKERS, desc="Fetching NSE stocks"):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0].lower() for c in df.columns]
            else:
                df.columns = [str(c).lower() for c in df.columns]

            required = ['open', 'high', 'low', 'close']
            if not all(c in df.columns for c in required):
                continue

            # Rename volume -> vol, compute amount
            df = df.rename(columns={'volume': 'vol'})
            df['amt'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4 * df['vol']

            # Keep only required features
            df = df[['open', 'high', 'low', 'close', 'vol', 'amt']]
            df = df.dropna()
            df.index.name = 'datetime'

            if len(df) >= 60:  # Need at least 60 weeks for meaningful training
                all_data[ticker.replace(".NS", "")] = df

        except Exception as e:
            print(f"  Error fetching {ticker}: {e}")
            continue

    return all_data


def split_and_save(data, output_dir, lookback=90, predict=10):
    """Split data into train/val/test and save as pickle."""
    os.makedirs(output_dir, exist_ok=True)

    # Sort by date across all symbols
    all_dates = sorted(set(
        date for df in data.values()
        for date in df.index
    ))
    n = len(all_dates)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    train_start_date = all_dates[0]
    train_end_date = all_dates[train_end]
    val_start_date = all_dates[train_end - lookback - predict]  # overlap for context
    val_end_date = all_dates[val_end]
    test_start_date = all_dates[val_end - lookback - predict]
    test_end_date = all_dates[-1]

    train_data, val_data, test_data = {}, {}, {}
    for symbol, df in data.items():
        train_data[symbol] = df.loc[(df.index >= train_start_date) & (df.index <= train_end_date)]
        val_data[symbol] = df.loc[(df.index >= val_start_date) & (df.index <= val_end_date)]
        test_data[symbol] = df.loc[(df.index >= test_start_date) & (df.index <= test_end_date)]

    for name, d in [("train", train_data), ("val", val_data), ("test", test_data)]:
        # Filter symbols with enough data
        d_filtered = {k: v for k, v in d.items() if len(v) >= lookback + predict + 1}
        path = os.path.join(output_dir, f"{name}_data.pkl")
        with open(path, 'wb') as f:
            pickle.dump(d_filtered, f)
        print(f"  {name}: {len(d_filtered)} symbols, saved to {path}")

    return output_dir


if __name__ == "__main__":
    WORKSPACE = os.path.dirname(os.path.dirname(__file__))
    output_dir = os.path.join(WORKSPACE, "kronos", "data", "nse_weekly")

    print("=== Fetching NSE weekly data ===")
    data = fetch_nse_data(period="5y", interval="1wk")
    print(f"Fetched {len(data)} stocks with sufficient data")

    print("\n=== Splitting and saving datasets ===")
    split_and_save(data, output_dir)
    print(f"\nDone! Data saved to {output_dir}")
