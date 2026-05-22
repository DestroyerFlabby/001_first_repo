from __future__ import annotations

import json
import msvcrt
import queue
import time
import wave
from datetime import datetime
from pathlib import Path

import sounddevice as sd
from vosk import KaldiRecognizer, Model


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "LOCAL_VOICE_ASSISTANT"
MODEL_DIR = APP_DIR / "models" / "vosk-model-small-en-us-0.15"
TRANSCRIPTS_DIR = APP_DIR / "offline_transcripts"
INBOX_DIR = TRANSCRIPTS_DIR / "inbox"
AUDIO_DIR = TRANSCRIPTS_DIR / "audio"
LATEST_PATH = TRANSCRIPTS_DIR / "latest.md"
SAMPLE_RATE = 16000
CHANNELS = 1


def wait_for_space_or_quit(prompt: str) -> bool:
    print(prompt, end="", flush=True)
    while True:
        char = msvcrt.getwch()
        if char.lower() == "q":
            print()
            return False
        if char == " ":
            print()
            return True


def capture_audio(audio_path: Path) -> None:
    audio_queue: queue.Queue[bytes] = queue.Queue()
    stop_requested = False

    def callback(indata, frames, time_info, status):  # noqa: ANN001
        if status:
            print(f"Audio warning: {status}")
        audio_queue.put(bytes(indata))

    print("Recording. Press Space to stop.", flush=True)
    with wave.open(str(audio_path), "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            callback=callback,
        ):
            while not stop_requested:
                if msvcrt.kbhit() and msvcrt.getwch() == " ":
                    stop_requested = True
                while not audio_queue.empty():
                    wav_file.writeframes(audio_queue.get())
                time.sleep(0.02)

            time.sleep(0.15)
            while not audio_queue.empty():
                wav_file.writeframes(audio_queue.get())


def transcribe_audio(model: Model, audio_path: Path) -> str:
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    chunks: list[str] = []

    with wave.open(str(audio_path), "rb") as wav_file:
        while True:
            data = wav_file.readframes(4000)
            if not data:
                break
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    chunks.append(text)

    final = json.loads(recognizer.FinalResult()).get("text", "").strip()
    if final:
        chunks.append(final)

    return " ".join(chunks).strip()


def write_transcript(transcript_path: Path, audio_path: Path, text: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = (
        f"# Voice Transcript\n\n"
        f"- Created: {timestamp}\n"
        f"- Audio: `{audio_path.relative_to(ROOT)}`\n\n"
        f"## Transcription\n\n"
        f"{text or '[No speech detected]'}\n"
    )
    transcript_path.write_text(content, encoding="utf-8")
    LATEST_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    if not MODEL_DIR.exists():
        raise SystemExit(
            "Missing offline speech model. Run:\n"
            ".\\.venv\\Scripts\\python.exe LOCAL_VOICE_ASSISTANT\\download_vosk_model.py"
        )

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading offline speech model...")
    model = Model(str(MODEL_DIR))

    print("Offline Transcriber")
    print("Press Space to start recording. Press Space again to stop. Press q at start prompt to quit.")
    print(f"Transcript inbox: {INBOX_DIR}")

    while True:
        if not wait_for_space_or_quit("\nReady. Press Space to record, or q to quit: "):
            break

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        audio_path = AUDIO_DIR / f"voice-{stamp}.wav"
        transcript_path = INBOX_DIR / f"voice-{stamp}.md"

        try:
            capture_audio(audio_path)
        except sd.PortAudioError as exc:
            print(f"Microphone error: {exc}")
            continue

        text = transcribe_audio(model, audio_path)
        write_transcript(transcript_path, audio_path, text)

        print(f"Saved: {transcript_path}")
        print(f"Text: {text or '[No speech detected]'}")


if __name__ == "__main__":
    main()
