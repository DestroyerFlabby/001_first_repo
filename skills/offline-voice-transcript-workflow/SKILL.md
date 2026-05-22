---
name: offline-voice-transcript-workflow
description: Use a local offline voice transcription inbox to receive spoken user instructions without calling the OpenAI API. Use when Codex is asked to read the latest voice transcript, continue from a newly updated transcript file, operate a push-to-talk offline speech workflow, or document how agents should use LOCAL_VOICE_ASSISTANT/offline_transcripts/latest.md as a voice-to-Codex bridge.
---

# Offline Voice Transcript Workflow

## Purpose

Use this workflow when the user speaks instructions into the local offline transcriber and asks Codex to continue from the newest transcript.

The workflow does not call the OpenAI API for transcription. It uses:

- `LOCAL_VOICE_ASSISTANT/offline_transcriber.py`
- `LOCAL_VOICE_ASSISTANT/download_vosk_model.py`
- `LOCAL_VOICE_ASSISTANT/offline_requirements.txt`
- `LOCAL_VOICE_ASSISTANT/offline_transcripts/latest.md`
- `LOCAL_VOICE_ASSISTANT/offline_transcripts/inbox/`

## Setup

Install local transcription dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r LOCAL_VOICE_ASSISTANT\offline_requirements.txt
```

Download the offline Vosk speech model:

```powershell
.\.venv\Scripts\python.exe LOCAL_VOICE_ASSISTANT\download_vosk_model.py
```

## Running The Transcriber

Start the local offline recorder:

```powershell
.\.venv\Scripts\python.exe LOCAL_VOICE_ASSISTANT\offline_transcriber.py
```

Controls:

- Press `Space` to start recording.
- Press `Space` again to stop recording.
- Press `q` at the start prompt to quit.

## Reading Instructions

When the user says a phrase like `next file is updated`, `read the latest voice transcript`, or `continue from my voice note`:

1. Read `LOCAL_VOICE_ASSISTANT/offline_transcripts/latest.md`.
2. Extract only the text under `## Transcription`.
3. Treat the transcription as the user's latest instruction.
4. If the transcription is ambiguous or obviously misrecognized, state the likely interpretation and make a conservative implementation.
5. If acting would be destructive or high-risk, ask for confirmation.
6. Mention in the final response that the instruction came from the latest offline transcript.

## Agent Constraints

Codex cannot silently monitor a file forever after a turn ends. Use a turn-based workflow:

1. User speaks into the offline transcriber.
2. User sends a short chat message such as `next file is updated`.
3. Codex reads `latest.md`.
4. Codex acts on the transcript.

Do not assume the latest transcript is new unless the user indicates it was updated or asks Codex to read it.

