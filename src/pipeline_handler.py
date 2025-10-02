"""
Pipeline Handler

Handles pipeline replication functionality.
"""

import logging
from typing import Dict, Optional

from .base_replicator import BaseReplicator
from .yaml_utils import YAMLUtils

logger = logging.getLogger(__name__)


class PipelineHandler(BaseReplicator):
    """Handles pipeline replication"""

    def replicate_pipelines(self, template_handler, inputset_handler, trigger_handler) -> bool:
        """Replicate all selected pipelines"""
        pipelines = self.config.get("pipelines", [])
        if not pipelines:
            logger.warning("No pipelines selected for replication")
            return True

        logger.info("Replicating %d pipelines...", len(pipelines))

        for pipeline in pipelines:
            pipeline_id = pipeline.get("identifier")
            if not pipeline_id:
                logger.error("Pipeline missing identifier, skipping: %s", pipeline)
                self.replication_stats["pipelines"]["failed"] += 1
                continue

            pipeline_name = pipeline.get("name") or pipeline_id

            logger.info("\nReplicating pipeline: %s (%s)", pipeline_name, pipeline_id)

            # Get pipeline details from source
            pipeline_endpoint = self._build_endpoint(
                "pipelines", org=self.source_org, project=self.source_project,
                resource_id=pipeline_id)
            pipeline_details = self.source_client.get(pipeline_endpoint)

            if not pipeline_details:
                logger.error("Failed to get pipeline details: %s", pipeline_id)
                self.replication_stats["pipelines"]["failed"] += 1
                continue

            # Extract and handle template dependencies
            yaml_content = pipeline_details.get("pipeline_yaml", "") if isinstance(pipeline_details, dict) else ""
            if yaml_content:
                templates = YAMLUtils.extract_template_refs(yaml_content)
                if templates:
                    logger.info("  Found %d template reference(s) in pipeline", len(templates))

                    # Check which templates already exist
                    for template_ref, version_label in templates:
                        if template_handler.check_template_exists(template_ref, version_label):
                            logger.info(
                                "  Template '%s' (v%s) already exists in destination",
                                template_ref, version_label if version_label else "stable"
                            )
                            self.replication_stats["templates"]["skipped"] += 1

                    # Handle missing templates
                    if not template_handler.handle_missing_templates(templates, pipeline_name):
                        self.replication_stats["pipelines"]["failed"] += 1
                        continue

            # Create or update the pipeline
            if isinstance(pipeline_details, dict):
                result = self._create_or_update_pipeline(pipeline_id, pipeline_name, pipeline_details)
            else:
                logger.error("Pipeline details is not a dictionary: %s", pipeline_id)
                result = None

            if result is True:
                self.replication_stats["pipelines"]["success"] += 1
            elif result is False:
                # Skipped - already exists
                self.replication_stats["pipelines"]["skipped"] += 1
            else:
                # Failed
                self.replication_stats["pipelines"]["failed"] += 1

            # Replicate associated resources regardless of pipeline creation result
            # (input sets and triggers should be replicated even if pipeline already exists)
            if result is not None:  # Only skip if pipeline replication completely failed
                # Replicate associated input sets
                if self._get_option("replicate_input_sets", True):
                    inputset_handler.replicate_input_sets(pipeline_id)
                    
                # Replicate associated triggers (after input sets since triggers may reference them)
                if self._get_option("replicate_triggers", True):
                    trigger_handler.replicate_triggers(pipeline_id)

        return True

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
            yaml_content = YAMLUtils.update_identifiers(
                yaml_content, self.dest_org, self.dest_project, wrapper_key="pipeline")
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
            logger.info("  ✓ Pipeline '%s' replicated successfully", pipeline_name)
            return True
        else:
            logger.error("  ✗ Failed to replicate pipeline: %s", pipeline_name)
            return None  # Failed
