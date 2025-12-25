"""Configuration management for ytce."""

from __future__ import annotations

import os
from typing import Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


DEFAULT_CONFIG = {
    "output_dir": "data",
    "language": "en",
    "comment_sort": "recent",
}

CONFIG_FILE = "ytce.yaml"
CHANNELS_FILE = "channels.txt"

CHANNELS_TEMPLATE = """# List of YouTube channels to scrape
# One channel per line
# Supported formats:
#   - @handle
#   - https://www.youtube.com/@handle
#   - https://www.youtube.com/channel/UC...
#   - /channel/UC...
#   - UC... (channel ID)
#
# Lines starting with # are comments and will be ignored
# Empty lines are ignored

@skryp
@errornil
"""


def load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """Load configuration from ytce.yaml or return defaults."""
    path = config_path or CONFIG_FILE
    
    if not os.path.exists(path):
        return DEFAULT_CONFIG.copy()
    
    if not HAS_YAML:
        print(f"Warning: PyYAML not installed, using defaults. Install with: pip install pyyaml")
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        
        # Merge with defaults
        config = DEFAULT_CONFIG.copy()
        config.update(user_config)
        return config
    except Exception as e:
        print(f"Warning: Failed to load {path}: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any], config_path: Optional[str] = None) -> None:
    """Save configuration to ytce.yaml."""
    path = config_path or CONFIG_FILE
    
    if not HAS_YAML:
        # Fallback: write as simple key=value format
        with open(path, "w", encoding="utf-8") as f:
            f.write("# ytce configuration\n")
            f.write("# Note: PyYAML not installed. Using simple format.\n\n")
            for key, value in config.items():
                f.write(f"{key}: {value}\n")
        return
    
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def init_project(output_dir: Optional[str] = None) -> None:
    """Initialize a new ytce project with config and directories."""
    config = DEFAULT_CONFIG.copy()
    
    if output_dir:
        config["output_dir"] = output_dir
    
    # Create output directory
    data_dir = config["output_dir"]
    os.makedirs(data_dir, exist_ok=True)
    
    # Save config file (if it doesn't exist)
    if not os.path.exists(CONFIG_FILE):
        save_config(config)
        print(f"✔ Config file: ./{CONFIG_FILE}")
    else:
        print(f"⚠️  Config file already exists: ./{CONFIG_FILE}")
    
    # Create channels.txt template (if it doesn't exist)
    if not os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
            f.write(CHANNELS_TEMPLATE)
        print(f"✔ Channels file: ./{CHANNELS_FILE}")
    else:
        print(f"⚠️  Channels file already exists: ./{CHANNELS_FILE}")
    
    # Success messages
    print("✔ Project initialized")
    print(f"✔ Output directory: ./{data_dir}")

