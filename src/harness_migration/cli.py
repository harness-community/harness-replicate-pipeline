"""
Command Line Interface

Handles argument parsing and main entry point.
"""

import argparse
import logging
import sys
from datetime import datetime
from typing import Any, Dict

from .api_client import HarnessAPIClient
from .config import apply_cli_overrides, load_config
from .migrator import HarnessMigrator
from .ui import get_selections_from_clients

logger = logging.getLogger(__name__)


def setup_logging(debug=False):
    """Setup logging configuration"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )


def non_interactive_mode(config_file: str) -> Dict[str, Any]:
    """Non-interactive mode - use all values from config file"""
    logger.info("Running in non-interactive mode")

    config = load_config(config_file)
    if not config:
        logger.error("Failed to load configuration from %s", config_file)
        sys.exit(1)

    # Validate required fields
    required_fields = [
        ("source", "base_url"), ("source", "api_key"), ("source", "org"), ("source", "project"),
        ("destination", "base_url"), ("destination", "api_key"), ("destination", "org"), ("destination", "project"),
        ("pipelines", None)
    ]

    for field_path in required_fields:
        if len(field_path) == 2:
            section, key = field_path
            if not config.get(section, {}).get(key):
                logger.error("Missing required field: %s.%s", section, key)
                sys.exit(1)
        else:
            section = field_path[0]
            if not config.get(section):
                logger.error("Missing required section: %s", section)
                sys.exit(1)

    return config


def hybrid_mode(config_file: str) -> Dict[str, Any]:
    """Hybrid mode - use config file with interactive prompts for missing values"""
    logger.info("Running in hybrid mode")

    config = load_config(config_file)
    if not config:
        logger.error("Failed to load configuration from %s", config_file)
        sys.exit(1)

    # Initialize API clients
    source_config = config.get("source", {})
    dest_config = config.get("destination", {})

    if not source_config.get("base_url") or not source_config.get("api_key"):
        logger.error("Source base_url and api_key are required")
        sys.exit(1)

    if not dest_config.get("base_url") or not dest_config.get("api_key"):
        logger.error("Destination base_url and api_key are required")
        sys.exit(1)

    source_client = HarnessAPIClient(source_config["base_url"], source_config["api_key"])
    dest_client = HarnessAPIClient(dest_config["base_url"], dest_config["api_key"])

    # Get user selections
    config = get_selections_from_clients(source_client, dest_client, config, config_file)
    if not config:
        logger.error("Failed to get required selections")
        sys.exit(1)

    return config


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Migrate Harness pipelines between accounts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
    # Interactive mode (with dialogs for selection)
    python -m harness_migration

    # Non-interactive mode (use all values from config file)
    python -m harness_migration --non-interactive

    # Dry run to test without making changes
    python -m harness_migration --dry-run

    # Debug mode for troubleshooting
    python -m harness_migration --debug

    # Override specific values via CLI
    python -m harness_migration --source-org my_org --dest-org target_org

    # Override migration options
    python -m harness_migration --no-migrate-input-sets --no-skip-existing

    # Full CLI configuration (minimal config file needed)
    python -m harness_migration \\
        --source-url https://app.harness.io \\
        --source-api-key sat.xxxxx.xxxxx.xxxxx \\
        --source-org source_org \\
        --source-project source_project \\
        --dest-url https://app3.harness.io \\
        --dest-api-key sat.yyyyy.yyyyy.yyyyy \\
        --dest-org dest_org \\
        --dest-project dest_project

Configuration File Format (supports JSONC with comments):
{
  "source": {
    "base_url": "https://app.harness.io",
    "api_key": "your-source-api-key",
    // "org": "source_org",  // Leave commented to select interactively
    // "project": "source_project"  // Leave commented to select interactively
  },
  "destination": {
    "base_url": "https://app3.harness.io",
    "api_key": "your-dest-api-key",
    // "org": "dest_org",  // Leave commented to select interactively
    // "project": "dest_project"  // Leave commented to select interactively
  },
  "options": {
    "migrate_input_sets": true,
    "skip_existing": true
  }
}
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration JSON/JSONC file (default: config.json)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )

    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging for troubleshooting"
    )

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip prompts and use all values from config file (no dialogs)",
    )

    # Source configuration arguments
    parser.add_argument(
        "--source-url",
        type=str,
        help="Source Harness base URL (e.g., https://app.harness.io)",
    )
    parser.add_argument(
        "--source-api-key",
        type=str,
        help="Source Harness API key (starts with 'sat.')",
    )
    parser.add_argument(
        "--source-org",
        type=str,
        help="Source organization identifier",
    )
    parser.add_argument(
        "--source-project",
        type=str,
        help="Source project identifier",
    )

    # Destination configuration arguments
    parser.add_argument(
        "--dest-url",
        type=str,
        help="Destination Harness base URL (e.g., https://app3.harness.io)",
    )
    parser.add_argument(
        "--dest-api-key",
        type=str,
        help="Destination Harness API key (starts with 'sat.')",
    )
    parser.add_argument(
        "--dest-org",
        type=str,
        help="Destination organization identifier",
    )
    parser.add_argument(
        "--dest-project",
        type=str,
        help="Destination project identifier",
    )

    # Migration options
    parser.add_argument(
        "--migrate-input-sets",
        action="store_true",
        help="Migrate input sets with pipelines (default: true)",
    )
    parser.add_argument(
        "--no-migrate-input-sets",
        action="store_true",
        help="Skip migrating input sets",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip pipelines that already exist in destination (default: true)",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Update/overwrite existing pipelines",
    )

    args = parser.parse_args()

    # Setup logging with debug level if requested
    setup_logging(debug=args.debug)

    # Choose mode based on flag
    if args.non_interactive:
        config = non_interactive_mode(args.config)
    else:
        # Use hybrid mode with interactive prompts
        config = hybrid_mode(args.config)

    # Apply CLI argument overrides (priority: config file > CLI args > interactive)
    config = apply_cli_overrides(config, args)

    # Add dry-run flag to config
    config["dry_run"] = args.dry_run

    # Run migration
    migrator = HarnessMigrator(config)
    success = migrator.run_migration()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
