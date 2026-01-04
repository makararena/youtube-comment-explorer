"""Tests for CLI argument parsing."""

from __future__ import annotations

import os
import tempfile

from ytce.cli.main import build_parser, init_questions_yaml
from ytce.errors import EXIT_SUCCESS, EXIT_USER_ERROR


def test_parser_init_command():
    """Test ytce init command parsing."""
    parser = build_parser()
    args = parser.parse_args(["init"])
    assert args.cmd == "init"


def test_parser_analyze_command_defaults():
    """Test ytce analyze command parsing with defaults."""
    parser = build_parser()
    args = parser.parse_args(["analyze"])
    assert args.cmd == "analyze"
    assert args.questions == "questions.yaml"
    assert args.output == "analysis_results.csv"
    assert args.model is None
    assert args.batch_size == 20
    assert args.temperature == 0.0
    assert args.dry_run is False
    assert args.preview_count == 5
    assert args.skip_preview is False


def test_analyze_dry_run_smoke(tmp_path):
    """
    Smoke test for ytce analyze in dry-run mode.

    Creates a minimal comments file + questions.yaml, runs analyze, and verifies
    a CSV is produced.
    """
    import os

    # Minimal comments CSV with custom columns to ensure InputConfig mapping works.
    comments_path = tmp_path / "comments.csv"
    comments_path.write_text("cid,body\nc1,hello\nc2,world\n", encoding="utf-8")

    questions_path = tmp_path / "questions.yaml"
    questions_path.write_text(
        "\n".join(
            [
                "version: 1",
                "input:",
                f"  path: \"{comments_path.as_posix()}\"",
                "  format: csv",
                "  id_field: cid",
                "  text_field: body",
                "custom_prompt: \"\"",
                "tasks:",
                "  - id: sentiment",
                "    type: binary_classification",
                "    question: \"Is this positive?\"",
                "    labels: [\"yes\", \"no\"]",
                "",
            ]
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "out.csv"

    # Run via CLI entrypoint
    from ytce.cli.main import main

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        exit_code = main(["analyze", str(questions_path), "--dry-run", "-o", str(output_path)])
        assert exit_code == EXIT_SUCCESS
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "sentiment_value" in content
    finally:
        os.chdir(cwd)

def test_init_questions_yaml_creates_file():
    """Test that init_questions_yaml creates questions.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            exit_code = init_questions_yaml()
            
            assert exit_code == EXIT_SUCCESS
            assert os.path.exists("questions.yaml")
            
            # Verify content structure
            with open("questions.yaml", "r") as f:
                content = f.read()
                assert "version: 1" in content
                assert "input:" in content
                assert "tasks:" in content
                assert "sentiment" in content
                assert "spam" in content
                assert "topics" in content
                assert "toxicity" in content
                assert "multi_class" in content
                assert "binary_classification" in content
                assert "multi_label" in content
                assert "scoring" in content
        finally:
            os.chdir(original_cwd)


def test_init_questions_yaml_rejects_existing_file():
    """Test that init_questions_yaml refuses to overwrite existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Create an existing file
            with open("questions.yaml", "w") as f:
                f.write("existing content")
            
            exit_code = init_questions_yaml()
            
            assert exit_code == EXIT_USER_ERROR
            
            # Verify original content is preserved
            with open("questions.yaml", "r") as f:
                content = f.read()
                assert content == "existing content"
        finally:
            os.chdir(original_cwd)


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

