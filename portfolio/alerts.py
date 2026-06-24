"""
portfolio/alerts.py — price alert CRUD and trigger checking.

An alert fires when a stock's current price crosses the user's target.
Alerts are one-shot: once triggered they become inactive and show as a
banner on the dashboard until dismissed.
"""

from datetime import datetime
from typing import Optional

from db.database import PriceAlert, get_session


def get_alerts(active_only: bool = False) -> list[dict]:
    session = get_session()
    try:
        q = session.query(PriceAlert).order_by(PriceAlert.created_at.desc())
        if active_only:
            q = q.filter(PriceAlert.is_active == True)
        return [_row(a) for a in q.all()]
    finally:
        session.close()


def add_alert(ticker: str, direction: str, target_price: float) -> dict:
    session = get_session()
    try:
        alert = PriceAlert(
            ticker       = ticker.upper().strip(),
            direction    = direction,          # "above" or "below"
            target_price = target_price,
            created_at   = datetime.now().strftime("%Y-%m-%d %H:%M"),
            is_active    = True,
        )
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return _row(alert)
    finally:
        session.close()


def delete_alert(alert_id: int) -> bool:
    session = get_session()
    try:
        alert = session.get(PriceAlert, alert_id)
        if alert is None:
            return False
        session.delete(alert)
        session.commit()
        return True
    finally:
        session.close()


def check_and_trigger(scored_results: list[dict]) -> list[dict]:
    """
    Compare current prices in scored_results against all active alerts.
    Marks triggered alerts inactive and returns a list of newly-fired alerts
    for display as a dashboard banner.
    """
    price_map = {r["ticker"]: r["current_price"] for r in scored_results}

    session = get_session()
    try:
        active = session.query(PriceAlert).filter(PriceAlert.is_active == True).all()
        triggered = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        for alert in active:
            price = price_map.get(alert.ticker)
            if price is None:
                continue
            fired = (
                (alert.direction == "above" and price >= alert.target_price) or
                (alert.direction == "below" and price <= alert.target_price)
            )
            if fired:
                alert.triggered_at = now
                alert.is_active    = False
                triggered.append({
                    "ticker":       alert.ticker,
                    "direction":    alert.direction,
                    "target_price": alert.target_price,
                    "current_price": price,
                    "triggered_at": now,
                })

        if triggered:
            session.commit()
        return triggered
    finally:
        session.close()


def _row(a: PriceAlert) -> dict:
    return {
        "id":           a.id,
        "ticker":       a.ticker,
        "direction":    a.direction,
        "target_price": a.target_price,
        "created_at":   a.created_at,
        "triggered_at": a.triggered_at,
        "is_active":    a.is_active,
    }
