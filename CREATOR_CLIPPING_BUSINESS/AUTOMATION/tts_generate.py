from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BUSINESS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUSINESS_ROOT.parent
PIPELINE_ROOT = BUSINESS_ROOT / "PIPELINE_ZONES"
INTERMEDIATE_DIR = PIPELINE_ROOT / "02_INTERMEDIATE"
SCRIPTS_DIR = INTERMEDIATE_DIR / "SCRIPTS"
VOICEOVER_DIR = INTERMEDIATE_DIR / "VOICEOVER"

DEFAULT_ELEVENLABS_VOICE_NAME = "Adam"
DEFAULT_ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"
DEFAULT_ELEVENLABS_MODEL = "eleven_multilingual_v2"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_script_files(scripts_dir: Path = SCRIPTS_DIR) -> list[Path]:
    if not scripts_dir.exists():
        return []
    return sorted(scripts_dir.rglob("script.txt"))


def script_topic(script_path: Path) -> str:
    try:
        relative = script_path.relative_to(SCRIPTS_DIR)
    except ValueError:
        return script_path.parent.name or "general"
    return relative.parts[0] if relative.parts else "general"


def placeholder_instructions(script_text: str, provider: str, reason: str) -> str:
    return f"""# Manual Voiceover Placeholder

Provider requested: {provider}
Reason: {reason}

Manual steps:

1. Open your preferred TTS tool.
2. Paste the script below.
3. Generate an MP3 voiceover.
4. Save it as `voiceover.mp3` in this same folder.
5. Rerun the edit stage.

Script:

{script_text.strip()}
"""


def create_placeholder(topic_dir: Path, script_text: str, provider: str, reason: str, voice_used: str) -> dict:
    placeholder_path = topic_dir / "voiceover_placeholder.txt"
    write_text(placeholder_path, placeholder_instructions(script_text, provider, reason))

    metadata = {
        "provider": provider,
        "status": "placeholder",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration": None,
        "voice_used": voice_used,
        "output_file": None,
        "placeholder_file": str(placeholder_path.relative_to(BUSINESS_ROOT)),
        "reason": reason,
    }
    write_json(topic_dir / "metadata.json", metadata)
    return metadata


def generate_with_elevenlabs(script_text: str, output_path: Path, api_key: str, voice_id: str) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": script_text,
        "model_id": os.getenv("ELEVENLABS_MODEL", DEFAULT_ELEVENLABS_MODEL),
        "voice_settings": {
            "stability": float(os.getenv("ELEVENLABS_STABILITY", "0.5")),
            "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.75")),
        },
    }
    response = requests.post(
        url,
        headers={
            "xi-api-key": api_key,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)


def generate_voiceover_for_script(script_path: Path, provider: str) -> dict:
    script_text = script_path.read_text(encoding="utf-8").strip()
    topic = script_topic(script_path)
    topic_dir = VOICEOVER_DIR / topic
    output_path = topic_dir / "voiceover.mp3"

    voice_name = os.getenv("TTS_VOICE", DEFAULT_ELEVENLABS_VOICE_NAME)
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_ELEVENLABS_VOICE_ID)

    if not script_text:
        return create_placeholder(topic_dir, "", provider, "script.txt is empty", voice_name)

    if provider == "stub":
        return create_placeholder(topic_dir, script_text, provider, "TTS_PROVIDER is set to stub", voice_name)

    if provider != "elevenlabs":
        return create_placeholder(topic_dir, script_text, provider, "unsupported TTS_PROVIDER", voice_name)

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        return create_placeholder(topic_dir, script_text, provider, "ELEVENLABS_API_KEY is not set", voice_name)

    try:
        generate_with_elevenlabs(script_text, output_path, api_key, voice_id)
    except requests.RequestException as exc:
        return create_placeholder(topic_dir, script_text, provider, f"ElevenLabs request failed: {exc}", voice_name)

    metadata = {
        "provider": "elevenlabs",
        "status": "generated",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration": None,
        "voice_used": voice_name,
        "voice_id": voice_id,
        "output_file": str(output_path.relative_to(BUSINESS_ROOT)),
        "source_script": str(script_path.relative_to(BUSINESS_ROOT)),
    }
    write_json(topic_dir / "metadata.json", metadata)
    return metadata


def generate_voiceovers(provider: str | None = None) -> list[dict]:
    load_dotenv(REPO_ROOT / ".env")
    selected_provider = (provider or os.getenv("TTS_PROVIDER", "stub")).lower().strip()
    script_paths = read_script_files()

    if not script_paths:
        note_path = VOICEOVER_DIR / "README_NO_SCRIPTS.md"
        write_text(note_path, "# No Scripts Found\n\nRun the transform stage first, then rerun edit.\n")
        print("No script.txt files found. Wrote voiceover placeholder note.")
        return []

    results = [generate_voiceover_for_script(path, selected_provider) for path in script_paths]
    generated = sum(1 for item in results if item.get("status") == "generated")
    placeholders = sum(1 for item in results if item.get("status") == "placeholder")
    print(f"Voiceover results: {generated} generated, {placeholders} placeholder")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate voiceovers from INTERMEDIATE script.txt files.")
    parser.add_argument(
        "--provider",
        choices=["stub", "elevenlabs"],
        default=None,
        help="Optional provider override. Defaults to TTS_PROVIDER from .env or stub.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_voiceovers(args.provider)


if __name__ == "__main__":
    main()
