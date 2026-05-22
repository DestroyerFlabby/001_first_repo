from __future__ import annotations

import os
import queue
import tempfile
import textwrap
import wave
import winsound
from datetime import datetime
from pathlib import Path

import sounddevice as sd
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS_DIR = ROOT / "LOCAL_VOICE_ASSISTANT" / "transcripts"
SAMPLE_RATE = int(os.getenv("VOICE_CHAT_SAMPLE_RATE", "16000"))
CHANNELS = 1


SYSTEM_PROMPT = """You are a practical coding and business planning assistant.
Keep answers concise and actionable. When the user is brainstorming, help clarify
next steps. When the user asks about this repository, remind them to paste or
save details into the repo if file-level work is needed."""


def record_until_enter(output_path: Path) -> None:
    audio_queue: queue.Queue[bytes] = queue.Queue()

    def callback(indata, frames, time_info, status):  # noqa: ANN001
        if status:
            print(f"Audio warning: {status}")
        audio_queue.put(bytes(indata))

    print("Recording. Press Enter to stop.")
    try:
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(2)
            wav_file.setframerate(SAMPLE_RATE)

            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                callback=callback,
            ):
                input()
                while not audio_queue.empty():
                    wav_file.writeframes(audio_queue.get())
    except sd.PortAudioError as exc:
        raise RuntimeError(
            "Could not open the microphone. Check Windows microphone permissions "
            "and that an input device is connected."
        ) from exc


def transcribe(client: OpenAI, audio_path: Path) -> str:
    model = os.getenv("VOICE_CHAT_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
    with audio_path.open("rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format="text",
        )
    return str(result).strip()


def ask_model(client: OpenAI, messages: list[dict[str, str]]) -> str:
    model = os.getenv("VOICE_CHAT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    response = client.responses.create(
        model=model,
        input=messages,
    )
    return response.output_text.strip()


def speak(client: OpenAI, text: str) -> None:
    model = os.getenv("VOICE_CHAT_TTS_MODEL", "gpt-4o-mini-tts")
    voice = os.getenv("VOICE_CHAT_VOICE", "alloy")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_path = Path(temp_audio.name)

    try:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format="wav",
        )
        response.write_to_file(temp_path)
        winsound.PlaySound(str(temp_path), winsound.SND_FILENAME)
    finally:
        temp_path.unlink(missing_ok=True)


def append_transcript(path: Path, speaker: str, text: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as file:
        file.write(f"\n## {speaker} - {timestamp}\n\n{text.strip()}\n")


def explain_openai_quota_error(exc: RateLimitError) -> str:
    message = str(exc)
    if "insufficient_quota" in message:
        return (
            "OpenAI rejected the request because this API key has insufficient quota. "
            "Check billing/credits for the OpenAI Platform account tied to this key, "
            "then run the assistant again."
        )
    return f"OpenAI rate limit or quota error: {exc}"


def main() -> None:
    env_path = ROOT / ".env"
    load_dotenv(env_path)

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "Set OPENAI_API_KEY in .env or your shell environment first. "
            f"Expected .env at: {env_path}"
        )

    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    transcript_path = TRANSCRIPTS_DIR / datetime.now().strftime("voice-chat-%Y%m%d-%H%M%S.md")
    client = OpenAI()
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("Local Voice Assistant")
    print("This uses an AI-generated voice. Press Enter to record, or type q then Enter to quit.")
    print(f"Transcript: {transcript_path}")

    while True:
        try:
            command = input("\nReady> ").strip().lower()
        except EOFError:
            print("No interactive terminal input was available. Run this from PowerShell.")
            break

        if command in {"q", "quit", "exit"}:
            break

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            audio_path = Path(temp_audio.name)

        try:
            try:
                record_until_enter(audio_path)
            except EOFError:
                print("Recording stopped because terminal input was unavailable.")
                break
            user_text = transcribe(client, audio_path)
        except RateLimitError as exc:
            print(f"Error: {explain_openai_quota_error(exc)}")
            break
        except Exception as exc:
            print(f"Error: {exc}")
            continue
        finally:
            audio_path.unlink(missing_ok=True)

        if not user_text:
            print("No speech detected.")
            continue

        print(f"\nYou: {user_text}")
        append_transcript(transcript_path, "You", user_text)
        messages.append({"role": "user", "content": user_text})

        try:
            answer = ask_model(client, messages)
        except RateLimitError as exc:
            print(f"Error: {explain_openai_quota_error(exc)}")
            break
        messages.append({"role": "assistant", "content": answer})

        wrapped = textwrap.fill(answer, width=88)
        print(f"\nAssistant: {wrapped}")
        append_transcript(transcript_path, "Assistant", answer)
        try:
            speak(client, answer)
        except RateLimitError as exc:
            print(f"Error: {explain_openai_quota_error(exc)}")
            break


if __name__ == "__main__":
    main()
