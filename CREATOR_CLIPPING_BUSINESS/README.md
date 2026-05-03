# Creator Clipping Business

This workspace supports two connected business tracks:

1. A semi-faceless, AI-assisted media page for audience growth, niche authority, and future monetization.
2. A client services clipping business for immediate revenue from creators, coaches, founders, podcasters, and educators.

The full workflow is:

Find content -> select strong moments -> transform the idea -> edit the clip -> post consistently -> track performance -> use proof to outreach -> monetize.

Downloaded footage should only be used for public posting when we have permission or appropriate rights. Before posting sourced footage, check `LEGAL_AND_SOURCING/source_rights_checklist.md` and record `source_url` plus `rights_status` in the media page content calendar.

Pipeline work is organized into four zones:

1. `PIPELINE_ZONES/01_RAW`: acquire data.
2. `PIPELINE_ZONES/02_INTERMEDIATE`: transform clips into angles, hooks, and candidates.
3. `PIPELINE_ZONES/03_STAGING`: edit and review drafts.
4. `PIPELINE_ZONES/04_CURATED`: prepare approved assets for posting and tracking.

## Bulk Ingestion

`POST_LINKS` is the intake queue for source links. Each dated folder is one batch job.

Example:

```text
POST_LINKS/
  2026-05-03/
    source_links.txt
    downloaded_videos/
```

Each line in `source_links.txt` uses:

```text
url | topic | rights_status
```

`downloaded_videos` is the raw batch storage for that date. After download, the script also copies each video into the structured RAW zone:

```text
PIPELINE_ZONES/01_RAW/DOWNLOADED_MEDIA/{topic}/
```

Each successful video gets a metadata sidecar named like:

```text
video_name.video_metadata.json
```

Run ingestion only:

```powershell
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\batch_download.py
```

The downloader does not trigger editing or posting.

## Pipeline Runner

Use the central runner when you want to run one stage at a time or run the full workflow up to human review.

```powershell
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage download
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage transform
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage edit
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage curate
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage all
```

`--stage all` stops at human review in `PIPELINE_ZONES/04_CURATED/READY_TO_POST`. It does not auto-post to TikTok, Instagram, or YouTube. Posting remains manual.

## Two Tracks

### 01 Media Page

The media page is a curated brand. It uses clips, commentary, captions, hooks, added context, and clear storytelling to build a niche audience. This is not a repost page. Every post should add a point of view, a takeaway, or a new frame.

Primary goal: grow attention and trust.

Monetization can come from brand deals, affiliate links, selling clipping services, lead generation, or eventually platform monetization where eligible.

### 02 Client Services

The services track sells clipping and short-form content support to creators and businesses. This is the faster cash-flow path.

Primary goal: get hired to turn long-form content into high-performing short clips.

Revenue can come from per-clip work, monthly retainers, or performance-based deals once there is proof.

## How They Connect

The media page builds skill, proof, and a public portfolio. The client services track turns that proof into revenue. Strong posts can become case studies. Client results can become outreach material. Both tracks improve the same core skill: finding and transforming attention-worthy moments.

## Getting Started

- Pick one niche for the media page.
- Define 3-5 content pillars.
- Create 10 starter clips using the post templates.
- Confirm source rights before public posting.
- Track every post in `TRACKING/media_page_content_calendar.csv`.
- Use `OPERATING_MANUAL.md` and `PIPELINE_ZONES/README.md` as the central workflow for source downloading, clipping, posting, tracking, and outreach.
- Start outreach to 20 creators using `02_CLIENT_SERVICES/outreach_templates.md`.
- Offer a small paid test package or 1 free sample clip.
- Track all leads in `TRACKING/client_pipeline.csv`.
- Review performance weekly and double down on the best formats.

## Execution Rule

Simple subtitles are not enough. Each clip should include transformation through hooks, captions, framing, commentary, visual context, summarization, or a clear takeaway.
