from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def llm_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def generate_json(system_prompt: str, user_prompt: str) -> dict:
    if not llm_enabled():
        return {
            "caption": "Stub content: API key missing.",
            "hashtags": ["#StubMode", "#ClinicContent"],
            "soft_cta": "Contact us for more information",
            "disclaimer": "Educational information only — not medical advice.",
            "reel_script": ["Stub reel script line 1", "Stub reel script line 2"],
        }

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    raw_text = response.choices[0].message.content or "{}"

    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {"caption": raw_text}
