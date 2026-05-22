# Offline Transcription Inbox

This tool records your microphone locally, transcribes with a local Vosk speech model, and writes Markdown files into an inbox.

It does not call the OpenAI API.

## Setup

Install offline dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r LOCAL_VOICE_ASSISTANT\offline_requirements.txt
```

Download the local speech model:

```powershell
.\.venv\Scripts\python.exe LOCAL_VOICE_ASSISTANT\download_vosk_model.py
```

## Run

```powershell
.\.venv\Scripts\python.exe LOCAL_VOICE_ASSISTANT\offline_transcriber.py
```

Controls:

- Press `Space` to start recording.
- Press `Space` again to stop.
- Press `q` at the start prompt to quit.

Markdown transcripts are saved to:

```text
LOCAL_VOICE_ASSISTANT/offline_transcripts/inbox/
```

The newest transcript is also copied to:

```text
LOCAL_VOICE_ASSISTANT/offline_transcripts/latest.md
```

## Codex Workflow

Codex cannot silently monitor files forever after a chat turn ends. The practical workflow is:

1. Keep `offline_transcriber.py` running in a terminal.
2. Speak your instruction.
3. Ask Codex: `read the latest voice transcript and do it`.
4. Codex reads `LOCAL_VOICE_ASSISTANT/offline_transcripts/latest.md` and acts on it.

