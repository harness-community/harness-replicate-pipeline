"""
Input Set Handler

Handles input set replication functionality.
"""

import logging
import time
# No additional imports needed

from .api_client import HarnessAPIClient
from .base_replicator import BaseReplicator
from .yaml_utils import YAMLUtils

logger = logging.getLogger(__name__)


class InputSetHandler(BaseReplicator):
    """Handles input set replication"""

    def replicate_input_sets(self, pipeline_id: str) -> bool:
        """Replicate input sets for a specific pipeline"""
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

        logger.info("  Replicating %d input sets...", len(input_sets))

        for input_set in input_sets:
            input_set_id = input_set.get("identifier")
            input_set_name = input_set.get("name", input_set_id)
            logger.info("  Replicating input set: %s", input_set_name)

            # Get full input set details
            get_endpoint = self._build_endpoint(
                "input-sets", org=self.source_org, project=self.source_project,
                resource_id=input_set_id)
            input_set_details = self.source_client.get(
                get_endpoint, params={"pipeline": pipeline_id})

            if not input_set_details:
                logger.error("  Failed to get details for input set: %s", input_set_id)
                self.replication_stats["input_sets"]["failed"] += 1
                continue

            # Update org/project identifiers in input set YAML
            if isinstance(input_set_details, dict) and "input_set_yaml" in input_set_details:
                yaml_content = input_set_details["input_set_yaml"]
                updated_yaml = YAMLUtils.update_identifiers(
                    yaml_content, self.dest_org, self.dest_project, wrapper_key="inputSet")
                input_set_details["input_set_yaml"] = updated_yaml

            # Create input set in destination
            create_endpoint = self._build_endpoint(
                "input-sets", org=self.dest_org, project=self.dest_project)

            if self._is_dry_run():
                logger.info("  [DRY RUN] Would create input set '%s'", input_set_name)
                result = True
            else:
                json_data = input_set_details if isinstance(input_set_details, dict) else None
                result = self.dest_client.post(
                    create_endpoint, params={"pipeline": pipeline_id},
                    json=json_data)

            if result:
                logger.info("  ✓ Input set '%s' replicated successfully", input_set_name)
                self.replication_stats["input_sets"]["success"] += 1
            else:
                logger.error("  ✗ Failed to replicate input set: %s", input_set_name)
                self.replication_stats["input_sets"]["failed"] += 1

            time.sleep(0.3)

        return True
