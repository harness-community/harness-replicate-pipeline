"""
YAML Utilities

Utilities for manipulating YAML content during replication.
"""

import logging
import re
from typing import List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


class YAMLUtils:
    """Utilities for YAML manipulation during replication"""

    @staticmethod
    def update_identifiers(yaml_content: str, dest_org: str, dest_project: str,
                           wrapper_key: Optional[str] = None) -> str:
        """Update org and project identifiers in YAML content"""
        try:
            data = yaml.safe_load(yaml_content)

            # Determine where to update identifiers
            target = data.get(wrapper_key, data) if wrapper_key else data

            target["orgIdentifier"] = dest_org
            target["projectIdentifier"] = dest_project

            return yaml.dump(data, default_flow_style=False, sort_keys=False)
        except (yaml.YAMLError, ValueError, TypeError, KeyError) as e:
            logger.error("Failed to update YAML identifiers: %s", e)
            # Fallback to string replacement
            yaml_content = re.sub(
                r'orgIdentifier:\s*["\']?[^"\'\s]+["\']?',
                f'orgIdentifier: "{dest_org}"',
                yaml_content
            )
            yaml_content = re.sub(
                r'projectIdentifier:\s*["\']?[^"\'\s]+["\']?',
                f'projectIdentifier: "{dest_project}"',
                yaml_content
            )
            return yaml_content

    @staticmethod
    def extract_template_refs(yaml_content: str) -> List[Tuple[str, Optional[str]]]:
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

    @staticmethod
    def set_template_version(yaml_content: str, version_label: Optional[str] = None) -> str:
        """Set version label in template YAML"""
        try:
            template_dict = yaml.safe_load(yaml_content)
            if "template" in template_dict:
                template_dict["template"]["versionLabel"] = version_label or "stable"
            return yaml.dump(template_dict, default_flow_style=False, sort_keys=False)
        except yaml.YAMLError:
            logger.warning("Failed to set template version, using original YAML")
            return yaml_content
