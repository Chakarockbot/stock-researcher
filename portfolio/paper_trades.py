"""
portfolio/paper_trades.py — create, read, and close hypothetical positions.

This module is the only thing that talks to the trades database.
"""

from datetime import date
from typing import Optional

from db.database import PaperTrade, get_session
from data import loader


def open_trade(
    ticker: str,
    shares: float,
    price_open: float,
    date_opened: str,
    notes: str = "",
) -> PaperTrade:
    session = get_session()
    try:
        trade = PaperTrade(
            ticker      = ticker.upper().strip(),
            shares      = shares,
            price_open  = price_open,
            date_opened = date_opened,
            notes       = notes or "",
        )
        session.add(trade)
        session.commit()
        session.refresh(trade)
        return trade
    finally:
        session.close()


def close_trade(trade_id: int, price_close: float, date_closed: str) -> Optional[PaperTrade]:
    session = get_session()
    try:
        trade = session.get(PaperTrade, trade_id)
        if trade is None or trade.date_closed is not None:
            return None
        trade.price_close = price_close
        trade.date_closed = date_closed
        session.commit()
        session.refresh(trade)
        return trade
    finally:
        session.close()


def delete_trade(trade_id: int) -> bool:
    session = get_session()
    try:
        trade = session.get(PaperTrade, trade_id)
        if trade is None:
            return False
        session.delete(trade)
        session.commit()
        return True
    finally:
        session.close()


def get_all_trades() -> list[dict]:
    """
    Return all trades enriched with current price and P&L calculations.
    Open trades show unrealized P&L; closed trades show realized P&L.
    """
    session = get_session()
    try:
        rows = session.query(PaperTrade).order_by(PaperTrade.date_opened.desc()).all()
        results = []
        for t in rows:
            results.append(_enrich(t))
        return results
    finally:
        session.close()


def get_open_trades() -> list[dict]:
    session = get_session()
    try:
        rows = (
            session.query(PaperTrade)
            .filter(PaperTrade.date_closed == None)
            .order_by(PaperTrade.date_opened.desc())
            .all()
        )
        return [_enrich(t) for t in rows]
    finally:
        session.close()


def _enrich(t: PaperTrade) -> dict:
    """Attach current price and P&L to a trade record."""
    is_open = t.date_closed is None

    current_price = None
    if is_open:
        data = loader.get_ticker(t.ticker)
        if data is not None:
            current_price = float(data["history"]["Close"].iloc[-1])

    exit_price = current_price if is_open else t.price_close
    pnl        = None
    pnl_pct    = None
    if exit_price is not None:
        pnl     = round((exit_price - t.price_open) * t.shares, 2)
        pnl_pct = round((exit_price - t.price_open) / t.price_open * 100, 2)

    return {
        "id":            t.id,
        "ticker":        t.ticker,
        "shares":        t.shares,
        "price_open":    t.price_open,
        "date_opened":   t.date_opened,
        "price_close":   t.price_close,
        "date_closed":   t.date_closed,
        "notes":         t.notes,
        "current_price": current_price,
        "pnl":           pnl,
        "pnl_pct":       pnl_pct,
        "is_open":       is_open,
        "cost_basis":    round(t.price_open * t.shares, 2),
    }
