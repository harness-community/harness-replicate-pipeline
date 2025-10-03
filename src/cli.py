"""
Command Line Interface

Main CLI orchestrator that coordinates all components.
"""

import logging
import sys

from .argument_parser import ArgumentParser
from .config import build_complete_config, load_config, save_config, should_save_config
from .logging_utils import setup_logging
from .mode_handlers import ModeHandlers
from .replicator import HarnessReplicator

logger = logging.getLogger(__name__)


def main():
    """Main entry point that creates a single source of truth configuration.

    Merges all input sources in priority order:
    1. Config file (may not exist) - uses as defaults
    2. Environment variables (may not exist) - overrides existing values
    3. CLI arguments (may not exist) - overrides existing values
    4. Interactive mode selections (may not exist) - overrides existing values

    Creates single source of truth that all subsequent operations use.
    """
    # Parse command line arguments
    parser = ArgumentParser.create_parser()
    args = parser.parse_args()

    # Load original config for comparison (before any modifications)
    original_config = load_config(args.config)

    # Build complete configuration from all input sources
    if args.non_interactive:
        # Non-interactive: config file + env vars + CLI args
        config = build_complete_config(args.config, args)
    else:
        # Interactive: config file + env vars + CLI args + interactive selections
        interactive_selections = ModeHandlers.get_interactive_selections(args.config, args)
        config = build_complete_config(args.config, args, interactive_selections)

    # Setup logging using the single source of truth
    setup_logging(
        debug=config.get("debug", False),
        output_json=config.get("output_json", False),
        output_color=config.get("output_color", True)
    )

    # Handle config saving based on mode and changes
    _handle_config_saving(config, original_config, args)

    # Final validation - check for required variables and declare what must be set
    if not _validate_final_config(config, config.get("non_interactive", False), bool(config.get("pipelines"))):
        sys.exit(1)

    # Run replication using the single source of truth
    replicator = HarnessReplicator(config)
    success = replicator.run_replication()

    sys.exit(0 if success else 1)


def _handle_config_saving(config: dict, original_config: dict, args) -> None:
    """Handle configuration saving based on mode and user preferences"""
    is_interactive = not args.non_interactive
    save_config_flag = getattr(args, 'save_config', False)

    if should_save_config(config, original_config, is_interactive, save_config_flag):
        if is_interactive:
            # Interactive mode: prompt user to save
            _prompt_save_config(config, args.config)
        else:
            # Non-interactive mode: save automatically (flag and changes already checked)
            if save_config(config, args.config):
                logger.info("Configuration automatically saved (--save-config flag provided and changes detected)")
            else:
                logger.warning("Failed to save configuration file")
    else:
        # Log why config is not being saved
        if is_interactive:
            logger.debug("Interactive mode: no configuration changes detected")
        else:
            if save_config_flag:
                logger.debug("Non-interactive mode: --save-config provided but no changes detected")
            else:
                logger.debug("Non-interactive mode: --save-config not provided")


def _prompt_save_config(config: dict, config_file: str) -> None:
    """Prompt user to save configuration in interactive mode"""
    try:
        from prompt_toolkit.shortcuts import yes_no_dialog

        should_save = yes_no_dialog(
            title="Save Configuration",
            text=f"The configuration has been updated with your selections.\n\n"
                 f"Would you like to save these changes to '{config_file}'?\n\n"
                 f"This will preserve your selections for future runs."
        ).run()

        if should_save:
            if save_config(config, config_file):
                logger.info("Configuration saved successfully")
            else:
                logger.error("Failed to save configuration")
        else:
            logger.info("Configuration not saved (user choice)")

    except ImportError:
        # Fallback if prompt_toolkit is not available
        logger.warning("Interactive save prompt not available - configuration not saved")


def _validate_final_config(config: dict, is_non_interactive: bool, has_cli_pipelines: bool) -> bool:
    """Final validation - check for required variables and declare what must be set"""
    missing_vars = []

    # Required fields for all modes
    required_fields = [
        ("source", "base_url", "Source Harness URL"),
        ("source", "api_key", "Source API key"),
        ("source", "org", "Source organization"),
        ("source", "project", "Source project"),
        ("destination", "base_url", "Destination Harness URL"),
        ("destination", "api_key", "Destination API key"),
        ("destination", "org", "Destination organization"),
        ("destination", "project", "Destination project"),
    ]

    # Check required fields
    for section, key, description in required_fields:
        section_data = config.get(section, {})
        if not isinstance(section_data, dict) or not section_data.get(key):
            missing_vars.append(f"{section}.{key} ({description})")

    # Check pipelines requirement for non-interactive mode without CLI pipelines
    if is_non_interactive and not has_cli_pipelines:
        if not config.get("pipelines"):
            missing_vars.append("pipelines (Pipeline specifications)")

    # If any required variables are missing, error and declare what must be set
    if missing_vars:
        logger.error("Missing required configuration variables:")
        for var in missing_vars:
            logger.error("  - %s", var)
        logger.error("")
        logger.error("These variables must be set via:")
        logger.error("  - Config file (config.json)")
        logger.error("  - Environment variables (HARNESS_*)")
        logger.error("  - CLI arguments (--source-*, --dest-*, --pipeline)")
        logger.error("  - Interactive mode (prompts)")
        return False

    return True


if __name__ == "__main__":
    main()
