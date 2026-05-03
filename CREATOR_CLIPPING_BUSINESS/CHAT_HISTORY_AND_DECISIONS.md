# Chat History And Decisions

Saved on: 2026-05-03

This file captures the useful working memory from today's build session for the creator clipping business repository.

## Starting Point

The repository began as a broader VS Code workspace with multiple business and coding workstreams. We organized the creator clipping business into one clean folder that supports both:

1. A semi-faceless media page for growth, audience building, and future monetization.
2. A client services clipping business for immediate revenue.

The core idea is that simple reposting with subtitles is not enough. Clips should be transformed through hooks, commentary, added context, storytelling, captions, framing, B-roll, or useful takeaways.

## Major Folder Decisions

We standardized the business folder as:

```text
CREATOR_CLIPPING_BUSINESS/
```

We used all caps and underscores for major folders, matching the workspace naming style.

Main sections:

- `01_MEDIA_PAGE`: strategy, pillars, brand identity, AI voice guidelines, post templates, monetization paths.
- `02_CLIENT_SERVICES`: offer, pricing, outreach, onboarding, sample workflow.
- `SHARED_ASSETS`: prompts and editing references.
- `TRACKING`: CSV trackers for content, performance, pipeline, and client results.
- `AUTOMATION`: scripts and operating workflows.
- `LEGAL_AND_SOURCING`: source rights checklist and public posting safety.
- `POST_LINKS`: source-link intake queue.
- `PIPELINE_ZONES`: the structured working system.

## Pipeline Zone Architecture

We mapped the pipeline into four zones:

1. `PIPELINE_ZONES/01_RAW`: acquire data.
2. `PIPELINE_ZONES/02_INTERMEDIATE`: transform raw material into scripts, clip candidates, hooks, and voiceover assets.
3. `PIPELINE_ZONES/03_STAGING`: prepare draft clips and review packages.
4. `PIPELINE_ZONES/04_CURATED`: human-review-ready material for manual posting.

Posting is intentionally manual for now. The pipeline does not auto-post to TikTok, Instagram, or YouTube.

## Source Rights And Safety

We added `LEGAL_AND_SOURCING/source_rights_checklist.md`.

Safest footage:

- Original footage.
- Creator-provided footage.
- Public domain footage.
- Creative Commons footage with attribution.
- Licensed stock footage.

Avoid:

- Copyrighted documentary clips.
- TV/news footage without permission.
- Random YouTube downloads without rights.

The media page content calendar now includes `source_url` and `rights_status`.

## Download Intake System

We added date-based batching:

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

Current test links:

```text
https://www.youtube.com/watch?v=qiiCgnznuFc&list=PLRBp0Fe2GpgnIh0AiYKh7o7HnYAej-5ph | test | approved
https://www.youtube.com/watch?v=USgWGbUdJwM | nature_documentary | unknown
```

Safe mode downloads only:

- `approved`
- `public_domain`
- `creative_commons`

Unknown links are skipped in safe mode.

## Downloader Behavior

The downloader is:

```text
CREATOR_CLIPPING_BUSINESS/AUTOMATION/batch_download.py
```

It:

1. Detects the latest dated folder in `POST_LINKS`.
2. Reads `source_links.txt`.
3. Downloads approved links into that batch's `downloaded_videos` folder.
4. Copies the downloaded file into `PIPELINE_ZONES/01_RAW/DOWNLOADED_MEDIA/{topic}/`.
5. Writes `.video_metadata.json` files.
6. Logs failures to `download_errors.log`.
7. Prints a summary.

Important fix made:

- The script now uses the active Python environment's `yt_dlp` module instead of whichever `yt-dlp` happens to be on PATH.
- It uses `--no-playlist`.
- It prefers format `18`, a simple MP4 with audio and video, to avoid needing ffmpeg during basic ingestion tests.
- It handles Windows Unicode filenames more safely.

## Download Test

We tested this link:

```text
https://www.youtube.com/watch?v=qiiCgnznuFc&list=PLRBp0Fe2GpgnIh0AiYKh7o7HnYAej-5ph
```

The pipeline downloaded it successfully and skipped the unknown Lake Natron link.

Local output:

```text
CREATOR_CLIPPING_BUSINESS/POST_LINKS/2026-05-03/downloaded_videos/
```

RAW organized output:

```text
CREATOR_CLIPPING_BUSINESS/PIPELINE_ZONES/01_RAW/DOWNLOADED_MEDIA/test/
```

The successful run took about 5 seconds through the pipeline.

Generated media and metadata are ignored by Git.

## Central Pipeline Runner

We added:

```text
CREATOR_CLIPPING_BUSINESS/AUTOMATION/run_pipeline.py
```

Commands:

```powershell
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage download
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage transform
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage edit
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage curate
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\run_pipeline.py --stage all
```

Behavior:

- `download`: source links into RAW.
- `transform`: RAW metadata into clip plans and starter scripts.
- `edit`: clip plans plus voiceover assets into draft packages.
- `curate`: draft packages into human-review-ready packages.
- `all`: runs through curate and stops at human review.

## AI Voiceover Stage

We added:

```text
CREATOR_CLIPPING_BUSINESS/AUTOMATION/tts_generate.py
```

Flow:

1. `transform` creates `script.txt` under `PIPELINE_ZONES/02_INTERMEDIATE/SCRIPTS/{topic}/`.
2. `edit` calls the TTS generator.
3. Voiceover outputs go to `PIPELINE_ZONES/02_INTERMEDIATE/VOICEOVER/{topic}/`.

If configured for ElevenLabs and an API key exists:

```text
voiceover.mp3
metadata.json
```

If no key exists or `TTS_PROVIDER=stub`:

```text
voiceover_placeholder.txt
metadata.json
```

Environment variables:

```text
TTS_PROVIDER=stub
TTS_VOICE=Adam
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB
ELEVENLABS_MODEL=eleven_multilingual_v2
```

Stub mode was tested successfully.

## Git And Pushes

Recent pushed commits:

- `dac8ebd Fix downloader and approve test source link`
- `de9c35e Add creator clipping TTS voiceover stage`

Generated raw media, audio, downloaded videos, intermediate artifacts, and staging draft artifacts are ignored by Git.

## Current State

The repository is set up to:

1. Intake approved source links.
2. Download raw video safely.
3. Store raw media in dated batches and topic-organized RAW folders.
4. Generate clip plans and starter scripts.
5. Generate or stub voiceover audio.
6. Build staging draft packages.
7. Stop at human review before posting.

Next likely improvements:

- Add transcript extraction.
- Add better AI hook/script generation.
- Add actual video editing/export integration.
- Add subtitle generation.
- Add separate media-page and client-service lanes once volume increases.
- Add a quality review checklist before anything moves to CURATED.
