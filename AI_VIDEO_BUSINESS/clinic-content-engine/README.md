## Source of Truth

All architectural decisions, scope constraints, and compliance philosophy are defined in STRATEGY.md.

If any implementation detail conflicts with STRATEGY.md, STRATEGY.md takes precedence.

Future changes must align with:
- Compliance-first design
- Minimal operational burden
- Config-driven multi-clinic support
- v1 simplicity before v2 complexity

Do not add features outside of defined scope unless explicitly requested.

# Clinic Content Engine

A Python 3.11+ CLI pipeline to generate compliant clinic social content for two profiles from one system:
- Conservative medical consultancy (`clients/ammc`)
- Aesthetics / injectables / plastic surgery clinic (`clients/aesthetics`)

The pipeline supports end-to-end execution in stub mode when no OpenAI API key is configured.

## Features
- Ingest clinic source text into local knowledge-base chunks
- Build monthly content plans from client strategy
- Generate grounded drafts (captions, hashtags, CTAs, disclaimers, optional reel scripts)
- Review drafts against rule-based guardrails and auto-fix where possible
- Export deliverables (CSV posts, reel scripts, audit log)

## Setup (Windows)
1. Create and activate a virtual environment:
```powershell
cd "C:\Users\nisar\OneDrive\Desktop\Coding\Github Repositories\001_first_repo\AI_VIDEO_BUSINESS\clinic-content-engine"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install in editable mode:
```powershell
pip install -e .
pip install -e .[dev]
```

3. Configure environment:
```powershell
Copy-Item .env.example .env
# Edit .env and set OPENAI_API_KEY=your_key_here (optional)
```

If `OPENAI_API_KEY` is missing, the app runs in stub mode and still produces outputs.

## Commands
Run for AMMC:
```powershell
cce ingest --client clients/ammc
cce plan --client clients/ammc --month 2026-03
cce generate --client clients/ammc --month 2026-03
cce review --client clients/ammc --month 2026-03
cce export --client clients/ammc --month 2026-03
```

Run for aesthetics:
```powershell
cce ingest --client clients/aesthetics
cce plan --client clients/aesthetics --month 2026-03
cce generate --client clients/aesthetics --month 2026-03
cce review --client clients/aesthetics --month 2026-03
cce export --client clients/aesthetics --month 2026-03
```

## Output Paths
- Ingest chunks: `clients/<clinic>/kb/kb_chunks.jsonl`
- Plan: `clients/<clinic>/runs/<month>/plan.json`
- Drafts: `clients/<clinic>/runs/<month>/drafts.jsonl`
- Reviewed: `clients/<clinic>/runs/<month>/reviewed.jsonl`
- Deliverables:
  - `clients/<clinic>/deliverables/<month>/posts.csv`
  - `clients/<clinic>/deliverables/<month>/reels_scripts.txt`
  - `clients/<clinic>/deliverables/<month>/audit_log.json`

## Extend Later
This structure is designed to support future upgrades like embeddings retrieval, Whisper transcription, video clipping, and analytics feedback loops.
