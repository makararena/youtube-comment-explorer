# Tests

This directory contains the test suite for ytce.

## Running Tests

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_paths.py

# Run with verbose output
pytest -v tests/

# Run with coverage
pip install pytest-cov
pytest --cov=ytce tests/
```

## Test Structure

- `test_paths.py` - Storage path generation
- `test_resume.py` - Resume logic
- `test_config.py` - Configuration management
- `test_cli.py` - CLI argument parsing
- `test_errors.py` - Error handling
- `test_version.py` - Version information

## Writing Tests

Follow the existing patterns:

```python
def test_feature_name():
    """Test description."""
    # Arrange
    input_data = "test"
    
    # Act
    result = process(input_data)
    
    # Assert
    assert result == expected
```

## What We Test

- ✅ Path generation
- ✅ Argument parsing
- ✅ Configuration loading
- ✅ Resume logic
- ✅ Error handling
- ✅ Exit codes

## What We Don't Test

- ❌ Actual YouTube scraping (too fragile, requires network)
- ❌ HTML parsing (YouTube structure changes frequently)
- ❌ Real file I/O in pipelines (tested via integration tests)

## Mocking

Use mocks for external dependencies:

```python
from unittest.mock import Mock, patch

@patch("ytce.youtube.html.fetch_html")
def test_scraper(mock_fetch):
    mock_fetch.return_value = "<html>...</html>"
    # Your test here
```

## CI Integration

These tests run automatically on:
- Pull requests
- Commits to main
- Release tags

All tests must pass before merging.

