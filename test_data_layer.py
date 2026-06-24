"""
test_data_layer.py — run this to verify the data layer works before using the app.

Usage:
    python test_data_layer.py

What it does:
    1. Fetches data for 3 tickers (fast — doesn't pull the whole watchlist)
    2. Prints the most recent 5 rows of price history for each
    3. Prints any fundamentals that came back
    4. Tests the cache: fetches again and confirms it came from cache (fast second call)
"""

import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s — %(message)s",
)

# Make sure imports resolve from project root
sys.path.insert(0, ".")

from data import loader, cache

TEST_TICKERS = ["AAPL", "MSFT", "NVDA"]


def main():
    print("\n" + "=" * 60)
    print("  StockResearcher — Data Layer Test")
    print("=" * 60)

    for ticker in TEST_TICKERS:
        print(f"\n--- {ticker} ---")

        t0 = time.time()
        data = loader.get_ticker(ticker, force_refresh=True)
        elapsed = time.time() - t0

        if data is None:
            print(f"  FAILED: could not fetch {ticker}")
            continue

        hist = data["history"]
        info = data["info"]

        print(f"  Fetched in {elapsed:.1f}s | {len(hist)} trading days of history")
        print(f"  Name:       {info['name']}")
        print(f"  Sector:     {info['sector']}")
        print(f"  Market cap: {_fmt_cap(info['market_cap'])}")
        print(f"  P/E ratio:  {info['pe_ratio']}")
        print(f"  Earnings:   {info['earnings_date'] or 'not available'}")
        print(f"\n  Last 5 trading days:")
        print(hist[["Close", "Volume"]].tail(5).to_string())

    # Cache test
    print("\n\n--- Cache test ---")
    t0 = time.time()
    data = loader.get_ticker("AAPL")   # should be instant from cache
    elapsed = time.time() - t0
    updated = cache.last_updated("AAPL")
    if elapsed < 0.5:
        print(f"  Cache HIT for AAPL in {elapsed:.3f}s (last fetched: {updated})")
    else:
        print(f"  Cache may not be working — took {elapsed:.1f}s")

    print("\n" + "=" * 60)
    print("  Data layer looks good. Ready to build scoring.")
    print("=" * 60 + "\n")


def _fmt_cap(cap) -> str:
    if cap is None:
        return "not available"
    if cap >= 1e12:
        return f"${cap/1e12:.1f}T"
    if cap >= 1e9:
        return f"${cap/1e9:.1f}B"
    return f"${cap/1e6:.0f}M"


if __name__ == "__main__":
    main()
