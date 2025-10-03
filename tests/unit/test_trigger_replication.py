"""
Unit Tests for Trigger Replication

These tests focus on the behavior of trigger replication functionality,
using mocks to isolate the logic from external dependencies.
"""
from unittest.mock import Mock

from src.trigger_handler import TriggerHandler
from src.api_client import HarnessAPIClient


class TestTriggerReplication:
    """Unit tests for trigger replication functionality"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.config = {
            "source": {
                "base_url": "https://source.harness.io",
                "api_key": "source-api-key",
                "org": "source_org",
                "project": "source_project"
            },
            "destination": {
                "base_url": "https://dest.harness.io",
                "api_key": "dest-api-key",
                "org": "dest_org",
                "project": "dest_project"
            },
            "options": {
                "replicate_triggers": True
            },
            "dry_run": False,
            "non_interactive": True
        }

        # Create mock clients
        self.mock_source_client = Mock(spec=HarnessAPIClient)
        self.mock_dest_client = Mock(spec=HarnessAPIClient)

        # Mock the session attribute for trigger API calls
        self.mock_dest_client.session = Mock()
        self.mock_dest_client.base_url = "https://dest.harness.io"

        # Create replication stats
        self.replication_stats = {
            "triggers": {"success": 0, "failed": 0, "skipped": 0}
        }

        # Create handler
        self.handler = TriggerHandler(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )

    def test_replicate_triggers_no_triggers_found(self):
        """Test replicate_triggers when no triggers exist for pipeline"""
        # Arrange
        pipeline_id = "test_pipeline"
        self.mock_source_client.get.return_value = None

        # Act
        result = self.handler.replicate_triggers(pipeline_id)

        # Assert
        assert result is True
        assert self.replication_stats["triggers"]["success"] == 0
        assert self.replication_stats["triggers"]["failed"] == 0
        assert self.replication_stats["triggers"]["skipped"] == 0

    def test_replicate_triggers_empty_response(self):
        """Test replicate_triggers when API returns empty response"""
        # Arrange
        pipeline_id = "test_pipeline"
        self.mock_source_client.get.return_value = {"data": {"content": []}}

        # Act
        result = self.handler.replicate_triggers(pipeline_id)

        # Assert
        assert result is True
        assert self.replication_stats["triggers"]["success"] == 0

    def test_replicate_triggers_successful_creation(self):
        """Test successful trigger replication"""
        # Arrange
        pipeline_id = "test_pipeline"
        trigger_data = {
            "identifier": "test_trigger",
            "name": "Test Trigger"
        }

        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List triggers response
            {"data": {"content": [trigger_data]}},
            # Get trigger details
            {"data": {"yaml": "trigger:\n  name: Test Trigger\n  orgIdentifier: source_org\n  projectIdentifier: source_project"}}
        ]

        # Mock destination client - trigger doesn't exist
        self.mock_dest_client.get.return_value = None

        # Mock successful creation
        mock_response = Mock()
        mock_response.status_code = 201
        self.mock_dest_client.session.post.return_value = mock_response

        # Act
        result = self.handler.replicate_triggers(pipeline_id)

        # Assert
        assert result is True
        assert self.replication_stats["triggers"]["success"] == 1
        assert self.replication_stats["triggers"]["failed"] == 0

    def test_replicate_triggers_skip_existing(self):
        """Test trigger replication skips existing triggers when skip_existing is True"""
        # Arrange
        pipeline_id = "test_pipeline"
        trigger_data = {
            "identifier": "test_trigger",
            "name": "Test Trigger"
        }

        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List triggers response
            {"data": {"content": [trigger_data]}},
        ]

        # Mock existing trigger check (exists)
        self.mock_dest_client.get.return_value = {"data": {"identifier": "test_trigger"}}

        # Act
        result = self.handler.replicate_triggers(pipeline_id)

        # Assert
        assert result is True
        assert self.replication_stats["triggers"]["success"] == 0
        assert self.replication_stats["triggers"]["skipped"] == 1

    def test_replicate_triggers_update_existing(self):
        """Test trigger replication updates existing triggers when skip_existing is False"""
        # Arrange
        pipeline_id = "test_pipeline"
        trigger_data = {
            "identifier": "test_trigger",
            "name": "Test Trigger"
        }

        # Override config to update existing
        self.config["options"]["update_existing"] = True
        handler = TriggerHandler(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )

        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List triggers response
            {"data": {"content": [trigger_data]}},
            # Get trigger details
            {"data": {"yaml": "trigger:\n  name: Test Trigger\n  orgIdentifier: source_org\n  projectIdentifier: source_project"}}
        ]

        # Mock existing trigger check (exists)
        self.mock_dest_client.get.return_value = {"data": {"identifier": "test_trigger"}}

        # Mock successful update
        mock_response = Mock()
        mock_response.status_code = 200
        self.mock_dest_client.session.put.return_value = mock_response

        # Act
        result = handler.replicate_triggers(pipeline_id)

        # Assert
        assert result is True
        assert self.replication_stats["triggers"]["success"] == 1

    def test_replicate_triggers_creation_fails(self):
        """Test trigger replication handles creation failures"""
        # Arrange
        pipeline_id = "test_pipeline"
        trigger_data = {
            "identifier": "test_trigger",
            "name": "Test Trigger"
        }

        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List triggers response
            {"data": {"content": [trigger_data]}},
            # Get trigger details
            {"data": {"yaml": "trigger:\n  name: Test Trigger"}}
        ]

        # Mock destination client - trigger doesn't exist
        self.mock_dest_client.get.return_value = None

        # Mock failed creation
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        self.mock_dest_client.session.post.return_value = mock_response

        # Act
        result = self.handler.replicate_triggers(pipeline_id)

        # Assert
        assert result is True  # Method continues despite individual failures
        assert self.replication_stats["triggers"]["failed"] == 1
        assert self.replication_stats["triggers"]["success"] == 0

    def test_replicate_triggers_dry_run_mode(self):
        """Test trigger replication in dry run mode"""
        # Arrange
        pipeline_id = "test_pipeline"
        trigger_data = {
            "identifier": "test_trigger",
            "name": "Test Trigger"
        }

        # Enable dry run
        self.config["dry_run"] = True
        handler = TriggerHandler(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )

        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List triggers response
            {"data": {"content": [trigger_data]}},
            # Get trigger details
            {"data": {"yaml": "trigger:\n  name: Test Trigger"}}
        ]

        # Mock destination client - trigger doesn't exist
        self.mock_dest_client.get.return_value = None

        # Act
        result = handler.replicate_triggers(pipeline_id)

        # Assert
        assert result is True
        assert self.replication_stats["triggers"]["success"] == 1
        # Verify no actual API calls were made to create
        self.mock_dest_client.session.post.assert_not_called()

    def test_replicate_triggers_missing_trigger_details(self):
        """Test trigger replication handles missing trigger details"""
        # Arrange
        pipeline_id = "test_pipeline"
        trigger_data = {
            "identifier": "test_trigger",
            "name": "Test Trigger"
        }

        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List triggers response
            {"data": {"content": [trigger_data]}},
            # Get trigger details (fails)
            None
        ]

        # Mock destination client - trigger doesn't exist
        self.mock_dest_client.get.return_value = None

        # Act
        result = self.handler.replicate_triggers(pipeline_id)

        # Assert
        assert result is True  # Method continues despite individual failures
        assert self.replication_stats["triggers"]["failed"] == 1
        assert self.replication_stats["triggers"]["success"] == 0
