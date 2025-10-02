"""
Migration Logic

Core migration functionality for pipelines, input sets, and templates.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .api_client import HarnessAPIClient

logger = logging.getLogger(__name__)


class HarnessMigrator:
    """Main migration orchestrator"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize migrator with configuration"""
        self.config = config
        self.source_org = config["source"]["org"]
        self.source_project = config["source"]["project"]
        self.dest_org = config["destination"]["org"]
        self.dest_project = config["destination"]["project"]

        # Initialize API clients
        self.source_client = HarnessAPIClient(
            config["source"]["base_url"], config["source"]["api_key"]
        )
        self.dest_client = HarnessAPIClient(
            config["destination"]["base_url"], config["destination"]["api_key"]
        )

        # Migration statistics
        self.migration_stats = {
            "pipelines": {"success": 0, "failed": 0, "skipped": 0},
            "input_sets": {"success": 0, "failed": 0, "skipped": 0},
            "templates": {"success": 0, "failed": 0, "skipped": 0},
        }

    def _get_option(self, key: str, default: Any = None) -> Any:
        """Get configuration option with default value"""
        return self.config.get("options", {}).get(key, default)

    def _is_dry_run(self) -> bool:
        """Check if running in dry-run mode"""
        return self.config.get("dry_run", False)

    def _is_interactive(self) -> bool:
        """Check if running in interactive mode"""
        return not self.config.get("non_interactive", False)

    def _build_endpoint(self, resource: Optional[str] = None, org: Optional[str] = None,
                        project: Optional[str] = None, resource_id: Optional[str] = None,
                        sub_resource: Optional[str] = None) -> str:
        """Build consistent API endpoint paths"""
        parts = ["/v1"]

        if org:
            parts.extend(["orgs", org])
        if project:
            parts.extend(["projects", project])
        if resource:
            parts.append(resource)
        if resource_id:
            parts.append(resource_id)
        if sub_resource:
            parts.append(sub_resource)

        return "/".join(parts)

    def _update_yaml_identifiers(self, yaml_content: str, wrapper_key: Optional[str] = None) -> str:
        """Update org and project identifiers in YAML content"""
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
            yaml_content = re.sub(
                r'orgIdentifier:\s*["\']?[^"\'\s]+["\']?',
                f'orgIdentifier: "{self.dest_org}"',
                yaml_content
            )
            yaml_content = re.sub(
                r'projectIdentifier:\s*["\']?[^"\'\s]+["\']?',
                f'projectIdentifier: "{self.dest_project}"',
                yaml_content
            )
            return yaml_content

    def extract_template_refs(self, yaml_content: str) -> List[Tuple[str, Optional[str]]]:
        """Extract template references from pipeline YAML"""
        try:
            data = yaml.safe_load(yaml_content)
            templates = []

            def find_templates(obj, path=""):
                if isinstance(obj, dict):
                    if "templateRef" in obj:
                        template_ref = obj["templateRef"]
                        version_label = obj.get("versionLabel")
                        templates.append((template_ref, version_label))
                    for key, value in obj.items():
                        find_templates(value, f"{path}.{key}" if path else key)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        find_templates(item, f"{path}[{i}]")

            find_templates(data)
            return templates
        except yaml.YAMLError as e:
            logger.error("Failed to parse YAML for template extraction: %s", e)
            return []

    def check_template_exists(self, template_ref: str, version_label: Optional[str] = None) -> bool:
        """Check if template exists in destination"""
        org = self.dest_org
        project = self.dest_project

        # Build sub_resource for version if specified
        sub_resource = f"versions/{version_label}" if version_label else None
        endpoint = self._build_endpoint(
            "templates", org=org, project=project,
            resource_id=template_ref, sub_resource=sub_resource
        )

        response = self.dest_client.get(endpoint)
        return response is not None

    def migrate_template(self, template_ref: str, version_label: Optional[str] = None) -> bool:
        """Migrate a template from source to destination"""
        logger.info("  Migrating template: %s (v%s)", template_ref, version_label or "stable")

        # Get template from source
        source_org = self.source_org
        source_project = self.source_project

        sub_resource = f"versions/{version_label}" if version_label else None
        source_endpoint = self._build_endpoint(
            "templates", org=source_org, project=source_project,
            resource_id=template_ref, sub_resource=sub_resource
        )

        template_data = self.source_client.get(source_endpoint)
        if not template_data:
            logger.error("  Failed to get template from source: %s", template_ref)
            self.migration_stats["templates"]["failed"] += 1
            return False

        # Extract template YAML
        template_yaml = template_data.get("template", {}).get("yaml", "")
        if not template_yaml:
            logger.error("  Template missing YAML content: %s", template_ref)
            self.migration_stats["templates"]["failed"] += 1
            return False

        # Update YAML to use destination org/project and set version
        updated_yaml = self._update_yaml_identifiers(template_yaml, wrapper_key="template")

        # Ensure version is set in the YAML
        try:
            template_dict = yaml.safe_load(updated_yaml)
            if "template" in template_dict:
                template_dict["template"]["versionLabel"] = version_label or "stable"
            updated_yaml = yaml.dump(template_dict, default_flow_style=False, sort_keys=False)
        except yaml.YAMLError:
            pass  # Continue with original YAML if version setting fails

        # Create template in destination
        dest_endpoint = self._build_endpoint(
            "templates", org=self.dest_org, project=self.dest_project)

        if self._is_dry_run():
            logger.info("  [DRY RUN] Would create template '%s'", template_ref)
            result = True
        else:
            template_payload = {
                "template_yaml": updated_yaml,
                "template_identifier": template_ref,
                "version_label": version_label or "stable"
            }
            result = self.dest_client.post(dest_endpoint, json=template_payload)

        if result:
            logger.info("  ✓ Template '%s' migrated successfully", template_ref)
            self.migration_stats["templates"]["success"] += 1
        else:
            logger.error("  ✗ Failed to migrate template: %s", template_ref)
            self.migration_stats["templates"]["failed"] += 1

        time.sleep(0.3)
        return result

    def run_migration(self) -> bool:
        """Run the complete migration process"""
        logger.info("Starting Harness Pipeline Migration")
        logger.info("Source: %s/%s", self.source_org, self.source_project)
        logger.info("Destination: %s/%s", self.dest_org, self.dest_project)

        # Verify prerequisites
        if not self.verify_prerequisites():
            return False

        # Migrate pipelines
        if not self.migrate_pipelines():
            return False

        # Print summary
        self.print_summary()
        return True

    def verify_prerequisites(self) -> bool:
        """Verify that destination org and project exist"""
        logger.info("Verifying destination org and project...")

        if not self._create_org_if_missing():
            return False

        if not self._create_project_if_missing():
            return False

        return True

    def _create_org_if_missing(self) -> bool:
        """Create organization if it doesn't exist"""
        # Check if org exists
        orgs_endpoint = self._build_endpoint("orgs")
        orgs = self.dest_client.get(orgs_endpoint)
        orgs_list = HarnessAPIClient.normalize_response(orgs)

        for org in orgs_list:
            if org.get("identifier") == self.dest_org:
                logger.info("Organization '%s' already exists", self.dest_org)
                return True

        # Create organization
        logger.info("Creating organization: %s", self.dest_org)
        create_org_data = {
            "org": {
                "identifier": self.dest_org,
                "name": self.dest_org.replace("_", " ").title(),
                "description": "Organization created by migration tool"
            }
        }

        create_org = self.dest_client.post(orgs_endpoint, json=create_org_data)
        if not create_org:
            logger.error("Failed to create organization")
            return False

        logger.info("Organization '%s' created successfully", self.dest_org)
        return True

    def _create_project_if_missing(self) -> bool:
        """Create project if it doesn't exist"""
        # Check if project exists
        projects_endpoint = self._build_endpoint("projects", org=self.dest_org)
        projects = self.dest_client.get(projects_endpoint)
        projects_list = HarnessAPIClient.normalize_response(projects)

        for project in projects_list:
            if project.get("identifier") == self.dest_project:
                logger.info("Project '%s' already exists", self.dest_project)
                return True

        # Create project
        logger.info("Creating project: %s", self.dest_project)
        create_project_data = {
            "project": {
                "orgIdentifier": self.dest_org,
                "identifier": self.dest_project,
                "name": self.dest_project.replace("_", " ").title(),
                "description": "Project created by migration tool"
            }
        }

        create_project = self.dest_client.post(projects_endpoint, json=create_project_data)
        if not create_project:
            logger.error("Failed to create project")
            return False

        logger.info("Project '%s' created successfully", self.dest_project)
        return True

    def migrate_input_sets(self, pipeline_id: str) -> bool:
        """Migrate input sets for a specific pipeline"""
        logger.info("  Checking for input sets for pipeline: %s", pipeline_id)

        # List input sets
        endpoint = self._build_endpoint(
            "input-sets", org=self.source_org, project=self.source_project)
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
                "input-sets", org=self.source_org, project=self.source_project,
                resource_id=input_set_id)
            input_set_details = self.source_client.get(
                get_endpoint, params={"pipeline": pipeline_id})

            if not input_set_details:
                logger.error("  Failed to get details for input set: %s", input_set_id)
                self.migration_stats["input_sets"]["failed"] += 1
                continue

            # Update org/project identifiers in input set YAML
            if "input_set_yaml" in input_set_details:
                yaml_content = input_set_details["input_set_yaml"]
                updated_yaml = self._update_yaml_identifiers(
                    yaml_content, wrapper_key="inputSet")
                input_set_details["input_set_yaml"] = updated_yaml

            # Create input set in destination
            create_endpoint = self._build_endpoint(
                "input-sets", org=self.dest_org, project=self.dest_project)

            if self._is_dry_run():
                logger.info("  [DRY RUN] Would create input set '%s'", input_set_name)
                result = True
            else:
                result = self.dest_client.post(
                    create_endpoint, params={"pipeline": pipeline_id},
                    json=input_set_details)

            if result:
                logger.info("  ✓ Input set '%s' migrated successfully", input_set_name)
                self.migration_stats["input_sets"]["success"] += 1
            else:
                logger.error("  ✗ Failed to migrate input set: %s", input_set_name)
                self.migration_stats["input_sets"]["failed"] += 1

            time.sleep(0.3)

        return True

    def migrate_pipelines(self) -> bool:
        """Migrate all selected pipelines"""
        pipelines = self.config.get("pipelines", [])
        if not pipelines:
            logger.warning("No pipelines selected for migration")
            return True

        logger.info("Migrating %d pipelines...", len(pipelines))

        for pipeline in pipelines:
            pipeline_id = pipeline.get("identifier")
            if not pipeline_id:
                logger.error("Pipeline missing identifier, skipping: %s", pipeline)
                self.migration_stats["pipelines"]["failed"] += 1
                continue

            pipeline_name = pipeline.get("name") or pipeline_id

            logger.info("\nMigrating pipeline: %s (%s)", pipeline_name, pipeline_id)

            # Get pipeline details from source
            pipeline_endpoint = self._build_endpoint(
                "pipelines", org=self.source_org, project=self.source_project,
                resource_id=pipeline_id)
            pipeline_details = self.source_client.get(pipeline_endpoint)

            if not pipeline_details:
                logger.error("Failed to get pipeline details: %s", pipeline_id)
                self.migration_stats["pipelines"]["failed"] += 1
                continue

            # Extract and handle template dependencies
            yaml_content = pipeline_details.get("pipeline_yaml", "")
            if yaml_content:
                templates = self.extract_template_refs(yaml_content)
                if templates:
                    logger.info("  Found %d template reference(s) in pipeline", len(templates))

                    # Check which templates already exist
                    for template_ref, version_label in templates:
                        if self.check_template_exists(template_ref, version_label):
                            logger.info(
                                "  Template '%s' (v%s) already exists in destination",
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
            else:
                # Failed
                self.migration_stats["pipelines"]["failed"] += 1

        return True

    def _handle_missing_templates(self, templates: List[Tuple[str, Optional[str]]],
                                  pipeline_name: str) -> bool:
        """Handle missing templates - either migrate them or skip pipeline"""
        missing_templates = []
        for template_ref, version_label in templates:
            if not self.check_template_exists(template_ref, version_label):
                missing_templates.append((template_ref, version_label))

        if not missing_templates:
            return True

        logger.warning("  Pipeline '%s' references %d missing template(s):",
                       pipeline_name, len(missing_templates))
        for template_ref, version_label in missing_templates:
            logger.warning("    - %s (v%s)", template_ref, version_label or "stable")

        if not self._is_interactive():
            logger.info("  Auto-migrating missing templates...")
            for template_ref, version_label in missing_templates:
                self.migrate_template(template_ref, version_label)
            return True

        # Ask user what to do
        choice = self._ask_user_about_templates(missing_templates, pipeline_name)
        if choice is None:  # Skip pipeline
            return False
        elif choice:  # Migrate templates
            for template_ref, version_label in missing_templates:
                self.migrate_template(template_ref, version_label)
            return True
        else:  # Skip templates
            logger.warning(
                "  Continuing without migrating templates (pipeline creation will likely fail)")
            return True

    def _ask_user_about_templates(self, missing_templates: List[Tuple[str, Optional[str]]],
                                  pipeline_name: str) -> Optional[bool]:
        """Ask user interactively what to do about missing templates"""
        from prompt_toolkit.shortcuts import button_dialog

        template_list = "\n".join(
            f"    - {ref} (v{version or 'stable'})" for ref, version in missing_templates)
        text = (
            f"Pipeline '{pipeline_name}' references {len(missing_templates)} template(s) "
            f"that don't exist in the destination:\n\n{template_list}\n\n"
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
            logger.warning(
                "  ⚠ Unexpected dialog result: %s, defaulting to skip templates", choice)
            return False

    def _create_or_update_pipeline(self, pipeline_id: str, pipeline_name: str,
                                   pipeline_details: Dict) -> Optional[bool]:
        """Create or update a pipeline in the destination"""
        # Check if pipeline already exists
        existing_endpoint = self._build_endpoint(
            "pipelines", org=self.dest_org, project=self.dest_project,
            resource_id=pipeline_id)
        existing_pipeline = self.dest_client.get(existing_endpoint)

        if existing_pipeline:
            if self._get_option("skip_existing", True):
                logger.info("  Pipeline '%s' already exists, skipping", pipeline_name)
                return False  # Skipped
            else:
                logger.info("  Pipeline '%s' already exists, updating", pipeline_name)

        # Update YAML identifiers
        yaml_content = pipeline_details.get("pipeline_yaml", "")
        if yaml_content:
            yaml_content = self._update_yaml_identifiers(yaml_content, wrapper_key="pipeline")
            pipeline_details["pipeline_yaml"] = yaml_content

        # Create or update pipeline
        endpoint = self._build_endpoint("pipelines", org=self.dest_org, project=self.dest_project)

        if self._is_dry_run():
            logger.info("  [DRY RUN] Would create/update pipeline '%s'", pipeline_name)
            return True

        if existing_pipeline:
            result = self.dest_client.put(endpoint, json=pipeline_details)
        else:
            result = self.dest_client.post(endpoint, json=pipeline_details)

        if result:
            logger.info("  ✓ Pipeline '%s' migrated successfully", pipeline_name)
            return True
        else:
            logger.error("  ✗ Failed to migrate pipeline: %s", pipeline_name)
            return None  # Failed

    def print_summary(self):
        """Print migration summary"""
        logger.info("\n%s", "=" * 50)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 50)

        for resource_type, stats in self.migration_stats.items():
            logger.info("\n%s:", resource_type.upper())
            logger.info("  Success: %s", stats['success'])
            logger.info("  Failed: %s", stats['failed'])
            logger.info("  Skipped: %s", stats['skipped'])

        logger.info("\n%s", "=" * 50)
