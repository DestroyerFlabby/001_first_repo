# Pipeline Zones

This folder organizes the creator clipping workflow by pipeline state.

The core pipeline is:

1. Acquire data.
2. Clip transformation.
3. Editing.
4. Posting.

Each item should move through the zones below.

## Zone Map

| Zone | Pipeline Step | Purpose | Typical Inputs | Typical Outputs |
| --- | --- | --- | --- | --- |
| `01_RAW` | 1. Acquire data | Capture source material before judgment or editing. | URLs, raw downloads, creator-provided footage. | Source links, downloaded videos, rights notes. |
| `02_INTERMEDIATE` | 2. Clip transformation | Turn raw material into candidate clips and angles. | Raw videos, transcripts, notes. | Clip candidates, hooks, transformation ideas. |
| `03_STAGING` | 3. Editing | Build post-ready drafts that still need review. | Candidate clips, captions, B-roll ideas. | Draft clips, captions, thumbnails, review notes. |
| `04_CURATED` | 4. Posting | Store approved, safe-to-post, tracked assets. | Approved edits, final captions, rights status. | Ready-to-post assets, posted records, performance notes. |

## Operating Rule

Do not jump straight from raw download to public post. Raw material must pass through rights review, transformation, editing, and final approval.

## Current Automation

`AUTOMATION/batch_download.py` supports the RAW zone by reading source URLs and downloading media.

## Current Manual Systems

- `SHARED_ASSETS/PROMPTS` supports the INTERMEDIATE zone.
- `SHARED_ASSETS/EDITING` supports the STAGING zone.
- `TRACKING` supports the CURATED and performance-review steps.
- `LEGAL_AND_SOURCING` supports every zone before public posting.
