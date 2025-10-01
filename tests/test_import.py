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
