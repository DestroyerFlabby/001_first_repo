from __future__ import annotations

import sys
import os
import hashlib
import threading
import time
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

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
    paper_ledger_summaries,
    parse_date,
    saved_strategy_preview_detail,
    strategy_lab_detail,
    trader_detail,
)
from backend.dashboard_cache import (  # noqa: E402
    cached_or_build_eod,
    cached_or_build_overview,
    default_preload_window,
    latest_cached_overview_window,
    preload_dashboard_cache,
    read_cache,
)
from backend.benchmark_service import benchmark_registry_response, upsert_benchmark  # noqa: E402
from backend.correlation_service import correlation_response  # noqa: E402
from backend.scenario_service import scenario_response  # noqa: E402
from backend.basket_service import (  # noqa: E402
    basket_performance,
    custom_basket_response,
    upsert_basket,
    upsert_basket_member,
)
from backend.allocation_service import (  # noqa: E402
    metadata_index,
    resolved_instrument_metadata,
    wealth_allocation_response,
)
from backend.email_service import send_daily_instructions  # noqa: E402
from backend.day_rotation_service import daily_rotation_portfolio_response  # noqa: E402
from backend.external_portfolio_service import external_portfolio_response  # noqa: E402
from backend.model_portfolio_service import systematic_model_portfolio_response  # noqa: E402
from backend.news_service import news_summary  # noqa: E402
from backend.performance_service import portfolio_performance_response  # noqa: E402
from backend.research_service import research_index_response, research_note_response  # noqa: E402
from backend.rebalance_service import rebalance_preview, rebalance_profiles_response  # noqa: E402
from backend.risk_service import portfolio_risk_response  # noqa: E402
from backend.strategy_registry_service import read_strategies, strategy_registry_response, upsert_strategy  # noqa: E402
from backend.strategy_selector_service import strategy_selector_response  # noqa: E402
from backend.universe_service import asset_universe_response, read_asset_universe, update_asset, upsert_asset  # noqa: E402
from backend.wealth_intelligence_service import wealth_intelligence_response  # noqa: E402
from backend.wealth_operations_service import wealth_operations_response  # noqa: E402


app = FastAPI(title="Paper Trading Dashboard", version="1.0.0")
FRONTEND = ROOT / "frontend"
OVERVIEW_JOBS: dict[str, dict[str, Any]] = {}
OVERVIEW_JOB_LOCK = threading.Lock()
OVERVIEW_JOB_STALE_SECONDS = 15 * 60
PRELOAD_JOB: dict[str, Any] = {
    "status": "idle",
    "message": "Preload cache is ready to rebuild.",
}
PRELOAD_JOB_LOCK = threading.Lock()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def configured_preload_window() -> tuple[date, date]:
    from_value = os.environ.get("PRELOAD_DASHBOARD_CACHE_FROM_DATE", "").strip()
    to_value = os.environ.get("PRELOAD_DASHBOARD_CACHE_TO_DATE", "").strip()
    start = date.fromisoformat(from_value) if from_value else None
    end = date.fromisoformat(to_value) if to_value else None
    return default_preload_window(start, end)


def configured_preload_preset_window() -> tuple[date, date]:
    from_value = os.environ.get("PRELOAD_DASHBOARD_CACHE_FROM_DATE", "").strip()
    to_value = os.environ.get("PRELOAD_DASHBOARD_CACHE_TO_DATE", "").strip()
    start = date.fromisoformat(from_value) if from_value else None
    if to_value:
        end = date.fromisoformat(to_value)
        return default_preload_window(start, end)
    preload_start, preload_target_end = default_preload_window(start, None)
    cached_window = latest_cached_overview_window(
        preload_start,
        apply_fees=env_bool("PRELOAD_DASHBOARD_CACHE_INCLUDE_FX"),
    )
    return cached_window or (preload_start, preload_target_end)


def warm_dashboard_cache_in_background() -> None:
    if not env_bool("PRELOAD_DASHBOARD_CACHE"):
        return

    def worker() -> None:
        try:
            start, end = configured_preload_window()
            rows = preload_dashboard_cache(
                start,
                end,
                include_fx=env_bool("PRELOAD_DASHBOARD_CACHE_INCLUDE_FX"),
                force=env_bool("PRELOAD_DASHBOARD_CACHE_FORCE"),
            )
            print(f"Dashboard cache warmup complete: {rows}", flush=True)
        except Exception as exc:
            print(f"Dashboard cache warmup failed: {exc}", flush=True)

    threading.Thread(target=worker, name="dashboard-cache-warmup", daemon=True).start()


@app.on_event("startup")
def startup() -> None:
    warm_dashboard_cache_in_background()


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


def overview_job_id(start: date, end: date | None, apply_fees: bool) -> str:
    token = f"{start.isoformat()}|{end.isoformat() if end else 'latest'}|fx={int(apply_fees)}"
    return hashlib.sha1(token.encode("utf-8")).hexdigest()[:16]


def overview_job_response(job_id: str, job: dict[str, Any], include_payload: bool = False) -> dict[str, Any]:
    response: dict[str, Any] = {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "message": job.get("message", ""),
        "from_date": job.get("from_date"),
        "to_date": job.get("to_date"),
        "wealthsimple_fx_fees": job.get("wealthsimple_fx_fees", False),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
    }
    if "detail" in job:
        response["detail"] = job["detail"]
    if include_payload and job.get("status") == "complete":
        response["payload"] = job.get("payload")
    return response


def build_overview_job(job_id: str, start: date, end: date | None, apply_fees: bool) -> None:
    try:
        payload = cached_or_build_overview(start, end, apply_fees)
    except Exception as exc:
        with OVERVIEW_JOB_LOCK:
            job = OVERVIEW_JOBS.setdefault(job_id, {})
            job.update(
                {
                    "status": "error",
                    "message": "Overview build failed.",
                    "detail": str(exc),
                    "completed_at": time.time(),
                }
            )
        return

    with OVERVIEW_JOB_LOCK:
        job = OVERVIEW_JOBS.setdefault(job_id, {})
        job.update(
            {
                "status": "complete",
                "message": "Overview ready.",
                "payload": payload,
                "completed_at": time.time(),
            }
        )


def start_or_get_overview_job(start: date, end: date | None, apply_fees: bool) -> tuple[str, dict[str, Any]]:
    job_id = overview_job_id(start, end, apply_fees)
    if end is not None:
        cached = read_cache("overview", start, end, apply_fees)
        if cached is not None:
            with OVERVIEW_JOB_LOCK:
                OVERVIEW_JOBS[job_id] = {
                    "status": "complete",
                    "message": "Overview loaded from dashboard cache.",
                    "from_date": start.isoformat(),
                    "to_date": end.isoformat(),
                    "wealthsimple_fx_fees": apply_fees,
                    "started_at": time.time(),
                    "completed_at": time.time(),
                    "payload": cached,
                }
                return job_id, dict(OVERVIEW_JOBS[job_id])

    with OVERVIEW_JOB_LOCK:
        existing = OVERVIEW_JOBS.get(job_id)
        if existing and existing.get("status") == "complete":
            return job_id, dict(existing)
        if existing and existing.get("status") == "running":
            started_at = float(existing.get("started_at") or 0)
            if time.time() - started_at < OVERVIEW_JOB_STALE_SECONDS:
                return job_id, dict(existing)

        OVERVIEW_JOBS[job_id] = {
            "status": "running",
            "message": "Building overview cache on the server.",
            "from_date": start.isoformat(),
            "to_date": end.isoformat() if end else None,
            "wealthsimple_fx_fees": apply_fees,
            "started_at": time.time(),
            "completed_at": None,
        }

    threading.Thread(
        target=build_overview_job,
        args=(job_id, start, end, apply_fees),
        name=f"overview-job-{job_id}",
        daemon=True,
    ).start()
    with OVERVIEW_JOB_LOCK:
        return job_id, dict(OVERVIEW_JOBS[job_id])


def preload_job_response(job: dict[str, Any]) -> dict[str, Any]:
    response = {
        "status": job.get("status", "idle"),
        "message": job.get("message", ""),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "from_date": job.get("from_date"),
        "to_date": job.get("to_date"),
        "rows": job.get("rows", []),
    }
    if "detail" in job:
        response["detail"] = job["detail"]
    return response


def rebuild_preload_cache_job() -> None:
    try:
        start, end = configured_preload_window()
        with PRELOAD_JOB_LOCK:
            PRELOAD_JOB.update(
                {
                    "status": "running",
                    "message": f"Rebuilding preload cache for {start.isoformat()} to {end.isoformat()}.",
                    "from_date": start.isoformat(),
                    "to_date": end.isoformat(),
                }
            )
        rows = preload_dashboard_cache(
            start,
            end,
            include_fx=env_bool("PRELOAD_DASHBOARD_CACHE_INCLUDE_FX"),
            force=True,
        )
    except Exception as exc:
        with PRELOAD_JOB_LOCK:
            PRELOAD_JOB.update(
                {
                    "status": "error",
                    "message": "Preload cache rebuild failed.",
                    "detail": str(exc),
                    "completed_at": time.time(),
                }
            )
        return

    with PRELOAD_JOB_LOCK:
        PRELOAD_JOB.update(
            {
                "status": "complete",
                "message": "Preload cache rebuilt.",
                "rows": rows,
                "completed_at": time.time(),
            }
        )


def start_or_get_preload_rebuild() -> dict[str, Any]:
    with PRELOAD_JOB_LOCK:
        if PRELOAD_JOB.get("status") == "running":
            return dict(PRELOAD_JOB)
        PRELOAD_JOB.clear()
        PRELOAD_JOB.update(
            {
                "status": "running",
                "message": "Starting preload cache rebuild.",
                "started_at": time.time(),
                "completed_at": None,
                "rows": [],
            }
        )

    threading.Thread(
        target=rebuild_preload_cache_job,
        name="preload-cache-rebuild",
        daemon=True,
    ).start()
    with PRELOAD_JOB_LOCK:
        return dict(PRELOAD_JOB)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict[str, object]:
    preload_start, preload_end = configured_preload_preset_window()
    preload_includes_fees = env_bool("PRELOAD_DASHBOARD_CACHE_INCLUDE_FX")
    preload_cache_available = read_cache(
        "overview",
        preload_start,
        preload_end,
        preload_includes_fees,
    ) is not None
    preload_label_prefix = "Preloaded" if preload_cache_available else "Load preset"
    return {
        "default_from_date": DEFAULT_START.isoformat(),
        "default_to_date": latest_market_date().isoformat(),
        "history_from_date": HISTORY_START.isoformat(),
        "public_dashboard": PUBLIC_DASHBOARD,
        "preload_preset": {
            "label": f"{preload_label_prefix} {preload_start.isoformat()} to {preload_end.isoformat()}",
            "from_date": preload_start.isoformat(),
            "to_date": preload_end.isoformat(),
            "includes_wealthsimple_fx_fees": preload_includes_fees,
            "cache_available": preload_cache_available,
        },
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


@app.get("/api/paper-ledger-portfolios")
def paper_ledger_portfolios(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat() if end else None,
        "traders": paper_ledger_summaries(start, end, wealthsimple_fx_fees),
    }


@app.post("/api/overview-jobs")
def create_overview_job(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    job_id, job = start_or_get_overview_job(start, end, wealthsimple_fx_fees)
    return overview_job_response(job_id, job, include_payload=job.get("status") == "complete")


@app.get("/api/overview-jobs/{job_id}")
def get_overview_job(job_id: str) -> dict[str, object]:
    with OVERVIEW_JOB_LOCK:
        job = OVERVIEW_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="overview job not found")
        snapshot = dict(job)
    return overview_job_response(job_id, snapshot, include_payload=snapshot.get("status") == "complete")


@app.post("/api/preload-cache/rebuild")
def rebuild_preload_cache() -> dict[str, object]:
    job = start_or_get_preload_rebuild()
    return preload_job_response(job)


@app.get("/api/preload-cache/rebuild")
def get_preload_cache_rebuild() -> dict[str, object]:
    with PRELOAD_JOB_LOCK:
        snapshot = dict(PRELOAD_JOB)
    return preload_job_response(snapshot)


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


@app.post("/api/benchmarks")
def create_or_update_benchmark(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    ensure_private_write()
    try:
        return {"benchmark": upsert_benchmark(payload)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/baskets")
def baskets(include_archived: bool = Query(default=False)) -> dict[str, object]:
    return custom_basket_response(include_archived=include_archived)


@app.post("/api/baskets")
def create_or_update_basket(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    ensure_private_write()
    try:
        return {"basket": upsert_basket(payload)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/baskets/{basket_id}/members")
def create_or_update_basket_member(
    basket_id: str,
    payload: dict[str, object] = Body(...),
) -> dict[str, object]:
    ensure_private_write()
    try:
        return {"member": upsert_basket_member(basket_id, payload)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown basket: {basket_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/baskets/{basket_id}/performance")
def basket_detail(
    basket_id: str,
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    try:
        return basket_performance(basket_id, start, end)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown basket: {basket_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/wealth-intelligence")
def wealth_intelligence(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    overview_payload = cached_or_build_overview(start, end, wealthsimple_fx_fees)
    baskets_payload = custom_basket_response(include_archived=False)
    return wealth_intelligence_response(overview_payload, baskets_payload, start, end)


@app.get("/api/wealth-operations")
def wealth_operations(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    resolved_end = end or latest_market_date()
    overview_payload = cached_or_build_overview(start, resolved_end, wealthsimple_fx_fees)
    baskets_payload = custom_basket_response(include_archived=False)
    wealth_payload = wealth_intelligence_response(overview_payload, baskets_payload, start, resolved_end)
    return wealth_operations_response(wealth_payload, start, resolved_end)


@app.get("/api/external-portfolios")
def external_portfolios() -> dict[str, object]:
    try:
        return external_portfolio_response()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/model-portfolio")
def model_portfolio(
    to_date: str | None = Query(default=None),
) -> dict[str, object]:
    try:
        end = parse_date(to_date) if to_date else latest_market_date()
        return systematic_model_portfolio_response(end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/day-rotation-portfolio")
def day_rotation_portfolio(
    to_date: str | None = Query(default=None),
) -> dict[str, object]:
    try:
        end = parse_date(to_date) if to_date else latest_market_date()
        return daily_rotation_portfolio_response(end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def strategy_selector_candidates(start: date, end: date, wealthsimple_fx_fees: bool) -> tuple[list[dict[str, object]], list[str]]:
    candidates: list[dict[str, object]] = []
    warnings: list[str] = []
    for strategy_id, builder in [
        ("systematic-model-portfolio", lambda: systematic_model_portfolio_response(end)),
        ("daily-eod-rotation-portfolio", lambda: daily_rotation_portfolio_response(end)),
    ]:
        try:
            detail = builder()
            detail["label"] = strategy_id.replace("-", " ").title()
            candidates.append(detail)
        except ValueError as exc:
            warnings.append(f"{strategy_id}: {exc}")
    for strategy_id in [
        "watchlist-variable-news-optimized-experimental",
        "master-portfolio",
        "insta_watchlist",
        "social_media_signal",
        "model-portfolio",
    ]:
        try:
            detail = trader_detail(strategy_id, start, end, wealthsimple_fx_fees)
            detail["label"] = strategy_id.replace("-", " ").replace("_", " ").title()
            candidates.append(detail)
        except KeyError:
            warnings.append(f"{strategy_id}: not present in tracked paper ledgers for this window.")
        except ValueError as exc:
            warnings.append(f"{strategy_id}: {exc}")
    return candidates, warnings


@app.get("/api/wealth/strategy-selector")
def wealth_strategy_selector(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    resolved_end = end or latest_market_date()
    candidates, warnings = strategy_selector_candidates(start, resolved_end, wealthsimple_fx_fees)
    payload = strategy_selector_response(start, resolved_end, candidates, apply_wealthsimple_fx_fees=wealthsimple_fx_fees)
    payload["warnings"] = sorted(set([*payload.get("warnings", []), *warnings]))
    return payload


@app.get("/api/wealth/risk")
def wealth_risk(
    portfolio: str = Query(..., min_length=1),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    resolved_end = end or latest_market_date()
    try:
        detail = wealth_portfolio_detail(portfolio, start, resolved_end, wealthsimple_fx_fees)
        return portfolio_risk_response(detail, start, resolved_end)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown portfolio: {portfolio}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def wealth_portfolio_detail(
    portfolio: str,
    start: date,
    end: date,
    wealthsimple_fx_fees: bool,
) -> dict[str, object]:
    if portfolio == "systematic-model-portfolio":
        return systematic_model_portfolio_response(end)
    if portfolio == "daily-eod-rotation-portfolio":
        return daily_rotation_portfolio_response(end)
    return trader_detail(portfolio, start, end, wealthsimple_fx_fees)


def detail_with_instrument_metadata(detail: dict[str, object]) -> dict[str, object]:
    positions = detail.get("positions")
    if not isinstance(positions, list):
        return detail
    indexed = metadata_index(read_asset_universe())
    hydrated: list[dict[str, object]] = []
    for raw_position in positions:
        if not isinstance(raw_position, dict):
            continue
        position = dict(raw_position)
        ticker = str(position.get("ticker") or "").strip().upper()
        asset_type = str(position.get("security_type") or position.get("asset_type") or "").strip().casefold()
        meta = indexed.get((ticker, asset_type)) or indexed.get((ticker, "")) or {}
        resolved = resolved_instrument_metadata(ticker, asset_type, position, meta)
        position["asset_type"] = resolved["asset_type"]
        position["sector"] = resolved["sector"]
        position["currency"] = resolved["currency"]
        hydrated.append(position)
    return {**detail, "positions": hydrated}


@app.get("/api/wealth/performance")
def wealth_performance(
    portfolio: str = Query(..., min_length=1),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    resolved_end = end or latest_market_date()
    try:
        detail = wealth_portfolio_detail(portfolio, start, resolved_end, wealthsimple_fx_fees)
        return portfolio_performance_response(detail, start, resolved_end)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown portfolio: {portfolio}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/wealth/correlation")
def wealth_correlation(
    portfolio: str = Query(..., min_length=1),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    resolved_end = end or latest_market_date()
    try:
        detail = wealth_portfolio_detail(portfolio, start, resolved_end, wealthsimple_fx_fees)
        return correlation_response(detail, start, resolved_end)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown portfolio: {portfolio}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/wealth/scenarios")
def wealth_scenarios(
    portfolio: str = Query(..., min_length=1),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    resolved_end = end or latest_market_date()
    try:
        detail = wealth_portfolio_detail(portfolio, start, resolved_end, wealthsimple_fx_fees)
        detail = detail_with_instrument_metadata(detail)
        return scenario_response(detail)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown portfolio: {portfolio}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/wealth/allocation")
def wealth_allocation(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    resolved_end = end or latest_market_date()
    overview_payload = cached_or_build_overview(start, resolved_end, wealthsimple_fx_fees)
    return wealth_allocation_response(
        start,
        resolved_end,
        wealthsimple_fx_fees,
        overview_payload=overview_payload,
    )


@app.get("/api/wealth/rebalance/profiles")
def wealth_rebalance_profiles() -> dict[str, object]:
    return rebalance_profiles_response()


@app.post("/api/wealth/rebalance/preview")
def wealth_rebalance_preview(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    try:
        return rebalance_preview(
            str(payload.get("profile_id") or ""),
            list(payload.get("current_allocations") or []),
            Decimal(str(payload.get("portfolio_value") or 0)),
            exact_target=bool(payload.get("exact_target", False)),
        )
    except (ValueError, InvalidOperation) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/strategies")
def strategies(include_retired: bool = Query(default=False)) -> dict[str, object]:
    return strategy_registry_response(include_retired=include_retired)


@app.post("/api/strategies")
def create_or_update_strategy(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    ensure_private_write()
    try:
        return {"strategy": upsert_strategy(payload)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/strategies/{strategy_id}/preview")
def strategy_preview(
    strategy_id: str,
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    strategy = next(
        (
            row
            for row in read_strategies(include_retired=True)
            if str(row["strategy_id"]) == strategy_id.casefold()
        ),
        None,
    )
    if not strategy:
        raise HTTPException(status_code=404, detail=f"unknown strategy: {strategy_id}")
    try:
        return saved_strategy_preview_detail(strategy, start, end, wealthsimple_fx_fees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/research")
def research_index() -> dict[str, object]:
    return research_index_response()


@app.get("/api/research/{slug}")
def research_note(slug: str) -> dict[str, object]:
    try:
        return research_note_response(slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown research note: {slug}") from exc


@app.get("/api/strategy-lab/run")
def run_strategy_lab(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    wealthsimple_fx_fees: bool = Query(default=False),
    entry_signal_rule: str = Query(default="any"),
    entry_news_rule: str = Query(default="ignore"),
    exit_rule: str = Query(default="signal-disappears"),
    universe: str = Query(default="tracked-stocks"),
) -> dict[str, object]:
    start, end = window(from_date, to_date)
    try:
        return strategy_lab_detail(
            start,
            end,
            entry_signal_rule=entry_signal_rule,
            entry_news_rule=entry_news_rule,
            exit_rule=exit_rule,
            universe=universe,
            apply_wealthsimple_fx_fees=wealthsimple_fx_fees,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    return FileResponse(
        FRONTEND / "index.html",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
