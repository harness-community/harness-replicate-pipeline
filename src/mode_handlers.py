"""
Mode Handlers

Handles interactive and non-interactive execution modes.
"""

import logging
import sys
from typing import Any, Dict

from .api_client import HarnessAPIClient
from .config_validator import ConfigValidator

logger = logging.getLogger(__name__)


class ModeHandlers:
    """Handles different execution modes"""

    @staticmethod
    def get_interactive_selections(config_file: str, args) -> Dict[str, Any]:
        """Get interactive selections that will be merged into the final configuration.

        This function handles the interactive mode by getting user selections
        that will later be merged as the final step in the configuration priority order.
        """
        logger.info("Running in interactive mode")

        # Build partial config (config file + env vars + CLI args) for API client initialization
        from .config import build_complete_config
        partial_config = build_complete_config(config_file, args)

        # Validate API credentials are present (required for interactive mode)
        if not ConfigValidator.validate_api_credentials(partial_config):
            logger.error("API credentials are required for interactive mode")
            sys.exit(1)

        # Initialize API clients using the partial config
        source_config = partial_config.get("source", {})
        dest_config = partial_config.get("destination", {})

        source_client = HarnessAPIClient(source_config["base_url"], source_config["api_key"])
        dest_client = HarnessAPIClient(dest_config["base_url"], dest_config["api_key"])

        # Get user selections with interactive dialogs (always show, even if values exist)
        from .ui import get_interactive_selections
        interactive_config = get_interactive_selections(source_client, dest_client, partial_config, config_file)
        if not interactive_config:
            logger.error("Failed to get required selections")
            sys.exit(1)

        # Return only the interactive selections (not the full config)
        # These will be merged as the final step in build_complete_config
        return interactive_config
