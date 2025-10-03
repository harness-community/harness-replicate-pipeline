"""
Argument Parser

Handles command line argument parsing and help text.
"""

import argparse


class ArgumentParser:
    """Handles command line argument parsing"""

    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create and configure the argument parser"""
        parser = argparse.ArgumentParser(
            description="Replicate Harness pipelines between accounts",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=ArgumentParser._get_help_text(),
        )

        ArgumentParser._add_basic_arguments(parser)
        ArgumentParser._add_source_arguments(parser)
        ArgumentParser._add_destination_arguments(parser)
        ArgumentParser._add_replication_options(parser)
        ArgumentParser._add_pipeline_arguments(parser)

        return parser

    @staticmethod
    def _get_help_text() -> str:
        """Get the help text for the CLI"""
        return """
Modes:
    Interactive (default): Always show dialogs to review/modify all selections
    Non-interactive:       Use config file values only, no dialogs

Usage Examples:
    # Interactive mode (default) - always show dialogs for review/confirmation
    python main.py

    # Non-interactive mode (use all values from config file)
    python main.py --non-interactive

    # Dry run to test without making changes
    python main.py --dry-run

    # Debug mode for troubleshooting
    python main.py --debug

    # JSON output for automation
    python main.py --output-json --non-interactive

    # Enable colors for terminal output
    python main.py --output-color

    # Save config after interactive selections
    python main.py --save-config

    # Override specific values via CLI
    python main.py --source-org my_org --dest-org target_org

    # Override replication options
    python main.py --skip-triggers --skip-input-sets --update-existing

    # Full CLI configuration (minimal config file needed)
    python main.py \\
        --source-url https://app.harness.io \\
        --source-api-key sat.xxxxx.xxxxx.xxxxx \\
        --source-org source_org \\
        --source-project source_project \\
        --dest-url https://app3.harness.io \\
        --dest-api-key sat.yyyyy.yyyyy.yyyyy \\
        --dest-org dest_org \\
        --dest-project dest_project \\
        --pipeline pipeline1 \\
        --pipeline pipeline2

    # Replicate specific pipelines with minimal config
    python main.py \\
        --non-interactive \\
        --pipeline api_deploy \\
        --pipeline db_migration \\
        --pipeline frontend_build

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
    "skip_input_sets": false,
    "skip_triggers": false,
    "skip_templates": false,
    "update_existing": false,
    "output_json": false,
    "output_color": false
  }
}
        """

    @staticmethod
    def _add_basic_arguments(parser: argparse.ArgumentParser) -> None:
        """Add basic CLI arguments"""
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
            "--debug",
            action="store_true",
            help="Enable debug logging for troubleshooting"
        )

        parser.add_argument(
            "--non-interactive",
            action="store_true",
            help="Skip prompts and use all values from config file (no dialogs)",
        )

        parser.add_argument(
            "--output-json",
            action="store_true",
            help="Output in JSON format for automation integration (default: terminal format)",
        )

        parser.add_argument(
            "--output-color",
            action="store_true",
            help="Enable colored output for terminal display (default: false, ignored for JSON output)",
        )

        parser.add_argument(
            "--save-config",
            action="store_true",
            help="Save the merged configuration to config file (interactive: prompt, non-interactive: only if this flag is set)",
        )

    @staticmethod
    def _add_source_arguments(parser: argparse.ArgumentParser) -> None:
        """Add source configuration arguments"""
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

    @staticmethod
    def _add_destination_arguments(parser: argparse.ArgumentParser) -> None:
        """Add destination configuration arguments"""
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

    @staticmethod
    def _add_replication_options(parser: argparse.ArgumentParser) -> None:
        """Add replication option arguments"""
        parser.add_argument(
            "--skip-input-sets",
            action="store_true",
            help="Skip replicating input sets (default: replicate input sets)",
        )
        parser.add_argument(
            "--skip-triggers",
            action="store_true",
            help="Skip replicating triggers (default: replicate triggers)",
        )
        parser.add_argument(
            "--skip-templates",
            action="store_true",
            help="Skip replicating missing templates (default: replicate templates)",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update/overwrite existing pipelines (default: skip existing)",
        )

    @staticmethod
    def _add_pipeline_arguments(parser: argparse.ArgumentParser) -> None:
        """Add pipeline specification arguments"""
        parser.add_argument(
            "--pipeline",
            action="append",
            dest="pipelines",
            help="Pipeline identifier to replicate (can be used multiple times)",
        )
