from cce.guardrails import evaluate_draft
from cce.models import DisclaimerRules, DraftItem, GuardrailsConfig, MedicalSafetyRules


def make_guardrails() -> GuardrailsConfig:
    return GuardrailsConfig(
        region="Ontario, Canada",
        profile="test",
        banned_phrases=["guaranteed", "risk-free"],
        banned_claim_patterns=[r"(?i)results\s+in\s+\d+\s+days\b"],
        medical_safety_rules=MedicalSafetyRules(),
        disclaimer_rules=DisclaimerRules(
            always_include_default_disclaimer=True,
            must_include_disclaimer_if_keywords=["results", "recovery"],
        ),
    )


def test_banned_phrase_detection() -> None:
    guardrails = make_guardrails()
    draft = DraftItem(
        id="1",
        platform="instagram",
        pillar="Myths vs Facts",
        service="Consultations",
        angle="myth vs fact",
        caption="This treatment is guaranteed to work.",
        hashtags=["#test"],
        cta="Book now",
        disclaimer="Educational information only — not medical advice.",
        reel_script=[],
    )

    result = evaluate_draft(draft, guardrails, "Educational information only — not medical advice.")
    assert result["ok"] is False
    assert any("Banned phrase" in r for r in result["reasons"])


def test_regex_claim_pattern_detection() -> None:
    guardrails = make_guardrails()
    draft = DraftItem(
        id="2",
        platform="instagram",
        pillar="Safety & Trust",
        service="Consultations",
        angle="safety & trust",
        caption="See results in 5 days with this plan.",
        hashtags=["#test"],
        cta="Learn more",
        disclaimer="Educational information only — not medical advice.",
        reel_script=[],
    )

    result = evaluate_draft(draft, guardrails, "Educational information only — not medical advice.")
    assert result["ok"] is False
    assert any("pattern" in r.lower() for r in result["reasons"])


def test_disclaimer_requirement_triggered_by_keywords() -> None:
    guardrails = make_guardrails()
    draft = DraftItem(
        id="3",
        platform="linkedin",
        pillar="Process Clarity",
        service="Medical consultancy",
        angle="what to expect",
        caption="Let's talk about recovery timelines and results.",
        hashtags=["#test"],
        cta="Send us a message",
        disclaimer="General education",
        reel_script=[],
    )

    required_default = "Educational information only — not medical advice."
    result = evaluate_draft(draft, guardrails, required_default)
    assert result["ok"] is False
    assert any("Disclaimer required" in r for r in result["reasons"])
    assert any("Default disclaimer missing" in r for r in result["reasons"])
