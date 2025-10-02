"""
Command Line Interface

Main CLI orchestrator that coordinates all components.
"""

import logging
import sys

from .argument_parser import ArgumentParser
from .config import apply_cli_overrides
from .logging_utils import setup_logging
from .mode_handlers import ModeHandlers
from .replicator import HarnessReplicator

logger = logging.getLogger(__name__)


def main():
    """Main entry point following priority order:
    1. Always try to load config file (may not exist), use as defaults
    2. Always try to load environment variables (may not exist), overrides existing values
    3. Always load CLI arguments (may not exist), overrides existing values
    4. Interactive mode follow dialog rules, overrides existing values
    5. Ultimately if any required variables are missing error and declare the variables that must be set
    """
    # Parse command line arguments (step 3 - always loaded)
    parser = ArgumentParser.create_parser()
    args = parser.parse_args()

    # Setup logging with debug level if requested (check env vars first, then CLI args)
    debug_mode = args.debug
    if not debug_mode:
        # Check environment variable if CLI arg not set
        import os
        debug_mode = os.getenv("HARNESS_DEBUG", "").lower() in ('true', '1', 'yes', 'on')
    setup_logging(debug=debug_mode)

    # Steps 1-2: Load config file and environment variables (handled in mode handlers)
    if args.non_interactive:
        config = ModeHandlers.non_interactive_mode(args.config)
    else:
        # Step 4: Interactive mode with dialog overrides
        config = ModeHandlers.interactive_mode(args.config)

    # Step 3: Always apply CLI argument overrides
    config = apply_cli_overrides(config, args)

    # Add runtime flags to config (CLI args override env vars)
    config["dry_run"] = args.dry_run or config.get("dry_run", False)
    config["non_interactive"] = args.non_interactive or config.get("non_interactive", False)

    # Step 5: Final validation - check for required variables and declare what must be set
    if not _validate_final_config(config, args.non_interactive, bool(args.pipelines)):
        sys.exit(1)

    # Run replication
    replicator = HarnessReplicator(config)
    success = replicator.run_replication()

    sys.exit(0 if success else 1)


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
