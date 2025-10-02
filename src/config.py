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
    """Save current configuration state (single source of truth) to JSON file.
    
    This saves the complete merged configuration that represents the current
    state in memory. The saved config will include all merged values from
    all input sources (config file, env vars, CLI args, interactive selections).
    """
    try:
        # Create a clean copy without metadata for saving
        clean_config = {k: v for k, v in config.items() if not k.startswith("_")}
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(clean_config, f, indent=2, ensure_ascii=False)
        
        logger.info("Configuration saved to %s (from single source of truth)", config_file)
        return True
    except (OSError, TypeError) as e:
        logger.error("Failed to save config file '%s': %s", config_file, e)
        return False


def build_complete_config(config_file: str, args, interactive_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build complete configuration from all input sources in priority order.
    
    This creates the single source of truth by merging all inputs:
    1. Config file (may not exist) - uses as defaults
    2. Environment variables (may not exist) - overrides existing values
    3. CLI arguments (may not exist) - overrides existing values
    4. Interactive selections (may not exist) - overrides existing values
    
    Returns the final merged configuration that serves as the single source of truth.
    All subsequent operations should read from this merged configuration only.
    """
    logger.info("Building complete configuration from all input sources")
    
    # Step 1: Load config file and apply environment variables
    config = load_config(config_file)
    
    # Step 2: Apply CLI argument overrides
    config = _apply_cli_overrides(config, args)
    
    # Step 3: Apply interactive selections if provided
    if interactive_config:
        config = _merge_interactive_config(config, interactive_config)
        logger.info("Applied interactive selections to configuration")
    
    # Step 4: Add runtime flags (already processed through env vars and CLI)
    config["dry_run"] = args.dry_run or config.get("dry_run", False)
    config["non_interactive"] = args.non_interactive or config.get("non_interactive", False)
    config["debug"] = args.debug or config.get("debug", False)
    
    # Add metadata about configuration sources for debugging
    config["_config_metadata"] = {
        "config_file": config_file,
        "has_interactive_selections": interactive_config is not None,
        "created_at": "build_complete_config"
    }
    
    logger.info("Configuration built successfully - single source of truth created")
    return config


def _apply_cli_overrides(config: Dict[str, Any], args) -> Dict[str, Any]:
    """Apply CLI argument overrides to configuration (step 3 in priority order)"""
    # Create a deep copy to avoid modifying the original
    import copy
    updated_config = copy.deepcopy(config)

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


def _merge_interactive_config(config: Dict[str, Any], interactive_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge interactive selections into configuration (step 4 in priority order)"""
    import copy
    merged_config = copy.deepcopy(config)
    
    # Interactive selections override all previous values
    for section, values in interactive_config.items():
        if isinstance(values, dict):
            merged_config.setdefault(section, {}).update(values)
        else:
            merged_config[section] = values
    
    return merged_config


# Legacy function for backward compatibility - will be removed
def apply_cli_overrides(config: Dict[str, Any], args) -> Dict[str, Any]:
    """Legacy function - use build_complete_config instead"""
    return _apply_cli_overrides(config, args)
