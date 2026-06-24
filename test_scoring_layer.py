"""
test_scoring_layer.py — verify the scoring engine works before building the UI.

Usage:
    python test_scoring_layer.py

What it does:
    1. Scores a small subset of the watchlist (5 tickers — fast)
    2. Prints a ranked table with score breakdown per indicator
    3. Shows any risk flags that triggered
    4. Prints position sizing advice for the top pick
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s — %(message)s")
sys.path.insert(0, ".")

# Temporarily override the watchlist so the test is fast (5 tickers, not 40)
import config
config.WATCHLIST = ["AAPL", "MSFT", "NVDA", "JPM", "XOM"]

from scoring.engine import score_watchlist

SEP = "-" * 72


def main():
    print(f"\n{'='*72}")
    print("  StockResearcher — Scoring Layer Test")
    print(f"{'='*72}")
    print("Fetching and scoring 5 tickers (uses cache if available)...\n")

    results = score_watchlist()

    if not results:
        print("ERROR: no results returned — check the data layer first.")
        return

    # --- Ranked table ---
    print(f"{'Rank':<5} {'Ticker':<7} {'Score':>6}  {'RSI':>6}  {'MA%':>6}  {'Mom%':>6}  {'RelVol':>6}")
    print(SEP)
    for i, r in enumerate(results, 1):
        ind = r["indicators"]
        rsi_v   = ind["rsi"]["value"]
        ma_v    = ind["ma_crossover"]["value"]
        mom_v   = ind["momentum"]["value"]
        rv_v    = ind["relative_volume"]["value"]
        print(
            f"#{i:<4} {r['ticker']:<7} {r['score']:>6.1f}  "
            f"{_fmt(rsi_v):>6}  {_fmt(ma_v):>6}  {_fmt(mom_v):>6}  {_fmt(rv_v):>6}"
        )

    # --- Detail for top pick ---
    top = results[0]
    print(f"\n{SEP}")
    print(f"  Detail: #{1} — {top['ticker']} ({top['name']})  Score: {top['score']}/100")
    print(f"  Price: ${top['current_price']:.2f}  |  Sector: {top['sector']}")
    print(SEP)

    for key, ind_result in top["indicators"].items():
        score_pct = ind_result["score"] * 100
        bar       = "#" * int(score_pct / 10) + "." * (10 - int(score_pct / 10))
        print(f"\n  {ind_result['label']}")
        print(f"  Score contribution: {bar}  {score_pct:.0f}/100")
        print(f"  -> {ind_result['interpretation']}")

    print(f"\n  Position sizing:")
    print(f"  -> {top['sizing']['note']}")

    flags = top["risk_flags"]
    if flags:
        print(f"\n  Risk flags:")
        for f in flags:
            icon = "(!)" if f["severity"] == "warning" else "(i)"
            print(f"  {icon} [{f['flag']}] {f['detail']}")
    else:
        print(f"\n  Risk flags: none")

    print(f"\n{'='*72}")
    print("  Scoring layer looks good. Ready to build the UI.")
    print(f"{'='*72}\n")


def _fmt(v) -> str:
    return f"{v:.1f}" if v is not None else "N/A"


if __name__ == "__main__":
    main()
