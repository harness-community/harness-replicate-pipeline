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
        return self._make_request('GET', endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> Optional[Dict]:
        """POST request"""
        return self._make_request('POST', endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> Optional[Dict]:
        """PUT request"""
        return self._make_request('PUT', endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Optional[Dict]:
        """DELETE request"""
        return self._make_request('DELETE', endpoint, **kwargs)


class HarnessMigrator:
    """Main migration orchestrator"""

    def __init__(self, config: Dict):
        self.config = config
        self.source_client = HarnessAPIClient(
            config['source']['base_url'],
            config['source']['api_key']
        )
        self.dest_client = HarnessAPIClient(
            config['destination']['base_url'],
            config['destination']['api_key']
        )

        self.source_org = config['source']['org']
        self.source_project = config['source']['project']
        self.dest_org = config['destination']['org']
        self.dest_project = config['destination']['project']

        self.migration_stats = {
            'pipelines': {'success': 0, 'failed': 0},
            'input_sets': {'success': 0, 'failed': 0},
            'templates': {'success': 0, 'failed': 0}
        }
        self.discovered_templates = set()  # Track templates found in pipelines

    def extract_template_refs(self, yaml_content: str) -> List[tuple]:
        """Extract template references from pipeline YAML
        
        Returns list of tuples: (templateRef, versionLabel)
        """
        import re
        templates = []
        
        # Pattern to match templateRef and versionLabel
        # Looks for: templateRef: <identifier> followed by versionLabel: "<version>"
        pattern = r'templateRef:\s*(\S+)\s+versionLabel:\s*["\']?([^"\'\n]+)["\']?'
        matches = re.findall(pattern, yaml_content)
        
        for template_ref, version_label in matches:
            templates.append((template_ref, version_label))
            self.discovered_templates.add((template_ref, version_label))
        
        return templates

    def list_templates(
            self, org: str, project: str,
            client: Optional[HarnessAPIClient] = None) -> List[Dict]:
        """List all templates in a project

        Args:
            org: Organization identifier
            project: Project identifier
            client: API client to use (defaults to source_client)

        Returns:
            List of template dictionaries
        """
        if client is None:
            client = self.source_client

        endpoint = f"/v1/orgs/{org}/projects/{project}/templates"
        response = client.get(endpoint)

        if response is None:
            return []

        # Handle both direct array format and wrapped content format
        if isinstance(response, list):
            return response
        elif 'content' in response:
            return response.get('content', [])
        else:
            return []

    def get_template(
            self, template_ref: str, version_label: str,
            org: str, project: str,
            client: Optional[HarnessAPIClient] = None) -> Optional[Dict]:
        """Get template details including YAML

        Args:
            template_ref: Template identifier
            version_label: Template version
            org: Organization identifier
            project: Project identifier
            client: API client to use (defaults to source_client)

        Returns:
            Template dictionary with YAML, or None if not found
        """
        if client is None:
            client = self.source_client

        endpoint = (
            f"/v1/orgs/{org}/"
            f"projects/{project}/"
            f"templates/{template_ref}/"
            f"versions/{version_label}")

        return client.get(endpoint)
    
    def check_template_exists(
            self, template_ref: str, version_label: str) -> bool:
        """Check if a template exists in destination

        Args:
            template_ref: Template identifier
            version_label: Template version

        Returns:
            True if exists, False otherwise
        """
        dest_template = self.get_template(
            template_ref, version_label,
            self.dest_org, self.dest_project,
            self.dest_client)
        return dest_template is not None

    def create_template(
            self, template_yaml: str, is_stable: bool = True,
            comments: str = "Migrated template") -> Optional[Dict]:
        """Create a template in destination

        NOTE: The template_yaml MUST include orgIdentifier and
        projectIdentifier fields that match the destination org and project.

        Args:
            template_yaml: Complete template YAML definition
            is_stable: Whether to mark this version as stable
            comments: Comments for the template creation

        Returns:
            Created template response, or None if failed
        """
        endpoint = (
            f"/v1/orgs/{self.dest_org}/"
            f"projects/{self.dest_project}/"
            f"templates")

        payload = {
            'template_yaml': template_yaml,
            'is_stable': is_stable,
            'comments': comments
        }

        return self.dest_client.post(endpoint, json=payload)
    
    def migrate_template(
            self, template_ref: str, version_label: str) -> bool:
        """Migrate a single template from source to destination

        Args:
            template_ref: Template identifier
            version_label: Template version

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            "  Migrating template: %s (v%s)", template_ref, version_label)

        # Check if already exists in destination
        if self.check_template_exists(template_ref, version_label):
            logger.info(
                "  ✓ Template already exists in destination, skipping")
            return True

        # Get template from source
        source_template = self.get_template(
            template_ref, version_label,
            self.source_org, self.source_project,
            self.source_client)

        if not source_template:
            logger.error("  ✗ Failed to get template from source")
            return False

        # Extract YAML and update org/project identifiers
        template_yaml = source_template.get('yaml', '')
        if not template_yaml:
            logger.error("  ✗ No YAML found in source template")
            return False

        # Parse and update the YAML to use destination org/project
        import yaml  # noqa: F401
        try:
            template_dict = yaml.safe_load(template_yaml)
            if 'template' in template_dict:
                template_dict['template']['orgIdentifier'] = (
                    self.dest_org)
                template_dict['template']['projectIdentifier'] = (
                    self.dest_project)
            else:
                # Sometimes the YAML might not have the 'template' wrapper
                template_dict['orgIdentifier'] = self.dest_org
                template_dict['projectIdentifier'] = self.dest_project

            # Convert back to YAML
            updated_yaml = yaml.dump(
                template_dict, default_flow_style=False, sort_keys=False)
        except Exception as e:  # noqa: E722
            logger.error("  ✗ Failed to update template YAML: %s", e)
            return False

        # Create in destination
        result = self.create_template(
            updated_yaml,
            is_stable=source_template.get('stable_template', True),
            comments=f"Migrated from {self.source_org}/{self.source_project}")

        if result:
            logger.info("  ✓ Template migrated successfully")
            self.migration_stats['templates']['success'] += 1
            return True
        else:
            logger.error("  ✗ Failed to create template in destination")
            self.migration_stats['templates']['failed'] += 1
            return False

    def verify_prerequisites(self) -> bool:
        """Verify that destination org and project exist"""
        logger.info("Verifying destination org and project...")

        # Check if in dry run mode
        dry_run = self.config.get('dry_run', False)

        # Check organization
        org_endpoint = f"/v1/orgs/{self.dest_org}"
        org_response = self.dest_client.get(org_endpoint)

        if not org_response:
            logger.error(
                "Destination organization '%s' does not exist", self.dest_org)

            if dry_run:
                logger.info(
                    "[DRY RUN] Would create organization '%s'", self.dest_org)
                logger.info(
                    "Organization '%s' would be created successfully",
                    self.dest_org)
            else:
                logger.info("Creating organization...")

                create_org = self.dest_client.post("/v1/orgs", json={
                    "org": {
                        "identifier": self.dest_org,
                        "name": self.dest_org
                    }
                })

                if not create_org:
                    logger.error("Failed to create organization")
                    return False
                logger.info(
                    "Organization '%s' created successfully", self.dest_org)

        # Check project
        project_endpoint = (
            f"/v1/orgs/{self.dest_org}/projects/{self.dest_project}")
        project_response = self.dest_client.get(project_endpoint)

        if not project_response:
            logger.error(
                "Destination project '%s' does not exist", self.dest_project)

            if dry_run:
                logger.info(
                    "[DRY RUN] Would create project '%s'", self.dest_project)
                logger.info(
                    "Project '%s' would be created successfully",
                    self.dest_project)
            else:
                logger.info("Creating project...")

                create_project = self.dest_client.post(
                    f"/v1/orgs/{self.dest_org}/projects",
                    json={
                        "project": {
                            "identifier": self.dest_project,
                            "name": self.dest_project,
                            "org": self.dest_org
                        }
                    }
                )

                if not create_project:
                    logger.error("Failed to create project")
                    return False
                logger.info(
                    "Project '%s' created successfully", self.dest_project)

        return True

    def migrate_input_sets(self, pipeline_id: str) -> bool:
        """Migrate input sets for a specific pipeline"""
        logger.info("  Checking for input sets for pipeline: %s", pipeline_id)

        # Check if in dry run mode
        dry_run = self.config.get('dry_run', False)

        # List input sets
        endpoint = (
            f"/v1/orgs/{self.source_org}/projects/{self.source_project}/"
            f"input-sets")
        params = {'pipelineIdentifier': pipeline_id}

        input_sets_response = self.source_client.get(endpoint, params=params)

        if input_sets_response is None:
            logger.info("  No input sets found for pipeline: %s", pipeline_id)
            return True

        # Handle both direct array format and wrapped content format
        if isinstance(input_sets_response, list):
            input_sets = input_sets_response
        elif 'content' in input_sets_response:
            input_sets = input_sets_response.get('content', [])
        else:
            logger.info(
                "  Unexpected response format when retrieving input sets")
            return True
        if input_sets:
            logger.info("  Migrating %d input sets...", len(input_sets))

        for input_set in input_sets:
            input_set_id = input_set.get('identifier')
            input_set_name = input_set.get('name', input_set_id)

            logger.info("  Migrating input set: %s", input_set_name)

            # Get full input set details
            get_endpoint = (
                f"/v1/orgs/{self.source_org}/projects/{self.source_project}/"
                f"input-sets/{input_set_id}")
            params = {'pipelineIdentifier': pipeline_id}
            input_set_details = self.source_client.get(
                get_endpoint, params=params)

            if not input_set_details:
                logger.error(
                    "  Failed to get details for input set: %s", input_set_id)
                self.migration_stats['input_sets']['failed'] += 1
                continue

            # Create input set in destination
            create_endpoint = (
                f"/v1/orgs/{self.dest_org}/projects/{self.dest_project}/"
                f"input-sets")
            params = {'pipelineIdentifier': pipeline_id}

            if dry_run:
                logger.info(
                    "  [DRY RUN] Would create input set '%s'", input_set_name)
                result = True  # Simulate success
            else:
                result = self.dest_client.post(
                    create_endpoint,
                    params=params,
                    json=input_set_details
                )

            if result:
                logger.info(
                    "  ✓ Input set '%s' migrated successfully", input_set_name)
                self.migration_stats['input_sets']['success'] += 1
            else:
                logger.error(
                    "  ✗ Failed to migrate input set: %s", input_set_name)
                self.migration_stats['input_sets']['failed'] += 1

            time.sleep(0.3)

        return True
