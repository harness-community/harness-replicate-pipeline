#!/usr/bin/env python3
# pylint: disable=too-many-lines
"""
Harness Pipeline Migration Script

This script migrates pipelines from one Harness account to another,
including all dependencies (connectors, secrets, input sets).

Usage:
    python harness_pipeline_migration.py --config config.json
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Union

import requests

# For interactive mode with arrow key navigation
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import (
    radiolist_dialog, checkboxlist_dialog, button_dialog, message_dialog,
    yes_no_dialog
)

# Configure logging


def setup_logging(debug=False):
    """Setup logging configuration"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(
                f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


logger = logging.getLogger(__name__)


class HarnessAPIClient:
    """Client for interacting with Harness API"""

    def __init__(self, base_url: str, api_key: str):
        # Harness API uses direct base URL with /v1 endpoints
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:  # noqa: E501
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"

        # Log the request for debugging
        logger.debug("Making %s request to: %s", method, url)
        if 'headers' in kwargs:
            logger.debug("Custom headers: %s", kwargs['headers'])
        if 'data' in kwargs:
            logger.debug("Sending raw data (not JSON)")

        try:
            response = self.session.request(
                method, url, **kwargs)
            
            # Check for error status codes before parsing
            if not response.ok:
                status_code = response.status_code
                
                if status_code == 404:
                    # 404s are often expected (checking if resource exists)
                    logger.debug("Resource not found (404): %s", url)
                    return None
                
                # For other errors, log at ERROR level
                logger.error("API Error: %s %s", status_code, response.reason)
                logger.error("Status: %s", status_code)
                logger.error("URL: %s", url)
                logger.error("Response Text: %s", response.text[:2000])
                
                if status_code == 400:
                    logger.error("Bad Request - check the request payload format")
                    # Try to parse and log the error details
                    try:
                        error_details = response.json()
                        logger.error(
                            "Error details: %s",
                            json.dumps(error_details, indent=2))
                    except (json.JSONDecodeError, ValueError):
                        logger.error("Could not parse error response as JSON")
                elif status_code == 401:
                    logger.error("Authentication failed - check your API key")
                elif status_code == 403:
                    logger.error("Access denied - check API key permissions")
                
                return None

            if response.status_code == 204:
                return {}

            return response.json() if response.content else {}

        except requests.exceptions.HTTPError as e:
            logger.error("HTTP Error: %s", e)
            return None
        except (requests.exceptions.RequestException,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            logger.error("Request failed: %s", e)
            return None

    def get(self, endpoint: str, **kwargs) -> Optional[Dict]:
        """GET request"""
