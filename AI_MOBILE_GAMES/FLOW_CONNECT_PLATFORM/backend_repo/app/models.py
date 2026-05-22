from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GridPoint(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class DotPair(BaseModel):
    color: str
    start: GridPoint
    end: GridPoint


class Level(BaseModel):
    id: str
    pack_id: str = "starter"
    title: str
    grid_size: int = Field(ge=2, le=12)
    difficulty: Literal["easy", "medium", "hard", "expert"] = "easy"
    dot_pairs: list[DotPair]


class CompletedLevel(BaseModel):
    level_id: str
    completed_at: datetime
    moves: int | None = Field(default=None, ge=0)
    seconds: int | None = Field(default=None, ge=0)


class PlayerProgress(BaseModel):
    player_id: str
    completed_levels: list[CompletedLevel] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsEvent(BaseModel):
    name: str
    player_id: str | None = None
    level_id: str | None = None
    properties: dict[str, str | int | float | bool] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

