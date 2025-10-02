"""
Logging Utilities

Handles logging configuration and setup.
"""

import logging
import sys
from datetime import datetime


def setup_logging(debug: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                f'replication_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )
