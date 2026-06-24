# ============================================================
# config.py — all tunable settings live here
# ============================================================
# The watchlist is now stored in watchlist.json so you can
# edit it from the Settings page without touching this file.
# The DEFAULT_WATCHLIST below is only used to seed watchlist.json
# the first time the app starts.
# ============================================================

import json
import os

_WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")

DEFAULT_WATCHLIST = [
    # Large-cap tech
    "AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "AMD", "INTC", "CSCO", "ORCL",
    # Finance
    "JPM", "BAC", "GS", "V", "MA", "WFC",
    # Healthcare
    "JNJ", "PFE", "UNH", "ABBV", "MRK",
    # Consumer
    "WMT", "COST", "HD", "MCD", "NKE", "SBUX",
    # Energy
    "XOM", "CVX", "COP",
    # Industrials
    "CAT", "BA", "GE", "HON",
    # Media / Telecom
    "DIS", "NFLX", "T", "VZ",
    # Growth
    "TSLA", "UBER", "PYPL", "SHOP",
]

# Large universe (~200 tickers) for the "replace watchlist by price" feature.
# Deliberately spans all price tiers so the smart-split algorithm always has
# enough affordable candidates regardless of the user's price threshold.
FULL_UNIVERSE = list(dict.fromkeys([
    # ── Mega/large-cap tech ──────────────────────────────────────────────
    "AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "ADBE", "CRM", "ORCL",
    "QCOM", "TXN", "AMAT", "KLAC",
    # ── Mid-cap tech / cloud (often $10–$150) ────────────────────────────
    "AMD", "INTC", "CSCO", "IBM", "MU", "SNAP", "PINS",
    "SNOW", "PLTR", "NET", "DDOG", "ZS", "CRWD", "PANW", "TTD", "MRVL", "SMCI",
    # ── Fintech / e-commerce ─────────────────────────────────────────────
    "PYPL", "SHOP", "AFRM", "ROKU", "SOFI", "HOOD", "NU", "COIN", "SEZL",
    # ── Finance ──────────────────────────────────────────────────────────
    "JPM", "BAC", "GS", "V", "MA", "WFC", "C", "MS", "AXP", "COF",
    "USB", "PNC", "SCHW", "BK", "BRK-B", "BLK", "ICE", "CME",
    "ALLY", "SYF", "KEY", "RF", "FITB", "CFG", "HBAN", "MTB",
    # ── Healthcare ───────────────────────────────────────────────────────
    "JNJ", "PFE", "UNH", "ABBV", "MRK", "BMY", "AMGN", "GILD", "CVS",
    "CI", "ISRG", "MDT", "ABT", "BSX", "SYK", "ZBH", "INCY",
    "MRNA", "DXCM", "HIMS", "TDOC", "VRTX", "REGN",
    # ── Consumer / retail ────────────────────────────────────────────────
    "WMT", "COST", "TGT", "HD", "MCD", "SBUX", "NKE", "LOW",
    "KO", "PEP", "PM", "MO", "CL", "PG", "KHC", "GIS", "CPB", "CAG",
    "LULU", "ROST", "TJX", "CMG", "YUM", "ETSY", "CHWY", "BKNG", "ABNB",
    "GAP", "KSS", "BBY", "M", "DG", "DLTR",
    # ── Auto / transportation ─────────────────────────────────────────────
    "TSLA", "F", "GM", "RIVN",
    "UBER", "LYFT", "DASH",
    # ── Airlines ─────────────────────────────────────────────────────────
    "AAL", "DAL", "UAL", "LUV", "JBLU",
    # ── Energy ───────────────────────────────────────────────────────────
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX", "OXY", "HAL",
    "DVN", "ET", "APA", "OVV",
    "ENPH", "FSLR", "NEE",
    # ── Industrials / defense ─────────────────────────────────────────────
    "CAT", "BA", "GE", "HON", "MMM", "UPS", "FDX", "DE", "EMR", "ETN",
    "LMT", "RTX", "NOC", "CARR", "ITW",
    "CSX", "NSC", "UNP",
    # ── Media / telecom ──────────────────────────────────────────────────
    "DIS", "NFLX", "T", "VZ", "CMCSA", "WBD", "FOX",
    # ── Gaming / entertainment ────────────────────────────────────────────
    "EA", "TTWO", "U", "RBLX", "SPOT", "ARM",
    # ── Crypto-adjacent ───────────────────────────────────────────────────
    "MARA", "RIOT",
    # ── REITs / utilities ─────────────────────────────────────────────────
    "O", "AMT", "SPG", "DLR", "EQR", "NLY", "AGNC", "VICI",
    # ── Hospitality / travel ──────────────────────────────────────────────
    "CCL", "RCL", "MGM", "WYNN", "MAR", "HLT",
]))

# How many guaranteed "affordable" slots when doing a price-filtered replace.
AFFORDABLE_SLOTS = 100


def get_watchlist() -> list[str]:
    """Return the current watchlist from watchlist.json (creates it from defaults if missing)."""
    if not os.path.exists(_WATCHLIST_FILE):
        save_watchlist(DEFAULT_WATCHLIST)
        return list(DEFAULT_WATCHLIST)
    with open(_WATCHLIST_FILE) as f:
        return json.load(f)


def save_watchlist(tickers: list[str]) -> None:
    """Persist the watchlist to watchlist.json."""
    with open(_WATCHLIST_FILE, "w") as f:
        json.dump([t.upper().strip() for t in tickers], f, indent=2)


# Keep WATCHLIST as a module-level alias for backwards compatibility
# with any code that imports config.WATCHLIST directly.
# It reads once at import; routes that need live data call get_watchlist().
WATCHLIST = get_watchlist()

# ---- Account settings ----------------------------------------
ACCOUNT_SIZE_USD = 100.0
MAX_POSITION_PCT = 0.20

# ---- Data fetching -------------------------------------------
HISTORY_PERIOD       = "1y"
CACHE_MAX_AGE_HOURS  = 8

# ---- RSI settings --------------------------------------------
RSI_PERIOD   = 14
RSI_OVERSOLD = 40
RSI_OVERBOUGHT = 70

# ---- Moving average settings ---------------------------------
MA_SHORT_DAYS = 20
MA_LONG_DAYS  = 50

# ---- Momentum settings ---------------------------------------
MOMENTUM_DAYS = 20

# ---- Relative volume settings --------------------------------
REL_VOLUME_DAYS      = 20
REL_VOLUME_THRESHOLD = 1.5

# ---- Scoring weights (must sum to 1.0) -----------------------
WEIGHTS = {
    "rsi":             0.30,
    "ma_crossover":    0.25,
    "momentum":        0.25,
    "relative_volume": 0.20,
}

# ---- Risk flag thresholds ------------------------------------
MIN_AVG_DOLLAR_VOLUME  = 5_000_000
EARNINGS_WARNING_DAYS  = 14
HIGH_VOLATILITY_PCTILE = 80
MAX_SINGLE_SHARE_PCT   = 0.50
