from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from cce.llm import llm_enabled
from cce.models import ReviewedItem
from cce.utils import ensure_dir, read_json, read_jsonl, write_json


def run_export(client_dir: Path, month: str, console: Console) -> None:
    reviewed_path = client_dir / "runs" / month / "reviewed.jsonl"
    if not reviewed_path.exists():
        raise FileNotFoundError(f"Missing reviewed file. Run review first: {reviewed_path}")

    reviewed = [ReviewedItem.model_validate(x) for x in read_jsonl(reviewed_path)]
    if not reviewed:
        raise ValueError(f"No reviewed posts found in {reviewed_path}")

    deliverables_dir = ensure_dir(client_dir / "deliverables" / month)
    posts_csv = deliverables_dir / "posts.csv"
    reels_txt = deliverables_dir / "reels_scripts.txt"
    audit_json = deliverables_dir / "audit_log.json"

    with posts_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["platform", "pillar", "service", "caption", "hashtags", "cta", "disclaimer", "status"],
        )
        writer.writeheader()
        for item in reviewed:
            writer.writerow(
                {
                    "platform": item.platform,
                    "pillar": item.pillar,
                    "service": item.service,
                    "caption": item.final_caption,
                    "hashtags": " ".join(item.final_hashtags),
                    "cta": item.final_cta,
                    "disclaimer": item.final_disclaimer,
                    "status": item.status,
                }
            )

    with reels_txt.open("w", encoding="utf-8") as f:
        for item in reviewed:
            f.write(f"=== {item.id} | {item.platform} | {item.pillar} | {item.service} ===\n")
            if item.reel_script:
                for line in item.reel_script:
                    f.write(f"- {line}\n")
            else:
                f.write("- No reel script generated.\n")
            f.write("\n")

    kb_path = client_dir / "kb" / "kb_chunks.jsonl"
    plan_path = client_dir / "runs" / month / "plan.json"
    sources_dir = client_dir / "sources"
    number_of_sources = len([p for p in sources_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".txt", ".md"}])
    number_of_chunks = len(read_jsonl(kb_path)) if kb_path.exists() else 0
    number_of_posts = len(read_json(plan_path).get("items", [])) if plan_path.exists() else len(reviewed)
    pass_rate = round(sum(1 for x in reviewed if x.status in {"PASS", "FIXED"}) / len(reviewed), 4)

    audit = {
        "client": client_dir.name,
        "month": month,
        "number_of_sources": number_of_sources,
        "number_of_chunks": number_of_chunks,
        "number_of_posts": number_of_posts,
        "pass_rate": pass_rate,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "stub_mode": not llm_enabled(),
    }
    write_json(audit_json, audit)

    console.print(f"[green]Export complete[/green]: {len(reviewed)} posts exported")
    console.print(f"[cyan]Wrote[/cyan] {posts_csv}")
    console.print(f"[cyan]Wrote[/cyan] {reels_txt}")
    console.print(f"[cyan]Wrote[/cyan] {audit_json}")
