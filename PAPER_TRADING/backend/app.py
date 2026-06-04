from __future__ import annotations

import sys
from calendar import monthrange
from datetime import date
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.dashboard_service import (  # noqa: E402
    DEFAULT_START,
    HISTORY_START,
    PUBLIC_DASHBOARD,
    asset_detail,
    latest_market_date,
    parse_date,
    trader_detail,
)
from backend.dashboard_cache import cached_or_build_eod, cached_or_build_overview  # noqa: E402
from backend.benchmark_service import benchmark_registry_response  # noqa: E402
from backend.email_service import send_daily_instructions  # noqa: E402
from backend.news_service import news_summary  # noqa: E402
from backend.universe_service import asset_universe_response, update_asset, upsert_asset  # noqa: E402


app = FastAPI(title="Paper Trading Dashboard", version="1.0.0")
FRONTEND = ROOT / "frontend"


def month_checkpoints(start: date, end: date) -> list[dict[str, str]]:
    checkpoints: list[dict[str, str]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        last_day = monthrange(year, month)[1]
        for label, day in (("BOM", 1), ("Mid-month", 15), ("EOM", last_day)):
            checkpoint = date(year, month, day)
            if start <= checkpoint <= end:
                checkpoints.append(
                    {
                        "label": f"{checkpoint.strftime('%b %Y')} {label}",
                        "date": checkpoint.isoformat(),
                    }
                )
        month += 1
        if month == 13:
            year += 1
            month = 1
    return checkpoints


def window(from_date: str | None, to_date: str | None) -> tuple[date, date | None]:
    try:
        start = parse_date(from_date, DEFAULT_START)
        end = parse_date(to_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="dates must use YYYY-MM-DD") from exc
    if not start:
        raise HTTPException(status_code=400, detail="from_date is required")
    if end and end < start:
        raise HTTPException(status_code=400, detail="to_date must be on or after from_date")
    return start, end


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict[str, object]:
    return {
        "default_from_date": DEFAULT_START.isoformat(),
        "default_to_date": latest_market_date().isoformat(),
        "history_from_date": HISTORY_START.isoformat(),
        "public_dashboard": PUBLIC_DASHBOARD,
        "key_dates": [
            {"label": "Jan 1 reference", "date": "2026-01-01"},
            {"label": "May 20 reference", "date": "2026-05-20"},
            {"label": "May 29 reference", "date": "2026-05-29"},
        ],
        "checkpoints": month_checkpoints(HISTORY_START, date.today()),
    }


@app.get("/api/overview")
def overview(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    return cached_or_build_overview(start, end, wealthsimple_fx_fees)


@app.get("/api/eod")
def eod(wealthsimple_fx_fees: bool = Query(default=False)) -> dict[str, object]:
    return cached_or_build_eod(wealthsimple_fx_fees)


@app.get("/api/universe/assets")
def universe_assets() -> dict[str, object]:
    return asset_universe_response()


def ensure_private_write() -> None:
    if PUBLIC_DASHBOARD:
        raise HTTPException(status_code=403, detail="asset universe writes are disabled in public dashboard mode")


@app.post("/api/universe/assets")
def create_or_update_universe_asset(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    ensure_private_write()
    try:
        return {"asset": upsert_asset(payload)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/universe/assets/{ticker}")
def patch_universe_asset(
    ticker: str,
    asset_type: str | None = Query(default=None),
    payload: dict[str, object] = Body(...),
) -> dict[str, object]:
    ensure_private_write()
    try:
        return {"asset": update_asset(ticker, payload, asset_type)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown asset: {ticker}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/benchmarks")
def benchmarks(include_inactive: bool = Query(default=False)) -> dict[str, object]:
    return benchmark_registry_response(include_inactive=include_inactive)


@app.post("/api/notifications/daily-instructions")
def daily_instructions(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    try:
        return send_daily_instructions(start, end, wealthsimple_fx_fees)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown notification strategy: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/traders/{investor}")
def get_trader(
    investor: str,
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    try:
        return trader_detail(investor, start, end, wealthsimple_fx_fees)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown trader: {investor}") from exc


@app.get("/api/stocks/{ticker}")
def get_stock(
    ticker: str,
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    try:
        return asset_detail(ticker, start, end)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown ticker: {ticker}") from exc


@app.get("/api/stocks/{ticker}/news")
def get_stock_news(ticker: str) -> dict[str, object]:
    return news_summary(ticker)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
