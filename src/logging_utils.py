"""
Logging Utilities

Handles logging configuration and setup with output orchestrator integration.
"""

import logging
from datetime import datetime

from .output_orchestrator import OutputType, setup_output


def setup_logging(debug: bool = False, output_json: bool = False, output_color: bool = True) -> None:
    """Setup logging configuration with output orchestrator integration"""
    level = logging.DEBUG if debug else logging.INFO

    # Determine output type based on configuration
    output_type = OutputType.JSON if output_json else OutputType.TERMINAL

    # Setup output orchestrator (this will handle logging integration)
    setup_output(output_type, output_color)

    # Set logging level
    logging.getLogger().setLevel(level)

    # Add file handler for persistent logging (in addition to orchestrator)
    file_handler = logging.FileHandler(
        f'replication_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))

    # Add file handler to root logger (orchestrator already handles console output)
    logging.getLogger().addHandler(file_handler)
