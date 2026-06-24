"""
app.py — FastAPI entry point.

Run with:
    python app.py
Then open http://localhost:8000 in your browser.
"""

import logging
import math
from contextlib import asynccontextmanager
from datetime import date

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

import config
from data import cache, fetcher, loader
from db import auth as auth_svc
from db.database import init_db
from portfolio import alerts as alert_svc
from portfolio import history as history_svc
from portfolio import paper_trades
from scoring.engine import score_one_ticker, score_watchlist

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s — %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="StockResearcher", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

_PUBLIC_PATHS = {"/login", "/logout", "/setup"}

class _AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)
        if auth_svc.user_count() == 0:
            return RedirectResponse(url="/setup", status_code=302)
        if not request.session.get("user"):
            return RedirectResponse(url="/login", status_code=302)
        return await call_next(request)

# SessionMiddleware must be added last so it wraps AuthMiddleware
app.add_middleware(_AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=auth_svc.get_secret_key(), session_cookie="sr_session", https_only=False)

_jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html"]),
    cache_size=0,
    auto_reload=True,
)
templates = Jinja2Templates(env=_jinja_env)


# ------------------------------------------------------------------
# Auth routes
# ------------------------------------------------------------------

@app.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    if auth_svc.user_count() > 0:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "setup.html", {"request": request})

@app.post("/setup")
def setup_submit(request: Request, username: str = Form(...), password: str = Form(...), confirm: str = Form(...)):
    if auth_svc.user_count() > 0:
        return RedirectResponse(url="/", status_code=302)
    if password != confirm:
        return templates.TemplateResponse(request, "setup.html", {"request": request, "error": "Passwords do not match."})
    if len(password) < 6:
        return templates.TemplateResponse(request, "setup.html", {"request": request, "error": "Password must be at least 6 characters."})
    auth_svc.create_user(username.strip(), password)
    request.session["user"] = username.strip()
    return RedirectResponse(url="/", status_code=302)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"request": request})

@app.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if auth_svc.verify_password(username.strip(), password):
        request.session["user"] = username.strip()
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Invalid username or password."})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    watchlist    = config.get_watchlist()
    results      = score_watchlist(cache_only=True)
    last_updated = cache.last_updated(watchlist[0]) if watchlist else "never"

    triggered = alert_svc.check_and_trigger(results)
    deltas    = history_svc.get_rank_deltas(results)

    sectors = sorted({r["sector"] for r in results if r["sector"] != "Unknown"})

    return templates.TemplateResponse(request, "dashboard.html", context={
        "results":         results,
        "last_updated":    last_updated or "never",
        "account_size":    config.ACCOUNT_SIZE_USD,
        "watchlist_count": len(watchlist),
        "triggered_alerts": triggered,
        "deltas":          deltas,
        "sectors":         sectors,
    })


@app.get("/refresh", response_class=RedirectResponse)
def refresh():
    results = score_watchlist(force_refresh=True)
    history_svc.save_snapshot(results)
    return RedirectResponse(url="/", status_code=302)


# ------------------------------------------------------------------
# Stock detail
# ------------------------------------------------------------------

@app.get("/stock/{ticker}", response_class=HTMLResponse)
def stock_detail(request: Request, ticker: str):
    ticker = ticker.upper()
    result = score_one_ticker(ticker)
    if result is None:
        return templates.TemplateResponse(request, "error.html", context={
            "message": f"Could not load data for {ticker}. Check that it's a valid ticker symbol.",
        }, status_code=404)

    data    = loader.get_ticker(ticker)
    history = data["history"].tail(60) if data else None
    chart_dates = chart_prices = chart_ma20 = chart_ma50 = []
    if history is not None and len(history) >= 2:
        closes      = history["Close"]
        ma20_series = closes.rolling(20).mean()
        ma50_series = closes.rolling(50).mean()
        chart_dates  = [d.strftime("%b %d") for d in closes.index]
        chart_prices = [round(float(p), 2) for p in closes]
        chart_ma20   = [round(float(v), 2) if not math.isnan(v) else None for v in ma20_series]
        chart_ma50   = [round(float(v), 2) if not math.isnan(v) else None for v in ma50_series]

    open_trades   = [t for t in paper_trades.get_all_trades() if t["ticker"] == ticker and t["is_open"]]
    active_alerts = [a for a in alert_svc.get_alerts(active_only=True) if a["ticker"] == ticker]

    return templates.TemplateResponse(request, "stock_detail.html", context={
        "result":         result,
        "chart_dates":    chart_dates,
        "chart_prices":   chart_prices,
        "chart_ma20":     chart_ma20,
        "chart_ma50":     chart_ma50,
        "open_trades":    open_trades,
        "active_alerts":  active_alerts,
        "today":          date.today().isoformat(),
    })


# ------------------------------------------------------------------
# Paper trades
# ------------------------------------------------------------------

@app.get("/trades", response_class=HTMLResponse)
def trades_page(request: Request):
    all_trades    = paper_trades.get_all_trades()
    open_trades   = [t for t in all_trades if t["is_open"]]
    closed_trades = [t for t in all_trades if not t["is_open"]]

    return templates.TemplateResponse(request, "paper_trades.html", context={
        "open_trades":      open_trades,
        "closed_trades":    closed_trades,
        "total_open_cost":  round(sum(t["cost_basis"] for t in open_trades), 2),
        "total_realized":   round(sum(t["pnl"] for t in closed_trades if t["pnl"] is not None), 2),
        "total_unrealized": round(sum(t["pnl"] for t in open_trades   if t["pnl"] is not None), 2),
        "today":            date.today().isoformat(),
        "watchlist":        config.get_watchlist(),
    })


@app.post("/trades/add")
def add_trade(
    ticker: str = Form(...), shares: float = Form(...),
    price_open: float = Form(...), date_opened: str = Form(...), notes: str = Form(""),
):
    paper_trades.open_trade(ticker, shares, price_open, date_opened, notes)
    return RedirectResponse(url="/trades", status_code=302)


@app.post("/trades/close/{trade_id}")
def close_trade(trade_id: int, price_close: float = Form(...), date_closed: str = Form(...)):
    paper_trades.close_trade(trade_id, price_close, date_closed)
    return RedirectResponse(url="/trades", status_code=302)


@app.post("/trades/delete/{trade_id}")
def delete_trade(trade_id: int):
    paper_trades.delete_trade(trade_id)
    return RedirectResponse(url="/trades", status_code=302)


# ------------------------------------------------------------------
# Alerts
# ------------------------------------------------------------------

@app.post("/alerts/add")
def add_alert(
    ticker: str = Form(...), direction: str = Form(...), target_price: float = Form(...),
    redirect_to: str = Form("/"),
):
    alert_svc.add_alert(ticker, direction, target_price)
    return RedirectResponse(url=redirect_to, status_code=302)


@app.post("/alerts/delete/{alert_id}")
def delete_alert(alert_id: int, redirect_to: str = Form("/")):
    alert_svc.delete_alert(alert_id)
    return RedirectResponse(url=redirect_to, status_code=302)


# ------------------------------------------------------------------
# Settings — watchlist editor
# ------------------------------------------------------------------

@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, error: str = "", success: str = ""):
    return templates.TemplateResponse(request, "settings.html", context={
        "watchlist":      config.get_watchlist(),
        "universe_count": len(config.FULL_UNIVERSE),
        "error":          error,
        "success":        success,
    })


@app.post("/settings/watchlist/add")
def watchlist_add(ticker: str = Form(...)):
    ticker  = ticker.upper().strip()
    current = config.get_watchlist()

    if ticker in current:
        return RedirectResponse(url=f"/settings?error={ticker} is already in your watchlist.", status_code=302)

    # Validate: try to fetch a tiny bit of data
    data = fetcher.fetch_ticker_data(ticker, period="5d")
    if data is None:
        return RedirectResponse(url=f"/settings?error=Could not find ticker {ticker} on Yahoo Finance. Check the symbol.", status_code=302)

    current.append(ticker)
    config.save_watchlist(current)
    # Seed the cache immediately so the dashboard doesn't spin on next load
    loader.get_ticker(ticker, force_refresh=True)
    return RedirectResponse(url=f"/settings?success={ticker} added to watchlist.", status_code=302)


@app.post("/settings/watchlist/remove")
def watchlist_remove(ticker: str = Form(...)):
    ticker  = ticker.upper().strip()
    current = config.get_watchlist()
    if ticker in current:
        current.remove(ticker)
        config.save_watchlist(current)
    return RedirectResponse(url="/settings", status_code=302)


@app.post("/settings/change-password")
def change_password(request: Request, current: str = Form(...), new_password: str = Form(...), confirm: str = Form(...)):
    username = request.session.get("user")
    if not auth_svc.verify_password(username, current):
        return RedirectResponse(url="/settings?error=Current password is incorrect.", status_code=302)
    if new_password != confirm:
        return RedirectResponse(url="/settings?error=New passwords do not match.", status_code=302)
    if len(new_password) < 6:
        return RedirectResponse(url="/settings?error=Password must be at least 6 characters.", status_code=302)
    auth_svc.update_password(username, new_password)
    return RedirectResponse(url="/settings?success=Password updated.", status_code=302)


@app.get("/settings/watchlist/rebuild")
def watchlist_rebuild(max_price: float):
    # Fetch ALL universe tickers — uses cache where fresh, fetches the rest
    all_scored = score_watchlist(force_refresh=False, cache_only=False,
                                 tickers=config.FULL_UNIVERSE)

    if not all_scored:
        return RedirectResponse(
            url="/settings?error=Could not score any universe stocks. Check your connection.",
            status_code=302,
        )

    # all_scored is sorted best-first by score
    affordable = [r for r in all_scored if r["current_price"] <= max_price]
    if not affordable:
        return RedirectResponse(
            url=f"/settings?error=No stocks found at or below ${max_price:.0f}. Try a higher price.",
            status_code=302,
        )

    top_affordable     = affordable[:config.AFFORDABLE_SLOTS]
    affordable_tickers = {r["ticker"] for r in top_affordable}
    remaining          = 100 - len(top_affordable)
    fill               = [r for r in all_scored if r["ticker"] not in affordable_tickers][:remaining]

    new_watchlist = [r["ticker"] for r in top_affordable] + [r["ticker"] for r in fill]
    config.save_watchlist(new_watchlist)

    affordable_count = len(top_affordable)
    fill_count       = len(fill)
    total            = len(new_watchlist)
    if fill_count > 0:
        msg = (
            f"Your watchlist is ready! {affordable_count} stocks at ${max_price:.0f} or less, "
            f"plus {fill_count} top-rated picks to round it out — {total} total."
        )
    else:
        msg = (
            f"Your watchlist is ready! Found {total} stocks at ${max_price:.0f} or less — "
            f"all {total} slots filled with affordable picks."
        )
    return RedirectResponse(url=f"/settings?success={msg}", status_code=302)


# ------------------------------------------------------------------
# API helpers
# ------------------------------------------------------------------

@app.get("/api/watchlist-count")
def api_watchlist_count():
    from data import cache as _cache
    wl_count      = len(config.get_watchlist())
    # How many universe tickers need a fresh fetch (for rebuild calibration)
    uncached = sum(1 for t in config.FULL_UNIVERSE
                   if _cache.get(t, max_age_hours=config.CACHE_MAX_AGE_HOURS) is None)
    return JSONResponse({"count": wl_count, "universe_uncached": uncached})


# ------------------------------------------------------------------
# History browser
# ------------------------------------------------------------------

@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, snapshot: str = ""):
    snapshots = history_svc.list_snapshots()
    selected_id = snapshot or (snapshots[0]["snapshot_id"] if snapshots else "")
    rows = history_svc.get_snapshot(selected_id) if selected_id else []
    return templates.TemplateResponse(request, "history.html", context={
        "snapshots":    snapshots,
        "selected_id":  selected_id,
        "rows":         rows,
    })


# ------------------------------------------------------------------
# Glossary
# ------------------------------------------------------------------

@app.get("/glossary", response_class=HTMLResponse)
def glossary_page(request: Request):
    return templates.TemplateResponse(request, "glossary.html", context={})


# ------------------------------------------------------------------
# Run
# ------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
