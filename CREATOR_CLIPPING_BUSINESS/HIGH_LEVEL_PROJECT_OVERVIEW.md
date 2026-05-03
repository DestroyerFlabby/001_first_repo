# High Level Project Overview

`CREATOR_CLIPPING_BUSINESS` is a practical operating system for building a creator clipping business.

It supports two connected tracks:

1. A semi-faceless media page that grows attention, tests formats, and can later monetize through brand deals, affiliates, services, and platform monetization where eligible.
2. A client services clipping business that sells short-form content support to creators, founders, coaches, podcasters, educators, and businesses.

## Core Purpose

The folder is designed to turn long-form source content into transformed short-form content packages.

The basic workflow is:

```text
find source -> verify rights -> download or collect media -> transform into angle/script -> edit draft -> human review -> manual post -> track results -> improve/outreach
```

The important principle is transformation. This is not a simple repost folder. Each clip should add value through:

- A stronger hook.
- A clear point of view.
- Added context.
- Commentary or narration.
- Storytelling structure.
- Captions and visual framing.
- B-roll or supporting visuals.
- A useful takeaway.

## Folder Map

```text
CREATOR_CLIPPING_BUSINESS/
  01_MEDIA_PAGE/
  02_CLIENT_SERVICES/
  AUTOMATION/
  LEGAL_AND_SOURCING/
  PIPELINE_ZONES/
  POST_LINKS/
  SHARED_ASSETS/
  TRACKING/
  README.md
  OPERATING_MANUAL.md
```

## Pipeline Zones

The system is organized into four zones:

```text
01_RAW -> 02_INTERMEDIATE -> 03_STAGING -> 04_CURATED
```

- `01_RAW`: source links, downloads, raw media, and metadata.
- `02_INTERMEDIATE`: transcripts, clip plans, scripts, hooks, transformation ideas, and voiceovers.
- `03_STAGING`: draft packages, subtitles, B-roll plans, and edit review notes.
- `04_CURATED`: human-review-ready packages for manual posting.

## Automation

Main commands:

```powershell
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage download
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage transform
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage edit
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage curate
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage all
```

The pipeline currently supports:

- Date-based bulk video ingestion.
- Safe-mode rights filtering.
- Topic-organized RAW media.
- Metadata sidecars.
- Stub clip-plan generation.
- Starter script generation.
- Optional ElevenLabs voiceover generation.
- Manual TTS fallback when no API key exists.
- Draft package creation.
- Human-review-ready curation.

The pipeline does not auto-post. Posting stays manual until that is intentionally changed.

## Safety Rules

Only use downloaded footage publicly when rights are clear.

Safer source types include:

- Original footage.
- Creator-provided footage.
- Public domain footage.
- Creative Commons footage with proper attribution.
- Licensed stock footage.

Risky source types include:

- Random YouTube downloads without permission.
- TV or news footage without permission.
- Copyrighted documentary clips.
- Any content where ownership or license is unclear.

Use `LEGAL_AND_SOURCING/source_rights_checklist.md` before public posting.

## Business Logic

The media page creates proof. Proof helps sell client services. Client services generate revenue. Client results can become case studies. Case studies improve outreach. Outreach feeds new client work.

That loop is the heart of the business:

```text
practice -> publish -> track -> prove -> outreach -> sell -> improve
```

## Current Best Next Steps

1. Add more approved source links into `POST_LINKS/YYYY-MM-DD/source_links.txt`.
2. Run the download stage.
3. Add transcript extraction.
4. Improve transform stage with real AI-generated hooks and scripts.
5. Add subtitle and edit automation.
6. Review every output manually before posting.
7. Track all posts and client leads in `TRACKING`.
