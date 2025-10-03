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
    import src.api_client
    import src.config
    import src.replicator
    import src.ui
    import src.cli

    # All modules should be importable
    assert src.api_client is not None
    assert src.config is not None
    assert src.replicator is not None
    assert src.ui is not None
    assert src.cli is not None
