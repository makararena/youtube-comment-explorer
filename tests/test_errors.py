"""Tests for error handling."""

from __future__ import annotations

from ytce.errors import (
    EXIT_INTERNAL_ERROR,
    EXIT_NETWORK_ERROR,
    EXIT_SUCCESS,
    EXIT_USER_ERROR,
    InternalError,
    NetworkError,
    UserError,
    handle_error,
)


def test_user_error_exit_code():
    """Test that UserError has correct exit code."""
    error = UserError("Invalid input")
    assert error.exit_code == EXIT_USER_ERROR


def test_network_error_exit_code():
    """Test that NetworkError has correct exit code."""
    error = NetworkError("Connection failed")
    assert error.exit_code == EXIT_NETWORK_ERROR


def test_internal_error_exit_code():
    """Test that InternalError has correct exit code."""
    error = InternalError("Something went wrong")
    assert error.exit_code == EXIT_INTERNAL_ERROR


def test_handle_user_error():
    """Test handling of UserError."""
    error = UserError("Invalid argument", hint="Use --help for options")
    exit_code = handle_error(error, debug=False)
    assert exit_code == EXIT_USER_ERROR


def test_handle_network_error():
    """Test handling of NetworkError."""
    error = NetworkError("YouTube unreachable")
    exit_code = handle_error(error, debug=False)
    assert exit_code == EXIT_NETWORK_ERROR


def test_handle_keyboard_interrupt():
    """Test handling of KeyboardInterrupt."""
    error = KeyboardInterrupt()
    exit_code = handle_error(error, debug=False)
    assert exit_code == EXIT_USER_ERROR


def test_handle_key_error():
    """Test handling of KeyError (YouTube structure change)."""
    error = KeyError("continuation")
    exit_code = handle_error(error, debug=False)
    assert exit_code == EXIT_NETWORK_ERROR


def test_handle_unknown_error():
    """Test handling of unknown error."""
    error = ValueError("Unknown error")
    exit_code = handle_error(error, debug=False)
    assert exit_code == EXIT_INTERNAL_ERROR

