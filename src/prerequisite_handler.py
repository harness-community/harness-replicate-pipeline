"""
Prerequisite Handler

Handles organization and project creation prerequisites.
"""

import logging
# No additional imports needed

from .api_client import HarnessAPIClient
from .base_replicator import BaseReplicator

logger = logging.getLogger(__name__)


class PrerequisiteHandler(BaseReplicator):
    """Handles organization and project prerequisites"""

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
        # Check if org exists by trying to get it directly
        org_endpoint = f"/v1/orgs/{self.dest_org}"
        existing_org = self.dest_client.get(org_endpoint)
        
        if existing_org:
            logger.info("Organization '%s' already exists", self.dest_org)
            return True

        # Create organization
        logger.info("Creating organization: %s", self.dest_org)
        create_org_data = {
            "org": {
                "identifier": self.dest_org,
                "name": self.dest_org.replace("_", " ").title(),
                "description": "Organization created by replication tool"
            }
        }

        orgs_endpoint = self._build_endpoint("orgs")
        create_org = self.dest_client.post(orgs_endpoint, json=create_org_data)
        if not create_org:
            # Check if it failed because org already exists (race condition)
            orgs_check = self.dest_client.get(orgs_endpoint)
            orgs_list_check = HarnessAPIClient.normalize_response(orgs_check)
            for org in orgs_list_check:
                if org.get("identifier") == self.dest_org:
                    logger.info("Organization '%s' already exists (created concurrently)", self.dest_org)
                    return True
            
            logger.error("Failed to create organization")
            return False

        logger.info("Organization '%s' created successfully", self.dest_org)
        return True

    def _create_project_if_missing(self) -> bool:
        """Create project if it doesn't exist"""
        # Check if project exists by trying to get it directly
        project_endpoint = f"/v1/orgs/{self.dest_org}/projects/{self.dest_project}"
        existing_project = self.dest_client.get(project_endpoint)
        
        if existing_project:
            logger.info("Project '%s' already exists", self.dest_project)
            return True

        # Create project
        logger.info("Creating project: %s", self.dest_project)
        create_project_data = {
            "project": {
                "orgIdentifier": self.dest_org,
                "identifier": self.dest_project,
                "name": self.dest_project.replace("_", " ").title(),
                "description": "Project created by replication tool"
            }
        }

        projects_endpoint = self._build_endpoint("projects", org=self.dest_org)
        create_project = self.dest_client.post(projects_endpoint, json=create_project_data)
        if not create_project:
            # Check if it failed because project already exists (race condition)
            projects_check = self.dest_client.get(projects_endpoint)
            projects_list_check = HarnessAPIClient.normalize_response(projects_check)
            for project in projects_list_check:
                if project.get("identifier") == self.dest_project:
                    logger.info("Project '%s' already exists (created concurrently)", self.dest_project)
                    return True
            
            logger.error("Failed to create project")
            return False

        logger.info("Project '%s' created successfully", self.dest_project)
        return True
