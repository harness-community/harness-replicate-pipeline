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


def hybrid_mode(config_file: str):
    """Hybrid mode: use config file values and prompt for missing fields"""
    print("\n" + "=" * 80)
    print("HARNESS PIPELINE MIGRATION")
    print("=" * 80)
    print(
        "Using config file values where available, "
        "prompting for missing fields")

    # Load base config
    base_config = load_config(config_file)

    # Initialize clients with config values
    source_url = base_config.get('source', {}).get('base_url')
    source_api_key = base_config.get('source', {}).get('api_key')
    dest_url = base_config.get('destination', {}).get('base_url')
    dest_api_key = base_config.get('destination', {}).get('api_key')

    # Prompt for missing credentials
    if not source_url:
        source_subdomain = radiolist_dialog(
            title="Source Account",
            text="Select source Harness subdomain:",
            values=[("app", "app.harness.io"), ("app3", "app3.harness.io")]
        ).run()
        if not source_subdomain:
            print("❌ Selection cancelled")
            sys.exit(1)
        source_url = f"https://{source_subdomain}.harness.io"
    else:
        print(f"✓ Using source URL from config: {source_url}")

    if not source_api_key:
        source_api_key = prompt("Source API Key: ", is_password=True).strip()
        if not source_api_key:
            print("❌ Error: Source API key is required")
            sys.exit(1)
    else:
        print("✓ Using source API key from config")

    if not dest_url:
        dest_subdomain = radiolist_dialog(
            title="Destination Account",
            text="Select destination Harness subdomain:",
            values=[("app", "app.harness.io"), ("app3", "app3.harness.io")]
        ).run()
        if not dest_subdomain:
            print("❌ Selection cancelled")
            sys.exit(1)
        dest_url = f"https://{dest_subdomain}.harness.io"
    else:
        print(f"✓ Using destination URL from config: {dest_url}")

    if not dest_api_key:
        dest_api_key = prompt("Destination API Key: ",
                              is_password=True).strip()
        if not dest_api_key:
            print("❌ Error: Destination API key is required")
            sys.exit(1)
    else:
        print("✓ Using destination API key from config")

    # Create clients
    source_client = HarnessAPIClient(source_url, source_api_key)
    dest_client = HarnessAPIClient(dest_url, dest_api_key)

    # Get organization and project selections
    return _get_selections_from_clients(
        source_client, dest_client, base_config, config_file)


def _get_selections_from_clients(source_client, dest_client, base_config,
                                 config_file):
    """Common logic for getting selections from clients"""
    # Initialize variables
    selected_pipelines = []

    # Select source organization
    print("\n" + "=" * 80)
    print("📂 SELECT SOURCE ORGANIZATION")
    print("=" * 80)

    # Check if already configured
    pre_selected_org = base_config.get('source', {}).get('org')
    if pre_selected_org:
        print(f"ℹ️  Previously selected: {pre_selected_org}")
        use_previous = yes_no_dialog(
            title="Use Previous Source Organization?",
            text=(f"Use previously selected SOURCE organization:\n"
                  f"  {pre_selected_org}?")
        ).run()

        if use_previous:
            source_org = pre_selected_org
            print(f"✓ Using: {source_org}")
        else:
            source_org = select_organization(source_client, "source")
            if not source_org:
                print("❌ Selection cancelled")
                sys.exit(1)
    else:
        source_org = select_organization(source_client, "source")
        if not source_org:
            print("❌ Selection cancelled")
            sys.exit(1)

    # Select source project
    print("\n" + "=" * 80)
    print("📁 SELECT SOURCE PROJECT")
    print("=" * 80)

    # Check if already configured
    pre_selected_project = base_config.get('source', {}).get('project')
    if pre_selected_project:
        print(f"ℹ️  Previously selected: {pre_selected_project}")
        use_previous = yes_no_dialog(
            title="Use Previous Source Project?",
            text=(f"Use previously selected SOURCE project:\n"
                  f"  {pre_selected_project}?")
        ).run()

        if use_previous:
            source_project = pre_selected_project
            print(f"✓ Using: {source_project}")
        else:
            source_project = select_project(
                source_client, source_org, "source")
            if not source_project:
                print("❌ Selection cancelled")
                sys.exit(1)
    else:
        source_project = select_project(source_client, source_org, "source")
        if not source_project:
            print("❌ Selection cancelled")
            sys.exit(1)

    # Select pipelines
    print("\n" + "=" * 80)
    print("🔧 SELECT PIPELINES TO MIGRATE")
    print("=" * 80)

    # Check if already configured
    pre_selected_pipelines = base_config.get('selected_pipelines', [])
    if pre_selected_pipelines:
        print(
            f"ℹ️  Previously selected "
            f"{len(pre_selected_pipelines)} pipeline(s):")
        for p in pre_selected_pipelines[:5]:  # Show first 5
            print(f"   - {p.get('name', p.get('identifier'))}")
        if len(pre_selected_pipelines) > 5:
            print(f"   ... and {len(pre_selected_pipelines) - 5} more")

        use_previous = yes_no_dialog(
            title="Use Previous Pipeline Selection?",
            text=(f"Use previously selected "
                  f"{len(pre_selected_pipelines)} SOURCE pipeline(s)?")
        ).run()

        if use_previous:
            # Fetch full pipeline objects for the pre-selected identifiers
            endpoint = (
                f"/v1/orgs/{source_org}/projects/{source_project}/pipelines")
            all_pipelines_response = source_client.get(endpoint)

            if all_pipelines_response:
                if isinstance(all_pipelines_response, list):
                    all_pipes = all_pipelines_response
                elif 'content' in all_pipelines_response:
                    all_pipes = all_pipelines_response.get('content', [])
                else:
                    all_pipes = []

                # Get identifiers from pre-selected
                pre_ids = [p.get('identifier') for p in pre_selected_pipelines]
                # Match with full objects
                selected_pipelines = [
                    p for p in all_pipes if p.get('identifier') in pre_ids]
                print(
                    f"✓ Using {len(selected_pipelines)} "
                    f"previously selected pipeline(s)")
            else:
                print("⚠️  Could not fetch pipelines, re-selecting...")
                selected_pipelines = select_pipelines(
                    source_client, source_org, source_project)
        else:
            selected_pipelines = select_pipelines(
                source_client, source_org, source_project)
    else:
        print("Use Space to select/deselect, Enter to confirm, Esc to cancel")
        selected_pipelines = select_pipelines(
            source_client, source_org, source_project)

    if selected_pipelines is None:
        print("❌ Migration cancelled")
        sys.exit(1)
    elif selected_pipelines == 'ERROR':
        print("⚠️  Error occurred")
        sys.exit(1)
    elif not selected_pipelines or selected_pipelines == 'BACK_TO_PROJECTS':
        print("⚠️  No pipelines selected - continuing with empty selection")
        selected_pipelines = []

    # Select/create destination organization
    print("\n" + "=" * 80)
    print("📂 SELECT DESTINATION ORGANIZATION")
    print("=" * 80)

    # Track if org was just created
    org_just_created = False

    # Check if already configured
    pre_selected_dest_org = base_config.get('destination', {}).get('org')
    if pre_selected_dest_org:
        print(f"ℹ️  Previously selected: {pre_selected_dest_org}")
        use_previous = yes_no_dialog(
            title="Use Previous Destination Organization?",
            text=(f"Use previously selected DESTINATION organization:\n"
                  f"  {pre_selected_dest_org}?")
        ).run()

        if use_previous:
            dest_org = pre_selected_dest_org
            print(f"✓ Using: {dest_org}")
        else:
            result = select_or_create_organization(
                dest_client, source_org, "destination")
            if not result:
                print("❌ Selection cancelled")
                sys.exit(1)
            dest_org, org_just_created = result
    else:
        result = select_or_create_organization(
            dest_client, source_org, "destination")
        if not result:
            print("❌ Selection cancelled")
            sys.exit(1)
        dest_org, org_just_created = result

    # Select/create destination project
    print("\n" + "=" * 80)
    print("📁 SELECT DESTINATION PROJECT")
    print("=" * 80)

    # If org was just created, skip to project creation
    if org_just_created:
        print(
            f"ℹ️  Organization '{dest_org}' was just created - "
            f"it has no projects yet")
        dest_project = select_or_create_project(
            dest_client, dest_org, source_project, "destination",
            force_create=True)
        if not dest_project:
            print("❌ Selection cancelled")
            sys.exit(1)
    else:
        # Check if already configured
        pre_selected_dest_project = base_config.get(
            'destination', {}).get('project')
        if pre_selected_dest_project:
            print(f"ℹ️  Previously selected: {pre_selected_dest_project}")
            use_previous = yes_no_dialog(
                title="Use Previous Destination Project?",
                text=(f"Use previously selected DESTINATION project:\n"
                      f"  {pre_selected_dest_project}?")
            ).run()

            if use_previous:
                dest_project = pre_selected_dest_project
                print(f"✓ Using: {dest_project}")
            else:
                dest_project = select_or_create_project(
                    dest_client, dest_org, source_project, "destination")
                if not dest_project:
                    print("❌ Selection cancelled")
                    sys.exit(1)
        else:
            dest_project = select_or_create_project(
                dest_client, dest_org, source_project, "destination")
            if not dest_project:
                print("❌ Selection cancelled")
                sys.exit(1)

    # Migration options
    print("\n" + "=" * 80)
    print("⚙️  MIGRATION OPTIONS")
    print("=" * 80)

    # Use config options or prompt for them
    migrate_input_sets = base_config.get(
        'options', {}).get('migrate_input_sets', True)
    skip_existing = base_config.get('options', {}).get('skip_existing', True)

    # Ask about dry run
    dry_run = yes_no_dialog(
        title="Dry Run",
        text="Do you want to run in dry-run mode? (No changes will be made)"
    ).run()

    # Build final config
    config = {
        'source': {
            'base_url': source_client.base_url,
            'api_key': source_client.api_key,
            'org': source_org,
            'project': source_project
        },
        'destination': {
            'base_url': dest_client.base_url,
            'api_key': dest_client.api_key,
            'org': dest_org,
            'project': dest_project
        },
        'options': {
            'migrate_input_sets': migrate_input_sets,
            'skip_existing': skip_existing
        },
        'pipelines': selected_pipelines if selected_pipelines else [],
        'dry_run': dry_run
    }

    # Ask if user wants to save the configuration
    print("\n" + "=" * 80)
    save_choice = yes_no_dialog(
        title="Save Configuration",
        text=(
            "Do you want to save these selections to the config file?\n\n"
            "This will allow you to quickly re-run with the same settings\n"
            "next time (useful for troubleshooting)."
        )
    ).run()

    if save_choice:
        if save_config(config, config_file):
            print(f"✓ Configuration saved to {config_file}")
        else:
            print(f"✗ Failed to save configuration to {config_file}")

    return config


def select_organization(client: HarnessAPIClient, context: str) -> Optional[str]:  # noqa: E501
    """Interactive organization selection with arrow keys"""
    response = client.get("/v1/orgs")

    if response is None:
        message_dialog(
            title="Error",
            text=f"Failed to retrieve organizations from {context}"
        ).run()
        return None

    # Handle both direct array format and wrapped content format
    if isinstance(response, list):
        orgs = response
    elif 'content' in response:
        orgs = response.get('content', [])
    else:
        message_dialog(
            title="Error",
            text=f"Unexpected response format from {context}"
        ).run()
        return None

    if not orgs:
        message_dialog(
            title="No Organizations",
            text=f"No organizations found in {context} account"
        ).run()
        return None

    # Build values for radiolist (without Back option)
    values = []
    for org in orgs:
        org_data = org.get('org', {})
        identifier = org_data.get('identifier', 'unknown')
        name = org_data.get('name', identifier)
        values.append((identifier, f"{name} ({identifier})"))

    # Show organization selection dialog
    # Note: Esc key cancels and returns None
    selected = radiolist_dialog(
        title=f"Select {context.capitalize()} Organization",
        text=(
            f"Use ↑↓ to navigate, Enter to select, Esc to cancel\n\n"
            f"Found {len(orgs)} organization(s):"),
        values=values
    ).run()

    if selected:
        # Find the selected org name for display
        selected_name = next((v[1]
                             for v in values if v[0] == selected), selected)
        print(f"✓ Selected: {selected_name}")

    return selected


def select_project(client: HarnessAPIClient, org: str, context: str) -> Optional[str]:  # noqa: E501
    """Interactive project selection with arrow keys"""
    endpoint = f"/v1/orgs/{org}/projects"
    response = client.get(endpoint)

    if response is None:
        message_dialog(
            title="Error",
            text=f"Failed to retrieve projects from {context}"
        ).run()
        return None

    # Handle both direct array format and wrapped content format
    if isinstance(response, list):
        projects = response
    elif 'content' in response:
        projects = response.get('content', [])
    else:
        message_dialog(
            title="Error",
            text=f"Unexpected response format from {context}"
        ).run()
        return None

    if not projects:
        message_dialog(
            title="No Projects",
            text=f"No projects found in organization '{org}'"
        ).run()
        return None

    # Build values for radiolist with pipeline counts (without Back option)
    values = []
    for project in projects:
        proj_data = project.get('project', {})
        identifier = proj_data.get('identifier', 'unknown')
        name = proj_data.get('name', identifier)

        # Get pipeline count for this project
        pipeline_endpoint = f"/v1/orgs/{org}/projects/{identifier}/pipelines"
        pipeline_response = client.get(pipeline_endpoint)

        if pipeline_response is not None and isinstance(pipeline_response, list):  # noqa: E501
            pipeline_count = len(pipeline_response)
        else:
            pipeline_count = 0

        values.append(
            (identifier, f"{name} ({identifier}) - {pipeline_count} pipelines"))  # noqa: E501

    selected = radiolist_dialog(
        title=f"Select {context.capitalize()} Project",
        text=(
            f"Use arrow keys to navigate, Enter to select\n\n"
            f"Found {len(projects)} project(s) in '{org}':"),
        values=values
    ).run()

    if selected:
        selected_name = next((v[1]
                             for v in values if v[0] == selected), selected)
        print(f"✓ Selected: {selected_name}")

    return selected


def select_pipelines(
        client: HarnessAPIClient, org: str, project: str
) -> Union[List[Dict], str, None]:
    """Interactive pipeline selection with arrow keys and space to multi-select"""  # noqa: E501
    endpoint = f"/v1/orgs/{org}/projects/{project}/pipelines"
    response = client.get(endpoint)

    if response is None:
        message_dialog(
            title="Error",
            text="Failed to retrieve pipelines"
        ).run()
        return []

    # Handle both direct array format and wrapped content format
    if isinstance(response, list):
        pipelines = response
    elif 'content' in response:
        pipelines = response.get('content', [])
    else:
        message_dialog(
            title="Error",
            text="Unexpected response format"
        ).run()
        return 'ERROR'  # Return error indicator instead of empty list

    if not pipelines:
        choice = button_dialog(
            title="No Pipelines Found",
            text=(
                "No pipelines found in the selected project.\n\n"
                "Would you like to:\n"
                "• Go back and select a different project\n"
                "• Continue with empty selection (skip pipelines)"
            ),
            buttons=[
                ('back', '← Go Back to Project Selection'),
                ('continue', 'Continue with No Pipelines'),
                ('cancel', 'Cancel Migration')
            ]
        ).run()

        if choice == 'back':
            return 'BACK_TO_PROJECTS'  # Special return value to indicate going back  # noqa: E501
        elif choice == 'continue':
            return []  # Empty list to continue with no pipelines
        else:
            return None  # Cancel

    # Build values for checkboxlist (without Back option)
    values = []
    for pipeline in pipelines:
        identifier = pipeline.get('identifier', 'unknown')
        name = pipeline.get('name', identifier)
        values.append((identifier, f"{name} ({identifier})"))

    selected_ids = checkboxlist_dialog(
        title="Select Pipelines to Migrate",
        text=(
            f"Use arrow keys to navigate, Space to select/deselect, "
            f"Enter to confirm\n\nFound {len(pipelines)} pipeline(s):"),  # noqa: E501
        values=values
    ).run()

    if not selected_ids:
        return []

    # Get full pipeline objects for selected IDs
    selected = [p for p in pipelines if p.get('identifier') in selected_ids]

    print(f"✓ Selected {len(selected)} pipeline(s):")
    for p in selected:
        print(f"   - {p.get('name', p.get('identifier'))}")

    return selected


def select_or_create_organization(
        client: HarnessAPIClient, source_org: str, context: str
) -> Optional[tuple]:
    """Interactive organization selection or creation with arrow keys

    Returns:
        tuple: (org_identifier, was_created) or None if cancelled
    """
    response = client.get("/v1/orgs")

    existing_orgs = []
    if response:
        # Handle both direct array format and wrapped content format
        if isinstance(response, list):
            existing_orgs = response
        elif 'content' in response:
            existing_orgs = response.get('content', [])

    # Check if source org exists
    source_org_exists = any(
        org.get('org', {}).get('identifier') == source_org
        for org in existing_orgs
    )

    # Build combined options list:
    # 1. Create with same name as source (if doesn't exist)
    # 2. Create custom name
    # 3. Existing organizations
    values = []

    # Option 1: Create matching org (only if source org doesn't exist)
    if not source_org_exists:
        values.append(
            ('CREATE_MATCHING',
             f"➕ Create '{source_org}' (same as source)"))

    # Option 2: Create custom org
    values.append(
        ('CREATE_CUSTOM', "➕ Create new organization with custom name"))

    # Option 3: Existing organizations
    for org in existing_orgs:
        org_data = org.get('org', {})
        identifier = org_data.get('identifier', 'unknown')
        name = org_data.get('name', identifier)
        values.append((identifier, f"{name} ({identifier})"))

    choice = radiolist_dialog(
        title=f"Select {context.capitalize()} Organization",
        text=(
            "Use ↑↓ to navigate, Enter to select, Esc to cancel\n\n"
            "Select an option:"),
        values=values
    ).run()

    if not choice:
        return None

    # Handle create matching org
    if choice == 'CREATE_MATCHING':
        print(f"\nCreating organization '{source_org}'...")
        result = client.post("/v1/orgs", json={
            "org": {
                "identifier": source_org,
                "name": source_org
            }
        })
        if result:
            print(f"✓ Organization '{source_org}' created successfully")
            return (source_org, True)  # Return tuple: (org_id, was_created)
        else:
            message_dialog(
                title="Error",
                text=f"Failed to create organization '{source_org}'"
            ).run()
            return None

    # Handle create custom
    elif choice == 'CREATE_CUSTOM':
        print()
        org_id = prompt("Enter organization identifier: ").strip()
        org_name = prompt(
            "Enter organization name (or press Enter for same as identifier): "
        ).strip() or org_id

        if not org_id:
            message_dialog(
                title="Error",
                text="Organization identifier is required"
            ).run()
            return None

        print(f"\nCreating organization '{org_name}'...")
        result = client.post("/v1/orgs", json={
            "org": {
                "identifier": org_id,
                "name": org_name
            }
        })
        if result:
            print(f"✓ Organization '{org_name}' created successfully")
            return (org_id, True)  # Return tuple: (org_id, was_created)
        else:
            message_dialog(
                title="Error",
                text=f"Failed to create organization '{org_name}'"
            ).run()
            return None

    # Otherwise, it's an existing organization identifier
    return (choice, False)  # Return tuple: (org_id, was_created)


def select_or_create_project(
        client: HarnessAPIClient, org: str, source_project: str, context: str,
        force_create: bool = False
) -> Optional[str]:
    """Interactive project selection or creation with arrow keys

    Args:
        force_create: If True, skip to creation dialog (for new orgs)
    """
    endpoint = f"/v1/orgs/{org}/projects"
    response = client.get(endpoint)

    existing_projects = []
    if response:
        # Handle both direct array format and wrapped content format
        if isinstance(response, list):
            existing_projects = response
        elif 'content' in response:
            existing_projects = response.get('content', [])

    # If force_create is True, only show creation options
    if force_create:
        values = []
        # Only show create matching and create custom options
        values.append(
            ('CREATE_MATCHING',
             f"➕ Create '{source_project}' (same as source)"))
        values.append(
            ('CREATE_CUSTOM', "➕ Create new project with custom name"))

        choice = radiolist_dialog(
            title=f"Create {context.capitalize()} Project",
            text=(
                "Use ↑↓ to navigate, Enter to select, Esc to cancel\n\n"
                "Organization was just created - "
                "select how to create project:"),
            values=values
        ).run()
    else:
        # Check if source project exists
        source_project_exists = any(
            proj.get('project', {}).get('identifier') == source_project
            for proj in existing_projects
        )

        # Build combined options list:
        # 1. Create with same name as source (if doesn't exist)
        # 2. Create custom name
        # 3. Existing projects
        values = []

        # Option 1: Create matching project (only if doesn't exist)
        if not source_project_exists:
            values.append(
                ('CREATE_MATCHING',
                 f"➕ Create '{source_project}' (same as source)"))

        # Option 2: Create custom project
        values.append(
            ('CREATE_CUSTOM', "➕ Create new project with custom name"))

        # Option 3: Existing projects
        for project in existing_projects:
            proj_data = project.get('project', {})
            identifier = proj_data.get('identifier', 'unknown')
            name = proj_data.get('name', identifier)
            values.append((identifier, f"{name} ({identifier})"))

        choice = radiolist_dialog(
            title=f"Select {context.capitalize()} Project",
            text=(
                "Use ↑↓ to navigate, Enter to select, Esc to cancel\n\n"
                "Select an option:"),
            values=values
        ).run()

    if not choice:
        return None

    # Handle create matching project
    if choice == 'CREATE_MATCHING':
        print(f"\nCreating project '{source_project}'...")
        result = client.post(f"/v1/orgs/{org}/projects", json={
            "project": {
                "identifier": source_project,
                "name": source_project,
                "org": org
            }
        })
        if result:
            print(f"✓ Project '{source_project}' created successfully")
            return source_project
        else:
            message_dialog(
                title="Error",
                text=f"Failed to create project '{source_project}'"
            ).run()
            return None

    # Handle create custom
    elif choice == 'CREATE_CUSTOM':
        print()
        proj_id = prompt("Enter project identifier: ").strip()
        proj_name = prompt(
            "Enter project name (or press Enter for same as identifier): "
        ).strip() or proj_id

        if not proj_id:
            message_dialog(
                title="Error",
                text="Project identifier is required"
            ).run()
            return None

        print(f"\nCreating project '{proj_name}'...")
        result = client.post(f"/v1/orgs/{org}/projects", json={
            "project": {
                "identifier": proj_id,
                "name": proj_name,
                "org": org
            }
        })
        if result:
            print(f"✓ Project '{proj_name}' created successfully")
            return proj_id
        else:
            message_dialog(
                title="Error",
                text=f"Failed to create project '{proj_name}'"
            ).run()
            return None

    # Otherwise, it's an existing project identifier
    return choice
