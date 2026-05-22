# Flow Connect Backend

FastAPI backend for the Flow Connect mobile game.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn AI_MOBILE_GAMES.FLOW_CONNECT_PLATFORM.backend_repo.app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

- `GET /health`
- `GET /levels`
- `GET /levels/{level_id}`
- `PUT /players/{player_id}/progress`
- `POST /events`

