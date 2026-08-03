"""Kronos financial forecast API endpoint."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
KRONOS_DIR = WORKSPACE / "kronos"
SAVE_DIR = WORKSPACE / "models" / "kronos_finetuned"

import sys
sys.path.insert(0, str(KRONOS_DIR))
from model import Kronos, KronosTokenizer, KronosPredictor

router = APIRouter(prefix="/forecast", tags=["Forecast"])

_model = None
_tokenizer = None
_predictor = None
_device = None


def get_model():
    global _model, _tokenizer, _predictor, _device
    if _model is None:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _tokenizer = KronosTokenizer.from_pretrained(str(SAVE_DIR / "tokenizer_best"))
        _model = Kronos.from_pretrained(str(SAVE_DIR / "predictor_best"))
        _model.to(_device)
        _model.eval()
        _tokenizer.to(_device)
        _tokenizer.eval()
        _predictor = KronosPredictor(_model, _tokenizer, max_context=512)
    return _predictor


class ForecastRequest(BaseModel):
    ticker: str = "RELIANCE.NS"
    period: str = "2y"
    interval: str = "1wk"
    lookback: int = 90
    pred_len: int = 10
    temperature: float = 0.7
    top_p: float = 0.9
    sample_count: int = 5


class ForecastResponse(BaseModel):
    ticker: str
    dates: list[str]
    actual_close: list[float]
    predicted_open: list[float]
    predicted_high: list[float]
    predicted_low: list[float]
    predicted_close: list[float]
    predicted_volume: list[float]
    mape: float | None = None
    last_actual_close: float | None = None
    last_predicted_close: float | None = None


@router.get("/tickers")
async def list_tickers() -> list[str]:
    return [
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


@router.post("/predict", response_model=ForecastResponse)
async def predict(req: ForecastRequest) -> Any:
    try:
        ticker = req.ticker
        if not ticker.endswith(".NS"):
            ticker = ticker + ".NS"

        df = yf.download(ticker, period=req.period, interval=req.interval, progress=False)
        if df.empty:
            df = yf.download(ticker.replace(".NS", ""), period=req.period, interval=req.interval, progress=False)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [str(c).lower() for c in df.columns]
        df = df.rename(columns={'volume': 'vol'})
        df['amt'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4 * df['vol']
        df = df[['open', 'high', 'low', 'close', 'vol', 'amt']]

        lookback = min(req.lookback, len(df) - req.pred_len - 1)
        if lookback < 10:
            raise HTTPException(status_code=400, detail=f"Need at least {req.pred_len + 11} weeks of data, got {len(df)}")

        x_df = df.iloc[:lookback].reset_index(drop=True)
        x_ts = pd.Series(df.index[:lookback])
        y_ts = pd.Series(df.index[lookback:lookback + req.pred_len])

        predictor = get_model()
        pred_df = predictor.predict(
            df=x_df, x_timestamp=x_ts, y_timestamp=y_ts,
            pred_len=req.pred_len, T=req.temperature,
            top_p=req.top_p, sample_count=req.sample_count, verbose=False
        )

        actual = df.iloc[lookback:lookback + req.pred_len]
        actual_close = actual['close'].values.tolist() if len(actual) > 0 else []
        pred_close = pred_df['close'].values[:len(actual)].tolist() if len(actual) > 0 else []

        mape = None
        if actual_close and pred_close:
            act = np.array(actual_close)
            pred = np.array(pred_close)
            mape = float(np.mean(np.abs((act - pred) / (act + 1e-10))) * 100)

        return ForecastResponse(
            ticker=req.ticker,
            dates=[str(d.date()) for d in y_ts[:len(pred_df)]],
            actual_close=actual_close if len(actual_close) <= len(pred_df) else actual_close[:len(pred_df)],
            predicted_open=pred_df['open'].tolist(),
            predicted_high=pred_df['high'].tolist(),
            predicted_low=pred_df['low'].tolist(),
            predicted_close=pred_df['close'].tolist(),
            predicted_volume=pred_df['volume'].tolist() if 'volume' in pred_df.columns else [],
            mape=mape,
            last_actual_close=actual_close[-1] if actual_close else None,
            last_predicted_close=pred_close[-1] if pred_close else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
