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
        # Simple approach: only remove // comments that start at beginning of line or after whitespace
        content = re.sub(r'^\s*//.*$', '', content, flags=re.MULTILINE)
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

    # Replication options overrides
    options = updated_config.setdefault("options", {})

    # Handle replicate_input_sets (CLI args override config)
    if hasattr(args, 'replicate_input_sets') and args.replicate_input_sets:
        options["replicate_input_sets"] = True
    elif hasattr(args, 'no_replicate_input_sets') and args.no_replicate_input_sets:
        options["replicate_input_sets"] = False

    # Handle replicate_triggers (CLI args override config)
    # Default is True, only set to False if explicitly disabled
    if hasattr(args, 'no_replicate_triggers') and args.no_replicate_triggers:
        options["replicate_triggers"] = False
    elif hasattr(args, 'replicate_triggers') and args.replicate_triggers:
        options["replicate_triggers"] = True

    # Handle skip_existing (CLI args override config)
    if args.skip_existing:
        options["skip_existing"] = True
    elif args.no_skip_existing:
        options["skip_existing"] = False

    # Handle pipeline specifications from CLI
    if args.pipelines:
        cli_pipelines = []
        for pipeline_id in args.pipelines:
            # Only store identifier, name will be fetched from API when needed
            cli_pipelines.append({"identifier": pipeline_id.strip()})
        
        # CLI pipelines override config file pipelines
        updated_config["pipelines"] = cli_pipelines

    return updated_config
