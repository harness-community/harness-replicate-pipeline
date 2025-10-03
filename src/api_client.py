"""
Harness API Client

Handles all API interactions with Harness instances.
"""

import logging
from typing import Dict, List, Optional, Union

import requests

logger = logging.getLogger(__name__)


class HarnessAuthenticationError(Exception):
    """Raised when API authentication fails (401 Unauthorized)"""
    def __init__(self, message: str, base_url: str):
        self.message = message
        self.base_url = base_url
        super().__init__(message)


class HarnessAPIClient:
    """Client for interacting with Harness API"""

    def __init__(self, base_url: str, api_key: str):
        """Initialize API client with base URL and API key"""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": api_key,
            "Content-Type": "application/json",
        })

    def _handle_auth_errors(self, e: requests.exceptions.RequestException) -> None:
        """Check if the error is authentication-related and raise appropriate exception"""
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            response_text = str(e.response.text).lower()
            
            if status_code == 401:
                raise HarnessAuthenticationError(
                    "Authentication failed. Please check your API key and ensure it has the required permissions.",
                    self.base_url
                )
            elif status_code == 403:
                raise HarnessAuthenticationError(
                    "Access forbidden. Your API key lacks the required permissions for this operation.",
                    self.base_url
                )
            elif status_code == 500:
                # Harness often returns 500 for authentication issues instead of 401
                # Check for authentication-related keywords or assume auth issue for certain endpoints
                auth_keywords = ["unauthorized", "invalid", "authentication", "forbidden", "access denied"]
                is_auth_endpoint = any(endpoint in e.request.url for endpoint in ["/v1/orgs", "/v1/projects", "/ng/api/"])
                
                if any(keyword in response_text for keyword in auth_keywords) or is_auth_endpoint:
                    raise HarnessAuthenticationError(
                        "Authentication failed (server error). Please verify your API key is valid and properly formatted.",
                        self.base_url
                    )

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Union[Dict, List]]:
        """Make GET request to API endpoint"""
        url = f"{self.base_url}{endpoint}"
        logger.debug("Making GET request to: %s", url)

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_auth_errors(e)
            logger.error("API Error: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Status: %s", e.response.status_code)
                logger.error("URL: %s", url)
                logger.error("Response Text: %s", e.response.text)
            return None

    def post(self, endpoint: str, params: Optional[Dict] = None,
             json: Optional[Dict] = None) -> Optional[Union[Dict, List]]:
        """Make POST request to API endpoint"""
        url = f"{self.base_url}{endpoint}"
        logger.debug("Making POST request to: %s", url)

        try:
            response = self.session.post(url, params=params, json=json)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_auth_errors(e)
            logger.error("API Error: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Status: %s", e.response.status_code)
                logger.error("URL: %s", url)
                logger.error("Response Text: %s", e.response.text)
            return None

    def put(self, endpoint: str, params: Optional[Dict] = None,
            json: Optional[Dict] = None) -> Optional[Union[Dict, List]]:
        """Make PUT request to API endpoint"""
        url = f"{self.base_url}{endpoint}"
        logger.debug("Making PUT request to: %s", url)

        try:
            response = self.session.put(url, params=params, json=json)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_auth_errors(e)
            logger.error("API Error: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Status: %s", e.response.status_code)
                logger.error("URL: %s", url)
                logger.error("Response Text: %s", e.response.text)
            return None

    def delete(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Union[Dict, List]]:
        """Make DELETE request to API endpoint"""
        url = f"{self.base_url}{endpoint}"
        logger.debug("Making DELETE request to: %s", url)

        try:
            response = self.session.delete(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_auth_errors(e)
            logger.error("API Error: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Status: %s", e.response.status_code)
                logger.error("URL: %s", url)
                logger.error("Response Text: %s", e.response.text)
            return None

    @staticmethod
    def normalize_response(response: Optional[Union[Dict, List]]) -> List[Dict]:
        """Normalize API response to always return a list.

        Handles both direct array format and wrapped content format.
        For Harness API responses, extracts the 'org' or 'project' data from each item.
        Returns empty list if response is None or invalid.
        """
        if response is None:
            return []
        if isinstance(response, list):
            # Extract 'org' or 'project' data from each item if it exists
            normalized = []
            for item in response:
                if isinstance(item, dict):
                    # Only extract nested objects, not string fields
                    if "org" in item and isinstance(item["org"], dict):
                        normalized.append(item["org"])
                    elif "project" in item and isinstance(item["project"], dict):
                        normalized.append(item["project"])
                    else:
                        normalized.append(item)
                else:
                    normalized.append(item)
            return normalized
        if isinstance(response, dict) and "content" in response:
            return response.get("content", [])
        return []
