"""Tests for storage path generation."""

from __future__ import annotations

import os

from ytce.storage.paths import (
    channel_comments_dir,
    channel_output_dir,
    channel_videos_path,
    video_comments_filename,
    video_comments_path,
)


def test_channel_videos_path():
    """Test channel videos path generation."""
    path = channel_videos_path("@testchannel")
    assert path == os.path.join("data", "testchannel", "videos.json")
    
    # With custom base dir
    path = channel_videos_path("@testchannel", base_dir="output")
    assert path == os.path.join("output", "testchannel", "videos.json")


def test_video_comments_path():
    """Test video comments path generation."""
    path = video_comments_path("dQw4w9WgXcQ")
    assert path == os.path.join("data", "dQw4w9WgXcQ", "comments.jsonl")


def test_channel_output_dir():
    """Test channel output directory generation."""
    path = channel_output_dir("@realmadrid")
    assert path == os.path.join("data", "realmadrid")


def test_channel_comments_dir():
    """Test comments subdirectory generation."""
    path = channel_comments_dir("data/testchannel")
    assert path == os.path.join("data", "testchannel", "comments")


def test_video_comments_filename():
    """Test video comments filename generation."""
    filename = video_comments_filename(1, "abc123")
    assert filename == "0001_abc123.jsonl"
    
    filename = video_comments_filename(42, "xyz789")
    assert filename == "0042_xyz789.jsonl"
    
    filename = video_comments_filename(999, "test")
    assert filename == "0999_test.jsonl"


def test_sanitize_channel_handle():
    """Test that @ symbols are removed from channel handles."""
    path = channel_output_dir("@channelname")
    assert "@" not in path
    assert "channelname" in path

