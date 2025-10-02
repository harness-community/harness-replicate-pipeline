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
        """Handle missing templates - automatically replicate based on configuration"""
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

        # Check if template replication is enabled
        skip_templates = self._get_option("skip_templates", False)
        
        if not skip_templates:
            logger.info("  Auto-replicating missing templates...")
            for template_ref, version_label in missing_templates:
                self.replicate_template(template_ref, version_label)
            return True
        else:
            logger.warning("  Template replication disabled, continuing without templates")
            logger.warning("  Pipeline creation may fail due to missing template dependencies")
            return True
