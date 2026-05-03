# Post Links

This is the intake queue for bulk source ingestion.

Create one folder per batch using `YYYY-MM-DD`.

Each batch folder should contain:

```text
source_links.txt
downloaded_videos/
```

Each line in `source_links.txt` uses:

```text
url | topic | rights_status
```

The downloader uses the latest dated folder by default. It downloads into that batch's `downloaded_videos` folder, then copies organized files into `PIPELINE_ZONES/01_RAW/DOWNLOADED_MEDIA/{topic}`.

Each successful video gets a metadata sidecar named like `video_name.video_metadata.json`.

`DOWNLOAD_MODE=safe` only downloads links marked:

- `approved`
- `public_domain`
- `creative_commons`

Use `--download-mode all` when you intentionally want to ingest every valid link for review.
