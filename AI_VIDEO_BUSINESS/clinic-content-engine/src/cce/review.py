from __future__ import annotations

from pathlib import Path

from rich.console import Console

from cce.guardrails import apply_rewrite_fixes, evaluate_draft
from cce.llm import generate_json, llm_enabled
from cce.models import DraftItem, ReviewedItem
from cce.utils import (
    ensure_dir,
    load_client_config,
    load_guardrails_config,
    read_jsonl,
    write_jsonl,
)


def run_review(client_dir: Path, month: str, console: Console) -> None:
    client = load_client_config(client_dir / "client.yaml")
    guardrails = load_guardrails_config(client_dir / "guardrails.yaml")

    drafts_path = client_dir / "runs" / month / "drafts.jsonl"
    if not drafts_path.exists():
        raise FileNotFoundError(f"Missing drafts file. Run generate first: {drafts_path}")

    drafts = [DraftItem.model_validate(x) for x in read_jsonl(drafts_path)]
    if not drafts:
        raise ValueError(f"No drafts found in {drafts_path}")

    reviewed: list[ReviewedItem] = []
    enabled = llm_enabled()

    for draft in drafts:
        result = evaluate_draft(draft, guardrails, client.disclaimers.default)
        if not result["ok"]:
            if enabled:
                system_prompt = "You fix medical content for compliance. Return strict JSON with caption, hashtags, cta, disclaimer, reel_script."
                user_prompt = (
                    f"Reasons to fix: {result['reasons']}\n"
                    f"Original caption: {draft.caption}\n"
                    f"Original hashtags: {draft.hashtags}\n"
                    f"Original CTA: {draft.cta}\n"
                    f"Original disclaimer: {draft.disclaimer}\n"
                    f"Required default disclaimer: {client.disclaimers.default}"
                )
                fixed = generate_json(system_prompt, user_prompt)
                final_caption = fixed.get("caption", draft.caption)
                final_hashtags = fixed.get("hashtags", draft.hashtags)
                if isinstance(final_hashtags, str):
                    final_hashtags = [x for x in final_hashtags.split() if x.startswith("#")]
                final_cta = fixed.get("cta", draft.cta)
                final_disclaimer = fixed.get("disclaimer", client.disclaimers.default)
                final_reel_script = fixed.get("reel_script", draft.reel_script)
                if isinstance(final_reel_script, str):
                    final_reel_script = [line for line in final_reel_script.splitlines() if line.strip()]
                status = "FIXED"
            else:
                patched = apply_rewrite_fixes(
                    draft.caption,
                    draft.disclaimer,
                    guardrails,
                    client.disclaimers.default,
                )
                final_caption = patched["caption"]
                final_disclaimer = patched["disclaimer"]
                final_hashtags = draft.hashtags
                final_cta = draft.cta
                final_reel_script = draft.reel_script
                status = "FAIL"
                result["reasons"] = result["reasons"] + [
                    "Suggested fix provided in final_caption/final_disclaimer."
                ]
        else:
            final_caption = draft.caption
            final_hashtags = draft.hashtags
            final_cta = draft.cta
            final_disclaimer = draft.disclaimer or client.disclaimers.default
            final_reel_script = draft.reel_script
            status = "PASS"

        reviewed.append(
            ReviewedItem(
                id=draft.id,
                platform=draft.platform,
                pillar=draft.pillar,
                service=draft.service,
                status=status,
                reasons=result["reasons"],
                final_caption=final_caption,
                final_hashtags=final_hashtags,
                final_cta=final_cta,
                final_disclaimer=final_disclaimer,
                reel_script=final_reel_script,
            )
        )

    run_dir = ensure_dir(client_dir / "runs" / month)
    out_path = run_dir / "reviewed.jsonl"
    write_jsonl(out_path, [x.model_dump() for x in reviewed])

    pass_or_fixed = sum(1 for x in reviewed if x.status in {"PASS", "FIXED"})
    console.print(f"[green]Review complete[/green]: {pass_or_fixed}/{len(reviewed)} compliant")
    console.print(f"[cyan]Wrote[/cyan] {out_path}")
