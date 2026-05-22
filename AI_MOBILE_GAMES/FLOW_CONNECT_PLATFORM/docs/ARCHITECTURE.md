# Architecture

## Frontend

The current playable frontend is the Godot project:

```text
AI_MOBILE_GAMES/FLOW_CONNECT_MVP
```

The frontend should treat backend level data as the source of truth once integration begins.

## Backend

The backend is a FastAPI service that provides:

- Health checks.
- Level catalog.
- Single-level lookup.
- Player progress upsert.
- Lightweight telemetry ingestion.

The first implementation uses local JSON files so the backend can run without a database. Move to SQLite/Postgres when accounts, sync, or production analytics become necessary.

## Shared Contracts

Keep JSON examples and API contract notes in `shared/` so the Godot frontend and backend stay aligned.

