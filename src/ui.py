"""
Interactive UI Components

Handles all user interactions and dialogs.
"""

import logging
from typing import Any, Dict, List, Optional

from prompt_toolkit.shortcuts import (
    checkboxlist_dialog,
    message_dialog,
    radiolist_dialog,
)

logger = logging.getLogger(__name__)


def select_organization(client, title: str = "SELECT ORGANIZATION") -> Optional[str]:
    """Select organization from list"""
    try:
        orgs_endpoint = "/v1/orgs"
        orgs_response = client.get(orgs_endpoint)
        orgs = client.normalize_response(orgs_response)

        if not orgs:
            message_dialog(
                title="Error", text="No organizations found"
            ).run()
            return None

        choices = [(org.get("identifier", ""),
                    org.get("name", org.get("identifier", ""))) for org in orgs]
        choice = radiolist_dialog(
            title=title,
            text="Select an organization:",
            values=choices,
        ).run()

        return choice
    except Exception as e:
        logger.error("Failed to select organization: %s", e)
        message_dialog(
            title="Error", text=f"Failed to load organizations: {e}"
        ).run()
        return None


def select_project(client, org: str, title: str = "SELECT PROJECT") -> Optional[str]:
    """Select project from list"""
    try:
        projects_endpoint = f"/v1/orgs/{org}/projects"
        projects_response = client.get(projects_endpoint)
        projects = client.normalize_response(projects_response)

        if not projects:
            message_dialog(
                title="Error", text="No projects found"
            ).run()
            return None

        choices = [(proj.get("identifier", ""),
                    proj.get("name", proj.get("identifier", ""))) for proj in projects]
        choice = radiolist_dialog(
            title=title,
            text="Select a project:",
            values=choices,
        ).run()

        return choice
    except Exception as e:
        logger.error("Failed to select project: %s", e)
        message_dialog(
            title="Error", text=f"Failed to load projects: {e}"
        ).run()
        return None


def select_pipelines(client, org: str, project: str,
                     title: str = "SELECT PIPELINES") -> List[Dict[str, str]]:
    """Select pipelines from list (multi-select)"""
    try:
        pipelines_endpoint = f"/v1/orgs/{org}/projects/{project}/pipelines"
        pipelines_response = client.get(pipelines_endpoint)
        pipelines = client.normalize_response(pipelines_response)

        if not pipelines:
            message_dialog(
                title="Error", text="No pipelines found"
            ).run()
            return []

        choices = [(pipeline.get("identifier", ""),
                    pipeline.get("name", pipeline.get("identifier", "")))
                   for pipeline in pipelines]
        selected = checkboxlist_dialog(
            title=title,
            text="Select pipelines to replicate (use Space to select/deselect):",
            values=choices,
        ).run()

        if not selected:
            return []

        # Convert to list of dicts
        result = []
        for pipeline in pipelines:
            if pipeline.get("identifier") in selected:
                result.append({
                    "identifier": pipeline.get("identifier"),
                    "name": pipeline.get("name", pipeline.get("identifier"))
                })

        return result
    except Exception as e:
        logger.error("Failed to select pipelines: %s", e)
        message_dialog(
            title="Error", text=f"Failed to load pipelines: {e}"
        ).run()
        return []


def select_or_create_organization(client,
                                  title: str = "SELECT OR CREATE ORGANIZATION") -> Optional[str]:
    """Select existing organization or create new one"""
    try:
        # First try to get existing orgs
        orgs_endpoint = "/v1/orgs"
        orgs_response = client.get(orgs_endpoint)
        orgs = client.normalize_response(orgs_response)

        if orgs:
            choices = [(org.get("identifier", ""),
                        org.get("name", org.get("identifier", ""))) for org in orgs]
            choices.append(("__create_new__", "Create New Organization"))

            choice = radiolist_dialog(
                title=title,
                text="Select an organization or create new:",
                values=choices,
            ).run()

            if choice == "__create_new__":
                return create_organization(client)
            return choice
        else:
            # No orgs found, create one
            return create_organization(client)
    except Exception as e:
        logger.error("Failed to select/create organization: %s", e)
        message_dialog(
            title="Error", text=f"Failed to load organizations: {e}"
        ).run()
        return None


def select_or_create_project(client, org: str,
                             title: str = "SELECT OR CREATE PROJECT") -> Optional[str]:
    """Select existing project or create new one"""
    try:
        # First try to get existing projects
        projects_endpoint = f"/v1/orgs/{org}/projects"
        projects_response = client.get(projects_endpoint)
        projects = client.normalize_response(projects_response)

        if projects:
            choices = [(proj.get("identifier", ""),
                        proj.get("name", proj.get("identifier", ""))) for proj in projects]
            choices.append(("__create_new__", "Create New Project"))

            choice = radiolist_dialog(
                title=title,
                text="Select a project or create new:",
                values=choices,
            ).run()

            if choice == "__create_new__":
                return create_project(client, org)
            return choice
        else:
            # No projects found, create one
            return create_project(client, org)
    except Exception as e:
        logger.error("Failed to select/create project: %s", e)
        message_dialog(
            title="Error", text=f"Failed to load projects: {e}"
        ).run()
        return None


def create_organization(client) -> Optional[str]:
    """Create a new organization"""
    from prompt_toolkit import prompt

    try:
        org_name = prompt("Enter organization identifier: ")
        if not org_name:
            return None

        # Create organization
        orgs_endpoint = "/v1/orgs"
        org_data = {
            "org": {
                "identifier": org_name,
                "name": org_name.replace("_", " ").title(),
                "description": "Organization created by migration tool"
            }
        }

        result = client.post(orgs_endpoint, json=org_data)
        if result:
            logger.info("Organization '%s' created successfully", org_name)
            return org_name
        else:
            message_dialog(
                title="Error", text=f"Failed to create organization '{org_name}'"
            ).run()
            return None
    except Exception as e:
        logger.error("Failed to create organization: %s", e)
        message_dialog(
            title="Error", text=f"Failed to create organization: {e}"
        ).run()
        return None


def create_project(client, org: str) -> Optional[str]:
    """Create a new project"""
    from prompt_toolkit import prompt

    try:
        proj_name = prompt("Enter project identifier: ")
        if not proj_name:
            return None

        # Create project
        projects_endpoint = f"/v1/orgs/{org}/projects"
        project_data = {
            "project": {
                "orgIdentifier": org,
                "identifier": proj_name,
                "name": proj_name.replace("_", " ").title(),
                "description": "Project created by migration tool"
            }
        }

        result = client.post(projects_endpoint, json=project_data)
        if result:
            logger.info("Project '%s' created successfully", proj_name)
            return proj_name
        else:
            message_dialog(
                title="Error", text=f"Failed to create project '{proj_name}'"
            ).run()
            return None
    except Exception as e:
        logger.error("Failed to create project: %s", e)
        message_dialog(
            title="Error", text=f"Failed to create project: {e}"
        ).run()
        return None


def get_selections_from_clients(source_client, dest_client, base_config: Dict[str, Any],
                                config_file: str) -> Dict[str, Any]:
    """Get user selections for source and destination"""
    from .config import save_config

    # Source organization
    source_org = base_config.get("source", {}).get("org")
    if not source_org:
        source_org = select_organization(source_client, "SELECT SOURCE ORGANIZATION")
        if not source_org:
            return {}
        base_config.setdefault("source", {})["org"] = source_org
        save_config(base_config, config_file)

    # Source project
    source_project = base_config.get("source", {}).get("project")
    if not source_project:
        source_project = select_project(source_client, source_org, "SELECT SOURCE PROJECT")
        if not source_project:
            return {}
        base_config.setdefault("source", {})["project"] = source_project
        save_config(base_config, config_file)

    # Source pipelines
    pipelines = base_config.get("pipelines", [])
    if not pipelines:
        pipelines = select_pipelines(source_client, source_org, source_project,
                                     "SELECT PIPELINES TO REPLICATE")
        if not pipelines:
            return {}
        base_config["pipelines"] = pipelines
        save_config(base_config, config_file)

    # Destination organization
    dest_org = base_config.get("destination", {}).get("org")
    if not dest_org:
        dest_org = select_or_create_organization(dest_client,
                                                 "SELECT OR CREATE DESTINATION ORGANIZATION")
        if not dest_org:
            return {}
        base_config.setdefault("destination", {})["org"] = dest_org
        save_config(base_config, config_file)

    # Destination project
    dest_project = base_config.get("destination", {}).get("project")
    if not dest_project:
        dest_project = select_or_create_project(dest_client, dest_org,
                                                "SELECT OR CREATE DESTINATION PROJECT")
        if not dest_project:
            return {}
        base_config.setdefault("destination", {})["project"] = dest_project
        save_config(base_config, config_file)

    return base_config


def get_interactive_selections(source_client, dest_client, base_config: Dict[str, Any],
                              config_file: str) -> Dict[str, Any]:
    """Get user selections with interactive dialogs - always show dialogs even if values exist"""
    from .config import save_config
    from prompt_toolkit.shortcuts import yes_no_dialog

    # Source organization - always show dialog
    current_source_org = base_config.get("source", {}).get("org")
    if current_source_org:
        # Ask if user wants to change the current selection
        keep_source_org = yes_no_dialog(
            title="Source Organization",
            text=f"Current source organization: '{current_source_org}'\n\n"
                 f"Keep this selection?"
        ).run()
        
        if not keep_source_org:
            source_org = select_organization(source_client, "SELECT NEW SOURCE ORGANIZATION")
            if not source_org:
                return {}
            base_config.setdefault("source", {})["org"] = source_org
            save_config(base_config, config_file)
        else:
            source_org = current_source_org
    else:
        source_org = select_organization(source_client, "SELECT SOURCE ORGANIZATION")
        if not source_org:
            return {}
        base_config.setdefault("source", {})["org"] = source_org
        save_config(base_config, config_file)

    # Source project - always show dialog
    current_source_project = base_config.get("source", {}).get("project")
    if current_source_project:
        # Ask if user wants to change the current selection
        keep_source_project = yes_no_dialog(
            title="Source Project",
            text=f"Current source project: '{current_source_project}'\n\n"
                 f"Keep this selection?"
        ).run()
        
        if not keep_source_project:
            source_project = select_project(source_client, source_org, "SELECT NEW SOURCE PROJECT")
            if not source_project:
                return {}
            base_config.setdefault("source", {})["project"] = source_project
            save_config(base_config, config_file)
        else:
            source_project = current_source_project
    else:
        source_project = select_project(source_client, source_org, "SELECT SOURCE PROJECT")
        if not source_project:
            return {}
        base_config.setdefault("source", {})["project"] = source_project
        save_config(base_config, config_file)

    # Source pipelines - always show dialog
    current_pipelines = base_config.get("pipelines", [])
    if current_pipelines:
        # Show current pipelines and ask if user wants to change
        pipeline_names = [p.get("name", p.get("identifier", "Unknown")) for p in current_pipelines]
        pipeline_list = "\n".join(f"  - {name}" for name in pipeline_names)
        
        keep_pipelines = yes_no_dialog(
            title="Pipeline Selection",
            text=f"Current selected pipelines ({len(current_pipelines)}):\n{pipeline_list}\n\n"
                 f"Keep this selection?"
        ).run()
        
        if not keep_pipelines:
            pipelines = select_pipelines(source_client, source_org, source_project,
                                       "SELECT NEW PIPELINES TO MIGRATE")
            if not pipelines:
                return {}
            base_config["pipelines"] = pipelines
            save_config(base_config, config_file)
        else:
            pipelines = current_pipelines
    else:
        pipelines = select_pipelines(source_client, source_org, source_project,
                                   "SELECT PIPELINES TO REPLICATE")
        if not pipelines:
            return {}
        base_config["pipelines"] = pipelines
        save_config(base_config, config_file)

    # Destination organization - always show dialog
    current_dest_org = base_config.get("destination", {}).get("org")
    if current_dest_org:
        # Ask if user wants to change the current selection
        keep_dest_org = yes_no_dialog(
            title="Destination Organization",
            text=f"Current destination organization: '{current_dest_org}'\n\n"
                 f"Keep this selection?"
        ).run()
        
        if not keep_dest_org:
            dest_org = select_or_create_organization(dest_client,
                                                   "SELECT OR CREATE NEW DESTINATION ORGANIZATION")
            if not dest_org:
                return {}
            base_config.setdefault("destination", {})["org"] = dest_org
            save_config(base_config, config_file)
        else:
            dest_org = current_dest_org
    else:
        dest_org = select_or_create_organization(dest_client,
                                               "SELECT OR CREATE DESTINATION ORGANIZATION")
        if not dest_org:
            return {}
        base_config.setdefault("destination", {})["org"] = dest_org
        save_config(base_config, config_file)

    # Destination project - always show dialog
    current_dest_project = base_config.get("destination", {}).get("project")
    if current_dest_project:
        # Ask if user wants to change the current selection
        keep_dest_project = yes_no_dialog(
            title="Destination Project",
            text=f"Current destination project: '{current_dest_project}'\n\n"
                 f"Keep this selection?"
        ).run()
        
        if not keep_dest_project:
            dest_project = select_or_create_project(dest_client, dest_org,
                                                   "SELECT OR CREATE NEW DESTINATION PROJECT")
            if not dest_project:
                return {}
            base_config.setdefault("destination", {})["project"] = dest_project
            save_config(base_config, config_file)
        else:
            dest_project = current_dest_project
    else:
        dest_project = select_or_create_project(dest_client, dest_org,
                                               "SELECT OR CREATE DESTINATION PROJECT")
        if not dest_project:
            return {}
        base_config.setdefault("destination", {})["project"] = dest_project
        save_config(base_config, config_file)

    return base_config
