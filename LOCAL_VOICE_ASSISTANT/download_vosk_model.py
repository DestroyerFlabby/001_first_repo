from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "LOCAL_VOICE_ASSISTANT" / "models"
MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / MODEL_NAME
    if model_path.exists():
        print(f"Model already exists: {model_path}")
        return

    zip_path = MODELS_DIR / f"{MODEL_NAME}.zip"
    print(f"Downloading {MODEL_URL}")
    urllib.request.urlretrieve(MODEL_URL, zip_path)

    print("Extracting model")
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(MODELS_DIR)

    zip_path.unlink(missing_ok=True)

    if not model_path.exists():
        extracted = next(MODELS_DIR.glob("vosk-model-small-en-us-*"), None)
        if extracted:
            shutil.move(str(extracted), model_path)

    print(f"Ready: {model_path}")


if __name__ == "__main__":
    main()
