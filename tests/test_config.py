"""Tests for configuration management."""

from __future__ import annotations

import os
import tempfile

from ytce.config import DEFAULT_CONFIG, load_config, save_config


def test_default_config():
    """Test default configuration values."""
    assert "output_dir" in DEFAULT_CONFIG
    assert "language" in DEFAULT_CONFIG
    assert "comment_sort" in DEFAULT_CONFIG


def test_load_config_no_file():
    """Test loading config when file doesn't exist."""
    config = load_config("/nonexistent/ytce.yaml")
    assert config == DEFAULT_CONFIG


def test_save_and_load_config():
    """Test saving and loading configuration."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = f.name
    
    try:
        # Save custom config
        custom_config = DEFAULT_CONFIG.copy()
        custom_config["language"] = "es"
        custom_config["output_dir"] = "custom"
        
        save_config(custom_config, temp_path)
        
        # Load it back
        loaded = load_config(temp_path)
        assert loaded["language"] == "es"
        assert loaded["output_dir"] == "custom"
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

