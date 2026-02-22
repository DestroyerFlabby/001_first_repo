from __future__ import annotations

import re

from cce.models import DraftItem, GuardrailsConfig


def evaluate_draft(draft: DraftItem, guardrails: GuardrailsConfig, default_disclaimer: str) -> dict:
    reasons: list[str] = []
    text = f"{draft.caption}\n{draft.cta}\n{' '.join(draft.hashtags)}"

    lower_text = text.lower()
    for phrase in guardrails.banned_phrases:
        if phrase.lower() in lower_text:
            reasons.append(f"Banned phrase detected: {phrase}")

    for pattern in guardrails.banned_claim_patterns:
        if re.search(pattern, text):
            reasons.append(f"Banned claim pattern matched: {pattern}")

    must_have_disclaimer = guardrails.disclaimer_rules.always_include_default_disclaimer
    for keyword in guardrails.disclaimer_rules.must_include_disclaimer_if_keywords:
        if keyword.lower() in lower_text:
            must_have_disclaimer = True
            reasons.append(f"Disclaimer required due to keyword: {keyword}")

    if must_have_disclaimer and default_disclaimer.lower() not in draft.disclaimer.lower():
        reasons.append("Default disclaimer missing")

    return {"ok": len(reasons) == 0, "reasons": reasons}


def apply_rewrite_fixes(caption: str, disclaimer: str, guardrails: GuardrailsConfig, default_disclaimer: str) -> dict:
    fixed_caption = caption

    for phrase in guardrails.banned_phrases:
        fixed_caption = re.sub(re.escape(phrase), "", fixed_caption, flags=re.IGNORECASE)

    fixed_caption = re.sub(r"\s+", " ", fixed_caption).strip()

    for pattern in guardrails.banned_claim_patterns:
        fixed_caption = re.sub(pattern, "", fixed_caption)
    fixed_caption = re.sub(r"\s+", " ", fixed_caption).strip()

    if default_disclaimer.lower() not in disclaimer.lower():
        fixed_disclaimer = default_disclaimer
    else:
        fixed_disclaimer = disclaimer

    return {"caption": fixed_caption, "disclaimer": fixed_disclaimer}
