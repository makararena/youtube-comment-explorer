from __future__ import annotations

import re
from typing import List


def parse_channels_file(file_path: str) -> List[str]:
    """
    Parse a channels file and extract valid channel references.
    
    Supports:
    - @handle
    - https://www.youtube.com/@handle
    - https://www.youtube.com/channel/UC...
    - /channel/UC...
    
    Ignores:
    - Empty lines
    - Lines starting with #
    - Whitespace
    
    Args:
        file_path: Path to channels file
    
    Returns:
        List of channel identifiers
    
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    channels = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Extract channel reference
            channel = extract_channel_ref(line)
            
            if channel:
                channels.append(channel)
            else:
                # Log warning but continue (don't fail)
                print(f"⚠️  Line {line_num}: Skipping invalid channel reference: {line}")
    
    return channels


def extract_channel_ref(text: str) -> str | None:
    """
    Extract channel reference from various formats.
    
    Returns:
        Channel identifier (@handle or channel ID) or None if invalid
    """
    text = text.strip()
    
    # Already a handle
    if text.startswith('@'):
        return text
    
    # Full URL with @handle
    match = re.search(r'youtube\.com/@([a-zA-Z0-9_-]+)', text)
    if match:
        return f"@{match.group(1)}"
    
    # Full URL with /channel/UC...
    match = re.search(r'youtube\.com/channel/(UC[a-zA-Z0-9_-]+)', text)
    if match:
        return match.group(1)
    
    # Path format /channel/UC...
    match = re.search(r'^/?channel/(UC[a-zA-Z0-9_-]+)', text)
    if match:
        return match.group(1)
    
    # Direct channel ID
    if re.match(r'^UC[a-zA-Z0-9_-]+$', text):
        return text
    
    return None

