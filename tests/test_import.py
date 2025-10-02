"""
Test that we can import the main module
"""


def test_can_import_src_package():
    """Test that we can import the new src package structure."""
    from src import HarnessAPIClient, HarnessReplicator, main

    assert HarnessAPIClient is not None
    assert HarnessReplicator is not None
    assert main is not None


def test_src_package_has_expected_modules():
    """Test that the src package has the expected modules."""
    import src.harness_migration.api_client
    import src.harness_migration.config
    import src.harness_migration.migrator
    import src.harness_migration.ui
    import src.harness_migration.cli

    # All modules should be importable
    assert src.harness_migration.api_client is not None
    assert src.harness_migration.config is not None
    assert src.harness_migration.migrator is not None
    assert src.harness_migration.ui is not None
    assert src.harness_migration.cli is not None
