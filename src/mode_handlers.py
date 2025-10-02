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
        """Non-interactive mode - use all values from config file and environment variables"""
        logger.info("Running in non-interactive mode")

        # Always try to load config (may not exist), then env vars, then CLI args
        config = load_config(config_file)
        
        return config

    @staticmethod
    def interactive_mode(config_file: str) -> Dict[str, Any]:
        """Interactive mode - show dialogs for all selections, allowing review/modification of existing values"""
        logger.info("Running in interactive mode")

        # Always try to load config (may not exist), then env vars, then CLI args
        config = load_config(config_file)

        # Validate API credentials are present (required for interactive mode)
        if not ConfigValidator.validate_api_credentials(config):
            logger.error("API credentials are required for interactive mode")
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
