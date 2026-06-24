"""
data/fetcher.py — the only file that talks to Yahoo Finance.

If you ever switch to a different data source (Alpha Vantage, etc.),
you only need to change this file. Everything else reads the dict
format returned by fetch_ticker_data().
"""

import logging
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_ticker_data(ticker: str, period: str = "1y") -> Optional[dict]:
    """
    Fetch price history + basic fundamentals for one ticker.

    Returns a dict with keys:
        ticker  — the symbol string
        history — pandas DataFrame with columns: Open, High, Low, Close, Volume
        info    — dict of fundamental fields (may be partially empty on free tier)

    Returns None if the ticker is invalid or the fetch fails entirely.
    """
    ticker = ticker.upper().strip()
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period)

        if hist.empty:
            logger.warning("No price history returned for %s", ticker)
            return None

        # Drop timezone info from the index — keeps downstream math simple
        hist.index = hist.index.tz_localize(None)

        info = _safe_fetch_info(t, ticker)

        return {
            "ticker": ticker,
            "history": hist,
            "info": info,
        }

    except Exception as exc:
        logger.error("Failed to fetch %s: %s", ticker, exc)
        return None


def _safe_fetch_info(t: yf.Ticker, ticker: str) -> dict:
    """
    Pull fundamental fields from yfinance .info dict.
    yfinance's .info can fail or return incomplete data — we handle that gracefully
    rather than crashing the whole fetch.
    """
    defaults = {
        "name": ticker,
        "sector": "Unknown",
        "market_cap": None,
        "pe_ratio": None,
        "earnings_date": None,
    }

    try:
        raw = t.info
        if not raw:
            return defaults

        return {
            "name":         raw.get("shortName") or raw.get("longName") or ticker,
            "sector":       raw.get("sector", "Unknown"),
            "market_cap":   raw.get("marketCap"),
            "pe_ratio":     raw.get("trailingPE"),
            "earnings_date": _parse_earnings_date(raw),
        }

    except Exception as exc:
        logger.warning("Could not fetch .info for %s: %s", ticker, exc)
        return defaults


def _parse_earnings_date(raw: dict) -> Optional[str]:
    """
    yfinance returns earnings dates inconsistently across versions.
    Try a few known field names and return the first ISO date string we find.
    """
    for field in ("earningsDate", "nextEarningsDate", "earningsTimestamp"):
        val = raw.get(field)
        if not val:
            continue
        # Sometimes it's a list (range), sometimes a single value
        if isinstance(val, (list, tuple)) and len(val) > 0:
            val = val[0]
        try:
            # Convert epoch int or pandas Timestamp to a plain date string
            return pd.Timestamp(val).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None
