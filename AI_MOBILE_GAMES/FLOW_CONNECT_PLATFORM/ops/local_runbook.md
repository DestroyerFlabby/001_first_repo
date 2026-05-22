# Local Runbook

## Backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn AI_MOBILE_GAMES.FLOW_CONNECT_PLATFORM.backend_repo.app.main:app --reload
```

## Godot Client

Open this folder in Godot:

```text
AI_MOBILE_GAMES/FLOW_CONNECT_MVP
```

## Voice-to-Codex Workflow

1. Run the offline transcriber.
2. Speak the next instruction.
3. Tell Codex: `next file is updated`.
4. Codex reads `LOCAL_VOICE_ASSISTANT/offline_transcripts/latest.md` and acts.

