from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .models import AnalyticsEvent, Level, PlayerProgress
from .storage import JsonStorage


app = FastAPI(title="Flow Connect Backend", version="0.1.0")
storage = JsonStorage()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/levels", response_model=list[Level])
def list_levels() -> list[Level]:
    return storage.list_levels()


@app.get("/levels/{level_id}", response_model=Level)
def get_level(level_id: str) -> Level:
    level = storage.get_level(level_id)
    if level is None:
        raise HTTPException(status_code=404, detail="Level not found")
    return level


@app.put("/players/{player_id}/progress", response_model=PlayerProgress)
def save_progress(player_id: str, progress: PlayerProgress) -> PlayerProgress:
    if progress.player_id != player_id:
        raise HTTPException(status_code=400, detail="player_id mismatch")
    storage.save_progress(progress)
    return progress


@app.post("/events")
def ingest_event(event: AnalyticsEvent) -> dict[str, str]:
    storage.append_event(event)
    return {"status": "accepted"}

