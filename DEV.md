# Developer Documentation

This document contains technical details for developers working on YouTube Comment Explorer.

## Development Setup

### 1. Clone and Setup Environment

```bash
git clone <repo-url>
cd youtube-comment-explorer

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Running Without Installation (Development Mode)

If you want to run the code without installing the package:

```bash
# Set PYTHONPATH so Python can find the ytce module
export PYTHONPATH=src

# Now you can run the module directly
python -m ytce channel @test
```

Or in one line:

```bash
PYTHONPATH=src python -m ytce channel @test
```

### 3. Installing in Editable Mode (Recommended)

For active development, install in editable mode:

```bash
pip install -e .
```

Now you can:
- Run `ytce` from anywhere
- Edit the source code and see changes immediately
- No need to set PYTHONPATH

## Project Architecture

### High-Level Structure

```
ytce/
├── cli/              # User interface
│   └── main.py       # Command-line argument parsing
├── pipelines/        # High-level workflows
│   ├── channel_videos.py
│   ├── video_comments.py
│   └── channel_comments.py
├── youtube/          # Core YouTube scraping primitives
│   ├── session.py        # HTTP session, headers, consent
│   ├── html.py           # HTML fetching
│   ├── extractors.py     # Extract ytcfg and ytInitialData
│   ├── innertube.py      # InnerTube API requests
│   ├── pagination.py     # Continuation tokens
│   ├── channel_videos.py
│   └── comments.py
├── storage/          # File I/O and resume logic
│   ├── paths.py
│   ├── writers.py
│   └── resume.py
├── models/           # Typed data structures
│   ├── video.py
│   └── comment.py
├── utils/            # Helpers
│   ├── logging.py
│   ├── parsing.py
│   ├── helpers.py
│   └── progress.py
└── config.py         # Configuration management
```

### Design Principles

1. **Separation of Concerns**
   - `youtube/` contains pure scraping logic (no file I/O)
   - `storage/` handles all file operations
   - `pipelines/` orchestrates workflows

2. **Reusability**
   - Core YouTube utilities in `youtube/` are shared between pipelines
   - `session.py` handles consent and headers for all scrapers

3. **Resume Capability**
   - `storage/resume.py` provides logic to skip existing files
   - Allows interrupted downloads to continue seamlessly

4. **Order Preservation**
   - Videos maintain YouTube's default order (newest → oldest)
   - `order` field: 1 = newest, N = oldest
   - Uses explicit list traversal (not dict search) to maintain order

## Core Components

### YouTube Session Management

**File:** `youtube/session.py`

Handles:
- User-Agent headers
- Cookie management
- GDPR consent bypass

```python
from ytce.youtube.session import get_session

session = get_session()
response = session.get(url)
```

### HTML Fetching

**File:** `youtube/html.py`

```python
from ytce.youtube.html import fetch_html

html = fetch_html(url, debug=False)
```

### Data Extraction

**File:** `youtube/extractors.py`

Extracts YouTube's embedded config and data:

```python
from ytce.youtube.extractors import extract_ytcfg, extract_ytinitialdata

ytcfg = extract_ytcfg(html)
ytinitialdata = extract_ytinitialdata(html)
```

### InnerTube API

**File:** `youtube/innertube.py`

Makes authenticated AJAX requests to YouTube's InnerTube API:

```python
from ytce.youtube.innertube import innertube_ajax_request

response = innertube_ajax_request(session, endpoint, data, ytcfg)
```

### Pagination

**File:** `youtube/pagination.py`

Utilities for handling continuation tokens:

```python
from ytce.youtube.pagination import search_dict, pick_longest_continuation

continuation = pick_longest_continuation(data)
```

## Adding New Features

### Adding a New Command

1. Add parser in `cli/main.py`:

```python
p_newcmd = sub.add_parser("newcmd", help="Description")
p_newcmd.add_argument("arg1")
# ... add arguments
```

2. Add handler in `main()`:

```python
if args.cmd == "newcmd":
    # Handle the command
    run_newcmd(args.arg1, ...)
    return
```

3. Create pipeline in `pipelines/`:

```python
# pipelines/newcmd.py
def run(*, arg1: str, ...) -> None:
    # Implementation
    pass
```

### Adding Configuration Options

1. Add to `DEFAULT_CONFIG` in `config.py`:

```python
DEFAULT_CONFIG = {
    "output_dir": "data",
    "new_option": "default_value",
    ...
}
```

2. Use in CLI:

```python
config = load_config()
value = args.option or config.get("new_option", "fallback")
```

### Improving Progress Output

Use utilities from `utils/progress.py`:

```python
from ytce.utils.progress import print_step, print_success, print_error

print_step("Starting process...")
# ... do work ...
print_success("Completed successfully!")
```

## Testing

### Manual Testing

```bash
# Test init
ytce init

# Test channel with limit
ytce channel @test --limit 2 --debug

# Test comments
ytce comments dQw4w9WgXcQ --limit 10

# Test open
ytce open @test
```

### Adding Tests

Create tests in `tests/` directory:

```python
# tests/test_something.py
def test_something():
    # Your test here
    pass
```

Run with pytest:

```bash
pytest tests/
```

## Debugging

### Enable Debug Mode

```bash
ytce channel @name --debug
```

This will:
- Show verbose output
- Save debug HTML to `/tmp/youtube_debug.html`
- Print stack traces on errors

### Common Issues

**"Failed to extract ytcfg"**
- YouTube changed page structure
- Check `/tmp/youtube_debug.html`
- Update extractors in `youtube/extractors.py`

**Import errors**
- Make sure PYTHONPATH is set: `export PYTHONPATH=src`
- Or install in editable mode: `pip install -e .`

**Module not found in production**
- User needs to install: `pip install -e .`
- Not a dev issue

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG (if you have one)
3. Test all commands
4. Commit and tag:

```bash
git commit -am "Release v0.2.0"
git tag v0.2.0
git push origin main --tags
```

## Code Style

- Use type hints: `def func(arg: str) -> int:`
- Use `from __future__ import annotations` for forward references
- Follow PEP 8
- Keep functions focused and single-purpose
- Document complex logic with comments

## Dependencies

### Core
- `requests` - HTTP requests

### Optional
- `pyyaml` - Config file support (graceful degradation if missing)

To add a new dependency:

1. Add to `requirements.txt`
2. Add to `pyproject.toml` dependencies
3. Document if optional

## File Formats

### Videos JSON
- Single JSON file
- All videos in one array
- Easy to load entirely into memory

### Comments JSONL
- Line-delimited JSON
- One comment per line
- Supports streaming processing
- Large files don't need to fit in memory

## Performance Considerations

- **Rate Limiting**: Built-in `sleep` between requests (0.1s default)
- **Memory**: Comments are streamed, not loaded all at once
- **Resume**: Avoids re-downloading existing data
- **Pagination**: Handles large channels efficiently

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Update documentation if needed
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

