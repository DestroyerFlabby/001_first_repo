from __future__ import annotations

from pathlib import Path

from rich.console import Console

from cce.llm import generate_json, llm_enabled
from cce.models import DraftItem, PlanItem
from cce.utils import (
    ensure_dir,
    load_client_config,
    load_guardrails_config,
    read_json,
    read_jsonl,
    retrieve_relevant_chunks,
    summarize_guardrails,
    write_jsonl,
)


def _stub_draft(item: PlanItem, client_name: str, cta: str, disclaimer: str, chunks: list[dict]) -> dict:
    facts = " ".join(chunk["text"][:120] for chunk in chunks[:2]).strip()
    caption = (
        f"{item.angle.title()} for {item.service}. "
        f"At {client_name}, we focus on clarity and safe expectations. "
        f"{facts}".strip()
    )
    return {
        "caption": caption,
        "hashtags": [
            "#ClinicEducation",
            "#PatientFirst",
            "#Healthcare",
            "#InformedDecisions",
            "#Toronto",
        ],
        "soft_cta": cta,
        "disclaimer": disclaimer,
        "reel_script": [
            "Hook: One thing people often misunderstand.",
            "Point 1: What to expect in simple terms.",
            "Point 2: Safety and realistic expectations.",
            f"CTA: {cta}",
        ],
    }


def run_generate(client_dir: Path, month: str, console: Console) -> None:
    client = load_client_config(client_dir / "client.yaml")
    guardrails = load_guardrails_config(client_dir / "guardrails.yaml")

    kb_path = client_dir / "kb" / "kb_chunks.jsonl"
    if not kb_path.exists():
        raise FileNotFoundError(f"Missing KB chunks file. Run ingest first: {kb_path}")

    plan_path = client_dir / "runs" / month / "plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"Missing plan file. Run plan first: {plan_path}")

    plan_payload = read_json(plan_path)
    items = [PlanItem.model_validate(x) for x in plan_payload.get("items", [])]
    kb_chunks = read_jsonl(kb_path)
    if not items:
        raise ValueError(f"No plan items found in {plan_path}")

    drafts: list[DraftItem] = []
    guardrails_summary = summarize_guardrails(guardrails)
    enabled = llm_enabled()

    for item in items:
        query = f"{item.pillar} {item.service} {item.angle}"
        retrieved = retrieve_relevant_chunks(query, kb_chunks, top_k=5)
        selected = retrieved[: max(2, min(5, len(retrieved)))] if retrieved else kb_chunks[:2]

        default_cta = client.ctas.soft[0] if client.ctas.soft else "Contact us to learn more"
        default_disclaimer = client.disclaimers.default

        if enabled:
            system_prompt = (
                "You are a medical clinic social content assistant. "
                "Return strict JSON with keys: caption, hashtags, soft_cta, disclaimer, reel_script."
            )
            user_prompt = (
                f"Clinic: {client.client_name}\n"
                f"Tone: {client.tone.style}\n"
                f"Platform: {item.platform}\n"
                f"Pillar: {item.pillar}\n"
                f"Service: {item.service}\n"
                f"Angle: {item.angle}\n"
                f"Target length: {item.target_length}\n"
                f"Guardrails: {guardrails_summary}\n"
                f"Default CTA options: {client.ctas.soft}\n"
                f"Default disclaimer: {default_disclaimer}\n"
                f"Grounding chunks:\n" + "\n---\n".join(chunk["text"] for chunk in selected)
            )
            raw = generate_json(system_prompt, user_prompt)
        else:
            raw = _stub_draft(item, client.client_name, default_cta, default_disclaimer, selected)

        hashtags = raw.get("hashtags", [])
        if isinstance(hashtags, str):
            hashtags = [x.strip() for x in hashtags.split() if x.strip().startswith("#")]
        if not hashtags:
            hashtags = ["#ClinicEducation", "#PatientCare", "#Healthcare", "#Toronto", "#Wellness"]

        reel_script = raw.get("reel_script", [])
        if isinstance(reel_script, str):
            reel_script = [line.strip() for line in reel_script.splitlines() if line.strip()]

        drafts.append(
            DraftItem(
                id=item.id,
                platform=item.platform,
                pillar=item.pillar,
                service=item.service,
                angle=item.angle,
                caption=raw.get("caption", ""),
                hashtags=hashtags[:10],
                cta=raw.get("soft_cta", default_cta),
                disclaimer=raw.get("disclaimer", default_disclaimer),
                reel_script=reel_script,
                retrieved_chunks=[x.get("chunk_id", "") for x in selected],
            )
        )

    run_dir = ensure_dir(client_dir / "runs" / month)
    out_path = run_dir / "drafts.jsonl"
    write_jsonl(out_path, [draft.model_dump() for draft in drafts])

    mode_text = "LLM mode" if enabled else "stub mode"
    console.print(f"[green]Generate complete[/green]: {len(drafts)} drafts ({mode_text})")
    console.print(f"[cyan]Wrote[/cyan] {out_path}")
