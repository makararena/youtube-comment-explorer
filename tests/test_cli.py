"""Tests for CLI argument parsing."""

from __future__ import annotations

from ytce.cli.main import build_parser


def test_parser_init_command():
    """Test ytce init command parsing."""
    parser = build_parser()
    args = parser.parse_args(["init"])
    assert args.cmd == "init"


def test_parser_channel_command():
    """Test ytce channel command parsing."""
    parser = build_parser()
    args = parser.parse_args(["channel", "@testchannel"])
    assert args.cmd == "channel"
    assert args.channel_id == "@testchannel"


def test_parser_channel_with_limit():
    """Test ytce channel command with --limit flag."""
    parser = build_parser()
    args = parser.parse_args(["channel", "@test", "--limit", "5"])
    assert args.limit == 5


def test_parser_channel_videos_only():
    """Test ytce channel command with --videos-only flag."""
    parser = build_parser()
    args = parser.parse_args(["channel", "@test", "--videos-only"])
    assert args.videos_only is True


def test_parser_channel_dry_run():
    """Test ytce channel command with --dry-run flag."""
    parser = build_parser()
    args = parser.parse_args(["channel", "@test", "--dry-run"])
    assert args.dry_run is True


def test_parser_comments_command():
    """Test ytce comments command parsing."""
    parser = build_parser()
    args = parser.parse_args(["comments", "dQw4w9WgXcQ"])
    assert args.cmd == "comments"
    assert args.video_id == "dQw4w9WgXcQ"


def test_parser_comments_with_limit():
    """Test ytce comments command with --limit flag."""
    parser = build_parser()
    args = parser.parse_args(["comments", "abc123", "--limit", "100"])
    assert args.limit == 100


def test_parser_open_command():
    """Test ytce open command parsing."""
    parser = build_parser()
    args = parser.parse_args(["open", "@testchannel"])
    assert args.cmd == "open"
    assert args.identifier == "@testchannel"


def test_parser_version():
    """Test --version flag."""
    parser = build_parser()
    # Version flag exits, so we just check it's registered
    assert any("--version" in action.option_strings for action in parser._actions)

