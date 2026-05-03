import subprocess
from pathlib import Path

# Input file with links
links_file = "links.txt"

# Output directory
output_path = r"C:\Users\Nisarg\Documents\GitHub\001_first_repo\YOUTUBE_CLIPPING\CLIPS_RAW_VIDEO"

# Ensure the output path exists
Path(output_path).mkdir(parents=True, exist_ok=True)

# Read all links from the txt file
with open(links_file, "r") as f:
    links = [line.strip() for line in f if line.strip()]

total_links = len(links)

# Download each link using yt-dlp
for i, link in enumerate(links, start=1):
    print(f"\n[{i}/{total_links}] Downloading: {link}")
    
    try:
        result = subprocess.run([
            "yt-dlp",
            link,
            "-o", f"{output_path}\\%(title)s.%(ext)s"
        ], check=True)
        print(f"[{i}/{total_links}] ✅ Success")
    except subprocess.CalledProcessError:
        print(f"[{i}/{total_links}] ❌ Failed to download: {link}")
