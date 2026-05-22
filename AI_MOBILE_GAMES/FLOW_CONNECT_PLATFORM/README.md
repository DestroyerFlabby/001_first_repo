# Flow Connect Platform

Production workspace for turning the existing `FLOW_CONNECT_MVP` Godot prototype into a mobile game with a backend, frontend, content pipeline, and AI-assisted iteration workflow.

## Repositories

- `backend_repo/` - FastAPI backend for levels, player progress, telemetry, and future live operations.
- `frontend_repo/` - Mobile client planning and integration notes. The current playable frontend is the Godot project at `../FLOW_CONNECT_MVP`.
- `docs/` - Product, architecture, and production notes.
- `shared/` - Cross-app schemas and contracts.
- `ops/` - Local runbooks and deployment notes.

## Current Game Assumption

The current game appears to be a Flow Connect style puzzle game:

- Grid-based board.
- Colored dot pairs.
- Player drags paths to connect matching dots.
- Paths cannot cross.
- A level is complete when all pairs are connected and the board is filled.

If this is not the intended game, update `docs/GAME_CONCEPT.md` first.

## Local Backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn AI_MOBILE_GAMES.FLOW_CONNECT_PLATFORM.backend_repo.app.main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```
