from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
BUSINESS_ROOT = REPO_ROOT / "CREATOR_CLIPPING_BUSINESS"
POST_LINKS_DIR = BUSINESS_ROOT / "POST_LINKS"
RAW_ORGANIZED_DIR = BUSINESS_ROOT / "PIPELINE_ZONES" / "01_RAW" / "DOWNLOADED_MEDIA"
SAFE_RIGHTS_STATUSES = {"approved", "public_domain", "creative_commons"}


def slugify(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in value.lower().strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "general"


def latest_batch_folder(post_links_dir: Path) -> Path:
    if not post_links_dir.exists():
        raise FileNotFoundError(f"POST_LINKS folder not found: {post_links_dir}")

    folders = sorted(path for path in post_links_dir.iterdir() if path.is_dir())
    if not folders:
        raise FileNotFoundError(f"No dated batch folders found in: {post_links_dir}")
    return folders[-1]


def is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def parse_source_line(line: str) -> dict | None:
    if not line.strip() or line.strip().startswith("#"):
        return None

    parts = [part.strip() for part in line.split("|")]
    url = parts[0] if parts else ""
    topic = parts[1] if len(parts) > 1 and parts[1] else "general"
    rights_status = parts[2] if len(parts) > 2 and parts[2] else "unknown"

    return {
        "url": url,
        "topic": slugify(topic),
        "rights_status": rights_status.lower().strip() or "unknown",
    }


def read_source_links(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Links file not found: {path}")

    items: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_source_line(line)
        if parsed:
            items.append(parsed)
    return items


def get_duration(url: str) -> float | None:
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--skip-download", url],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    duration = payload.get("duration")
    return float(duration) if isinstance(duration, int | float) else None


def newest_file(folder: Path, before: set[Path]) -> Path | None:
    candidates = [
        path
        for path in folder.iterdir()
        if path.is_file() and path not in before and path.suffix.lower() not in {".json", ".part", ".ytdl"}
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def write_metadata(path: Path, metadata: dict) -> None:
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def log_failure(error_log: Path, message: str) -> None:
    with error_log.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + "\n")


def download_batch(batch_folder: Path, download_mode: str) -> None:
    links_file = batch_folder / "source_links.txt"
    batch_download_dir = batch_folder / "downloaded_videos"
    error_log = batch_folder / "download_errors.log"
    batch_download_dir.mkdir(parents=True, exist_ok=True)

    source_items = read_source_links(links_file)
    total_links = len(source_items)
    successful = 0
    failed = 0
    topics_created: set[str] = set()

    for index, item in enumerate(source_items, start=1):
        url = item["url"]
        topic = item["topic"]
        rights_status = item["rights_status"]

        if not is_valid_url(url):
            failed += 1
            log_failure(error_log, f"INVALID URL | {url}")
            print(f"[{index}/{total_links}] Skipped invalid URL: {url}")
            continue

        if download_mode == "safe" and rights_status not in SAFE_RIGHTS_STATUSES:
            print(f"[{index}/{total_links}] Skipped by safe mode: {url} ({rights_status})")
            continue

        print(f"\n[{index}/{total_links}] Downloading: {url}")
        before = set(batch_download_dir.iterdir()) if batch_download_dir.exists() else set()
        output_template = str(batch_download_dir / "%(title)s [%(id)s].%(ext)s")
        duration = get_duration(url)

        try:
            subprocess.run(["yt-dlp", url, "-o", output_template], check=True)
        except subprocess.CalledProcessError as exc:
            failed += 1
            log_failure(error_log, f"DOWNLOAD FAILED | {url} | {exc}")
            print(f"[{index}/{total_links}] Failed: {url}")
            continue

        downloaded_file = newest_file(batch_download_dir, before)
        if downloaded_file is None:
            failed += 1
            log_failure(error_log, f"NO OUTPUT FILE DETECTED | {url}")
            print(f"[{index}/{total_links}] Failed: no output file detected")
            continue

        topic_dir = RAW_ORGANIZED_DIR / topic
        topic_dir.mkdir(parents=True, exist_ok=True)
        topics_created.add(topic)

        organized_file = topic_dir / downloaded_file.name
        shutil.copy2(downloaded_file, organized_file)

        metadata = {
            "source_url": url,
            "topic": topic,
            "rights_status": rights_status,
            "download_date": batch_folder.name,
            "filename": downloaded_file.name,
            "duration": duration,
            "original_batch_folder": str(batch_folder.relative_to(BUSINESS_ROOT)),
        }
        write_metadata(batch_download_dir / f"{downloaded_file.stem}.video_metadata.json", metadata)
        write_metadata(topic_dir / f"{downloaded_file.stem}.video_metadata.json", metadata)

        successful += 1
        print(f"[{index}/{total_links}] Success: {downloaded_file.name}")

    print("\nDownload summary")
    print(f"Batch folder used: {batch_folder}")
    print(f"Total links processed: {total_links}")
    print(f"Successful downloads: {successful}")
    print(f"Failed downloads: {failed}")
    print(f"Topics created: {', '.join(sorted(topics_created)) if topics_created else 'none'}")


def parse_args() -> argparse.Namespace:
    load_dotenv(REPO_ROOT / ".env")

    env_download_mode = os.getenv("DOWNLOAD_MODE", "safe").lower().strip()

    parser = argparse.ArgumentParser(description="Batch download source videos for creator clipping.")
    parser.add_argument(
        "--batch-folder",
        type=Path,
        default=None,
        help="Optional dated batch folder. Defaults to the latest folder in POST_LINKS.",
    )
    parser.add_argument(
        "--download-mode",
        choices=["safe", "all"],
        default=env_download_mode if env_download_mode in {"safe", "all"} else "safe",
        help="safe downloads only approved/public-domain/Creative Commons links; all downloads every valid URL.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    batch_folder = args.batch_folder or latest_batch_folder(POST_LINKS_DIR)
    download_batch(batch_folder, args.download_mode)


if __name__ == "__main__":
    main()
