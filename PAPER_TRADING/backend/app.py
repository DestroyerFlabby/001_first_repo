from __future__ import annotations

import sys
from calendar import monthrange
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.dashboard_service import (  # noqa: E402
    DEFAULT_START,
    HISTORY_START,
    asset_detail,
    build_overview,
    parse_date,
    trader_detail,
)


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
        "history_from_date": HISTORY_START.isoformat(),
        "presets": [
            {"label": "Since Jan 1", "from_date": "2026-01-01"},
            {"label": "Since May 20", "from_date": "2026-05-20"},
        ],
        "checkpoints": month_checkpoints(HISTORY_START, date.today()),
    }


@app.get("/api/overview")
def overview(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    return build_overview(start, end)


@app.get("/api/traders/{investor}")
def get_trader(
    investor: str,
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    try:
        return trader_detail(investor, start, end)
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


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
