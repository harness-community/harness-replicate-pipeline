#!/usr/bin/env python3
# pylint: disable=too-many-lines,line-too-long
# flake8: noqa: E501
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
from typing import Any, Dict, List, Optional, Union

import requests
import yaml

# For interactive mode with arrow key navigation
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import (
    radiolist_dialog,
    checkboxlist_dialog,
    button_dialog,
    message_dialog,
    yes_no_dialog,
)

# Configure logging


def setup_logging(debug=False):
    """Setup logging configuration"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )


def apply_cli_overrides(config: Dict[str, Any], args) -> Dict[str, Any]:
    """Apply CLI argument overrides to config with priority: config file > CLI args > interactive"""
    # Create a copy to avoid modifying the original
    updated_config = config.copy()
    
    # Source configuration overrides
    if args.source_url:
        updated_config.setdefault("source", {})["base_url"] = args.source_url
    if args.source_api_key:
        updated_config.setdefault("source", {})["api_key"] = args.source_api_key
    if args.source_org:
        updated_config.setdefault("source", {})["org"] = args.source_org
    if args.source_project:
        updated_config.setdefault("source", {})["project"] = args.source_project
    
    # Destination configuration overrides
    if args.dest_url:
        updated_config.setdefault("destination", {})["base_url"] = args.dest_url
    if args.dest_api_key:
        updated_config.setdefault("destination", {})["api_key"] = args.dest_api_key
    if args.dest_org:
        updated_config.setdefault("destination", {})["org"] = args.dest_org
    if args.dest_project:
        updated_config.setdefault("destination", {})["project"] = args.dest_project
    
    # Migration options overrides
    options = updated_config.setdefault("options", {})
    
    # Handle migrate_input_sets (CLI args override config)
    if args.migrate_input_sets:
        options["migrate_input_sets"] = True
    elif args.no_migrate_input_sets:
        options["migrate_input_sets"] = False
    
    # Handle skip_existing (CLI args override config)
    if args.skip_existing:
        options["skip_existing"] = True
    elif args.no_skip_existing:
        options["skip_existing"] = False
    
    return updated_config


logger = logging.getLogger(__name__)


class HarnessAPIClient:
    """Client for interacting with Harness API"""

    def __init__(self, base_url: str, api_key: str):
        # Harness API uses direct base URL with /v1 endpoints
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    @staticmethod
    def normalize_response(response: Optional[Union[Dict, List]]) -> List[Dict]:
        """Normalize API response to always return a list.
        
        Handles both direct array format and wrapped content format.
        Returns empty list if response is None or invalid.
        """
        if response is None:
            return []
        if isinstance(response, list):
            return response
        if isinstance(response, dict) and "content" in response:
            return response.get("content", [])
        return []

    def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[Dict]:  # noqa: E501
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"

        # Log the request for debugging
        logger.debug("Making %s request to: %s", method, url)
        if "headers" in kwargs:
            logger.debug("Custom headers: %s", kwargs["headers"])
        if "data" in kwargs:
            logger.debug("Sending raw data (not JSON)")

        try:
            response = self.session.request(method, url, **kwargs)

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
                            "Error details: %s", json.dumps(error_details, indent=2)
                        )
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
        except (
            requests.exceptions.RequestException,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as e:
            logger.error("Request failed: %s", e)
            return None

    def get(self, endpoint: str, **kwargs) -> Optional[Dict]:
        """GET request"""
        return self._make_request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> Optional[Dict]:
        """POST request"""
        return self._make_request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> Optional[Dict]:
        """PUT request"""
        return self._make_request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Optional[Dict]:
        """DELETE request"""
        return self._make_request("DELETE", endpoint, **kwargs)


class HarnessMigrator:
    """Main migration orchestrator"""

    def __init__(self, config: Dict):
        self.config = config
        self.source_client = HarnessAPIClient(
            config["source"]["base_url"], config["source"]["api_key"]
        )
        self.dest_client = HarnessAPIClient(
            config["destination"]["base_url"], config["destination"]["api_key"]
        )

        self.source_org = config["source"]["org"]
        self.source_project = config["source"]["project"]
        self.dest_org = config["destination"]["org"]
        self.dest_project = config["destination"]["project"]

        self.migration_stats = {
            "pipelines": {"success": 0, "failed": 0, "skipped": 0},
            "input_sets": {"success": 0, "failed": 0, "skipped": 0},
            "templates": {"success": 0, "failed": 0, "skipped": 0},
        }
        self.discovered_templates = set()  # Track templates found in pipelines

    def _get_option(self, key: str, default=None):
        """Helper to get config option with default."""
        return self.config.get("options", {}).get(key, default)

    def _is_dry_run(self) -> bool:
        """Check if running in dry-run mode."""
        return self.config.get("dry_run", False)

    def _is_interactive(self) -> bool:
        """Check if running in interactive mode."""
        return not self.config.get("non_interactive", False)

    def _build_endpoint(self, resource: Optional[str] = None, org: Optional[str] = None, 
                       project: Optional[str] = None, resource_id: Optional[str] = None, 
                       sub_resource: Optional[str] = None) -> str:
        """Build consistent API endpoint paths.
        
        Args:
            resource: Main resource type (e.g., 'orgs', 'projects', 'pipelines')
            org: Organization identifier
            project: Project identifier
            resource_id: Specific resource identifier
            sub_resource: Sub-resource path (e.g., 'versions/v1')
        
        Returns:
            Formatted endpoint path
        """
        parts = ["/v1"]
        
        if org:
            parts.extend(["orgs", org])
        if project:
            parts.extend(["projects", project])
        if resource and resource != "orgs":
            parts.append(resource)
        if resource_id:
            parts.append(resource_id)
        if sub_resource:
            parts.append(sub_resource)
            
        return "/".join(parts)

    def _update_yaml_identifiers(self, yaml_content: str, wrapper_key: Optional[str] = None) -> str:
        """Update org and project identifiers in YAML content.
        
        Args:
            yaml_content: YAML string to update
            wrapper_key: Optional wrapper key (e.g., 'template', 'pipeline')
        
        Returns:
            Updated YAML string
        """
        try:
            data = yaml.safe_load(yaml_content)
            
            # Determine where to update identifiers
            target = data.get(wrapper_key, data) if wrapper_key else data
            
            target["orgIdentifier"] = self.dest_org
            target["projectIdentifier"] = self.dest_project
            
            return yaml.dump(data, default_flow_style=False, sort_keys=False)
        except (yaml.YAMLError, ValueError, TypeError, KeyError) as e:
            logger.error("Failed to update YAML identifiers: %s", e)
            # Fallback to string replacement
            yaml_content = yaml_content.replace(
                f"orgIdentifier: {self.source_org}",
                f"orgIdentifier: {self.dest_org}"
            )
            yaml_content = yaml_content.replace(
                f"projectIdentifier: {self.source_project}",
                f"projectIdentifier: {self.dest_project}"
            )
            return yaml_content

    def extract_template_refs(self, yaml_content: str) -> List[tuple]:
        """Extract template references from pipeline YAML

        Returns list of tuples: (templateRef, versionLabel)
        """
        templates = []

        # Parse YAML to find template references
        # Template refs can appear at various levels in the YAML structure
        try:
            pipeline_dict = yaml.safe_load(yaml_content)
            self._find_template_refs(pipeline_dict, templates)
        except (yaml.YAMLError, ValueError, TypeError) as e:
            logger.warning("Could not parse YAML to extract templates: %s", e)
            # Fallback to regex if YAML parsing fails
            # Pattern matches templateRef and versionLabel on same or adjacent lines
            pattern = r'templateRef:\s*(\S+).*?versionLabel:\s*["\']?([^"\'\s]+)["\']?'
            matches = re.findall(pattern, yaml_content, re.DOTALL)
            for template_ref, version_label in matches:
                templates.append((template_ref, version_label))
                self.discovered_templates.add((template_ref, version_label))

        return templates

    def _find_template_refs(self, obj, templates):
        """Recursively find template references in YAML structure"""
        if isinstance(obj, dict):
            # Check if this dict has templateRef (versionLabel is optional)
            if "templateRef" in obj:
                template_ref = obj["templateRef"]
                # versionLabel can be empty/missing to indicate stable version
                version_label = obj.get("versionLabel", "")
                if version_label is None:
                    version_label = ""
                else:
                    version_label = str(version_label)
                templates.append((template_ref, version_label))
                self.discovered_templates.add((template_ref, version_label))
            # Recurse into dict values
            for value in obj.values():
                self._find_template_refs(value, templates)
        elif isinstance(obj, list):
            # Recurse into list items
            for item in obj:
                self._find_template_refs(item, templates)

    def list_templates(
        self, org: str, project: str, client: Optional[HarnessAPIClient] = None
    ) -> List[Dict]:
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

        endpoint = self._build_endpoint("templates", org=org, project=project)
        response = client.get(endpoint)
        return HarnessAPIClient.normalize_response(response)

    def get_template(
        self,
        template_ref: str,
        version_label: str,
        org: str,
        project: str,
        client: Optional[HarnessAPIClient] = None,
    ) -> Optional[Dict]:
        """Get template details including YAML

        Args:
            template_ref: Template identifier
            version_label: Template version (empty string = stable version)
            org: Organization identifier
            project: Project identifier
            client: API client to use (defaults to source_client)

        Returns:
            Template dictionary with YAML, or None if not found
        """
        if client is None:
            client = self.source_client

        # Build sub_resource for version if specified
        sub_resource = f"versions/{version_label}" if version_label else None
        endpoint = self._build_endpoint(
            "templates", org=org, project=project, 
            resource_id=template_ref, sub_resource=sub_resource
        )

        return client.get(endpoint)

    def check_template_exists(self, template_ref: str, version_label: str) -> bool:
        """Check if a template exists in destination

        Args:
            template_ref: Template identifier
            version_label: Template version

        Returns:
            True if exists, False otherwise
        """
        dest_template = self.get_template(
            template_ref,
            version_label,
            self.dest_org,
            self.dest_project,
            self.dest_client,
        )
        return dest_template is not None

    def create_template(
        self,
        template_yaml: str,
        is_stable: bool = True,
        comments: str = "Migrated template",
    ) -> Optional[Dict]:
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
        endpoint = self._build_endpoint("templates", org=self.dest_org, project=self.dest_project)

        payload = {
            "template_yaml": template_yaml,
            "is_stable": is_stable,
            "comments": comments,
        }

        return self.dest_client.post(endpoint, json=payload)

    def migrate_template(self, template_ref: str, version_label: str) -> bool:
        """Migrate a single template from source to destination

        Args:
            template_ref: Template identifier
            version_label: Template version (empty string = stable version)

        Returns:
            True if successful, False otherwise
        """
        version_display = version_label if version_label else "stable"
        logger.info("  Migrating template: %s (v%s)", template_ref, version_display)

        # Get template from source (empty version = get stable)
        source_template = self.get_template(
            template_ref,
            version_label,
            self.source_org,
            self.source_project,
            self.source_client,
        )

        if not source_template:
            logger.error("  ✗ Failed to get template from source")
            return False

        # If we requested stable (empty version), get the actual version from response
        # When creating a template, we need to specify the actual version
        # The version is nested under 'template' key
        template_data = source_template.get("template", {})
        actual_version = template_data.get(
            "version_label", template_data.get("versionLabel", "")
        )
        if not actual_version:
            logger.error("  ✗ Could not determine template version from source")
            logger.error("  ✗ Available fields: %s", list(source_template.keys()))
            logger.error("  ✗ Template fields: %s", list(template_data.keys()))
            return False

        # Check if already exists in destination (with actual version)
        if self.check_template_exists(template_ref, actual_version):
            logger.info("  ✓ Template already exists in destination, skipping")
            self.migration_stats["templates"]["skipped"] += 1
            return True

        # Extract YAML and update org/project identifiers
        # YAML is also nested under 'template' key
        template_yaml = template_data.get("yaml", "")
        if not template_yaml:
            logger.error("  ✗ No YAML found in source template")
            return False

        # Update YAML to use destination org/project and set version
        updated_yaml = self._update_yaml_identifiers(template_yaml, wrapper_key="template")
        
        # Ensure version is set in the YAML
        try:
            template_dict = yaml.safe_load(updated_yaml)
            target = template_dict.get("template", template_dict)
            target["versionLabel"] = actual_version
            updated_yaml = yaml.dump(template_dict, default_flow_style=False, sort_keys=False)
        except (yaml.YAMLError, ValueError, TypeError, KeyError) as e:
            logger.error("  ✗ Failed to set template version: %s", e)
            return False

        # Create in destination with actual version
        result = self.create_template(
            updated_yaml,
            is_stable=source_template.get("stable_template", True),
            comments=f"Migrated from {self.source_org}/{self.source_project}",
        )

        if result:
            logger.info("  ✓ Template migrated successfully")
            self.migration_stats["templates"]["success"] += 1
            return True
        else:
            logger.error("  ✗ Failed to create template in destination")
            self.migration_stats["templates"]["failed"] += 1
            return False

    def _create_org_if_missing(self) -> bool:
        """Create destination organization if it doesn't exist."""
        org_endpoint = self._build_endpoint("orgs", org=self.dest_org)
        org_response = self.dest_client.get(org_endpoint)

        if org_response:
            return True  # Already exists

        logger.error("Destination organization '%s' does not exist", self.dest_org)

        if self._is_dry_run():
            logger.info("[DRY RUN] Would create organization '%s'", self.dest_org)
            logger.info("Organization '%s' would be created successfully", self.dest_org)
            return True

        logger.info("Creating organization...")
        create_org = self.dest_client.post(
            "/v1/orgs",
            json={"org": {"identifier": self.dest_org, "name": self.dest_org}},
        )

        if not create_org:
            logger.error("Failed to create organization")
            return False
        
        logger.info("Organization '%s' created successfully", self.dest_org)
        return True

    def _create_project_if_missing(self) -> bool:
        """Create destination project if it doesn't exist."""
        project_endpoint = self._build_endpoint("projects", org=self.dest_org, resource_id=self.dest_project)
        project_response = self.dest_client.get(project_endpoint)

        if project_response:
            return True  # Already exists

        logger.error("Destination project '%s' does not exist", self.dest_project)

        if self._is_dry_run():
            logger.info("[DRY RUN] Would create project '%s'", self.dest_project)
            logger.info("Project '%s' would be created successfully", self.dest_project)
            return True

        logger.info("Creating project...")
        projects_endpoint = self._build_endpoint("projects", org=self.dest_org)
        create_project = self.dest_client.post(
            projects_endpoint,
            json={
                "project": {
                    "identifier": self.dest_project,
                    "name": self.dest_project,
                    "org": self.dest_org,
                }
            },
        )

        if not create_project:
            logger.error("Failed to create project")
            return False
        
        logger.info("Project '%s' created successfully", self.dest_project)
        return True

    def verify_prerequisites(self) -> bool:
        """Verify that destination org and project exist"""
        logger.info("Verifying destination org and project...")
        
        if not self._create_org_if_missing():
            return False
        
        if not self._create_project_if_missing():
            return False
        
        return True

    def migrate_input_sets(self, pipeline_id: str) -> bool:
        """Migrate input sets for a specific pipeline"""
        logger.info("  Checking for input sets for pipeline: %s", pipeline_id)

        # List input sets
        endpoint = self._build_endpoint("input-sets", org=self.source_org, project=self.source_project)
        params = {"pipeline": pipeline_id}
        input_sets_response = self.source_client.get(endpoint, params=params)
        input_sets = HarnessAPIClient.normalize_response(input_sets_response)

        if not input_sets:
            logger.info("  No input sets found for pipeline: %s", pipeline_id)
            return True

        logger.info("  Migrating %d input sets...", len(input_sets))

        for input_set in input_sets:
            input_set_id = input_set.get("identifier")
            input_set_name = input_set.get("name", input_set_id)
            logger.info("  Migrating input set: %s", input_set_name)

            # Get full input set details
            get_endpoint = self._build_endpoint(
                "input-sets", org=self.source_org, project=self.source_project, resource_id=input_set_id
            )
            input_set_details = self.source_client.get(get_endpoint, params={"pipeline": pipeline_id})

            if not input_set_details:
                logger.error("  Failed to get details for input set: %s", input_set_id)
                self.migration_stats["input_sets"]["failed"] += 1
                continue

            # Update org/project identifiers in input set YAML
            if "input_set_yaml" in input_set_details:
                yaml_content = input_set_details["input_set_yaml"]
                updated_yaml = self._update_yaml_identifiers(yaml_content, wrapper_key="inputSet")
                input_set_details["input_set_yaml"] = updated_yaml

            # Create input set in destination
            create_endpoint = self._build_endpoint("input-sets", org=self.dest_org, project=self.dest_project)

            if self._is_dry_run():
                logger.info("  [DRY RUN] Would create input set '%s'", input_set_name)
                result = True
            else:
                result = self.dest_client.post(create_endpoint, params={"pipeline": pipeline_id}, json=input_set_details)

            if result:
                logger.info("  ✓ Input set '%s' migrated successfully", input_set_name)
                self.migration_stats["input_sets"]["success"] += 1
            else:
                logger.error("  ✗ Failed to migrate input set: %s", input_set_name)
                self.migration_stats["input_sets"]["failed"] += 1

            time.sleep(0.3)

        return True

    def _get_pipelines_to_migrate(self) -> List[Dict]:
        """Fetch and filter pipelines to migrate."""
        endpoint = self._build_endpoint("pipelines", org=self.source_org, project=self.source_project)
        pipelines_response = self.source_client.get(endpoint)
        all_pipelines = HarnessAPIClient.normalize_response(pipelines_response)

        # Filter to selected pipelines if specified
        selected_pipelines = self.config.get("pipelines", [])
        if selected_pipelines:
            selected_ids = [p.get("identifier") for p in selected_pipelines]
            pipelines = [p for p in all_pipelines if p.get("identifier") in selected_ids]
            logger.info(
                "Migrating %d selected pipeline(s) out of %d total",
                len(pipelines), len(all_pipelines)
            )
        else:
            pipelines = all_pipelines
            logger.info("Found %d pipelines to migrate", len(pipelines))

        return pipelines

    def _get_pipeline_details(self, pipeline_id: str, pipeline: Dict) -> Optional[Dict]:
        """Fetch full pipeline details including YAML."""
        get_endpoint = self._build_endpoint(
            "pipelines", org=self.source_org, project=self.source_project, resource_id=pipeline_id
        )

        pipeline_response = self.source_client.get(
            get_endpoint, params={"getDefaultFromOtherRepo": "false"}
        )

        if not pipeline_response:
            logger.warning("Could not fetch pipeline details, trying to use list data: %s", pipeline_id)
            pipeline_response = pipeline

        logger.debug(
            "Pipeline GET response keys: %s",
            list(pipeline_response.keys()) if isinstance(pipeline_response, dict) else type(pipeline_response)
        )

        # Extract essential fields for pipeline creation
        if not isinstance(pipeline_response, dict):
            return None

        essential_fields = ["identifier", "name", "description", "tags", "pipeline_yaml", "yaml_pipeline"]
        pipeline_details = {
            field: pipeline_response[field]
            for field in essential_fields
            if field in pipeline_response
        }

        # Check if YAML field exists
        if "pipeline_yaml" not in pipeline_details and "yaml_pipeline" not in pipeline_details:
            logger.error(
                "Pipeline has no YAML content: %s. Available keys: %s",
                pipeline_id, list(pipeline_response.keys())
            )
            return None

        return pipeline_details

    def _handle_missing_templates(self, templates: List[tuple], pipeline_name: str) -> bool:
        """Handle missing templates - either migrate them or skip pipeline.
        
        Returns:
            True to continue with pipeline migration, False to skip
        """
        missing_templates = [
            (ref, ver) for ref, ver in templates
            if not self.check_template_exists(ref, ver)
        ]

        if not missing_templates:
            return True  # All templates exist

        # Log missing templates
        for template_ref, version_label in missing_templates:
            logger.warning(
                "  ⚠ Template '%s' (v%s) not found in dest",
                template_ref, version_label if version_label else "stable"
            )

        if self._is_dry_run():
            logger.info("  [DRY RUN] Would migrate %d template(s)", len(missing_templates))
            return True

        # Determine if we should auto-migrate
        should_migrate = self._get_option("auto_migrate_templates", False)

        # In interactive mode, ask user
        if self._is_interactive() and not should_migrate:
            should_migrate = self._ask_user_about_templates(missing_templates, pipeline_name)
            if should_migrate is None:  # User chose to skip pipeline
                return False

        # Migrate templates if needed
        if should_migrate:
            logger.info("  → Migrating %d missing template(s)...", len(missing_templates))
            for template_ref, version_label in missing_templates:
                success = self.migrate_template(template_ref, version_label)
                if not success:
                    logger.error("  ✗ Failed to migrate template, pipeline creation will likely fail")
        else:
            logger.warning("  ⚠ Continuing without migrating templates (pipeline creation will likely fail)")

        return True

    def _ask_user_about_templates(self, missing_templates: List[tuple], pipeline_name: str) -> Optional[bool]:
        """Ask user interactively what to do about missing templates.
        
        Returns:
            True to migrate templates, False to skip templates, None to skip pipeline
        """
        try:
            template_list = "\n".join([
                f"  • {ref} (version: {ver if ver else 'stable'})"
                for ref, ver in missing_templates
            ])

            text = (
                f"Pipeline '{pipeline_name}' requires templates that\n"
                f"don't exist in the destination:\n\n{template_list}\n\n"
                f"The script can automatically migrate these templates from "
                f"the source environment.\n\n"
                f"Do you want to migrate these templates?"
            )

            choice = button_dialog(
                title="Missing Templates",
                text=text,
                buttons=[
                    ("migrate", "Yes, Migrate Templates"),
                    ("skip_templates", "No, Continue Without Templates"),
                    ("skip", "Skip This Pipeline"),
                ],
            ).run()

            logger.debug("  Dialog returned: %s", choice)
            
            # Handle both button keys and display text for compatibility
            if choice in ["skip", "Skip This Pipeline"]:
                logger.info("  ⊘ Skipping pipeline due to missing templates")
                return None  # Skip pipeline
            elif choice in ["migrate", "Yes, Migrate Templates"]:
                logger.info("  → User chose to migrate templates")
                return True
            elif choice in ["skip_templates", "No, Continue Without Templates"]:
                logger.info("  → User chose to skip templates")
                return False
            else:
                logger.warning("  ⚠ Unexpected dialog result: %s, defaulting to skip templates", choice)
                return False

        except (EOFError, KeyboardInterrupt, OSError, ValueError) as e:
            logger.warning("  ⚠ Interactive dialog failed (%s), auto-migrating templates", type(e).__name__)
            return True

    def _create_or_update_pipeline(self, pipeline_id: str, pipeline_name: str, pipeline_details: Dict) -> Optional[bool]:
        """Create or update a pipeline in the destination.
        
        Returns:
            True if successful, False if skipped, None if failed
        """
        dest_endpoint = self._build_endpoint(
            "pipelines", org=self.dest_org, project=self.dest_project, resource_id=pipeline_id
        )
        existing = self.dest_client.get(dest_endpoint)

        if existing:
            if self._get_option("skip_existing", True):
                logger.info("Pipeline '%s' already exists. Skipping.", pipeline_id)
                return False  # Skipped
            else:
                logger.info("Pipeline '%s' exists. Updating...", pipeline_id)
                if self._is_dry_run():
                    logger.info("[DRY RUN] Would update pipeline '%s'", pipeline_name)
                    return True
                update_result = self.dest_client.put(dest_endpoint, json=pipeline_details)
                return True if update_result else None

        # Create new pipeline
        if self._is_dry_run():
            logger.info("[DRY RUN] Would create pipeline '%s'", pipeline_name)
            return True

        # Update org/project identifiers in YAML
        yaml_content = pipeline_details.get("pipeline_yaml", "")
        if yaml_content:
            yaml_content = self._update_yaml_identifiers(yaml_content, wrapper_key="pipeline")
            pipeline_details["pipeline_yaml"] = yaml_content

        # Build creation payload
        payload = {
            "identifier": pipeline_id,
            "name": pipeline_name,
            "pipeline_yaml": yaml_content,
        }

        # Add optional fields
        if pipeline_details.get("description"):
            payload["description"] = pipeline_details["description"]
        if pipeline_details.get("tags"):
            payload["tags"] = pipeline_details["tags"]

        logger.debug("Creating pipeline with payload keys: %s", list(payload.keys()))
        logger.debug("Final payload YAML (first 500 chars): %s", payload.get("pipeline_yaml", "")[:500])

        create_endpoint = self._build_endpoint("pipelines", org=self.dest_org, project=self.dest_project)
        result = self.dest_client.post(create_endpoint, json=payload)

        if not result:
            logger.error("Pipeline creation failed. Payload had keys: %s", list(pipeline_details.keys()))
            return None  # Failed

        return True  # Success

    def migrate_pipelines(self) -> bool:
        """Migrate pipelines from source to destination"""
        logger.info("=" * 80)
        logger.info("Starting pipeline migration...")

        if self._is_dry_run():
            logger.info("DRY RUN MODE: Simulating migration, no changes will be made")

        # Fetch pipelines to migrate
        pipelines = self._get_pipelines_to_migrate()

        if not pipelines:
            logger.info("No pipelines to migrate - skipping pipeline migration")
            return True

        # Process each pipeline
        for pipeline in pipelines:
            pipeline_id = pipeline.get("identifier")
            if not pipeline_id:
                logger.error("Pipeline missing identifier, skipping: %s", pipeline)
                self.migration_stats["pipelines"]["failed"] += 1
                continue
            
            pipeline_name = pipeline.get("name") or pipeline_id

            logger.info("\nMigrating pipeline: %s (%s)", pipeline_name, pipeline_id)

            # Get full pipeline details
            pipeline_details = self._get_pipeline_details(pipeline_id, pipeline)
            if not pipeline_details:
                logger.error("Invalid pipeline response format for: %s", pipeline_id)
                self.migration_stats["pipelines"]["failed"] += 1
                continue

            # Check and handle template dependencies
            yaml_content = pipeline_details.get("pipeline_yaml", pipeline_details.get("yaml_pipeline", ""))
            if yaml_content:
                templates = self.extract_template_refs(yaml_content)
                if templates:
                    logger.info("  Found %d template reference(s) in pipeline", len(templates))
                    
                    # Check which templates already exist
                    for template_ref, version_label in templates:
                        if self.check_template_exists(template_ref, version_label):
                            logger.info(
                                "  ✓ Template '%s' (v%s) exists in dest",
                                template_ref, version_label if version_label else "stable"
                            )
                            self.migration_stats["templates"]["skipped"] += 1
                    
                    # Handle missing templates
                    if not self._handle_missing_templates(templates, pipeline_name):
                        self.migration_stats["pipelines"]["failed"] += 1
                        continue

            # Create or update the pipeline
            result = self._create_or_update_pipeline(pipeline_id, pipeline_name, pipeline_details)
            
            if result is True:
                self.migration_stats["pipelines"]["success"] += 1

                # Migrate associated input sets
                if self._get_option("migrate_input_sets", True):
                    self.migrate_input_sets(pipeline_id)
            elif result is False:
                # Skipped - already exists
                self.migration_stats["pipelines"]["skipped"] += 1
            else:  # result is None - failed
                logger.error("✗ Failed to migrate pipeline: %s", pipeline_name)
                self.migration_stats["pipelines"]["failed"] += 1

            time.sleep(0.5)

        return True

    def run_migration(self):
        """Execute the full migration process"""
        logger.info("=" * 80)
        if self._is_dry_run():
            logger.info("HARNESS PIPELINE MIGRATION - DRY RUN MODE")
            logger.info("NO CHANGES WILL BE MADE")
        else:
            logger.info("HARNESS PIPELINE MIGRATION")
        logger.info("=" * 80)
        logger.info("Source: %s", self.config["source"]["base_url"])
        logger.info("  Org: %s, Project: %s", self.source_org, self.source_project)
        logger.info("Destination: %s", self.config["destination"]["base_url"])
        logger.info("  Org: %s, Project: %s", self.dest_org, self.dest_project)

        # Show selected pipelines if any
        selected_ids = self.config.get("selected_pipelines", [])
        if selected_ids:
            logger.info("  Selected Pipelines: %d", len(selected_ids))

        logger.info("=" * 80)

        # Step 1: Verify prerequisites
        if not self.verify_prerequisites():
            logger.error("Prerequisites verification failed. Aborting migration.")
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
        logger.info("\n%s", "=" * 80)
        logger.info("MIGRATION SUMMARY%s", " - DRY RUN" if self._is_dry_run() else "")
        if self._is_dry_run():
            logger.info("(No actual changes were made)")
        logger.info("=" * 80)

        for resource_type, stats in self.migration_stats.items():
            logger.info("\n%s:", resource_type.upper())
            for status, count in stats.items():
                logger.info("  %s: %s", status.capitalize(), count)

        logger.info("\n%s", "=" * 80)


def load_config(config_file: str) -> Dict:
    """Load configuration from JSON/JSONC file"""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove JSON comments (// style)
        # Remove single-line comments (// style) but preserve URLs with //
        lines = content.split("\n")
        cleaned_lines = []
        for line in lines:
            # Find // that's not part of a URL (not preceded by :)
            if "//" in line:
                # Check if it's a URL (contains ://)
                if "://" in line:
                    # It's a URL, don't remove the //
                    cleaned_lines.append(line)
                else:
                    # It's a comment, remove everything after //
                    comment_pos = line.find("//")
                    cleaned_line = line[:comment_pos].rstrip()
                    # Only add non-empty lines
                    if cleaned_line:
                        cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append(line)

        content = "\n".join(cleaned_lines)

        # Remove trailing commas before closing braces/brackets
        content = re.sub(r",(\s*[}\]])", r"\1", content)

        return json.loads(content)
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", config_file)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in configuration file: %s", e)
        sys.exit(1)


def save_config(config: Dict, config_file: str) -> bool:
    """Save configuration to JSON file"""
    try:
        # Create a clean config without API keys exposed
        clean_config = {
            "source": {
                "base_url": config["source"]["base_url"],
                "api_key": config["source"]["api_key"],
                "org": config["source"]["org"],
                "project": config["source"]["project"],
            },
            "destination": {
                "base_url": config["destination"]["base_url"],
                "api_key": config["destination"]["api_key"],
                "org": config["destination"]["org"],
                "project": config["destination"]["project"],
            },
            "options": config.get("options", {}),
            "selected_pipelines": (
                [
                    {"identifier": p.get("identifier"), "name": p.get("name")}
                    for p in config.get("pipelines", [])
                ]
                if config.get("pipelines")
                else []
            ),
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(clean_config, f, indent=2)

        return True
    except (IOError, OSError, json.JSONDecodeError) as e:
        logger.error("Failed to save configuration: %s", e)
        return False


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
        "source": ["base_url", "api_key", "org", "project"],
        "destination": ["base_url", "api_key", "org", "project"],
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
        "source": {
            "base_url": base_config["source"]["base_url"],
            "api_key": base_config["source"]["api_key"],
            "org": base_config["source"]["org"],
            "project": base_config["source"]["project"],
        },
        "destination": {
            "base_url": base_config["destination"]["base_url"],
            "api_key": base_config["destination"]["api_key"],
            "org": base_config["destination"]["org"],
            "project": base_config["destination"]["project"],
        },
        "options": base_config.get(
            "options", {"migrate_input_sets": True, "skip_existing": True}
        ),
        "pipelines": base_config.get("selected_pipelines", []),
        "dry_run": False,
        "non_interactive": True,
    }

    print(f"Source: {config['source']['org']}/{config['source']['project']}")
    print(f"Destination: {config['destination']['org']}/{config['destination']['project']}")
    print(f"Pipelines: {len(config['pipelines'])}")

    return config


def hybrid_mode(config_file: str):
    """Hybrid mode: use config file values and prompt for missing fields"""
    print("\n" + "=" * 80)
    print("HARNESS PIPELINE MIGRATION")
    print("=" * 80)
    print("Using config file values where available, prompting for missing fields")

    # Load base config
    base_config = load_config(config_file)

    # Initialize clients with config values
    source_url = base_config.get("source", {}).get("base_url")
    source_api_key = base_config.get("source", {}).get("api_key")
    dest_url = base_config.get("destination", {}).get("base_url")
    dest_api_key = base_config.get("destination", {}).get("api_key")

    # Prompt for missing credentials
    if not source_url:
        source_subdomain = radiolist_dialog(
            title="Source Account",
            text="Select source Harness subdomain:",
            values=[("app", "app.harness.io"), ("app3", "app3.harness.io")],
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
            values=[("app", "app.harness.io"), ("app3", "app3.harness.io")],
        ).run()
        if not dest_subdomain:
            print("❌ Selection cancelled")
            sys.exit(1)
        dest_url = f"https://{dest_subdomain}.harness.io"
    else:
        print(f"✓ Using destination URL from config: {dest_url}")

    if not dest_api_key:
        dest_api_key = prompt("Destination API Key: ", is_password=True).strip()
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
        source_client, dest_client, base_config, config_file
    )


def _get_selections_from_clients(source_client, dest_client, base_config, config_file):
    """Common logic for getting selections from clients"""
    # Initialize variables
    selected_pipelines = []

    # Select source organization
    print("\n" + "=" * 80)
    print("📂 SELECT SOURCE ORGANIZATION")
    print("=" * 80)

    # Check if already configured
    pre_selected_org = base_config.get("source", {}).get("org")
    if pre_selected_org:
        print(f"ℹ️  Previously selected: {pre_selected_org}")
        use_previous = yes_no_dialog(
            title="Use Previous Source Organization?",
            text=(
                f"Use previously selected SOURCE organization:\n"
                f"  {pre_selected_org}?"
            ),
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
    pre_selected_project = base_config.get("source", {}).get("project")
    if pre_selected_project:
        print(f"ℹ️  Previously selected: {pre_selected_project}")
        use_previous = yes_no_dialog(
            title="Use Previous Source Project?",
            text=(
                f"Use previously selected SOURCE project:\n"
                f"  {pre_selected_project}?"
            ),
        ).run()

        if use_previous:
            source_project = pre_selected_project
            print(f"✓ Using: {source_project}")
        else:
            source_project = select_project(source_client, source_org, "source")
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
    pre_selected_pipelines = base_config.get("selected_pipelines", [])
    if pre_selected_pipelines:
        print(f"ℹ️  Previously selected {len(pre_selected_pipelines)} pipeline(s):")
        for p in pre_selected_pipelines[:5]:  # Show first 5
            print(f"   - {p.get('name', p.get('identifier'))}")
        if len(pre_selected_pipelines) > 5:
            print(f"   ... and {len(pre_selected_pipelines) - 5} more")

        use_previous = yes_no_dialog(
            title="Use Previous Pipeline Selection?",
            text=(
                f"Use previously selected "
                f"{len(pre_selected_pipelines)} SOURCE pipeline(s)?"
            ),
        ).run()

        if use_previous:
            # Fetch full pipeline objects for the pre-selected identifiers
            endpoint = f"/v1/orgs/{source_org}/projects/{source_project}/pipelines"
            all_pipelines_response = source_client.get(endpoint)
            all_pipes = HarnessAPIClient.normalize_response(all_pipelines_response)

            if all_pipes:
                # Get identifiers from pre-selected
                pre_ids = [p.get("identifier") for p in pre_selected_pipelines]
                # Match with full objects
                selected_pipelines = [
                    p for p in all_pipes if p.get("identifier") in pre_ids
                ]
                print(
                    f"✓ Using {len(selected_pipelines)} previously selected pipeline(s)"
                )
            else:
                print("⚠️  Could not fetch pipelines, re-selecting...")
                selected_pipelines = select_pipelines(
                    source_client, source_org, source_project
                )
        else:
            selected_pipelines = select_pipelines(
                source_client, source_org, source_project
            )
    else:
        print("Use Space to select/deselect, Enter to confirm, Esc to cancel")
        selected_pipelines = select_pipelines(source_client, source_org, source_project)

    if selected_pipelines is None:
        print("❌ Migration cancelled")
        sys.exit(1)
    elif selected_pipelines == "ERROR":
        print("⚠️  Error occurred")
        sys.exit(1)
    elif not selected_pipelines or selected_pipelines == "BACK_TO_PROJECTS":
        print("⚠️  No pipelines selected - continuing with empty selection")
        selected_pipelines = []

    # Select/create destination organization
    print("\n" + "=" * 80)
    print("📂 SELECT DESTINATION ORGANIZATION")
    print("=" * 80)

    # Track if org was just created
    org_just_created = False

    # Check if already configured
    pre_selected_dest_org = base_config.get("destination", {}).get("org")
    if pre_selected_dest_org:
        print(f"ℹ️  Previously selected: {pre_selected_dest_org}")
        use_previous = yes_no_dialog(
            title="Use Previous Destination Organization?",
            text=(
                f"Use previously selected DESTINATION organization:\n"
                f"  {pre_selected_dest_org}?"
            ),
        ).run()

        if use_previous:
            dest_org = pre_selected_dest_org
            print(f"✓ Using: {dest_org}")
        else:
            result = select_or_create_organization(
                dest_client, source_org, "destination"
            )
            if not result:
                print("❌ Selection cancelled")
                sys.exit(1)
            dest_org, org_just_created = result
    else:
        result = select_or_create_organization(dest_client, source_org, "destination")
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
            f"it has no projects yet"
        )
        dest_project = select_or_create_project(
            dest_client, dest_org, source_project, "destination", force_create=True
        )
        if not dest_project:
            print("❌ Selection cancelled")
            sys.exit(1)
    else:
        # Check if already configured
        pre_selected_dest_project = base_config.get("destination", {}).get("project")
        if pre_selected_dest_project:
            print(f"ℹ️  Previously selected: {pre_selected_dest_project}")
            use_previous = yes_no_dialog(
                title="Use Previous Destination Project?",
                text=(
                    f"Use previously selected DESTINATION project:\n"
                    f"  {pre_selected_dest_project}?"
                ),
            ).run()

            if use_previous:
                dest_project = pre_selected_dest_project
                print(f"✓ Using: {dest_project}")
            else:
                dest_project = select_or_create_project(
                    dest_client, dest_org, source_project, "destination"
                )
                if not dest_project:
                    print("❌ Selection cancelled")
                    sys.exit(1)
        else:
            dest_project = select_or_create_project(
                dest_client, dest_org, source_project, "destination"
            )
            if not dest_project:
                print("❌ Selection cancelled")
                sys.exit(1)

    # Migration options
    print("\n" + "=" * 80)
    print("⚙️  MIGRATION OPTIONS")
    print("=" * 80)

    # Use config options or prompt for them
    migrate_input_sets = base_config.get("options", {}).get("migrate_input_sets", True)
    skip_existing = base_config.get("options", {}).get("skip_existing", True)

    # Ask about dry run
    dry_run = yes_no_dialog(
        title="Dry Run",
        text="Do you want to run in dry-run mode? (No changes will be made)",
    ).run()

    # Build final config
    config = {
        "source": {
            "base_url": source_client.base_url,
            "api_key": source_client.api_key,
            "org": source_org,
            "project": source_project,
        },
        "destination": {
            "base_url": dest_client.base_url,
            "api_key": dest_client.api_key,
            "org": dest_org,
            "project": dest_project,
        },
        "options": {
            "migrate_input_sets": migrate_input_sets,
            "skip_existing": skip_existing,
        },
        "pipelines": selected_pipelines if selected_pipelines else [],
        "dry_run": dry_run,
    }

    # Ask if user wants to save the configuration
    print("\n" + "=" * 80)
    save_choice = yes_no_dialog(
        title="Save Configuration",
        text=(
            "Do you want to save these selections to the config file?\n\n"
            "This will allow you to quickly re-run with the same settings\n"
            "next time (useful for troubleshooting)."
        ),
    ).run()

    if save_choice:
        if save_config(config, config_file):
            print(f"✓ Configuration saved to {config_file}")
        else:
            print(f"✗ Failed to save configuration to {config_file}")

    return config


def select_organization(
    client: HarnessAPIClient, context: str
) -> Optional[str]:  # noqa: E501
    """Interactive organization selection with arrow keys"""
    response = client.get("/v1/orgs")
    orgs = HarnessAPIClient.normalize_response(response)

    if not orgs:
        message_dialog(
            title="No Organizations",
            text=f"No organizations found in {context} account",
        ).run()
        return None

    # Build values for radiolist (without Back option)
    values = []
    for org in orgs:
        org_data = org.get("org", {})
        identifier = org_data.get("identifier", "unknown")
        name = org_data.get("name", identifier)
        values.append((identifier, f"{name} ({identifier})"))

    # Show organization selection dialog
    # Note: Esc key cancels and returns None
    selected = radiolist_dialog(
        title=f"Select {context.capitalize()} Organization",
        text=(
            f"Use ↑↓ to navigate, Enter to select, Esc to cancel\n\n"
            f"Found {len(orgs)} organization(s):"
        ),
        values=values,
    ).run()

    if selected:
        # Find the selected org name for display
        selected_name = next((v[1] for v in values if v[0] == selected), selected)
        print(f"✓ Selected: {selected_name}")

    return selected


def select_project(
    client: HarnessAPIClient, org: str, context: str
) -> Optional[str]:  # noqa: E501
    """Interactive project selection with arrow keys"""
    endpoint = f"/v1/orgs/{org}/projects"
    response = client.get(endpoint)
    projects = HarnessAPIClient.normalize_response(response)

    if not projects:
        message_dialog(
            title="No Projects", text=f"No projects found in organization '{org}'"
        ).run()
        return None

    # Build values for radiolist with pipeline counts (without Back option)
    values = []
    for project in projects:
        proj_data = project.get("project", {})
        identifier = proj_data.get("identifier", "unknown")
        name = proj_data.get("name", identifier)

        # Get pipeline count for this project
        pipeline_endpoint = f"/v1/orgs/{org}/projects/{identifier}/pipelines"
        pipeline_response = client.get(pipeline_endpoint)

        if pipeline_response is not None and isinstance(
            pipeline_response, list
        ):  # noqa: E501
            pipeline_count = len(pipeline_response)
        else:
            pipeline_count = 0

        values.append(
            (identifier, f"{name} ({identifier}) - {pipeline_count} pipelines")
        )  # noqa: E501

    selected = radiolist_dialog(
        title=f"Select {context.capitalize()} Project",
        text=(
            f"Use arrow keys to navigate, Enter to select\n\n"
            f"Found {len(projects)} project(s) in '{org}':"
        ),
        values=values,
    ).run()

    if selected:
        selected_name = next((v[1] for v in values if v[0] == selected), selected)
        print(f"✓ Selected: {selected_name}")

    return selected


def select_pipelines(
    client: HarnessAPIClient, org: str, project: str
) -> Union[List[Dict], str, None]:
    """Interactive pipeline selection with arrow keys and space to multi-select"""  # noqa: E501
    endpoint = f"/v1/orgs/{org}/projects/{project}/pipelines"
    response = client.get(endpoint)
    pipelines = HarnessAPIClient.normalize_response(response)

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
                ("back", "← Go Back to Project Selection"),
                ("continue", "Continue with No Pipelines"),
                ("cancel", "Cancel Migration"),
            ],
        ).run()

        if choice == "back":
            return "BACK_TO_PROJECTS"  # Special return value to indicate going back  # noqa: E501
        elif choice == "continue":
            return []  # Empty list to continue with no pipelines
        else:
            return None  # Cancel

    # Build values for checkboxlist (without Back option)
    values = []
    for pipeline in pipelines:
        identifier = pipeline.get("identifier", "unknown")
        name = pipeline.get("name", identifier)
        values.append((identifier, f"{name} ({identifier})"))

    selected_ids = checkboxlist_dialog(
        title="Select Pipelines to Migrate",
        text=(
            f"Use arrow keys to navigate, Space to select/deselect, "
            f"Enter to confirm\n\nFound {len(pipelines)} pipeline(s):"
        ),  # noqa: E501
        values=values,
    ).run()

    if not selected_ids:
        return []

    # Get full pipeline objects for selected IDs
    selected = [p for p in pipelines if p.get("identifier") in selected_ids]

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
    existing_orgs = HarnessAPIClient.normalize_response(response)

    # Check if source org exists
    source_org_exists = any(
        org.get("org", {}).get("identifier") == source_org for org in existing_orgs
    )

    # Build combined options list:
    # 1. Create with same name as source (if doesn't exist)
    # 2. Create custom name
    # 3. Existing organizations
    values = []

    # Option 1: Create matching org (only if source org doesn't exist)
    if not source_org_exists:
        values.append(("CREATE_MATCHING", f"➕ Create '{source_org}' (same as source)"))

    # Option 2: Create custom org
    values.append(("CREATE_CUSTOM", "➕ Create new organization with custom name"))

    # Option 3: Existing organizations
    for org in existing_orgs:
        org_data = org.get("org", {})
        identifier = org_data.get("identifier", "unknown")
        name = org_data.get("name", identifier)
        values.append((identifier, f"{name} ({identifier})"))

    choice = radiolist_dialog(
        title=f"Select {context.capitalize()} Organization",
        text=(
            "Use ↑↓ to navigate, Enter to select, Esc to cancel\n\n" "Select an option:"
        ),
        values=values,
    ).run()

    if not choice:
        return None

    # Handle create matching org
    if choice == "CREATE_MATCHING":
        print(f"\nCreating organization '{source_org}'...")
        result = client.post(
            "/v1/orgs", json={"org": {"identifier": source_org, "name": source_org}}
        )
        if result:
            print(f"✓ Organization '{source_org}' created successfully")
            return (source_org, True)  # Return tuple: (org_id, was_created)
        else:
            message_dialog(
                title="Error", text=f"Failed to create organization '{source_org}'"
            ).run()
            return None

    # Handle create custom
    elif choice == "CREATE_CUSTOM":
        print()
        org_id = prompt("Enter organization identifier: ").strip()
        org_name = (
            prompt(
                "Enter organization name (or press Enter for same as identifier): "
            ).strip()
            or org_id
        )

        if not org_id:
            message_dialog(
                title="Error", text="Organization identifier is required"
            ).run()
            return None

        print(f"\nCreating organization '{org_name}'...")
        result = client.post(
            "/v1/orgs", json={"org": {"identifier": org_id, "name": org_name}}
        )
        if result:
            print(f"✓ Organization '{org_name}' created successfully")
            return (org_id, True)  # Return tuple: (org_id, was_created)
        else:
            message_dialog(
                title="Error", text=f"Failed to create organization '{org_name}'"
            ).run()
            return None

    # Otherwise, it's an existing organization identifier
    return (choice, False)  # Return tuple: (org_id, was_created)


def select_or_create_project(
    client: HarnessAPIClient,
    org: str,
    source_project: str,
    context: str,
    force_create: bool = False,
) -> Optional[str]:
    """Interactive project selection or creation with arrow keys

    Args:
        force_create: If True, skip to creation dialog (for new orgs)
    """
    endpoint = f"/v1/orgs/{org}/projects"
    response = client.get(endpoint)
    existing_projects = HarnessAPIClient.normalize_response(response)

    # If force_create is True, only show creation options
    if force_create:
        values = []
        # Only show create matching and create custom options
        values.append(
            ("CREATE_MATCHING", f"➕ Create '{source_project}' (same as source)")
        )
        values.append(("CREATE_CUSTOM", "➕ Create new project with custom name"))

        choice = radiolist_dialog(
            title=f"Create {context.capitalize()} Project",
            text=(
                "Use ↑↓ to navigate, Enter to select, Esc to cancel\n\n"
                "Organization was just created - "
                "select how to create project:"
            ),
            values=values,
        ).run()
    else:
        # Check if source project exists
        source_project_exists = any(
            proj.get("project", {}).get("identifier") == source_project
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
                ("CREATE_MATCHING", f"➕ Create '{source_project}' (same as source)")
            )

        # Option 2: Create custom project
        values.append(("CREATE_CUSTOM", "➕ Create new project with custom name"))

        # Option 3: Existing projects
        for project in existing_projects:
            proj_data = project.get("project", {})
            identifier = proj_data.get("identifier", "unknown")
            name = proj_data.get("name", identifier)
            values.append((identifier, f"{name} ({identifier})"))

        choice = radiolist_dialog(
            title=f"Select {context.capitalize()} Project",
            text=(
                "Use ↑↓ to navigate, Enter to select, Esc to cancel\n\n"
                "Select an option:"
            ),
            values=values,
        ).run()

    if not choice:
        return None

    # Handle create matching project
    if choice == "CREATE_MATCHING":
        print(f"\nCreating project '{source_project}'...")
        result = client.post(
            f"/v1/orgs/{org}/projects",
            json={
                "project": {
                    "identifier": source_project,
                    "name": source_project,
                    "org": org,
                }
            },
        )
        if result:
            print(f"✓ Project '{source_project}' created successfully")
            return source_project
        else:
            message_dialog(
                title="Error", text=f"Failed to create project '{source_project}'"
            ).run()
            return None

    # Handle create custom
    elif choice == "CREATE_CUSTOM":
        print()
        proj_id = prompt("Enter project identifier: ").strip()
        proj_name = (
            prompt(
                "Enter project name (or press Enter for same as identifier): "
            ).strip()
            or proj_id
        )

        if not proj_id:
            message_dialog(title="Error", text="Project identifier is required").run()
            return None

        print(f"\nCreating project '{proj_name}'...")
        result = client.post(
            f"/v1/orgs/{org}/projects",
            json={"project": {"identifier": proj_id, "name": proj_name, "org": org}},
        )
        if result:
            print(f"✓ Project '{proj_name}' created successfully")
            return proj_id
        else:
            message_dialog(
                title="Error", text=f"Failed to create project '{proj_name}'"
            ).run()
            return None

    # Otherwise, it's an existing project identifier
    return choice


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Migrate Harness pipelines between accounts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
    # Interactive mode (with dialogs for selection)
    python harness_pipeline_migration.py

    # Non-interactive mode (use all values from config file)
    python harness_pipeline_migration.py --non-interactive

    # Dry run to test without making changes
    python harness_pipeline_migration.py --dry-run

    # Debug mode for troubleshooting
    python harness_pipeline_migration.py --debug

    # Override specific values via CLI
    python harness_pipeline_migration.py --source-org my_org --dest-org target_org

    # Override migration options
    python harness_pipeline_migration.py --no-migrate-input-sets --no-skip-existing

    # Full CLI configuration (minimal config file needed)
    python harness_pipeline_migration.py \\
        --source-url https://app.harness.io \\
        --source-api-key sat.xxxxx.xxxxx.xxxxx \\
        --source-org source_org \\
        --source-project source_project \\
        --dest-url https://app3.harness.io \\
        --dest-api-key sat.yyyyy.yyyyy.yyyyy \\
        --dest-org dest_org \\
        --dest-project dest_project

Configuration File Format (supports JSONC with comments):
{
  "source": {
    "base_url": "https://app.harness.io",
    "api_key": "your-source-api-key",
    // "org": "source_org",  // Leave commented to select interactively
    // "project": "source_project"  // Leave commented to select interactively
  },
  "destination": {
    "base_url": "https://app3.harness.io",
    "api_key": "your-dest-api-key",
    // "org": "dest_org",  // Leave commented to select interactively
    // "project": "dest_project"  // Leave commented to select interactively
  },
  "options": {
    "migrate_input_sets": true,
    "skip_existing": true
  }
}
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration JSON/JSONC file (default: config.json)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )

    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging for troubleshooting"
    )

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip prompts and use all values from config file (no dialogs)",
    )

    # Source configuration arguments
    parser.add_argument(
        "--source-url",
        type=str,
        help="Source Harness base URL (e.g., https://app.harness.io)",
    )
    parser.add_argument(
        "--source-api-key",
        type=str,
        help="Source Harness API key (starts with 'sat.')",
    )
    parser.add_argument(
        "--source-org",
        type=str,
        help="Source organization identifier",
    )
    parser.add_argument(
        "--source-project",
        type=str,
        help="Source project identifier",
    )

    # Destination configuration arguments
    parser.add_argument(
        "--dest-url",
        type=str,
        help="Destination Harness base URL (e.g., https://app3.harness.io)",
    )
    parser.add_argument(
        "--dest-api-key",
        type=str,
        help="Destination Harness API key (starts with 'sat.')",
    )
    parser.add_argument(
        "--dest-org",
        type=str,
        help="Destination organization identifier",
    )
    parser.add_argument(
        "--dest-project",
        type=str,
        help="Destination project identifier",
    )

    # Migration options
    parser.add_argument(
        "--migrate-input-sets",
        action="store_true",
        help="Migrate input sets with pipelines (default: true)",
    )
    parser.add_argument(
        "--no-migrate-input-sets",
        action="store_true",
        help="Skip migrating input sets",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip pipelines that already exist in destination (default: true)",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Update/overwrite existing pipelines",
    )

    args = parser.parse_args()

    # Setup logging with debug level if requested
    setup_logging(debug=args.debug)

    # Choose mode based on flag
    if args.non_interactive:
        config = non_interactive_mode(args.config)
    else:
        # Use hybrid mode with interactive prompts
        config = hybrid_mode(args.config)

    # Apply CLI argument overrides (priority: config file > CLI args > interactive)
    config = apply_cli_overrides(config, args)

    # Run migration
    migrator = HarnessMigrator(config)
    success = migrator.run_migration()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
