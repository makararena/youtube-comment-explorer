"""Tests for version information."""

from __future__ import annotations

from ytce.__version__ import __version__


def test_version_exists():
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_version_format():
    """Test that version follows semver format."""
    parts = __version__.split(".")
    assert len(parts) >= 2  # At least major.minor
    assert parts[0].isdigit()  # Major version is numeric
    assert parts[1].isdigit()  # Minor version is numeric

