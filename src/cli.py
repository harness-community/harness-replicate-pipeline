"""
Command Line Interface

Main CLI orchestrator that coordinates all components.
"""

import sys

from .argument_parser import ArgumentParser
from .config import apply_cli_overrides
from .config_validator import ConfigValidator
from .logging_utils import setup_logging
from .mode_handlers import ModeHandlers
from .replicator import HarnessReplicator


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = ArgumentParser.create_parser()
    args = parser.parse_args()

    # Setup logging with debug level if requested
    setup_logging(debug=args.debug)

    # Choose mode based on flag
    if args.non_interactive:
        config = ModeHandlers.non_interactive_mode(args.config)
        # Apply CLI argument overrides first
        config = apply_cli_overrides(config, args)
        # Validate configuration after applying CLI overrides
        if not ConfigValidator.validate_non_interactive_config(config, has_cli_pipelines=bool(args.pipelines)):
            sys.exit(1)
    else:
        # Use interactive mode by default (always show dialogs)
        config = ModeHandlers.interactive_mode(args.config)
        # Apply CLI argument overrides (priority: config file > CLI args > interactive)
        config = apply_cli_overrides(config, args)

    # Add dry-run and non-interactive flags to config
    config["dry_run"] = args.dry_run
    config["non_interactive"] = args.non_interactive

    # Run replication
    replicator = HarnessReplicator(config)
    success = replicator.run_replication()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

