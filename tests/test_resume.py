"""Tests for resume logic."""

from __future__ import annotations

import os
import tempfile

from ytce.storage.resume import should_skip_existing


def test_should_skip_existing_file_exists():
    """Test skip logic when file exists."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")  # Write some content so file is not empty
        temp_path = f.name
    
    try:
        # Should skip when file exists and resume=True
        assert should_skip_existing(temp_path, resume=True) is True
        
        # Should not skip when resume=False
        assert should_skip_existing(temp_path, resume=False) is False
    finally:
        os.unlink(temp_path)


def test_should_skip_existing_file_missing():
    """Test skip logic when file doesn't exist."""
    nonexistent = "/tmp/nonexistent_file_that_should_not_exist.jsonl"
    
    # Should not skip when file doesn't exist (regardless of resume flag)
    assert should_skip_existing(nonexistent, resume=True) is False
    assert should_skip_existing(nonexistent, resume=False) is False

