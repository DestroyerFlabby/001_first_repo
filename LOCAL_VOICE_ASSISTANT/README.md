# Local Voice Assistant

Push-to-talk voice chat loop for this repository.

It records your microphone, transcribes your speech with OpenAI speech-to-text, sends the text to an OpenAI model, speaks the answer back with text-to-speech, and saves a Markdown transcript.

This is a local voice assistant, not a direct voice bridge into the live Codex chat. It can talk through ideas and save transcripts you can paste back into Codex.

## Setup

1. Install dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r LOCAL_VOICE_ASSISTANT/requirements.txt
   ```

2. Create or update `.env` at the repo root:

   ```env
   OPENAI_API_KEY=your_api_key_here
   VOICE_CHAT_MODEL=gpt-4o-mini
   VOICE_CHAT_TRANSCRIBE_MODEL=gpt-4o-mini-transcribe
   VOICE_CHAT_TTS_MODEL=gpt-4o-mini-tts
   VOICE_CHAT_VOICE=alloy
   ```

3. Run:

   ```powershell
   python LOCAL_VOICE_ASSISTANT/voice_chat.py
   ```

## Controls

- Press `Enter` to start recording.
- Press `Enter` again to stop recording.
- Type `q` and press `Enter` at the prompt to quit.

The spoken voice is AI-generated.
