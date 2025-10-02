"""
Mode Handlers

Handles interactive and non-interactive execution modes.
"""

import logging
import sys
from typing import Any, Dict

from .api_client import HarnessAPIClient
from .config import load_config
from .config_validator import ConfigValidator

logger = logging.getLogger(__name__)


class ModeHandlers:
    """Handles different execution modes"""

    @staticmethod
    def non_interactive_mode(config_file: str) -> Dict[str, Any]:
        """Non-interactive mode - use all values from config file"""
        logger.info("Running in non-interactive mode")

        config = load_config(config_file)
        if not config:
            logger.error("Failed to load configuration from %s", config_file)
            sys.exit(1)

        return config

    @staticmethod
    def interactive_mode(config_file: str) -> Dict[str, Any]:
        """Interactive mode - show dialogs for all selections, allowing review/modification of existing values"""
        logger.info("Running in interactive mode")

        config = load_config(config_file)
        if not config:
            logger.error("Failed to load configuration from %s", config_file)
            sys.exit(1)

        # Validate API credentials first
        if not ConfigValidator.validate_api_credentials(config):
            sys.exit(1)

        # Initialize API clients
        source_config = config.get("source", {})
        dest_config = config.get("destination", {})

        source_client = HarnessAPIClient(source_config["base_url"], source_config["api_key"])
        dest_client = HarnessAPIClient(dest_config["base_url"], dest_config["api_key"])

        # Get user selections with interactive dialogs (always show, even if values exist)
        from .ui import get_interactive_selections
        config = get_interactive_selections(source_client, dest_client, config, config_file)
        if not config:
            logger.error("Failed to get required selections")
            sys.exit(1)

        return config
