"""
scoring/risk_flags.py — warnings shown alongside the score, not factored into it.

Risk flags don't make a stock "bad" — they tell you to look more carefully
before acting on a recommendation.  A stock can score 90/100 AND have two
risk flags; that's useful information, not a contradiction.

Each flag function returns None (no flag) or a dict describing the issue.
"""

from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

import config


def low_liquidity(indicator_results: dict) -> Optional[dict]:
    """
    Flag if average daily dollar volume is below the threshold.

    Why it matters: if a stock barely trades $5M/day, a small order from
    an individual investor can noticeably move the price, and it may be
    hard to sell quickly when you want out.
    """
    avg_dv = indicator_results.get("relative_volume", {}).get("avg_dollar_vol")
    if avg_dv is None:
        return None
    if avg_dv < config.MIN_AVG_DOLLAR_VOLUME:
        return {
            "flag":    "Low Liquidity",
            "detail":  (
                f"Average daily dollar volume is ${avg_dv/1e6:.1f}M — below the "
                f"${config.MIN_AVG_DOLLAR_VOLUME/1e6:.0f}M threshold.  "
                f"It may be hard to buy or sell without affecting the price."
            ),
            "severity": "warning",
        }
    return None


def high_share_price(current_price: float) -> Optional[dict]:
    """
    Flag if one share costs more than MAX_SINGLE_SHARE_PCT of the account.

    Why it matters: with a $100 account, a $150 stock means a single share
    is 150% of your capital — impossible to buy a whole share, and even
    a fractional share would be a very concentrated bet.

    Robinhood does support fractional shares, but it's still worth flagging.
    """
    threshold = config.ACCOUNT_SIZE_USD * config.MAX_SINGLE_SHARE_PCT
    if current_price > threshold:
        frac = current_price / config.ACCOUNT_SIZE_USD * 100
        return {
            "flag":    "High Share Price",
            "detail":  (
                f"At ${current_price:.2f}/share, one share is {frac:.0f}% of your "
                f"${config.ACCOUNT_SIZE_USD:.0f} account.  Consider buying a fractional "
                f"share on Robinhood, or waiting until your account grows."
            ),
            "severity": "info",
        }
    return None


def overbought_rsi(indicator_results: dict) -> Optional[dict]:
    """
    Flag if RSI is in overbought territory despite other signals being positive.

    Why it matters: a high score driven by strong momentum + MA crossover can
    coexist with RSI > 70 — meaning the stock has already moved a lot.
    Buying at the peak of a run is riskier than buying during a pullback.
    """
    rsi_val = indicator_results.get("rsi", {}).get("value")
    if rsi_val is None:
        return None
    if rsi_val > config.RSI_OVERBOUGHT:
        return {
            "flag":    "Overbought RSI",
            "detail":  (
                f"RSI is {rsi_val} — above {config.RSI_OVERBOUGHT}.  The stock has "
                f"been rallying strongly and may be overextended in the short term."
            ),
            "severity": "warning",
        }
    return None


def high_volatility(ticker: str, history: pd.DataFrame, volatility_percentile: float) -> Optional[dict]:
    """
    Flag if this stock's recent volatility ranks in the top 20% of the watchlist.

    volatility_percentile is computed by the engine after scoring all stocks,
    since you need the full watchlist to rank within it.

    Why it matters: high volatility means larger swings both up and down.
    With a small account, a 15% drop hurts more than it would for a larger one.
    """
    if volatility_percentile >= config.HIGH_VOLATILITY_PCTILE:
        # Compute the actual annualized vol for display
        close   = history["Close"].dropna()
        returns = close.pct_change().dropna()
        if len(returns) >= 20:
            daily_std     = returns.iloc[-20:].std()
            annualized_vol = daily_std * (252 ** 0.5) * 100
            vol_str = f"{annualized_vol:.0f}% annualized"
        else:
            vol_str = "above average"

        return {
            "flag":    "High Volatility",
            "detail":  (
                f"Recent price swings ({vol_str}) are in the top "
                f"{100 - config.HIGH_VOLATILITY_PCTILE:.0f}% of the watchlist.  "
                f"This stock moves more than most — position size accordingly."
            ),
            "severity": "warning",
        }
    return None


def upcoming_earnings(info: dict) -> Optional[dict]:
    """
    Flag if an earnings announcement falls within the holding window.

    Why it matters: stock prices often jump or drop 5–20% on earnings day,
    regardless of the prior trend.  It's a coin-flip event that can wipe out
    a paper gain or deepen a loss overnight.  Worth knowing about in advance.
    """
    earnings_str = info.get("earnings_date")
    if not earnings_str:
        return None

    try:
        earnings_dt = datetime.strptime(earnings_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    # Ignore the epoch-zero placeholder that yfinance sometimes returns
    if earnings_dt.year < 2000:
        return None

    today     = date.today()
    days_away = (earnings_dt - today).days

    if 0 <= days_away <= config.EARNINGS_WARNING_DAYS:
        return {
            "flag":    "Earnings Soon",
            "detail":  (
                f"Earnings announcement expected in {days_away} day(s) "
                f"({earnings_str}).  Prices can move sharply on earnings — "
                f"consider waiting until after the report."
            ),
            "severity": "warning",
        }
    return None


def collect_flags(
    ticker: str,
    history: pd.DataFrame,
    info: dict,
    indicator_results: dict,
    current_price: float,
    volatility_percentile: float,
) -> list[dict]:
    """
    Run all flag checks and return a list of triggered flags (may be empty).
    """
    candidates = [
        low_liquidity(indicator_results),
        high_share_price(current_price),
        overbought_rsi(indicator_results),
        high_volatility(ticker, history, volatility_percentile),
        upcoming_earnings(info),
    ]
    return [f for f in candidates if f is not None]
