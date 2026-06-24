"""
portfolio/history.py — score snapshot storage and rank-delta computation.

Every time the user clicks "Refresh Data," a snapshot of all scores and
ranks is saved.  The next time the dashboard loads, we compare the current
ranks against the most recent previous snapshot to show ↑/↓ badges.

Why save on refresh only (not every page load)?
  Page loads use cached data, so scores don't change between loads.
  Deltas would always be zero.  We only want to record a new snapshot
  when we've actually fetched fresh data from Yahoo Finance.
"""

from datetime import datetime
from typing import Optional

from db.database import ScoreSnapshot, get_session

MAX_SNAPSHOTS_TO_KEEP = 30   # ~1 month of daily refreshes


def save_snapshot(results: list[dict]) -> None:
    """Save the current scored ranking as a new snapshot batch."""
    snapshot_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    captured_at = snapshot_id
    session = get_session()
    try:
        for rank, r in enumerate(results, 1):
            session.add(ScoreSnapshot(
                snapshot_id = snapshot_id,
                ticker      = r["ticker"],
                score       = r["score"],
                rank        = rank,
                captured_at = captured_at,
            ))
        session.commit()
    finally:
        session.close()
    _cleanup()


def get_rank_deltas(current_results: list[dict]) -> dict[str, str]:
    """
    Return a dict mapping ticker → delta string, e.g.:
        "AAPL" → "+3"    (moved up 3 spots)
        "MSFT" → "-2"    (moved down 2 spots)
        "UBER" → "new"   (not in previous snapshot)
        "NVDA" → ""      (no change)

    If there is no previous snapshot at all, returns empty dict.
    """
    session = get_session()
    try:
        # Get the most recent snapshot_id
        latest = (
            session.query(ScoreSnapshot.snapshot_id)
            .order_by(ScoreSnapshot.captured_at.desc())
            .first()
        )
        if not latest:
            return {}

        prev_rows = (
            session.query(ScoreSnapshot)
            .filter(ScoreSnapshot.snapshot_id == latest[0])
            .all()
        )
        prev_rank = {row.ticker: row.rank for row in prev_rows}
    finally:
        session.close()

    deltas: dict[str, str] = {}
    for current_rank, r in enumerate(current_results, 1):
        ticker = r["ticker"]
        if ticker not in prev_rank:
            deltas[ticker] = "new"
        else:
            diff = prev_rank[ticker] - current_rank   # positive = moved up
            if diff > 0:
                deltas[ticker] = f"+{diff}"
            elif diff < 0:
                deltas[ticker] = str(diff)
            else:
                deltas[ticker] = ""
    return deltas


def list_snapshots() -> list[dict]:
    """Return all distinct snapshots, newest first, as {snapshot_id, label, count}."""
    session = get_session()
    try:
        rows = (
            session.query(ScoreSnapshot.snapshot_id, ScoreSnapshot.captured_at)
            .distinct(ScoreSnapshot.snapshot_id)
            .order_by(ScoreSnapshot.captured_at.desc())
            .all()
        )
        result = []
        for snap_id, captured_at in rows:
            count = session.query(ScoreSnapshot).filter(
                ScoreSnapshot.snapshot_id == snap_id
            ).count()
            result.append({"snapshot_id": snap_id, "captured_at": captured_at, "count": count})
        return result
    finally:
        session.close()


def get_snapshot(snapshot_id: str) -> list[dict]:
    """Return all ticker rows for a given snapshot, sorted by rank."""
    session = get_session()
    try:
        rows = (
            session.query(ScoreSnapshot)
            .filter(ScoreSnapshot.snapshot_id == snapshot_id)
            .order_by(ScoreSnapshot.rank)
            .all()
        )
        return [{"ticker": r.ticker, "score": r.score, "rank": r.rank} for r in rows]
    finally:
        session.close()


def _cleanup() -> None:
    """Remove old snapshot batches beyond MAX_SNAPSHOTS_TO_KEEP."""
    session = get_session()
    try:
        distinct = (
            session.query(ScoreSnapshot.snapshot_id)
            .distinct()
            .order_by(ScoreSnapshot.captured_at.desc())
            .all()
        )
        ids_to_keep = {row[0] for row in distinct[:MAX_SNAPSHOTS_TO_KEEP]}
        if len(distinct) > MAX_SNAPSHOTS_TO_KEEP:
            session.query(ScoreSnapshot).filter(
                ScoreSnapshot.snapshot_id.notin_(ids_to_keep)
            ).delete(synchronize_session=False)
            session.commit()
    finally:
        session.close()
