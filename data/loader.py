"""
data/loader.py — the single entry point for getting ticker data.

The rest of the app (scoring, UI) imports only from here.
This layer decides: hit cache, or go fetch.
"""

import logging
from typing import Optional

import config
from data import cache, fetcher

logger = logging.getLogger(__name__)


def get_ticker(ticker: str, force_refresh: bool = False, cache_only: bool = False) -> Optional[dict]:
    """
    Return data for a single ticker.

    cache_only=True: return cached data only — never hit the network.
                     Returns None if no cache entry exists.
    force_refresh=True: skip cache and fetch fresh from Yahoo Finance.
    Default: use cache if fresh, otherwise fetch.
    """
    if not force_refresh:
        cached = cache.get(ticker, max_age_hours=config.CACHE_MAX_AGE_HOURS)
        if cached is not None:
            logger.debug("Cache hit for %s", ticker)
            return cached

    if cache_only:
        return None

    logger.info("Fetching %s from Yahoo Finance...", ticker)
    data = fetcher.fetch_ticker_data(ticker, period=config.HISTORY_PERIOD)

    if data is not None:
        cache.set(ticker, data)

    return data


def get_tickers(tickers: list[str], force_refresh: bool = False, cache_only: bool = False) -> dict[str, Optional[dict]]:
    """Return data for an arbitrary list of tickers (not necessarily the watchlist)."""
    results = {}
    for ticker in tickers:
        results[ticker] = get_ticker(ticker, force_refresh=force_refresh, cache_only=cache_only)
    success = sum(1 for v in results.values() if v is not None)
    logger.info("Loaded %d/%d requested tickers.", success, len(tickers))
    return results


def get_watchlist(force_refresh: bool = False, cache_only: bool = False) -> dict[str, Optional[dict]]:
    """
    Return data for every ticker in the watchlist.

    cache_only=True skips any ticker not already in cache (no network calls).
    """
    watchlist = config.get_watchlist()
    results = {}
    for ticker in watchlist:
        results[ticker] = get_ticker(ticker, force_refresh=force_refresh, cache_only=cache_only)

    success = sum(1 for v in results.values() if v is not None)
    logger.info("Loaded %d/%d tickers from watchlist.", success, len(watchlist))
    return results
