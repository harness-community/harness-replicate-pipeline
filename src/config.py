"""
Configuration Management

Handles loading, saving, and managing configuration files.
"""

import json
import logging
import os
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from JSON file, handling JSONC comments and environment variable overrides
    
    Always tries to load config file (may not exist), uses as defaults.
    Always tries to load environment variables (may not exist), overrides existing values.
    """
    config = {}
    
    # Step 1: Try to load config file (may not exist)
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove JSONC comments (// and /* */)
        content = re.sub(r'^\s*//.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        config = json.loads(content)
        logger.info("Configuration loaded from %s", config_file)
        
    except FileNotFoundError:
        logger.info("Config file '%s' not found, starting with empty config", config_file)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to parse config file '%s': %s", config_file, e)
        logger.info("Starting with empty config due to parse error")
    
    # Step 2: Always apply environment variable overrides (may not exist)
    config = _apply_env_overrides(config)
    
    return config


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration (step 2 in priority order)"""
    # String configuration options with environment variable support
    string_env_mappings = {
        "HARNESS_SOURCE_URL": ("source", "base_url"),
        "HARNESS_SOURCE_API_KEY": ("source", "api_key"),
        "HARNESS_SOURCE_ORG": ("source", "org"),
        "HARNESS_SOURCE_PROJECT": ("source", "project"),
        "HARNESS_DEST_URL": ("destination", "base_url"),
        "HARNESS_DEST_API_KEY": ("destination", "api_key"),
        "HARNESS_DEST_ORG": ("destination", "org"),
        "HARNESS_DEST_PROJECT": ("destination", "project"),
    }
    
    # Boolean options with environment variable support
    bool_env_mappings = {
        "HARNESS_SKIP_INPUT_SETS": ("options", "skip_input_sets"),
        "HARNESS_SKIP_TRIGGERS": ("options", "skip_triggers"),
        "HARNESS_SKIP_TEMPLATES": ("options", "skip_templates"),
        "HARNESS_UPDATE_EXISTING": ("options", "update_existing"),
        "HARNESS_DRY_RUN": ("", "dry_run"),
        "HARNESS_DEBUG": ("", "debug"),
        "HARNESS_NON_INTERACTIVE": ("", "non_interactive"),
    }
    
    # Apply string environment variables
    for env_var, (section, key) in string_env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            if section:
                config.setdefault(section, {})[key] = env_value
                logger.info("Environment override: %s -> %s.%s=%s", env_var, section, key, env_value)
            else:
                config[key] = env_value
                logger.info("Environment override: %s -> %s=%s", env_var, key, env_value)
    
    # Apply boolean environment variables
    for env_var, (section, key) in bool_env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            # Convert string to boolean
            bool_value = env_value.lower() in ('true', '1', 'yes', 'on')
            if section:
                config.setdefault(section, {})[key] = bool_value
                logger.info("Environment override: %s=%s -> %s.%s=%s", env_var, env_value, section, key, bool_value)
            else:
                config[key] = bool_value
                logger.info("Environment override: %s=%s -> %s=%s", env_var, env_value, key, bool_value)
    
    return config


def save_config(config: Dict[str, Any], config_file: str) -> bool:
    """Save current configuration state in memory to JSON file"""
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except (OSError, TypeError) as e:
        logger.error("Failed to save config file '%s': %s", config_file, e)
        return False


def apply_cli_overrides(config: Dict[str, Any], args) -> Dict[str, Any]:
    """Apply CLI argument overrides to configuration (step 3 in priority order)
    
    Priority: Config file > Environment Variables > CLI arguments > Interactive prompts
    This function applies CLI arguments to config that already has env vars applied.
    """
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

    # Handle skip_input_sets (CLI args override config)
    if hasattr(args, 'skip_input_sets') and args.skip_input_sets:
        options["skip_input_sets"] = True

    # Handle skip_triggers (CLI args override config)
    if hasattr(args, 'skip_triggers') and args.skip_triggers:
        options["skip_triggers"] = True

    # Handle skip_templates (CLI args override config)
    if hasattr(args, 'skip_templates') and args.skip_templates:
        options["skip_templates"] = True

    # Handle update_existing (CLI args override config)
    if hasattr(args, 'update_existing') and args.update_existing:
        options["update_existing"] = True

    # Handle pipeline specifications from CLI
    if args.pipelines:
        cli_pipelines = []
        for pipeline_id in args.pipelines:
            # Only store identifier, name will be fetched from API when needed
            cli_pipelines.append({"identifier": pipeline_id.strip()})
        
        # CLI pipelines override config file pipelines
        updated_config["pipelines"] = cli_pipelines

    return updated_config
