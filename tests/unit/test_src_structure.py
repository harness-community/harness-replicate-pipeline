"""
Test the new src/ package structure
"""


def test_api_client_import():
    """Test that we can import the API client."""
    from src.api_client import HarnessAPIClient

    assert HarnessAPIClient is not None


def test_migrator_import():
    """Test that we can import the replicator."""
    from src.replicator import HarnessReplicator

    assert HarnessReplicator is not None


def test_config_import():
    """Test that we can import config functions."""
    from src.config import load_config, save_config, build_complete_config

    assert load_config is not None
    assert save_config is not None
    assert build_complete_config is not None


def test_ui_import():
    """Test that we can import UI functions."""
    from src.ui import select_organization, select_project

    assert select_organization is not None
    assert select_project is not None


def test_cli_import():
    """Test that we can import CLI functions."""
    from src.cli import main
    from src.logging_utils import setup_logging

    assert main is not None
    assert setup_logging is not None


def test_package_init():
    """Test that the package __init__.py works correctly."""
    from src import HarnessAPIClient, HarnessReplicator, main

    assert HarnessAPIClient is not None
    assert HarnessReplicator is not None
    assert main is not None
