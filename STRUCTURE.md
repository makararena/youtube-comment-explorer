# Project Structure Documentation

## Overview

YouTube Comment Explorer - unified tool for scraping YouTube data without API:
- Channel videos metadata (newest -> oldest)
- Video comments (with sorting and pagination)
- Recursive channel + comments pipeline
- Configuration management via ytce.yaml
- Beautiful progress output with emojis

## Directory Layout

```
youtube-comment-explorer/
|-- src/
|   `-- ytce/                        # Main python package
|       |-- __init__.py
|       |-- __main__.py              # python -m ytce
|       |-- config.py                # Configuration management
|       |-- cli/                     # CLI interface
|       |   `-- main.py
|       |-- pipelines/               # High-level workflows
|       |   |-- channel_videos.py
|       |   |-- video_comments.py
|       |   `-- channel_comments.py
|       |-- youtube/                 # YouTube primitives
|       |   |-- session.py
|       |   |-- html.py
|       |   |-- extractors.py
|       |   |-- innertube.py
|       |   |-- pagination.py
|       |   |-- channel_videos.py
|       |   `-- comments.py
|       |-- storage/                 # output / fs
|       |   |-- paths.py
|       |   `-- writers.py
|       |-- models/                  # typed structures
|       |   |-- video.py
|       |   `-- comment.py
|       `-- utils/
|           |-- logging.py
|           |-- parsing.py
|           |-- helpers.py
|           `-- progress.py
|-- data/                            # All exports (auto-created, gitignored)
|   `-- .gitkeep                     # Keep folder in git
|-- docs/
|   |-- commands.txt                 # Legacy reference
|   |-- QUICK_REFERENCE.md           # Quick command reference
|   `-- ytce.yaml.example            # Example config file
|-- scripts/                         # Dev/debug scripts
|-- tests/
|-- requirements.txt                 # Python dependencies
|-- pyproject.toml
|-- LICENSE
|-- README.md
|-- STRUCTURE.md
`-- ytce.yaml                        # Config file (created by ytce init)
```

## Module Responsibilities

### `src/ytce/cli/main.py` (Main CLI)
- Unified command-line interface
- Five subcommands: `init`, `channel`, `video`, `comments`, `open`
- Auto-generates output paths in `data/` folder
- Loads configuration from ytce.yaml
- Orchestrates calls to pipelines

### `src/ytce/pipelines/`
- `channel_videos.py`: exports videos metadata JSON
- `video_comments.py`: exports comments JSONL for a single video
- `channel_comments.py`: exports channel videos + per-video comments JSONL

### `src/ytce/youtube/`
- `session.py`: session headers and consent bypass
- `html.py`: `fetch_html()`
- `extractors.py`: `extract_ytcfg()`, `extract_ytinitialdata()`
- `innertube.py`: InnerTube API requests
- `pagination.py`: continuation helpers, `search_dict()`
- `channel_videos.py`: `YoutubeChannelVideosScraper`
- `comments.py`: `YoutubeCommentDownloader`

### `src/ytce/storage/`
- `paths.py`: default output paths
- `writers.py`: JSON and JSONL writers

## Data Flow

### 1. Init Command
```
User -> ytce init
  -> config.init_project()
  -> Creates data/ directory
  -> Creates ytce.yaml config file
```

### 2. Channel Command (with comments)
```
User -> ytce channel @channel
  -> config.load_config()
  -> pipelines.channel_comments
  -> youtube.channel_videos + youtube.comments
  -> data/<channel>/videos.json
  -> data/<channel>/comments/NNNN_<videoId>.jsonl
```

### 3. Channel Command (videos only)
```
User -> ytce channel @channel --videos-only
  -> config.load_config()
  -> pipelines.channel_videos
  -> youtube.channel_videos + youtube.*
  -> data/<channel>/videos.json
```

### 4. Comments Command
```
User -> ytce comments VIDEO_ID
  -> config.load_config()
  -> pipelines.video_comments
  -> youtube.comments + youtube.*
  -> data/<video_id>/comments.jsonl
```

### 5. Open Command
```
User -> ytce open @channel
  -> Detects output directory
  -> Opens in system file manager
```

## Key Features

### Auto-Path Generation
- Default paths: `data/<export-name>/`
- Sanitizes channel/video IDs for safe folder names
- Creates directories automatically
- Optional custom paths via `-o` or `--out-dir`

### Configuration Management
- `ytce.yaml` for project-level defaults
- Smart defaults from config file
- Command-line flags override config
- Graceful degradation if PyYAML not installed

### Fresh Scraping
- Each channel scrape starts fresh, deleting any existing data
- Simple and predictable behavior
- No complex state management

### Progress Tracking
- Beautiful emoji-based progress indicators
- Real-time statistics with percentages and ETA
- Data size tracking (KB/MB/GB)
- Comment count per video
- Final statistics summary box
- Ctrl+C safe interruption with confirmation
- Error handling with clear messages

### Error Handling
- Consent redirect bypass
- Robust JSON extraction
- Continuation token fallback

## Output Formats

### Videos JSON
```json
{
  "channel_id": "@channelname",
  "total_videos": 123,
  "videos": [
    {
      "order": 1,
      "video_id": "abc123",
      "title": "Video Title",
      "title_length": 11,
      "view_count": 123456,
      "view_count_raw": "123K views",
      "length": "10:25",
      "length_minutes": 10.417,
      "thumbnail_url": "https://...",
      "url": "https://www.youtube.com/watch?v=abc123",
      "channel_id": "UC..."
    }
  ]
}
```

### Comments JSONL
Each line is a JSON object:
```json
{"cid": "...", "text": "Comment text", "text_length": 12, "time": "2 days ago", "author": "@user", "channel": "UC...", "votes": "5", "replies": "2", "photo": "https://...", "heart": false, "reply": false}
```

## Dependencies

- `requests` - HTTP client for web scraping
- `pyyaml` - YAML config file support
- Python 3.7+ - type hints, f-strings

## Git Configuration

### `.gitignore`
- Ignores `data/*` (except `.gitkeep`)
- Ignores `venv/`, `__pycache__/`, `*.pyc`
- Ignores `*.json`, `*.jsonl` (except in data/)

### Tracked Files
- Source code (`.py`)
- Documentation (`.md`, `.txt`)
- Config files (`requirements.txt`, `pyproject.toml`, `LICENSE`)
- `data/.gitkeep` (keeps folder in repo)

## Development Notes

### Adding New Features
1. Add shared utilities to `src/ytce/youtube/`
2. Extend pipelines in `src/ytce/pipelines/`
3. Update CLI in `src/ytce/cli/main.py`
4. Update README.md

### Testing
```bash
# Install in editable mode
pip install -e .

# Initialize project
ytce init

# Quick test
ytce channel @test --limit 1
ytce comments VIDEO_ID --limit 1

# Check data folder
find data -type f

# Open output
ytce open @test
```

### Code Style
- Type hints for function signatures
- Docstrings for public methods
