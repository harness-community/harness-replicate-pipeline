"""
Replication Logic

Main replication orchestrator that coordinates all handlers.
"""

import logging
from typing import Any, Dict

from .api_client import HarnessAPIClient
from .inputset_handler import InputSetHandler
from .pipeline_handler import PipelineHandler
from .prerequisite_handler import PrerequisiteHandler
from .template_handler import TemplateHandler
from .trigger_handler import TriggerHandler

logger = logging.getLogger(__name__)


class HarnessReplicator:
    """Main replication orchestrator"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize replicator with configuration"""
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

        # Replication statistics
        self.replication_stats = {
            "pipelines": {"success": 0, "failed": 0, "skipped": 0},
            "input_sets": {"success": 0, "failed": 0, "skipped": 0},
            "templates": {"success": 0, "failed": 0, "skipped": 0},
            "triggers": {"success": 0, "failed": 0, "skipped": 0},
        }

        # Initialize handlers
        self.prerequisite_handler = PrerequisiteHandler(
            config, self.source_client, self.dest_client, self.replication_stats)
        self.template_handler = TemplateHandler(
            config, self.source_client, self.dest_client, self.replication_stats)
        self.inputset_handler = InputSetHandler(
            config, self.source_client, self.dest_client, self.replication_stats)
        self.trigger_handler = TriggerHandler(
            config, self.source_client, self.dest_client, self.replication_stats)
        self.pipeline_handler = PipelineHandler(
            config, self.source_client, self.dest_client, self.replication_stats)

    def run_replication(self) -> bool:
        """Run the complete replication process"""
        logger.info("Starting Harness Pipeline Replication")
        logger.info("Source: %s/%s", self.source_org, self.source_project)
        logger.info("Destination: %s/%s", self.dest_org, self.dest_project)

        # Verify prerequisites
        if not self.prerequisite_handler.verify_prerequisites():
            return False

        # Replicate pipelines
        if not self.pipeline_handler.replicate_pipelines(
                self.template_handler, self.inputset_handler, self.trigger_handler):
            return False

        # Print summary
        self.print_summary()
        return True

    def print_summary(self):
        """Print replication summary using output orchestrator"""
        from .output_orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        orchestrator.output_summary(self.replication_stats)
