# YouTube Comment Explorer

Download YouTube videos metadata and comments without using the YouTube API.

## TL;DR

```bash
pip install -e .
ytce channel @realmadrid
```

That's it! Your data will be in `data/realmadrid/`

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Initialize (optional but recommended)

```bash
ytce init
```

This creates:
- `data/` directory for outputs
- `ytce.yaml` config file with smart defaults

### 3. Download data

```bash
# Download channel videos + all comments
ytce channel @skryp

# Download only videos metadata (no comments)
ytce channel @skryp --videos-only

# Download comments for a specific video
ytce comments dQw4w9WgXcQ

# Open the downloaded data
ytce open @skryp
```

## Usage

### Channel (videos + comments)

Download all videos and comments from a channel:

```bash
ytce channel @channelname
```

This will:
1. Fetch all videos from the channel
2. Download comments for each video
3. Save everything to `data/channelname/`

**Options:**
- `--videos-only` - Download only videos metadata, skip comments
- `--limit N` - Process only first N videos
- `--per-video-limit N` - Download max N comments per video
- `--sort {recent,popular}` - Comment sort order (default: from config)
- `--language CODE` - Language for YouTube UI (default: from config)
- `--no-resume` - Re-download everything (ignore existing files)

**Examples:**

```bash
# Quick test with 5 videos
ytce channel @realmadrid --limit 5

# Get popular comments instead of recent
ytce channel @skryp --sort popular

# Limit comments per video
ytce channel @channelname --limit 10 --per-video-limit 100
```

### Comments (single video)

Download comments for one video:

```bash
ytce comments VIDEO_ID
```

**Options:**
- `--limit N` - Download max N comments
- `--sort {recent,popular}` - Sort order
- `--language CODE` - Language code
- `-o PATH` - Custom output path

**Example:**

```bash
ytce comments dQw4w9WgXcQ --limit 500
```

### Open Output Directory

Quickly open the data folder in your file manager:

```bash
ytce open @channelname
ytce open VIDEO_ID
```

## Output Structure

After running `ytce channel @skryp`, you'll get:

```
data/
└── skryp/
    ├── videos.json              # All videos metadata
    └── comments/
        ├── 0001_VIDEO_ID.jsonl  # Comments for video 1
        ├── 0002_VIDEO_ID.jsonl  # Comments for video 2
        └── ...
```

### Videos JSON

Single JSON file with all videos:

```json
{
  "channel_id": "@skryp",
  "total_videos": 312,
  "scraped_at": "2025-01-05T12:34:56+00:00",
  "source": "ytce/0.2.0",
  "videos": [
    {
      "video_id": "abc123",
      "title": "Video Title",
      "order": 1,
      "view_count": 123456,
      "view_count_raw": "123,456 views",
      "length": "10:25",
      "thumbnail_url": "https://...",
      "url": "https://www.youtube.com/watch?v=abc123",
      "channel_id": "UC..."
    }
  ]
}
```

**Guaranteed fields:**
- `channel_id` (string)
- `total_videos` (integer)
- `scraped_at` (ISO 8601 timestamp)
- `source` (string, ytce version)
- `videos` (array)

**Each video object contains:**
- `video_id` (string) - YouTube video ID
- `title` (string)
- `url` (string)
- `order` (integer) - 1 = newest, N = oldest
- `channel_id` (string, may be empty)
- `view_count` (integer or null)
- `view_count_raw` (string)
- `length` (string)
- `thumbnail_url` (string)

### Comments JSONL

Line-delimited JSON (one comment per line):

```jsonl
{"cid": "...", "text": "Great video!", "time": "2 days ago", "author": "@user", "channel": "UC...", "votes": "5", "replies": "2", "photo": "https://...", "heart": false, "reply": false, "scraped_at": "2025-01-05T12:34:56+00:00", "source": "ytce/0.2.0"}
{"cid": "...", "text": "Another comment", "time": "1 week ago", "author": "@another", "channel": "UC...", "votes": "12", "replies": "0", "photo": "https://...", "heart": true, "reply": false, "scraped_at": "2025-01-05T12:34:56+00:00", "source": "ytce/0.2.0"}
```

**Guaranteed fields (each comment):**
- `cid` (string) - Comment ID
- `text` (string) - Comment text
- `time` (string) - Relative time (e.g., "2 days ago")
- `author` (string) - Author username
- `channel` (string) - Author channel ID
- `votes` (string) - Like count
- `replies` (string) - Reply count
- `photo` (string) - Author avatar URL
- `heart` (boolean) - Has creator heart
- `reply` (boolean) - Is a reply
- `scraped_at` (string) - ISO 8601 timestamp
- `source` (string) - ytce version

### Format Guarantees

**Stability Promise:**
- ✅ All documented fields will always be present
- ✅ Field types will never change
- ✅ New fields may be added in the future (but never removed)
- ✅ One JSON file = one JSON object
- ✅ One JSONL file = one JSON object per line

This makes ytce safe for:
- Data pipelines
- BI tools
- Machine learning
- Long-term archival

## Configuration

Create `ytce.yaml` in your project root (or run `ytce init`):

```yaml
output_dir: data
language: en
comment_sort: recent
resume: true
```

These become your defaults, so you don't need to pass flags every time.

## Progress Output

You'll see nice progress indicators:

```
▶ Fetching channel: @skryp
✔ Found 312 videos

▶ Processing videos
[001/312] dQw4w9WgXcQ — 1,245 comments
[002/312] xYz123      — comments disabled
[003/312] abc987      — 532 comments
...

✔ Done
✔ Saved to data/skryp/
```

## Features

- **No API Key Required** - Uses YouTube's web interface
- **Smart Resume** - Automatically skips already downloaded videos
- **Config File** - Set defaults once, use everywhere
- **Progress Indicators** - Always know what's happening
- **Auto-organizing** - Clean folder structure

## Requirements

- Python 3.7+
- `requests` library

## Advanced Usage

### Custom Output Directory

```bash
ytce channel @name --out-dir /path/to/custom/location
```

### Debug Mode

```bash
ytce channel @name --debug
```

### Process Specific Range

```bash
# Get first 10 videos only
ytce channel @name --limit 10

# Get 50 comments per video
ytce channel @name --per-video-limit 50
```

## Troubleshooting

### "Failed to extract ytcfg" error
YouTube may have changed their page structure. Debug HTML is saved to `/tmp/youtube_debug.html`.

### Comments not downloading
Check if comments are disabled for the video. The scraper will automatically skip these.

### Module not found
Make sure you installed the package: `pip install -e .`

## Project Structure

```
youtube-comment-explorer/
├── src/
│   └── ytce/                    # Main package
│       ├── cli/                 # CLI interface
│       ├── pipelines/           # High-level workflows
│       ├── youtube/             # YouTube scraping primitives
│       ├── storage/             # File I/O and paths
│       ├── models/              # Data structures
│       ├── utils/               # Helpers
│       └── config.py            # Configuration management
├── data/                        # Downloaded data (gitignored)
├── README.md                    # This file
├── pyproject.toml               # Package configuration
└── requirements.txt             # Dependencies
```

## License

This project incorporates code from [youtube-comment-downloader](https://github.com/egbertbouman/youtube-comment-downloader) by Egbert Bouman (MIT License).

## Notes

- **Rate Limiting**: Built-in delays between requests to respect YouTube's servers
- **No Authentication**: Works without YouTube account login
- **Order Preservation**: Videos are always ordered newest → oldest
