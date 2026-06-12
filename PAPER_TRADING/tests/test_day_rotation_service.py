from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.day_rotation_service import (
    ROTATION_MAX_NAME_WEIGHT,
    ROTATION_MAX_NAMES_PER_SECTOR,
    ROTATION_MAX_POSITIONS,
    ROTATION_MAX_SECTOR_WEIGHT,
    _rotation_score,
    _rotation_weights,
    _select_rotation_candidates,
)


def candidate(ticker: str, sector: str, score: int) -> dict[str, object]:
    return {"ticker": ticker, "sector": sector, "rotation_score": Decimal(score)}


def signal(*, overall: int = 60, three_day: int = 4, relative: int = 5, volume: float = 1.5) -> dict[str, object]:
    return {
        "overall_score": overall,
        "horizons": {
            "3d": {"return_pct": three_day},
            "5d": {"relative_strength_pct": relative, "volume_ratio": volume},
            "1m": {"return_pct": 12},
        },
    }


def test_rotation_selection_limits_positions_and_sector_names() -> None:
    rows = [candidate(f"TECH{index}", "Technology", 200 - index) for index in range(8)]
    rows += [candidate(f"OTHER{index}", f"Sector {index}", 150 - index) for index in range(12)]
    selected = _select_rotation_candidates(rows)
    assert len(selected) == ROTATION_MAX_POSITIONS
    assert sum(row["sector"] == "Technology" for row in selected) <= ROTATION_MAX_NAMES_PER_SECTOR


def test_rotation_weights_respect_name_and_sector_caps() -> None:
    rows = [candidate(f"TECH{index}", "Technology", 200 - index) for index in range(3)]
    rows += [candidate(f"OTHER{index}", f"Sector {index}", 150 - index) for index in range(7)]
    weights = _rotation_weights(rows)
    assert sum(weights.values()) <= Decimal("0.95")
    assert max(weights.values()) <= ROTATION_MAX_NAME_WEIGHT
    technology_weight = sum(weights[row["ticker"]] for row in rows if row["sector"] == "Technology")
    assert technology_weight <= ROTATION_MAX_SECTOR_WEIGHT


def test_fresh_volume_and_news_raise_rotation_score() -> None:
    quiet_news = {"articles_7d": 0, "articles_prior_7d": 0}
    active_news = {"articles_7d": 4, "articles_prior_7d": 1}
    quiet, _ = _rotation_score(signal(volume=1.0), "strict", quiet_news, Decimal("40"))
    active, components = _rotation_score(signal(volume=2.0), "fresh", active_news, Decimal("40"))
    assert active > quiet
    assert components["category_bonus"] == 30
    assert components["news_bonus"] == 16


def test_overextended_high_volatility_candidate_is_penalized() -> None:
    normal, _ = _rotation_score(signal(three_day=8), "fresh", {"articles_7d": 0, "articles_prior_7d": 0}, Decimal("40"))
    stretched_signal = signal(three_day=30)
    stretched_signal["horizons"]["1m"]["return_pct"] = 100
    stretched, components = _rotation_score(
        stretched_signal,
        "fresh",
        {"articles_7d": 0, "articles_prior_7d": 0},
        Decimal("120"),
    )
    assert components["overextension_penalty"] == 24
    assert components["volatility_penalty"] > 0
    assert stretched < normal
