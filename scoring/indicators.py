"""
scoring/indicators.py — one function per indicator, each returning a 0.0–1.0 score.

Every function follows the same contract:
    Input:  a pandas DataFrame with at least a 'Close' and 'Volume' column
            (the 'history' field from the data layer)
    Output: a dict with:
              value         — the raw calculated number (e.g. RSI = 43.2)
              score         — normalized 0.0 to 1.0 (1.0 = strongest buy signal)
              label         — short display name for the UI
              interpretation — plain-English explanation of what the value means right now

Keeping each indicator isolated here means you can unit-test them individually
and swap in a better formula later without touching the engine.
"""

import numpy as np
import pandas as pd

import config


# ------------------------------------------------------------------
# RSI — Relative Strength Index
# ------------------------------------------------------------------
# WHAT IT IS:
#   RSI measures whether a stock has been going up or down more
#   aggressively than usual over the past N trading days.
#   The result is always between 0 and 100.
#
#   Below ~40 = the stock has been selling off hard ("oversold").
#              The theory is that sellers may be exhausted and a
#              bounce is more likely.
#   Above ~70 = the stock has been rallying hard ("overbought").
#              The theory is that buyers may be exhausted.
#   40–70     = neutral, no strong signal either way.
#
# IMPORTANT CAVEAT:
#   Oversold stocks can keep falling. RSI alone is not a reliable
#   buy signal — it's one input among several.

def rsi(history: pd.DataFrame) -> dict:
    period = config.RSI_PERIOD
    close  = history["Close"].dropna()

    if len(close) < period + 1:
        return _empty("RSI", "Not enough data")

    delta  = close.diff().dropna()
    gains  = delta.clip(lower=0)
    losses = (-delta).clip(lower=0)

    # Wilder's smoothing (the standard method): exponential moving average
    # with alpha = 1/period.  Using adjust=False matches the original formula.
    avg_gain = gains.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False).mean()

    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]

    if last_loss == 0:
        rsi_value = 100.0   # no losing days at all — maximum overbought
    else:
        rs        = last_gain / last_loss
        rsi_value = round(100 - (100 / (1 + rs)), 1)

    # Score: 1.0 when RSI is at 20 (very oversold), 0.0 when RSI is at 70+
    # Linear scale between those poles.
    score = max(0.0, min(1.0, (70 - rsi_value) / (70 - 20)))

    # Plain-English interpretation
    if rsi_value < config.RSI_OVERSOLD:
        note = f"Oversold ({rsi_value}) — stock has been selling off; may be due for a bounce"
    elif rsi_value > config.RSI_OVERBOUGHT:
        note = f"Overbought ({rsi_value}) — stock has been rallying hard; momentum may be fading"
    else:
        note = f"Neutral ({rsi_value}) — neither oversold nor overbought"

    return {
        "value":          rsi_value,
        "score":          round(score, 3),
        "label":          f"RSI ({period}-day)",
        "interpretation": note,
    }


# ------------------------------------------------------------------
# Moving Average Crossover — 20-day SMA vs 50-day SMA
# ------------------------------------------------------------------
# WHAT IT IS:
#   A Simple Moving Average (SMA) is the plain average of a stock's
#   closing price over N days.  We track two:
#     Short (20-day): reflects the last ~1 month of prices
#     Long  (50-day): reflects the last ~2.5 months of prices
#
#   When the 20-day line is ABOVE the 50-day line, the stock's recent
#   trajectory is higher than its medium-term trend — bullish.
#   When it's BELOW, recent momentum is lagging the medium-term — bearish.
#
#   The magnitude of the gap matters too.  A 3% gap is a much stronger
#   signal than a 0.1% gap.

def ma_crossover(history: pd.DataFrame) -> dict:
    close = history["Close"].dropna()

    if len(close) < config.MA_LONG_DAYS:
        return _empty("MA Crossover", "Not enough data for 50-day average")

    ma_short = close.rolling(config.MA_SHORT_DAYS).mean().iloc[-1]
    ma_long  = close.rolling(config.MA_LONG_DAYS).mean().iloc[-1]

    # How far above/below the short MA is vs the long MA, as a percentage
    pct_diff = (ma_short - ma_long) / ma_long * 100

    # Score: 0.5 when MAs are equal, sliding toward 1.0 (+5%) or 0.0 (-5%)
    # Capped: anything beyond ±5% is treated as max signal.
    score = max(0.0, min(1.0, 0.5 + pct_diff / 10))

    if pct_diff > 1.0:
        note = (
            f"Bullish: 20-day avg (${ma_short:.2f}) is {pct_diff:+.1f}% above "
            f"50-day avg (${ma_long:.2f}) — short-term momentum is beating the medium-term trend"
        )
    elif pct_diff < -1.0:
        note = (
            f"Bearish: 20-day avg (${ma_short:.2f}) is {pct_diff:+.1f}% below "
            f"50-day avg (${ma_long:.2f}) — recent price action is lagging the medium-term trend"
        )
    else:
        note = (
            f"Neutral: 20-day avg (${ma_short:.2f}) and 50-day avg (${ma_long:.2f}) "
            f"are nearly equal ({pct_diff:+.1f}%) — no clear directional signal"
        )

    return {
        "value":          round(pct_diff, 2),
        "score":          round(score, 3),
        "label":          f"MA Crossover ({config.MA_SHORT_DAYS}/{config.MA_LONG_DAYS}-day)",
        "interpretation": note,
        "ma_short":       round(ma_short, 2),
        "ma_long":        round(ma_long, 2),
    }


# ------------------------------------------------------------------
# Price Momentum — 20-day price change %
# ------------------------------------------------------------------
# WHAT IT IS:
#   The simplest possible trend signal: how much has the closing price
#   changed over the last N trading days, as a percentage?
#
#   Positive = the stock has been climbing.
#   Negative = the stock has been falling.
#
#   This is a trend-following signal — it says "this stock has been
#   moving in this direction lately."  It does NOT predict reversals.
#   Pair with RSI (which does lean toward reversals) for balance.

def momentum(history: pd.DataFrame) -> dict:
    close = history["Close"].dropna()

    if len(close) < config.MOMENTUM_DAYS + 1:
        return _empty("Momentum", "Not enough data")

    price_now  = close.iloc[-1]
    price_then = close.iloc[-(config.MOMENTUM_DAYS + 1)]
    pct_change = (price_now - price_then) / price_then * 100

    # Score: 0.5 at flat, 1.0 at +10%, 0.0 at -10%
    score = max(0.0, min(1.0, 0.5 + pct_change / 20))

    direction = "up" if pct_change >= 0 else "down"
    note = (
        f"Price is {abs(pct_change):.1f}% {direction} over the last "
        f"{config.MOMENTUM_DAYS} trading days (from ${price_then:.2f} to ${price_now:.2f})"
    )

    return {
        "value":          round(pct_change, 2),
        "score":          round(score, 3),
        "label":          f"Momentum ({config.MOMENTUM_DAYS}-day)",
        "interpretation": note,
    }


# ------------------------------------------------------------------
# Relative Volume
# ------------------------------------------------------------------
# WHAT IT IS:
#   Volume = how many shares changed hands in a day.
#   Relative volume = today's volume divided by the average daily volume
#   over the past N days.
#
#   A reading of 1.0 = perfectly normal day.
#   A reading of 2.0 = twice the normal activity — something is happening
#     (news, earnings rumor, index rebalancing, big fund buying/selling).
#   A reading of 0.5 = unusually quiet — the market isn't paying attention.
#
#   High relative volume is a signal of conviction — it suggests that the
#   day's price movement (up or down) is backed by real participation, not
#   just a few trades drifting the price.
#
# NOTE: yfinance returns today's volume as a partial day figure if the
#   market is still open.  This is fine for an end-of-day check.

def relative_volume(history: pd.DataFrame) -> dict:
    volume = history["Volume"].dropna()
    close  = history["Close"].dropna()

    if len(volume) < config.REL_VOLUME_DAYS + 1:
        return _empty("Relative Volume", "Not enough data")

    today_vol   = volume.iloc[-1]
    avg_vol     = volume.iloc[-(config.REL_VOLUME_DAYS + 1):-1].mean()

    if avg_vol == 0:
        return _empty("Relative Volume", "Average volume is zero")

    rel_vol     = today_vol / avg_vol
    today_price = close.iloc[-1]

    # Average daily dollar volume = average shares × price (proxy for liquidity)
    avg_dollar_vol = avg_vol * today_price

    # Score: 0.0 at 0.5× avg, 0.5 at 1.5× avg, 1.0 at 2.5× avg
    score = max(0.0, min(1.0, (rel_vol - 0.5) / 2.0))

    if rel_vol >= config.REL_VOLUME_THRESHOLD:
        note = (
            f"Elevated: {rel_vol:.1f}× normal volume today — "
            f"above-average participation suggests conviction behind today's move"
        )
    elif rel_vol < 0.7:
        note = (
            f"Quiet: {rel_vol:.1f}× normal volume — "
            f"low participation; today's price move may not be meaningful"
        )
    else:
        note = f"Normal: {rel_vol:.1f}× average daily volume"

    return {
        "value":          round(rel_vol, 2),
        "score":          round(score, 3),
        "label":          f"Relative Volume ({config.REL_VOLUME_DAYS}-day avg)",
        "interpretation": note,
        "avg_dollar_vol": avg_dollar_vol,
    }


# ------------------------------------------------------------------
# Internal helper
# ------------------------------------------------------------------

def _empty(label: str, reason: str) -> dict:
    return {
        "value":          None,
        "score":          0.0,
        "label":          label,
        "interpretation": f"Could not calculate — {reason}",
    }
