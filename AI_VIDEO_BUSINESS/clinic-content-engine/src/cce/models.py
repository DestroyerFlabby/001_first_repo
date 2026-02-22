from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Pillar(BaseModel):
    name: str
    description: str


class Cadence(BaseModel):
    posts_per_week: int = Field(ge=1)
    mix: dict[str, float] = Field(default_factory=dict)


class ContentStrategy(BaseModel):
    pillars: list[Pillar]
    cadence: Cadence


class Tone(BaseModel):
    style: str
    reading_level: str
    do: list[str] = Field(default_factory=list)
    dont: list[str] = Field(default_factory=list)


class CTAs(BaseModel):
    soft: list[str] = Field(default_factory=list)


class Disclaimers(BaseModel):
    default: str


class Links(BaseModel):
    homepage: str
    booking: str


class ClientConfig(BaseModel):
    client_name: str
    location: str
    primary_platforms: list[str] = Field(default_factory=list)
    secondary_platforms: list[str] = Field(default_factory=list)
    tone: Tone
    content_strategy: ContentStrategy
    services: list[str] = Field(default_factory=list)
    ctas: CTAs
    disclaimers: Disclaimers
    links: Links


class MedicalSafetyRules(BaseModel):
    require_balanced_language: bool = True
    avoid_diagnosis_language: bool = True
    avoid_outcome_promises: bool = True
    avoid_specific_treatment_advice: bool | None = None
    avoid_before_after_encouragement: bool | None = None


class BeforeAfterPolicy(BaseModel):
    allowed_in_organic: str | None = None
    allowed_in_promoted_ads: bool | None = None


class DisclaimerRules(BaseModel):
    always_include_default_disclaimer: bool = True
    must_include_disclaimer_if_keywords: list[str] = Field(default_factory=list)


class GuardrailsConfig(BaseModel):
    region: str
    profile: str
    banned_phrases: list[str] = Field(default_factory=list)
    banned_claim_patterns: list[str] = Field(default_factory=list)
    medical_safety_rules: MedicalSafetyRules
    before_after_policy: BeforeAfterPolicy | None = None
    disclaimer_rules: DisclaimerRules


class PlanItem(BaseModel):
    id: str
    pillar: str
    service: str
    platform: str
    angle: str
    target_length: Literal["short", "medium", "long"]


class DraftItem(BaseModel):
    id: str
    platform: str
    pillar: str
    service: str
    angle: str
    caption: str
    hashtags: list[str]
    cta: str
    disclaimer: str
    reel_script: list[str] = Field(default_factory=list)
    retrieved_chunks: list[str] = Field(default_factory=list)


class ReviewedItem(BaseModel):
    id: str
    platform: str
    pillar: str
    service: str
    status: Literal["PASS", "FAIL", "FIXED"]
    reasons: list[str] = Field(default_factory=list)
    final_caption: str
    final_hashtags: list[str]
    final_cta: str
    final_disclaimer: str
    reel_script: list[str] = Field(default_factory=list)
