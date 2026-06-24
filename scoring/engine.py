"""
scoring/engine.py — orchestrates data → indicators → score → risk flags → ranked list.

This is the main entry point for the scoring layer.
The UI (and eventually any execution module) calls score_watchlist() and gets
back a clean, sorted list of results.  It never needs to know about yfinance,
pandas, or the math behind each indicator.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

import config
from data import loader
from scoring import indicators as ind
from scoring import risk_flags as flags

logger = logging.getLogger(__name__)


def score_watchlist(force_refresh: bool = False, cache_only: bool = False,
                    tickers: list[str] = None) -> list[dict]:
    """
    Fetch and score every ticker in the watchlist (or a custom ticker list).

    tickers: optional override list — if provided, scores these instead of the watchlist.
    Returns a list of result dicts sorted by score descending (best first).
    """
    if tickers is not None:
        raw_data = loader.get_tickers(tickers, force_refresh=force_refresh, cache_only=cache_only)
    else:
        raw_data = loader.get_watchlist(force_refresh=force_refresh, cache_only=cache_only)

    # First pass: compute indicators and raw volatility for each ticker
    # We need all volatilities before we can compute percentile ranks.
    partial_results = []
    volatilities    = []

    for ticker, data in raw_data.items():
        if data is None:
            logger.warning("Skipping %s — no data", ticker)
            continue

        result = _score_one(ticker, data)
        if result is None:
            continue

        partial_results.append(result)
        volatilities.append(result["_raw_volatility"])

    if not partial_results:
        return []

    # Second pass: compute volatility percentile ranks and attach risk flags
    vol_array = np.array(volatilities, dtype=float)
    results   = []

    for result in partial_results:
        raw_vol = result.pop("_raw_volatility")   # remove the staging field

        if np.isnan(raw_vol) or vol_array.max() == vol_array.min():
            vol_pctile = 50.0
        else:
            vol_pctile = float(np.sum(vol_array <= raw_vol) / len(vol_array) * 100)

        result["risk_flags"] = flags.collect_flags(
            ticker               = result["ticker"],
            history              = result["_history"],
            info                 = result["info"],
            indicator_results    = result["indicators"],
            current_price        = result["current_price"],
            volatility_percentile= vol_pctile,
        )
        result.pop("_history")   # don't expose the raw DataFrame to the UI layer
        results.append(result)

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def score_one_ticker(ticker: str, force_refresh: bool = False) -> Optional[dict]:
    """Score a single ticker. Used for the detail page."""
    data = loader.get_ticker(ticker, force_refresh=force_refresh)
    if data is None:
        return None

    result = _score_one(ticker, data)
    if result is None:
        return None

    result.pop("_raw_volatility", None)
    result["risk_flags"] = flags.collect_flags(
        ticker               = result["ticker"],
        history              = result["_history"],
        info                 = result["info"],
        indicator_results    = result["indicators"],
        current_price        = result["current_price"],
        volatility_percentile= 50.0,   # can't rank a single ticker; use neutral
    )
    result.pop("_history")
    return result


# ------------------------------------------------------------------
# Internal
# ------------------------------------------------------------------

def _score_one(ticker: str, data: dict) -> Optional[dict]:
    """
    Compute all indicators for one ticker and return a partial result dict.
    Attaches _raw_volatility and _history as staging fields (removed by callers).
    """
    history = data["history"]
    info    = data["info"]

    if len(history) < config.MA_LONG_DAYS:
        logger.warning("Not enough history for %s (%d rows)", ticker, len(history))
        return None

    current_price = float(history["Close"].iloc[-1])

    # --- Run all indicators ---
    indicator_results = {
        "rsi":             ind.rsi(history),
        "ma_crossover":    ind.ma_crossover(history),
        "momentum":        ind.momentum(history),
        "relative_volume": ind.relative_volume(history),
    }

    # --- Weighted composite score (0–100) ---
    total_score = 0.0
    for key, weight in config.WEIGHTS.items():
        ind_score = indicator_results.get(key, {}).get("score", 0.0)
        total_score += ind_score * weight
    total_score = round(total_score * 100, 1)

    # --- Raw volatility (20-day annualized std dev of returns) ---
    # Stored temporarily so the caller can compute cross-stock percentile ranks.
    close   = history["Close"].dropna()
    returns = close.pct_change().dropna()
    if len(returns) >= 20:
        raw_vol = float(returns.iloc[-20:].std() * (252 ** 0.5))
    else:
        raw_vol = float("nan")

    # --- Position sizing hint ---
    sizing = _position_sizing(current_price)

    raw_cap = info.get("market_cap")
    market_cap_b = round(raw_cap / 1e9, 2) if raw_cap else None  # billions

    return {
        "ticker":        ticker,
        "name":          info.get("name", ticker),
        "sector":        info.get("sector", "Unknown"),
        "current_price": current_price,
        "market_cap_b":  market_cap_b,   # in billions, may be None
        "score":         total_score,
        "indicators":    indicator_results,
        "sizing":        sizing,
        "info":          info,
        # staging fields, removed before returning to callers:
        "_raw_volatility": raw_vol,
        "_history":        history,
    }


def _position_sizing(price: float) -> dict:
    """
    Given the current share price and account size from config,
    return practical guidance on position sizing.

    Rule of thumb used here:
        Max position = 20% of account (config.MAX_POSITION_PCT)
        This limits any single stock from dominating a small portfolio.
    """
    account      = config.ACCOUNT_SIZE_USD
    max_dollars  = account * config.MAX_POSITION_PCT
    max_shares   = max_dollars / price if price > 0 else 0

    if price <= max_dollars:
        whole_shares  = int(max_dollars // price)
        cost_of_whole = whole_shares * price
        note = (
            f"Up to {whole_shares} whole share(s) = ${cost_of_whole:.2f} "
            f"({config.MAX_POSITION_PCT*100:.0f}% of account max)"
        )
    else:
        # One whole share exceeds the position limit
        frac = max_dollars / price
        note = (
            f"One whole share (${price:.2f}) exceeds the "
            f"{config.MAX_POSITION_PCT*100:.0f}% position limit (${max_dollars:.2f}).  "
            f"Consider a fractional share of {frac:.3f} shares on Robinhood."
        )

    return {
        "max_position_dollars": round(max_dollars, 2),
        "max_shares":           round(max_shares, 4),
        "note":                 note,
    }
