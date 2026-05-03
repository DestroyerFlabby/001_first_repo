from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LINKS_FILE = REPO_ROOT / "CREATOR_CLIPPING_BUSINESS" / "RAW_MEDIA" / "source_links.txt"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "CREATOR_CLIPPING_BUSINESS" / "RAW_MEDIA" / "CLIPS_RAW_VIDEO"


def read_links(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Links file not found: {path}")

    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def download_links(links: list[str], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    if not links:
        print("No links found. Add one URL per line to the links file.")
        return

    output_template = str(output_dir / "%(title)s.%(ext)s")
    total_links = len(links)

    for index, link in enumerate(links, start=1):
        print(f"\n[{index}/{total_links}] Downloading: {link}")
        try:
            subprocess.run(["yt-dlp", link, "-o", output_template], check=True)
            print(f"[{index}/{total_links}] Success")
        except subprocess.CalledProcessError:
            print(f"[{index}/{total_links}] Failed: {link}")


def parse_args() -> argparse.Namespace:
    load_dotenv(REPO_ROOT / ".env")

    env_links_file = os.getenv("YOUTUBE_LINKS_FILE")
    env_output_dir = os.getenv("YOUTUBE_DOWNLOAD_DIR")

    parser = argparse.ArgumentParser(description="Batch download source videos for creator clipping.")
    parser.add_argument(
        "--links-file",
        type=Path,
        default=REPO_ROOT / env_links_file if env_links_file else DEFAULT_LINKS_FILE,
        help="Text file with one source URL per line.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / env_output_dir if env_output_dir else DEFAULT_OUTPUT_DIR,
        help="Folder where raw source videos should be stored.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    links = read_links(args.links_file)
    download_links(links, args.output_dir)


if __name__ == "__main__":
    main()
