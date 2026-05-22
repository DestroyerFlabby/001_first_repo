# Flow Connect Frontend

The active playable client is currently the Godot project:

```text
AI_MOBILE_GAMES/FLOW_CONNECT_MVP
```

This folder is for frontend production planning, integration notes, and future client-specific files.

## Near-Term Frontend Work

- Load levels from the backend API.
- Add touch-first mobile controls.
- Add level select.
- Add progress persistence.
- Add reset and undo buttons.
- Add portrait safe-area layout.
- Add export presets for Android and iOS.

## Backend Integration Contract

Use:

```text
GET /levels
GET /levels/{level_id}
PUT /players/{player_id}/progress
POST /events
```

See `../shared/api_contract.md`.

