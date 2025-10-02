"""
Configuration Management

Handles loading, saving, and managing configuration files.
"""

import json
import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from JSON file, handling JSONC comments"""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove JSONC comments (// and /* */)
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to load config file '%s': %s", config_file, e)
        return {}


def save_config(config: Dict[str, Any], config_file: str) -> bool:
    """Save configuration to JSON file"""
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except (OSError, TypeError) as e:
        logger.error("Failed to save config file '%s': %s", config_file, e)
        return False


def apply_cli_overrides(config: Dict[str, Any], args) -> Dict[str, Any]:
    """Apply CLI argument overrides to config with priority: config file > CLI args > interactive"""
    # Create a copy to avoid modifying the original
    updated_config = config.copy()

    # Source configuration overrides
    if args.source_url:
        updated_config.setdefault("source", {})["base_url"] = args.source_url
    if args.source_api_key:
        updated_config.setdefault("source", {})["api_key"] = args.source_api_key
    if args.source_org:
        updated_config.setdefault("source", {})["org"] = args.source_org
    if args.source_project:
        updated_config.setdefault("source", {})["project"] = args.source_project

    # Destination configuration overrides
    if args.dest_url:
        updated_config.setdefault("destination", {})["base_url"] = args.dest_url
    if args.dest_api_key:
        updated_config.setdefault("destination", {})["api_key"] = args.dest_api_key
    if args.dest_org:
        updated_config.setdefault("destination", {})["org"] = args.dest_org
    if args.dest_project:
        updated_config.setdefault("destination", {})["project"] = args.dest_project

    # Migration options overrides
    options = updated_config.setdefault("options", {})

    # Handle migrate_input_sets (CLI args override config)
    if args.migrate_input_sets:
        options["migrate_input_sets"] = True
    elif args.no_migrate_input_sets:
        options["migrate_input_sets"] = False

    # Handle skip_existing (CLI args override config)
    if args.skip_existing:
        options["skip_existing"] = True
    elif args.no_skip_existing:
        options["skip_existing"] = False

    return updated_config
