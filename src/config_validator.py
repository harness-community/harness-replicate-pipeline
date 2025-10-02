"""
Configuration Validator

Handles validation of configuration for different modes.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates configuration for different execution modes"""

    @staticmethod
    def validate_non_interactive_config(config: Dict[str, Any], has_cli_pipelines: bool = False) -> bool:
        """Validate configuration for non-interactive mode"""
        # Validate required fields
        required_fields = [
            ("source", "base_url"), ("source", "api_key"), ("source", "org"),
            ("source", "project"), ("destination", "base_url"), ("destination", "api_key"),
            ("destination", "org"), ("destination", "project")
        ]
        
        # Check all required fields
        for section, key in required_fields:
            section_data = config.get(section, {})
            if isinstance(section_data, dict) and not section_data.get(key):
                logger.error("Missing required field: %s.%s", section, key)
                return False
        
        # Only require pipelines in config if not provided via CLI
        if not has_cli_pipelines:
            if not config.get("pipelines"):
                logger.error("Missing required section: pipelines")
                return False

        return True

    @staticmethod
    def validate_api_credentials(config: Dict[str, Any]) -> bool:
        """Validate that API credentials are present"""
        source_config = config.get("source", {})
        dest_config = config.get("destination", {})

        if not source_config.get("base_url") or not source_config.get("api_key"):
            logger.error("Source base_url and api_key are required")
            return False

        if not dest_config.get("base_url") or not dest_config.get("api_key"):
            logger.error("Destination base_url and api_key are required")
            return False

        return True
