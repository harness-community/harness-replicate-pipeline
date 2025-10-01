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

    def migrate_pipelines(self) -> bool:
        """Migrate pipelines from source to destination"""
        logger.info("=" * 80)
        logger.info("Starting pipeline migration...")

        # Check if in dry run mode
        dry_run = self.config.get('dry_run', False)
        if dry_run:
            logger.info(
                "DRY RUN MODE: Simulating migration, no changes will be made")

        # List pipelines from source
        endpoint = (
            f"/v1/orgs/{self.source_org}/projects/{self.source_project}/"
            f"pipelines")
        pipelines_response = self.source_client.get(endpoint)

        if pipelines_response is None:
            logger.error("Failed to retrieve pipelines from source")
            return False

        # Handle both direct array format and wrapped content format
        if isinstance(pipelines_response, list):
            all_pipelines = pipelines_response
        elif 'content' in pipelines_response:
            all_pipelines = pipelines_response.get('content', [])
        else:
            logger.error(
                "Unexpected response format when retrieving pipelines")
            return False

        # Filter to selected pipelines if specified
        selected_pipelines = self.config.get('pipelines', [])
        if selected_pipelines:
            # Extract identifiers from selected pipeline objects
            selected_ids = [p.get('identifier') for p in selected_pipelines]
            pipelines = [p for p in all_pipelines if p.get(
                'identifier') in selected_ids]
            logger.info(
                "Migrating %d selected pipeline(s) out of %d total",
                len(pipelines), len(all_pipelines))
        else:
            pipelines = all_pipelines
            logger.info("Found %d pipelines to migrate", len(pipelines))

        if not pipelines:
            logger.info(
                "No pipelines to migrate - skipping pipeline migration")
            return True

        for pipeline in pipelines:
            pipeline_id = pipeline.get('identifier')
            pipeline_name = pipeline.get('name', pipeline_id)

            logger.info(
                "\nMigrating pipeline: %s (%s)", pipeline_name, pipeline_id)

            # Get full pipeline details from source
            # We need the complete pipeline definition, not just summary
            get_endpoint = (
                f"/v1/orgs/{self.source_org}/"
                f"projects/{self.source_project}/"
                f"pipelines/{pipeline_id}")

            # Add query parameter to get full YAML
            pipeline_response = self.source_client.get(
                get_endpoint, params={'getDefaultFromOtherRepo': 'false'})

            if not pipeline_response:
                logger.warning(
                    "Could not fetch pipeline details, "
                    "trying to use list data: %s", pipeline_id)
                # Fallback to list data if available
                pipeline_response = pipeline

            # Log the response structure for debugging
            logger.debug(
                "Pipeline GET response keys: %s",
                list(pipeline_response.keys()) if isinstance(
                    pipeline_response, dict) else type(pipeline_response))

            # Extract the pipeline object from response
            if isinstance(pipeline_response, dict):
                # Filter out read-only/metadata fields that shouldn't be sent
                # Only keep fields needed for pipeline creation
                pipeline_details = {}

                # Essential fields for pipeline creation
                essential_fields = [
                    'identifier', 'name', 'description', 'tags',
                    'pipeline_yaml', 'yaml_pipeline'
                ]

                for field in essential_fields:
                    if field in pipeline_response:
                        pipeline_details[field] = pipeline_response[field]

                # If no YAML field found, log error
                if ('pipeline_yaml' not in pipeline_details and
                        'yaml_pipeline' not in pipeline_details):
                    logger.error(
                        "Pipeline has no YAML content: %s. Available keys: %s",
                        pipeline_id, list(pipeline_response.keys()))
                    self.migration_stats['pipelines']['failed'] += 1
                    continue
            else:
                logger.error(
                    "Invalid pipeline response format for: %s", pipeline_id)
                self.migration_stats['pipelines']['failed'] += 1
                continue

            # Extract template references from pipeline YAML
            yaml_content = pipeline_details.get(
                'pipeline_yaml',
                pipeline_details.get('yaml_pipeline', ''))
            missing_templates = []
            if yaml_content:
                templates = self.extract_template_refs(yaml_content)
                if templates:
                    logger.info(
                        "  Found %d template reference(s) in pipeline",
                        len(templates))

                    # Check which templates are missing in destination
                    for template_ref, version_label in templates:
                        exists = self.check_template_exists(
                            template_ref, version_label)
                        if not exists:
                            missing_templates.append(
                                (template_ref, version_label))
                            logger.warning(
                                "  ⚠ Template '%s' (v%s) not found in dest",
                                template_ref, version_label)
                        else:
                            logger.info(
                                "  ✓ Template '%s' (v%s) exists in dest",
                                template_ref, version_label)

                    # If templates are missing, try to migrate them
                    if missing_templates and not dry_run:
                        # Check if auto_migrate_templates is enabled
                        auto_migrate = self.config.get(
                            'options', {}).get('auto_migrate_templates',
                                               False)
                        interactive = not self.config.get(
                            'non_interactive', False)

                        if auto_migrate or interactive:
                            template_list = "\n".join([
                                f"  • {ref} (version: {ver})"
                                for ref, ver in missing_templates
                            ])

                            # In interactive mode, ask what to do
                            if interactive and not auto_migrate:
                                from prompt_toolkit.shortcuts import (  # noqa: F401, E501
                                    button_dialog)

                                text = (
                                    f"Pipeline '{pipeline_name}' requires "
                                    f"templates that\ndon't exist in the "
                                    f"destination:\n\n{template_list}\n\n"
                                    f"Do you want to automatically migrate "
                                    f"these templates?")

                                choice = button_dialog(
                                    title="Missing Templates",
                                    text=text,
                                    buttons=[
                                        ('migrate', 'Migrate Templates'),
                                        ('skip_templates',
                                         'Continue Without Templates'),
                                        ('skip', 'Skip This Pipeline')
                                    ]
                                ).run()

                                if choice == 'skip':
                                    logger.info(
                                        "  ⊘ Skipping pipeline due to "
                                        "missing templates")
                                    self.migration_stats['pipelines'][
                                        'failed'] += 1
                                    continue
                                elif choice == 'migrate':
                                    should_migrate = True
                                else:
                                    should_migrate = False
                            else:
                                # Auto-migrate enabled
                                should_migrate = True
                                logger.info(
                                    "  → Attempting to auto-migrate "
                                    "templates...")

                            # Try to migrate the templates
                            if should_migrate:
                                for template_ref, version_label in (
                                        missing_templates):
                                    self.migrate_template(
                                        template_ref, version_label)
                        else:
                            # In non-interactive mode without
                            # auto-migrate, just warn
                            logger.warning(
                                "  ⚠ Pipeline requires %d template(s) "
                                "that must be created manually",
                                len(missing_templates))

            # Check if pipeline already exists
            dest_endpoint = (
                f"/v1/orgs/{self.dest_org}/projects/{self.dest_project}/"
                f"pipelines/{pipeline_id}")
            existing = self.dest_client.get(dest_endpoint)

            if existing:
                if self.config.get('options', {}).get('skip_existing', True):
                    logger.info(
                        "Pipeline '%s' already exists. Skipping.", pipeline_id)
                    continue
                else:
                    logger.info(
                        "Pipeline '%s' exists. Updating...", pipeline_id)
                    if dry_run:
                        logger.info(
                            "[DRY RUN] Would update pipeline '%s'", pipeline_name)  # noqa: E501
                        result = True  # Simulate success
                    else:
                        result = self.dest_client.put(
                            dest_endpoint, json=pipeline_details)
            else:
                # Create pipeline in destination
                create_endpoint = (
                    f"/v1/orgs/{self.dest_org}/projects/{self.dest_project}/"
                    f"pipelines")
                if dry_run:
                    logger.info(
                        "[DRY RUN] Would create pipeline '%s'", pipeline_name)
                    result = True  # Simulate success
                else:
                    logger.info(
                        "Creating pipeline with payload keys: %s",
                        list(pipeline_details.keys()) if isinstance(
                            pipeline_details, dict) else "not a dict")
                    logger.debug("Pipeline payload: %s",
                                 json.dumps(pipeline_details, indent=2)[:2000])

                    # Update org and project identifiers in YAML
                    if 'pipeline_yaml' in pipeline_details:
                        yaml_content = pipeline_details['pipeline_yaml']

                        # Replace source org/project with dest org/project
                        yaml_content = yaml_content.replace(
                            f'orgIdentifier: {self.source_org}',
                            f'orgIdentifier: {self.dest_org}')
                        yaml_content = yaml_content.replace(
                            f'projectIdentifier: {self.source_project}',
                            f'projectIdentifier: {self.dest_project}')

                        logger.debug(
                            "Updated identifiers: org=%s, project=%s",
                            self.dest_org, self.dest_project)

                        # Update the pipeline_details with corrected YAML
                        pipeline_details['pipeline_yaml'] = yaml_content

                    # The v1 API requires snake_case field name: pipeline_yaml
                    # with identifier and name as separate fields
                    yaml_content = pipeline_details.get('pipeline_yaml', '')
                    payload = {
                        'identifier': pipeline_id,
                        'name': pipeline_name,
                        'pipeline_yaml': yaml_content
                    }

                    # Add description and tags if present
                    if pipeline_details.get('description'):
                        payload['description'] = (
                            pipeline_details['description'])
                    if pipeline_details.get('tags'):
                        payload['tags'] = pipeline_details['tags']

                    logger.debug("Sending pipeline creation payload")
                    logger.debug("Final payload YAML (first 500 chars): %s",
                                 payload.get('pipeline_yaml', '')[:500])
                    result = self.dest_client.post(
                        create_endpoint, json=payload)
                    if not result:
                        logger.error(
                            "Pipeline creation failed. Payload had keys: %s",
                            list(pipeline_details.keys()))

            if result:
                self.migration_stats['pipelines']['success'] += 1

                # Migrate associated input sets
                if self.config.get('options', {}).get('migrate_input_sets', True):  # noqa: E501
                    self.migrate_input_sets(pipeline_id)
            else:
                logger.error("✗ Failed to migrate pipeline: %s", pipeline_name)
                self.migration_stats['pipelines']['failed'] += 1

            time.sleep(0.5)

        return True

    def run_migration(self):
        """Execute the full migration process"""
        dry_run = self.config.get('dry_run', False)

        logger.info("=" * 80)
        if dry_run:
            logger.info("HARNESS PIPELINE MIGRATION - DRY RUN MODE")
            logger.info("NO CHANGES WILL BE MADE")
        else:
            logger.info("HARNESS PIPELINE MIGRATION")
        logger.info("=" * 80)
        logger.info("Source: %s", self.config['source']['base_url'])
        logger.info(
            "  Org: %s, Project: %s", self.source_org, self.source_project)
        logger.info("Destination: %s", self.config['destination']['base_url'])
        logger.info("  Org: %s, Project: %s", self.dest_org, self.dest_project)

        # Show selected pipelines if any
        selected_ids = self.config.get('selected_pipelines', [])
        if selected_ids:
            logger.info("  Selected Pipelines: %d", len(selected_ids))

        logger.info("=" * 80)

        # Step 1: Verify prerequisites
        if not self.verify_prerequisites():
            logger.error(
                "Prerequisites verification failed. Aborting migration.")
            return False

        # Step 2: Migrate pipelines
        if not self.migrate_pipelines():
            logger.error("Pipeline migration failed")
            return False

        # Print summary
        self.print_summary()

        return True

    def print_summary(self):
        """Print migration summary"""
        dry_run = self.config.get('dry_run', False)

        logger.info("\n%s", "=" * 80)
        if dry_run:
            logger.info("MIGRATION SUMMARY - DRY RUN")
            logger.info("(No actual changes were made)")
        else:
            logger.info("MIGRATION SUMMARY")
        logger.info("=" * 80)

        for resource_type, stats in self.migration_stats.items():
            logger.info("\n%s:", resource_type.upper())
            for status, count in stats.items():
                logger.info("  %s: %s", status.capitalize(), count)

        logger.info("\n%s", "=" * 80)


def non_interactive_mode(config_file: str):
    """Non-interactive mode: use all values from config file without prompts"""
    print("\n" + "=" * 80)
    print("HARNESS PIPELINE MIGRATION - NON-INTERACTIVE MODE")
    print("=" * 80)
    print("Using all values from config file")

    # Load config
    base_config = load_config(config_file)

    # Validate required fields
    required_fields = {
        'source': ['base_url', 'api_key', 'org', 'project'],
        'destination': ['base_url', 'api_key', 'org', 'project']
    }

    for section, fields in required_fields.items():
        if section not in base_config:
            print(f"❌ Error: Missing '{section}' section in config")
            sys.exit(1)
        for field in fields:
            if not base_config[section].get(field):
                print(f"❌ Error: Missing '{field}' in '{section}' section")
                sys.exit(1)

    # Build config from file
    config = {
        'source': {
            'base_url': base_config['source']['base_url'],
            'api_key': base_config['source']['api_key'],
            'org': base_config['source']['org'],
            'project': base_config['source']['project']
        },
        'destination': {
            'base_url': base_config['destination']['base_url'],
            'api_key': base_config['destination']['api_key'],
            'org': base_config['destination']['org'],
            'project': base_config['destination']['project']
        },
        'options': base_config.get('options', {
            'migrate_input_sets': True,
            'skip_existing': True
        }),
        'pipelines': base_config.get('selected_pipelines', []),
        'dry_run': False
    }

    print(
        f"Source: {config['source']['org']}/"
        f"{config['source']['project']}")
    print(f"Destination: {config['destination']['org']}/"
          f"{config['destination']['project']}")
    print(f"Pipelines: {len(config['pipelines'])}")

    return config
