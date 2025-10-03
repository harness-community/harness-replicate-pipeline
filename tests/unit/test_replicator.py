"""
Comprehensive unit tests for HarnessReplicator

Tests replication functionality with proper mocking and AAA methodology.
"""

import pytest
from unittest.mock import patch

from src.api_client import HarnessAPIClient
from src.replicator import HarnessReplicator


@pytest.mark.unit
class TestHarnessReplicator:
    """Test suite for HarnessReplicator"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.config = {
            "source": {
                "base_url": "https://app.harness.io",
                "api_key": "source-key",
                "org": "source-org",
                "project": "source-project"
            },
            "destination": {
                "base_url": "https://app3.harness.io",
                "api_key": "dest-key",
                "org": "dest-org",
                "project": "dest-project"
            },
            "options": {
                "replicate_input_sets": True,
                "skip_existing": True
            },
            "pipelines": [
                {"identifier": "pipeline1", "name": "Pipeline 1"}
            ]
        }
        self.replicator = HarnessReplicator(self.config)

    def test_init_sets_correct_attributes(self):
        """Test that initialization sets correct attributes"""
        # Arrange & Act
        replicator = HarnessReplicator(self.config)

        # Assert
        assert replicator.source_org == "source-org"
        assert replicator.source_project == "source-project"
        assert replicator.dest_org == "dest-org"
        assert replicator.dest_project == "dest-project"
        assert isinstance(replicator.source_client, HarnessAPIClient)
        assert isinstance(replicator.dest_client, HarnessAPIClient)
        assert replicator.replication_stats == {
            "pipelines": {"success": 0, "failed": 0, "skipped": 0},
            "input_sets": {"success": 0, "failed": 0, "skipped": 0},
            "templates": {"success": 0, "failed": 0, "skipped": 0},
            "triggers": {"success": 0, "failed": 0, "skipped": 0}
        }

    def test_run_replication_success(self):
        """Test successful replication run"""
        # Arrange
        with patch.object(self.replicator.prerequisite_handler, 'verify_prerequisites', return_value=True):
            with patch.object(self.replicator.pipeline_handler, 'replicate_pipelines', return_value=True):
                with patch.object(self.replicator, 'print_summary'):
                    # Act
                    result = self.replicator.run_replication()

        # Assert
        assert result is True

    def test_run_replication_prerequisites_fail(self):
        """Test replication fails when prerequisites fail"""
        # Arrange
        with patch.object(self.replicator.prerequisite_handler, 'verify_prerequisites', return_value=False):
            # Act
            result = self.replicator.run_replication()

        # Assert
        assert result is False

    def test_run_replication_pipelines_fail(self):
        """Test replication fails when pipeline replication fails"""
        # Arrange
        with patch.object(self.replicator.prerequisite_handler, 'verify_prerequisites', return_value=True):
            with patch.object(self.replicator.pipeline_handler, 'replicate_pipelines', return_value=False):
                # Act
                result = self.replicator.run_replication()

        # Assert
        assert result is False

    def test_print_summary(self):
        """Test print_summary outputs correct format"""
        # Arrange
        self.replicator.replication_stats = {
            "pipelines": {"success": 2, "failed": 1, "skipped": 0},
            "input_sets": {"success": 3, "failed": 0, "skipped": 1},
            "templates": {"success": 1, "failed": 0, "skipped": 0},
            "triggers": {"success": 2, "failed": 0, "skipped": 0}
        }

        # Act & Assert (just verify it doesn't crash)
        self.replicator.print_summary()
