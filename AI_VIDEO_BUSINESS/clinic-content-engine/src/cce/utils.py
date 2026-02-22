from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from cce.models import ClientConfig, GuardrailsConfig


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        chunk = text[start : start + chunk_size]
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def read_source_files(sources_dir: Path) -> list[tuple[Path, str]]:
    files = sorted([p for p in sources_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".txt", ".md"}])
    return [(path, path.read_text(encoding="utf-8")) for path in files]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML format in {path}")
    return data


def load_client_config(path: Path) -> ClientConfig:
    return ClientConfig.model_validate(load_yaml(path))


def load_guardrails_config(path: Path) -> GuardrailsConfig:
    return GuardrailsConfig.model_validate(load_yaml(path))


def score_chunk(query_terms: set[str], chunk_text_value: str) -> int:
    words = set(re.findall(r"[a-z0-9_]+", chunk_text_value.lower()))
    return len(query_terms & words)


def retrieve_relevant_chunks(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
    scored: list[tuple[int, dict]] = []
    for chunk in chunks:
        text = str(chunk.get("text", ""))
        score = score_chunk(terms, text)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    if scored:
        return [chunk for _, chunk in scored[:top_k]]
    return chunks[:top_k]


def summarize_guardrails(guardrails: GuardrailsConfig) -> str:
    return (
        f"Banned phrases: {guardrails.banned_phrases}. "
        f"Banned claim regex: {guardrails.banned_claim_patterns}. "
        f"Always include default disclaimer: {guardrails.disclaimer_rules.always_include_default_disclaimer}. "
        f"Keywords requiring disclaimer: {guardrails.disclaimer_rules.must_include_disclaimer_if_keywords}."
    )
