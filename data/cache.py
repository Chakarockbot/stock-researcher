"""
data/cache.py — saves fetched data to disk so we don't hammer Yahoo Finance.

Why cache?  yfinance is a scraper, not an official API.  If you fetch
40 tickers every time you refresh the page, you'll get rate-limited or
temporarily blocked.  The cache stores each ticker's data as a file and
skips the network if the data is fresh enough (see CACHE_MAX_AGE_HOURS
in config.py).

Cache format: one pickle file per ticker in the /cache directory.
A JSON metadata file tracks when each ticker was last fetched.
"""

import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Resolve cache directory relative to this file's location
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
_META_FILE = os.path.join(_CACHE_DIR, "_meta.json")


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def get(ticker: str, max_age_hours: float) -> Optional[dict]:
    """Return cached data for ticker if it exists and is fresh. Otherwise None."""
    path = _ticker_path(ticker)
    if not os.path.exists(path):
        return None

    cached_at = _load_meta().get(ticker)
    if not cached_at:
        return None

    age = datetime.now() - datetime.fromisoformat(cached_at)
    if age > timedelta(hours=max_age_hours):
        logger.debug("Cache stale for %s (age: %s)", ticker, age)
        return None

    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as exc:
        logger.warning("Could not read cache for %s: %s", ticker, exc)
        return None


def set(ticker: str, data: dict) -> None:
    """Write data to cache and record the current timestamp."""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    try:
        with open(_ticker_path(ticker), "wb") as f:
            pickle.dump(data, f)
        meta = _load_meta()
        meta[ticker] = datetime.now().isoformat()
        _save_meta(meta)
    except Exception as exc:
        logger.warning("Could not write cache for %s: %s", ticker, exc)


def last_updated(ticker: str) -> Optional[str]:
    """Return a human-readable 'last fetched' string, or None if not cached."""
    cached_at = _load_meta().get(ticker)
    if not cached_at:
        return None
    return datetime.fromisoformat(cached_at).strftime("%Y-%m-%d %H:%M")


def clear(ticker: str = None) -> None:
    """
    Clear cache for one ticker, or all tickers if ticker=None.
    Useful if you get bad data and want to force a fresh fetch.
    """
    if ticker:
        path = _ticker_path(ticker)
        if os.path.exists(path):
            os.remove(path)
        meta = _load_meta()
        meta.pop(ticker, None)
        _save_meta(meta)
    else:
        for fname in os.listdir(_CACHE_DIR):
            if fname.endswith(".pkl"):
                os.remove(os.path.join(_CACHE_DIR, fname))
        _save_meta({})


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _ticker_path(ticker: str) -> str:
    return os.path.join(_CACHE_DIR, f"{ticker.upper()}.pkl")


def _load_meta() -> dict:
    if not os.path.exists(_META_FILE):
        return {}
    try:
        with open(_META_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_meta(meta: dict) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_META_FILE, "w") as f:
        json.dump(meta, f, indent=2)
