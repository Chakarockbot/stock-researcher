"""
db/database.py — SQLite setup. All tables defined here.
"""

import os

from sqlalchemy import Boolean, Column, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_DB_PATH = os.path.join(os.path.dirname(__file__), "trades.db")
_ENGINE  = create_engine(f"sqlite:///{_DB_PATH}", connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class PaperTrade(Base):
    """One row = one hypothetical position."""
    __tablename__ = "paper_trades"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    ticker      = Column(String(10), nullable=False, index=True)
    shares      = Column(Float, nullable=False)
    price_open  = Column(Float, nullable=False)
    date_opened = Column(String(10), nullable=False)
    price_close = Column(Float, nullable=True)
    date_closed = Column(String(10), nullable=True)
    notes       = Column(Text, nullable=True)


class PriceAlert(Base):
    """Alert fires when a ticker crosses a user-set price threshold."""
    __tablename__ = "price_alerts"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    ticker       = Column(String(10), nullable=False, index=True)
    direction    = Column(String(5), nullable=False)   # "above" or "below"
    target_price = Column(Float, nullable=False)
    created_at   = Column(String(20), nullable=False)
    triggered_at = Column(String(20), nullable=True)   # null = not yet triggered
    is_active    = Column(Boolean, default=True, nullable=False)


class ScoreSnapshot(Base):
    """
    One row per ticker per refresh cycle.
    Used to compute rank-change deltas on the dashboard.
    """
    __tablename__ = "score_snapshots"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(30), nullable=False, index=True)  # ISO datetime of the refresh
    ticker      = Column(String(10), nullable=False)
    score       = Column(Float, nullable=False)
    rank        = Column(Integer, nullable=False)
    captured_at = Column(String(30), nullable=False)


class User(Base):
    """App login credentials — stored locally, never synced."""
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)


def init_db() -> None:
    Base.metadata.create_all(_ENGINE)


def get_session() -> Session:
    SessionLocal = sessionmaker(bind=_ENGINE)
    return SessionLocal()
