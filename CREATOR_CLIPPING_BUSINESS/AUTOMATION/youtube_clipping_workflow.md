# YouTube Clipping Workflow

This workflow transfers the useful parts of the older `YOUTUBE_CLIPPING` setup into the creator clipping business system.

## Current Knowledge From Existing Setup

The archived downloader uses:

- `yt-dlp` to download YouTube videos.
- A simple `links.txt` file as the input queue.
- A raw output folder at `YOUTUBE_CLIPPING/CLIPS_RAW_VIDEO`.
- One URL per line.

That is a good starter workflow for collecting source material. The important business rule is that downloaded clips are only raw inputs. They still need selection, transformation, editing, captions, and tracking.

## Folder Roles

`YOUTUBE_CLIPPING/CLIPS_RAW_VIDEO`

Stores raw downloaded videos. Raw media files are ignored by Git, so this folder can hold large source files locally without bloating the repository.

`ARCHIVE/PYTHON_CODE_PROJECTS/links.txt`

Stores source YouTube links, one per line.

`ARCHIVE/PYTHON_CODE_PROJECTS/batch_download.py`

Old starter script that reads `links.txt` and downloads each video with `yt-dlp`.

## Basic Download Flow

1. Add source YouTube URLs to `ARCHIVE/PYTHON_CODE_PROJECTS/links.txt`.
2. Activate the repo virtual environment.
3. Run the downloader script from the folder where `links.txt` lives.
4. Confirm raw videos land in `YOUTUBE_CLIPPING/CLIPS_RAW_VIDEO`.
5. Review the raw video and identify strong moments.
6. Use the prompts in `SHARED_ASSETS/PROMPTS` to create hooks, captions, and transformation angles.
7. Edit the selected clip into a platform-ready short.
8. Track the post in `TRACKING/media_page_content_calendar.csv`.
9. Track results in `TRACKING/media_page_clip_performance.csv`.

## Commands

From the repo root:

```powershell
.\.venv\Scripts\Activate.ps1
cd ARCHIVE\PYTHON_CODE_PROJECTS
python batch_download.py
```

## Transformation Checklist

Before posting anything sourced from YouTube, add at least one layer of transformation:

- New hook text.
- Added context.
- Commentary or takeaway.
- Storytelling frame.
- Edited pacing.
- Visual B-roll.
- Summarized lesson in the caption.

## Monetization Note

Do not treat downloading and reposting as the business. The business is finding valuable moments, reframing them, editing them into original short-form assets, and using the output to grow media pages or sell services to creators.

## Improvement Ideas

Future versions of this workflow could add:

- A cleaner downloader script inside `CREATOR_CLIPPING_BUSINESS/AUTOMATION`.
- A CSV source tracker with creator name, source URL, topic, and usage status.
- Automatic transcript extraction.
- Clip candidate scoring.
- Output folders by niche, client, or platform.
