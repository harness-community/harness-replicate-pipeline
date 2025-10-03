"""
Base Replicator

Base class with common functionality for all replication handlers.
"""

import logging
from typing import Any, Dict, Optional

from .api_client import HarnessAPIClient

logger = logging.getLogger(__name__)


class BaseReplicator:
    """Base class for replication handlers"""

    def __init__(self, config: Dict[str, Any], source_client: HarnessAPIClient,
                 dest_client: HarnessAPIClient, replication_stats: Dict[str, Dict[str, int]]):
        """Initialize base replicator"""
        self.config = config
        self.source_org = config["source"]["org"]
        self.source_project = config["source"]["project"]
        self.dest_org = config["destination"]["org"]
        self.dest_project = config["destination"]["project"]

        self.source_client = source_client
        self.dest_client = dest_client
        self.replication_stats = replication_stats

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
