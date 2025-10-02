"""
Test that we can import the main module
"""
import harness_pipeline_migration


def test_can_import_main_module():
    """Test that we can import the main migration script."""
    assert harness_pipeline_migration is not None


def test_module_has_expected_classes():
    """Test that the module has the expected classes."""
    # Check that main classes exist
    assert hasattr(harness_pipeline_migration, 'HarnessAPIClient')
    assert hasattr(harness_pipeline_migration, 'HarnessMigrator')

    # Check that main function exists
    assert hasattr(harness_pipeline_migration, 'main')


def test_can_import_src_package():
    """Test that we can import the new src package structure."""
    from src.harness_migration import HarnessAPIClient, HarnessMigrator, main

    assert HarnessAPIClient is not None
    assert HarnessMigrator is not None
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
