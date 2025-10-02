"""
Trigger Handler

Handles trigger replication functionality.
"""

import logging
import time
# No additional imports needed

from .api_client import HarnessAPIClient
from .base_replicator import BaseReplicator
from .yaml_utils import YAMLUtils

logger = logging.getLogger(__name__)


class TriggerHandler(BaseReplicator):
    """Handles trigger replication"""

    def replicate_triggers(self, pipeline_id: str) -> bool:
        """Replicate triggers for a specific pipeline"""
        logger.info("  Checking for triggers for pipeline: %s", pipeline_id)

        # List triggers using the discovered API endpoint
        endpoint = "/pipeline/api/triggers"
        params = {
            "orgIdentifier": self.source_org,
            "projectIdentifier": self.source_project,
            "targetIdentifier": pipeline_id
        }
        triggers_response = self.source_client.get(endpoint, params=params)
        
        if not triggers_response:
            logger.info("  No triggers found for pipeline: %s", pipeline_id)
            return True

        # Extract triggers from the response structure
        triggers_data = triggers_response.get("data", {})
        if isinstance(triggers_data, dict):
            triggers_list = triggers_data.get("content", [])
        else:
            triggers_list = []

        triggers = HarnessAPIClient.normalize_response(triggers_list)

        if not triggers:
            logger.info("  No triggers found for pipeline: %s", pipeline_id)
            return True

        logger.info("  Replicating %d triggers...", len(triggers))

        for trigger in triggers:
            trigger_id = trigger.get("identifier")
            trigger_name = trigger.get("name", trigger_id)
            logger.info("  Replicating trigger: %s", trigger_name)

            # Check if trigger already exists in destination
            existing_trigger_endpoint = f"/pipeline/api/triggers/{trigger_id}"
            existing_trigger_params = {
                "orgIdentifier": self.dest_org,
                "projectIdentifier": self.dest_project,
                "targetIdentifier": pipeline_id
            }
            existing_trigger = self.dest_client.get(existing_trigger_endpoint, params=existing_trigger_params)

            if existing_trigger:
                if not self._get_option("update_existing", False):
                    logger.info("  Trigger '%s' already exists, skipping", trigger_name)
                    self.replication_stats["triggers"]["skipped"] += 1
                    continue
                else:
                    logger.info("  Trigger '%s' already exists, updating", trigger_name)

            # Get full trigger details from source
            get_endpoint = f"/pipeline/api/triggers/{trigger_id}"
            get_params = {
                "orgIdentifier": self.source_org,
                "projectIdentifier": self.source_project,
                "targetIdentifier": pipeline_id
            }
            trigger_response = self.source_client.get(get_endpoint, params=get_params)
            
            # Extract trigger details from response
            if trigger_response and isinstance(trigger_response, dict):
                trigger_details = trigger_response.get("data", {})
            else:
                trigger_details = None

            if not trigger_details:
                logger.error("  Failed to get details for trigger: %s", trigger_id)
                self.replication_stats["triggers"]["failed"] += 1
                continue

            # Update org/project identifiers in trigger YAML
            if isinstance(trigger_details, dict) and "yaml" in trigger_details:
                yaml_content = trigger_details["yaml"]
                updated_yaml = YAMLUtils.update_identifiers(
                    yaml_content, self.dest_org, self.dest_project, wrapper_key="trigger")
                trigger_details["yaml"] = updated_yaml

            # Create or update trigger in destination
            if existing_trigger:
                # Update existing trigger (use PUT)
                update_endpoint = f"/pipeline/api/triggers/{trigger_id}"
                create_params = {
                    "orgIdentifier": self.dest_org,
                    "projectIdentifier": self.dest_project,
                    "targetIdentifier": pipeline_id
                }
                action = "update"
            else:
                # Create new trigger (use POST)
                update_endpoint = "/pipeline/api/triggers"
                create_params = {
                    "orgIdentifier": self.dest_org,
                    "projectIdentifier": self.dest_project,
                    "targetIdentifier": pipeline_id
                }
                action = "create"

            if self._is_dry_run():
                logger.info("  [DRY RUN] Would %s trigger '%s'", action, trigger_name)
                result = True
            else:
                # Send the YAML content directly as the request body
                if isinstance(trigger_details, dict) and "yaml" in trigger_details:
                    yaml_content = trigger_details["yaml"]
                    
                    if existing_trigger:
                        # Use PUT for updates
                        result = self.dest_client.session.put(
                            f"{self.dest_client.base_url}{update_endpoint}",
                            params=create_params,
                            data=yaml_content,
                            headers={"Content-Type": "application/yaml"}
                        )
                    else:
                        # Use POST for creation
                        result = self.dest_client.session.post(
                            f"{self.dest_client.base_url}{update_endpoint}",
                            params=create_params,
                            data=yaml_content,
                            headers={"Content-Type": "application/yaml"}
                        )
                    
                    # Check if the request was successful
                    if result.status_code in [200, 201]:
                        result = True
                    else:
                        logger.error("  API Error: %s", result.text)
                        result = False
                else:
                    result = False

            if result:
                logger.info("  ✓ Trigger '%s' %s successfully", trigger_name, "updated" if existing_trigger else "replicated")
                self.replication_stats["triggers"]["success"] += 1
            else:
                logger.error("  ✗ Failed to %s trigger: %s", action, trigger_name)
                self.replication_stats["triggers"]["failed"] += 1

            time.sleep(0.3)

        return True
