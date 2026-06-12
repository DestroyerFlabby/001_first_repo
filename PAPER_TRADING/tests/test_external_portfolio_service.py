from __future__ import annotations

import csv
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.external_portfolio_service import (  # noqa: E402
    SNAPSHOT_FIELDS,
    external_portfolio_response,
    validate_snapshot,
)


def write_snapshot(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SNAPSHOT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_external_registry_tracks_model_and_social_portfolios() -> None:
    response = external_portfolio_response()
    portfolios = {row["portfolio_id"]: row for row in response["portfolios"]}

    assert set(portfolios) >= {"model-portfolio", "social-media-signal"}
    assert portfolios["model-portfolio"]["effective_status"] == "awaiting_source"
    assert portfolios["model-portfolio"]["source_status"]["position_count"] == 0
    assert portfolios["social-media-signal"]["effective_status"] == "active"
    assert portfolios["social-media-signal"]["source_status"]["position_count"] == 10
    assert response["snapshot_contract"] == SNAPSHOT_FIELDS


def test_snapshot_validation_accepts_balanced_latest_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "portfolio.csv"
    write_snapshot(
        snapshot,
        [
            {
                "snapshot_date": "2026-06-12",
                "ticker": "spy",
                "asset_type": "etf",
                "target_weight": "60",
                "signal_date": "2026-06-11",
                "source": "model-v1",
                "confidence": "0.8",
                "thesis": "Core allocation",
                "status": "active",
            },
            {
                "snapshot_date": "2026-06-12",
                "ticker": "QQQ",
                "asset_type": "etf",
                "target_weight": "40",
                "signal_date": "2026-06-11",
                "source": "model-v1",
                "confidence": "0.7",
                "thesis": "Growth allocation",
                "status": "active",
            },
        ],
    )

    result = validate_snapshot(snapshot)

    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["latest_snapshot_date"] == "2026-06-12"
    assert result["latest_weight_pct"] == 100.0
    assert result["latest_rows"][0]["ticker"] == "SPY"


def test_snapshot_validation_flags_duplicates_and_weight_drift(tmp_path: Path) -> None:
    snapshot = tmp_path / "portfolio.csv"
    row = {
        "snapshot_date": "2026-06-12",
        "ticker": "NVDA",
        "asset_type": "stock",
        "target_weight": "30",
        "signal_date": "2026-06-11",
        "source": "model-v1",
        "confidence": "0.9",
        "thesis": "AI exposure",
        "status": "active",
    }
    write_snapshot(snapshot, [row, row])

    result = validate_snapshot(snapshot)

    assert any("duplicate tickers" in error for error in result["errors"])
    assert any("instead of 100%" in warning for warning in result["warnings"])
