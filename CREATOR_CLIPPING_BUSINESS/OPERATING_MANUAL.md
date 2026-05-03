# Creator Clipping Business Operating Manual

This is the central operating document for the creator clipping business. It combines the business strategy, client-service workflow, and the useful knowledge from the older YouTube clipping setup.

## Business Model

This business has two connected tracks:

1. Media page: grow a semi-faceless niche page using transformed short-form content.
2. Client services: sell clipping services to creators and businesses for immediate revenue.

The media page builds skill, proof, and attention. Client services turn that skill into cash flow.

## Core Workflow

Find source content -> download or collect raw material -> identify strong moments -> transform the idea -> edit the short clip -> write caption and CTA -> post -> track performance -> use proof for outreach.

## What We Learned From The Old YouTube Clipping Setup

The older workflow was simple and useful:

- Keep source links in a plain `links.txt` file.
- Use `yt-dlp` to download source videos.
- Store raw videos in a local raw-media folder.
- Keep raw video files out of Git.
- Treat downloaded video as source material, not finished content.

That becomes the new internal workflow for this folder.

## Current Folder Roles

`RAW_MEDIA/CLIPS_RAW_VIDEO`

Local storage for downloaded source videos. Raw media files are ignored by Git. The folder is tracked with `.gitkeep` so the structure exists.

`RAW_MEDIA/source_links.txt`

Current source-link queue for the business. One YouTube URL per line.

`AUTOMATION/batch_download.py`

Current downloader. It reads `RAW_MEDIA/source_links.txt` and downloads videos with `yt-dlp` into this business workspace's raw-media folder. It can also read `YOUTUBE_LINKS_FILE` and `YOUTUBE_DOWNLOAD_DIR` from `.env`.

`SHARED_ASSETS/PROMPTS`

Prompts for selecting moments, writing hooks, creating captions, and finding transformation angles.

`TRACKING`

CSV trackers for content calendars, media-page performance, client leads, and client clip performance.

## Download Workflow

1. Add source URLs to `RAW_MEDIA/source_links.txt`.
2. Activate the repo environment.
3. Run the downloader.
4. Confirm raw files land in `CREATOR_CLIPPING_BUSINESS/RAW_MEDIA/CLIPS_RAW_VIDEO`.
5. Review the raw source and find strong moments.
6. Use prompt files to generate hooks, captions, and transformation angles.
7. Edit into short-form clips.
8. Track posts and performance.

Command:

```powershell
.\.venv\Scripts\Activate.ps1
python CREATOR_CLIPPING_BUSINESS\AUTOMATION\batch_download.py
```

## Transformation Rules

Do not post simple reposts. Before posting, add at least one transformation layer:

- New hook text.
- Added context.
- Commentary or takeaway.
- Storytelling frame.
- Edited pacing.
- B-roll or visual support.
- Caption that summarizes the lesson.
- Clear reason the viewer should care.

For YouTube especially, originality matters. A subtitled repost is weak for monetization and weak for long-term brand building.

## Media Page Execution

Use the media page to practice the full clipping system:

1. Pick one niche.
2. Build around 3-5 content pillars.
3. Post consistently.
4. Track every clip.
5. Review winners weekly.
6. Turn winning formats into repeatable templates.

The goal is not random virality. The goal is a page with a clear audience, consistent taste, and proof that the clipping system works.

## Client Services Execution

Use the client services track for revenue:

1. Find creators already making long-form content.
2. Identify strong short-form moments from their existing videos.
3. Send a short, specific outreach message.
4. Offer a sample or small test package.
5. Deliver clips with hooks, subtitles, captions, and transformation.
6. Track results and turn strong clips into case studies.

## Weekly Operating Rhythm

Monday:

- Pick source videos.
- Add links to the queue.
- Download raw material.

Tuesday:

- Select clip moments.
- Write hooks and captions.

Wednesday and Thursday:

- Edit clips.
- Prepare posts.

Friday:

- Post or schedule.
- Send creator outreach.

Weekend:

- Review performance.
- Update trackers.
- Decide what to repeat next week.

## Next Improvements

- Add transcript extraction.
- Add a source-video tracker CSV.
- Add scoring for clip candidates.
- Add separate raw folders for media page and client work.
