"""
Template Handler

Handles template replication functionality.
"""

import logging
import time
from typing import List, Optional, Tuple

from .base_replicator import BaseReplicator
from .yaml_utils import YAMLUtils

logger = logging.getLogger(__name__)


class TemplateHandler(BaseReplicator):
    """Handles template replication"""

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

    def replicate_template(self, template_ref: str, version_label: Optional[str] = None) -> bool:
        """Replicate a template from source to destination"""
        logger.info("  Replicating template: %s (v%s)", template_ref, version_label or "stable")

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
            self.replication_stats["templates"]["failed"] += 1
            return False

        # Extract template YAML
        if isinstance(template_data, dict):
            template_yaml = template_data.get("template", {}).get("yaml", "")
        else:
            template_yaml = ""
        if not template_yaml:
            logger.error("  Template missing YAML content: %s", template_ref)
            self.replication_stats["templates"]["failed"] += 1
            return False

        # Update YAML to use destination org/project and set version
        updated_yaml = YAMLUtils.update_identifiers(
            template_yaml, self.dest_org, self.dest_project, wrapper_key="template")
        updated_yaml = YAMLUtils.set_template_version(updated_yaml, version_label)

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
            logger.info("  ✓ Template '%s' replicated successfully", template_ref)
            self.replication_stats["templates"]["success"] += 1
        else:
            logger.error("  ✗ Failed to replicate template: %s", template_ref)
            self.replication_stats["templates"]["failed"] += 1

        time.sleep(0.3)
        return bool(result)

    def handle_missing_templates(self, templates: List[Tuple[str, Optional[str]]],
                                 pipeline_name: str) -> bool:
        """Handle missing templates - either replicate them or skip pipeline"""
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
            logger.info("  Auto-replicating missing templates...")
            for template_ref, version_label in missing_templates:
                self.replicate_template(template_ref, version_label)
            return True

        # Ask user what to do
        choice = self._ask_user_about_templates(missing_templates, pipeline_name)
        if choice is None:  # Skip pipeline
            return False
        elif choice:  # Replicate templates
            for template_ref, version_label in missing_templates:
                self.replicate_template(template_ref, version_label)
            return True
        else:  # Skip templates
            logger.warning(
                "  Continuing without replicating templates (pipeline creation will likely fail)")
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
            f"The script can automatically replicate these templates from "
            f"the source environment.\n\n"
            f"Do you want to replicate these templates?"
        )

        choice = button_dialog(
            title="Missing Templates",
            text=text,
            buttons=[
                ("replicate", "Yes, Replicate Templates"),
                ("skip_templates", "No, Continue Without Templates"),
                ("skip", "Skip This Pipeline"),
            ],
        ).run()

        logger.debug("  Dialog returned: %s", choice)

        # Handle both button keys and display text for compatibility
        if choice in ["skip", "Skip This Pipeline"]:
            logger.info("  ⊘ Skipping pipeline due to missing templates")
            return None  # Skip pipeline
        elif choice in ["replicate", "Yes, Replicate Templates"]:
            logger.info("  → User chose to replicate templates")
            return True
        elif choice in ["skip_templates", "No, Continue Without Templates"]:
            logger.info("  → User chose to skip templates")
            return False
        else:
            logger.warning(
                "  ⚠ Unexpected dialog result: %s, defaulting to skip templates", choice)
            return False
