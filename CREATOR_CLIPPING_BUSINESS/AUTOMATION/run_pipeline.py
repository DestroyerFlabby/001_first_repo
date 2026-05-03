from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from batch_download import POST_LINKS_DIR, RAW_ORGANIZED_DIR, download_batch, latest_batch_folder


BUSINESS_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = BUSINESS_ROOT / "PIPELINE_ZONES"
INTERMEDIATE_DIR = PIPELINE_ROOT / "02_INTERMEDIATE"
STAGING_DIR = PIPELINE_ROOT / "03_STAGING"
CURATED_DIR = PIPELINE_ROOT / "04_CURATED"


def load_metadata_files(folder: Path) -> list[dict]:
    items: list[dict] = []
    if not folder.exists():
        return items

    for path in folder.rglob("*.video_metadata.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        payload["_metadata_path"] = str(path.relative_to(BUSINESS_ROOT))
        items.append(payload)
    return items


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_download(batch_folder: Path | None, download_mode: str) -> Path:
    selected_batch = batch_folder or latest_batch_folder(POST_LINKS_DIR)
    print(f"Running download stage with batch: {selected_batch}")
    download_batch(selected_batch, download_mode)
    return selected_batch


def run_transform() -> None:
    print("Running transform stage")
    metadata_items = load_metadata_files(RAW_ORGANIZED_DIR)
    output_dir = INTERMEDIATE_DIR / "CLIP_CANDIDATES"

    if not metadata_items:
        write_text(
            output_dir / "README_NO_RAW_MEDIA.md",
            "# No Raw Media Found\n\nRun the download stage first, then rerun transform.\n",
        )
        print("No raw metadata found. Wrote placeholder transform note.")
        return

    for index, item in enumerate(metadata_items, start=1):
        topic = item.get("topic", "general")
        filename = item.get("filename", "unknown")
        package = {
            "stage": "transform",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_url": item.get("source_url"),
            "topic": topic,
            "rights_status": item.get("rights_status"),
            "source_filename": filename,
            "duration": item.get("duration"),
            "clip_candidates": [
                {
                    "candidate_id": f"{index:03d}-001",
                    "working_title": f"Candidate moment from {filename}",
                    "hook": "TODO: Generate hook with AI later.",
                    "angle": "TODO: Add transformation angle.",
                    "notes": "Stub candidate. Replace after transcript review.",
                }
            ],
            "todos": [
                "TODO: Add transcript extraction.",
                "TODO: Add AI clip scoring.",
                "TODO: Add hook generation integration.",
            ],
        }
        write_json(output_dir / topic / f"{Path(filename).stem}.clip_plan.json", package)

    print(f"Created transform packages: {len(metadata_items)}")


def run_edit() -> None:
    print("Running edit stage")
    clip_plans = list((INTERMEDIATE_DIR / "CLIP_CANDIDATES").rglob("*.clip_plan.json"))
    output_dir = STAGING_DIR / "DRAFT_CLIPS"

    if not clip_plans:
        write_text(
            output_dir / "README_NO_CLIP_PLANS.md",
            "# No Clip Plans Found\n\nRun the transform stage first, then rerun edit.\n",
        )
        print("No clip plans found. Wrote placeholder edit note.")
        return

    for plan_path in clip_plans:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        topic = plan.get("topic", "general")
        source_stem = Path(plan.get("source_filename", plan_path.stem)).stem
        draft_package = {
            "stage": "edit",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_plan": str(plan_path.relative_to(BUSINESS_ROOT)),
            "topic": topic,
            "draft_assets": {
                "draft_video": "TODO: Create edited draft video later.",
                "subtitle_file": "TODO: Generate subtitles later.",
                "b_roll_plan": "TODO: Add B-roll plan later.",
            },
            "review_notes": [
                "Check rights_status before public use.",
                "Confirm hook and caption fit the clip.",
                "TODO: Add video editing integration.",
                "TODO: Add TTS or voiceover integration only if needed.",
            ],
        }
        write_json(output_dir / topic / f"{source_stem}.draft_package.json", draft_package)

    print(f"Created edit draft packages: {len(clip_plans)}")


def run_curate() -> None:
    print("Running curate stage")
    draft_packages = list((STAGING_DIR / "DRAFT_CLIPS").rglob("*.draft_package.json"))
    output_dir = CURATED_DIR / "READY_TO_POST"

    if not draft_packages:
        write_text(
            output_dir / "README_NO_DRAFTS.md",
            "# No Draft Packages Found\n\nRun the edit stage first, then rerun curate.\n",
        )
        print("No draft packages found. Wrote placeholder curate note.")
        return

    for draft_path in draft_packages:
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        topic = draft.get("topic", "general")
        source_stem = draft_path.stem.replace(".draft_package", "")
        review_package = {
            "stage": "curate",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_draft": str(draft_path.relative_to(BUSINESS_ROOT)),
            "topic": topic,
            "human_review_required": True,
            "auto_posting": False,
            "posting_status": "manual_review_required",
            "checklist": [
                "Rights status checked.",
                "Clip is transformed, not a simple repost.",
                "Caption and hook reviewed.",
                "Final export reviewed on mobile.",
                "Manual posting only.",
            ],
            "todos": [
                "TODO: Add optional AI quality review.",
                "TODO: Add optional export validation.",
                "Do not add auto-posting until explicitly approved.",
            ],
        }
        write_json(output_dir / topic / f"{source_stem}.human_review_package.json", review_package)

    print(f"Created human-review packages: {len(draft_packages)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run creator clipping pipeline stages.")
    parser.add_argument(
        "--stage",
        choices=["download", "transform", "edit", "curate", "all"],
        required=True,
        help="Pipeline stage to run. 'all' stops at human review and never auto-posts.",
    )
    parser.add_argument(
        "--batch-folder",
        type=Path,
        default=None,
        help="Optional POST_LINKS/YYYY-MM-DD batch folder for download stage.",
    )
    parser.add_argument(
        "--download-mode",
        choices=["safe", "all"],
        default="safe",
        help="Download mode used only by download/all stages.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.stage in {"download", "all"}:
        run_download(args.batch_folder, args.download_mode)
    if args.stage in {"transform", "all"}:
        run_transform()
    if args.stage in {"edit", "all"}:
        run_edit()
    if args.stage in {"curate", "all"}:
        run_curate()

    if args.stage == "all":
        print("\nPipeline complete. Stopped at human review. No auto-posting was performed.")


if __name__ == "__main__":
    main()
