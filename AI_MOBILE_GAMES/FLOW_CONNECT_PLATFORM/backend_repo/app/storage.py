from __future__ import annotations

import json
from pathlib import Path

from .models import AnalyticsEvent, Level, PlayerProgress


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LEVELS_PATH = DATA_DIR / "levels.json"
PROGRESS_PATH = DATA_DIR / "player_progress.json"
EVENTS_PATH = DATA_DIR / "events.jsonl"


class JsonStorage:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def list_levels(self) -> list[Level]:
        raw_levels = json.loads(LEVELS_PATH.read_text(encoding="utf-8"))
        return [Level.model_validate(level) for level in raw_levels]

    def get_level(self, level_id: str) -> Level | None:
        for level in self.list_levels():
            if level.id == level_id:
                return level
        return None

    def save_progress(self, progress: PlayerProgress) -> None:
        existing: dict[str, dict] = {}
        if PROGRESS_PATH.exists():
            existing = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        existing[progress.player_id] = progress.model_dump(mode="json")
        PROGRESS_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def append_event(self, event: AnalyticsEvent) -> None:
        with EVENTS_PATH.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event.model_dump(mode="json")) + "\n")

