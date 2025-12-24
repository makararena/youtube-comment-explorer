"""Error handling and exit codes for ytce."""

from __future__ import annotations

import sys
from typing import Optional

# Exit codes
EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1
EXIT_NETWORK_ERROR = 2
EXIT_INTERNAL_ERROR = 3


class YtceError(Exception):
    """Base exception for ytce errors."""

    exit_code = EXIT_INTERNAL_ERROR

    def __init__(self, message: str, hint: Optional[str] = None):
        self.message = message
        self.hint = hint
        super().__init__(message)


class UserError(YtceError):
    """User input error (invalid arguments, etc)."""

    exit_code = EXIT_USER_ERROR


class NetworkError(YtceError):
    """Network or YouTube API error."""

    exit_code = EXIT_NETWORK_ERROR


class InternalError(YtceError):
    """Internal bug or unexpected error."""

    exit_code = EXIT_INTERNAL_ERROR


def handle_error(error: Exception, debug: bool = False) -> int:
    """
    Handle an error and return appropriate exit code.
    
    Args:
        error: The exception that occurred
        debug: Whether to show full traceback
    
    Returns:
        Exit code (1, 2, or 3)
    """
    from ytce.utils.progress import print_error, print_warning
    
    if isinstance(error, YtceError):
        print_error(f"Failed: {error.message}")
        if error.hint:
            print_warning(f"Hint: {error.hint}")
        if debug:
            import traceback
            traceback.print_exc()
        return error.exit_code
    
    # Handle common exceptions
    if isinstance(error, KeyboardInterrupt):
        print()  # New line after ^C
        print_warning("Interrupted by user")
        return EXIT_USER_ERROR
    
    if isinstance(error, FileNotFoundError):
        print_error(f"File not found: {error}")
        return EXIT_USER_ERROR
    
    if isinstance(error, PermissionError):
        print_error(f"Permission denied: {error}")
        return EXIT_USER_ERROR
    
    if "KeyError" in str(type(error)) or "AttributeError" in str(type(error)):
        print_error("Failed to parse YouTube response")
        print_warning("Reason: YouTube page structure may have changed")
        print_warning("Hint: Try again later or open an issue on GitHub")
        if debug:
            import traceback
            traceback.print_exc()
        return EXIT_NETWORK_ERROR
    
    # Unknown error
    print_error(f"Unexpected error: {error}")
    print_warning("Hint: Run with --debug for more details")
    if debug:
        import traceback
        traceback.print_exc()
    return EXIT_INTERNAL_ERROR


def exit_with_error(message: str, hint: Optional[str] = None, exit_code: int = EXIT_USER_ERROR) -> None:
    """Print error and exit with code."""
    from ytce.utils.progress import print_error, print_warning
    
    print_error(message)
    if hint:
        print_warning(f"Hint: {hint}")
    sys.exit(exit_code)

