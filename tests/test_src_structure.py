"""
Test the new src/ package structure
"""


def test_api_client_import():
    """Test that we can import the API client."""
    from src.harness_migration.api_client import HarnessAPIClient

    assert HarnessAPIClient is not None


def test_migrator_import():
    """Test that we can import the migrator."""
    from src.harness_migration.migrator import HarnessMigrator

    assert HarnessMigrator is not None


def test_config_import():
    """Test that we can import config functions."""
    from src.harness_migration.config import load_config, save_config, apply_cli_overrides

    assert load_config is not None
    assert save_config is not None
    assert apply_cli_overrides is not None


def test_ui_import():
    """Test that we can import UI functions."""
    from src.harness_migration.ui import select_organization, select_project

    assert select_organization is not None
    assert select_project is not None


def test_cli_import():
    """Test that we can import CLI functions."""
    from src.harness_migration.cli import main, setup_logging

    assert main is not None
    assert setup_logging is not None


def test_package_init():
    """Test that the package __init__.py works correctly."""
    from src.harness_migration import HarnessAPIClient, HarnessMigrator, main

    assert HarnessAPIClient is not None
    assert HarnessMigrator is not None
    assert main is not None
