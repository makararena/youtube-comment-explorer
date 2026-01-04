"""
Prompt layer for AI comment analysis.

This module provides prompt compilation functionality that converts TaskConfig
and comments into LLM-ready prompts with strict JSON output requirements.
"""
from ytce.ai.promts.compiler import compile_prompt
from ytce.ai.promts.formatter import format_comments_for_prompt, format_json_schema
from ytce.ai.promts.templates import PROMPT_VERSION, build_base_prompt, get_task_instruction

__all__ = [
    # Main public API
    "compile_prompt",
    # Utilities (may be useful for testing/debugging)
    "format_json_schema",
    "format_comments_for_prompt",
    "get_task_instruction",
    "build_base_prompt",
    # Constants
    "PROMPT_VERSION",
]

