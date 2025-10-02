"""
Comprehensive unit tests for InputSetHandler

Tests input set replication functionality with proper mocking and AAA methodology.
"""

from unittest.mock import Mock, patch

from src.inputset_handler import InputSetHandler
from src.api_client import HarnessAPIClient


class TestInputSetHandler:
    """Unit tests for InputSetHandler class"""

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
                "update_existing": False
            },
            "dry_run": False,
            "non_interactive": True
        }
        
        # Create mock clients
        self.mock_source_client = Mock(spec=HarnessAPIClient)
        self.mock_dest_client = Mock(spec=HarnessAPIClient)
        
        # Create replication stats
        self.replication_stats = {
            "input_sets": {"success": 0, "failed": 0, "skipped": 0}
        }
        
        # Create handler
        self.handler = InputSetHandler(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )

    def test_replicate_input_sets_no_input_sets_found(self):
        """Test replicate_input_sets when no input sets exist for pipeline"""
        # Arrange
        pipeline_id = "test_pipeline"
        self.mock_source_client.get.return_value = None
        
        # Act
        result = self.handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True
        assert self.replication_stats["input_sets"]["success"] == 0
        assert self.replication_stats["input_sets"]["failed"] == 0
        assert self.replication_stats["input_sets"]["skipped"] == 0
        self.mock_source_client.get.assert_called_once()

    def test_replicate_input_sets_empty_response(self):
        """Test replicate_input_sets with empty normalized response"""
        # Arrange
        pipeline_id = "test_pipeline"
        self.mock_source_client.get.return_value = {"data": {"content": []}}
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[]):
            # Act
            result = self.handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True
        assert self.replication_stats["input_sets"]["success"] == 0
        assert self.replication_stats["input_sets"]["failed"] == 0
        assert self.replication_stats["input_sets"]["skipped"] == 0

    def test_replicate_input_sets_successful_creation(self):
        """Test successful input set replication"""
        # Arrange
        pipeline_id = "test_pipeline"
        input_set_data = {
            "identifier": "test_input_set",
            "name": "Test Input Set"
        }
        
        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List input sets response
            {"data": {"content": [input_set_data]}},
            # Get input set details
            {"input_set_yaml": "inputSet:\n  name: Test Input Set\n  orgIdentifier: source_org\n  projectIdentifier: source_project"}
        ]
        
        # Mock destination client - input set doesn't exist
        self.mock_dest_client.get.return_value = None
        
        # Mock successful creation
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[input_set_data]):
            with patch('src.inputset_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
                mock_yaml_update.return_value = "updated_yaml"
                
                # Act
                result = self.handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True
        assert self.replication_stats["input_sets"]["success"] == 1
        assert self.replication_stats["input_sets"]["failed"] == 0
        assert self.replication_stats["input_sets"]["skipped"] == 0
        self.mock_dest_client.post.assert_called_once()

    def test_replicate_input_sets_skip_existing(self):
        """Test input set replication skips existing input sets when update_existing is False"""
        # Arrange
        pipeline_id = "test_pipeline"
        input_set_data = {
            "identifier": "test_input_set",
            "name": "Test Input Set"
        }
        
        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List input sets response
            {"data": {"content": [input_set_data]}},
            # Get input set details
            {"input_set_yaml": "inputSet:\n  name: Test Input Set"}
        ]
        
        # Mock existing input set check (exists)
        self.mock_dest_client.get.return_value = {"identifier": "test_input_set"}
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[input_set_data]):
            # Act
            result = self.handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True
        assert self.replication_stats["input_sets"]["success"] == 0
        assert self.replication_stats["input_sets"]["skipped"] == 1
        self.mock_dest_client.post.assert_not_called()
        self.mock_dest_client.put.assert_not_called()

    def test_replicate_input_sets_update_existing(self):
        """Test input set replication updates existing input sets when update_existing is True"""
        # Arrange
        pipeline_id = "test_pipeline"
        input_set_data = {
            "identifier": "test_input_set",
            "name": "Test Input Set"
        }
        
        # Override config to update existing
        self.config["options"]["update_existing"] = True
        handler = InputSetHandler(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )
        
        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List input sets response
            {"data": {"content": [input_set_data]}},
            # Get input set details
            {"input_set_yaml": "inputSet:\n  name: Test Input Set"}
        ]
        
        # Mock existing input set check (exists)
        self.mock_dest_client.get.return_value = {"identifier": "test_input_set"}
        
        # Mock successful update
        self.mock_dest_client.put.return_value = {"status": "SUCCESS"}
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[input_set_data]):
            with patch('src.inputset_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
                mock_yaml_update.return_value = "updated_yaml"
                
                # Act
                result = handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True
        assert self.replication_stats["input_sets"]["success"] == 1
        assert self.replication_stats["input_sets"]["failed"] == 0
        self.mock_dest_client.put.assert_called_once()

    def test_replicate_input_sets_creation_fails(self):
        """Test input set replication handles creation failures"""
        # Arrange
        pipeline_id = "test_pipeline"
        input_set_data = {
            "identifier": "test_input_set",
            "name": "Test Input Set"
        }
        
        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List input sets response
            {"data": {"content": [input_set_data]}},
            # Get input set details
            {"input_set_yaml": "inputSet:\n  name: Test Input Set"}
        ]
        
        # Mock destination client - input set doesn't exist
        self.mock_dest_client.get.return_value = None
        
        # Mock failed creation
        self.mock_dest_client.post.return_value = None
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[input_set_data]):
            with patch('src.inputset_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
                mock_yaml_update.return_value = "updated_yaml"
                
                # Act
                result = self.handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True  # Method continues despite individual failures
        assert self.replication_stats["input_sets"]["failed"] == 1
        assert self.replication_stats["input_sets"]["success"] == 0

    def test_replicate_input_sets_dry_run_mode(self):
        """Test input set replication in dry run mode"""
        # Arrange
        pipeline_id = "test_pipeline"
        input_set_data = {
            "identifier": "test_input_set",
            "name": "Test Input Set"
        }
        
        # Enable dry run
        self.config["dry_run"] = True
        handler = InputSetHandler(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )
        
        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List input sets response
            {"data": {"content": [input_set_data]}},
            # Get input set details
            {"input_set_yaml": "inputSet:\n  name: Test Input Set"}
        ]
        
        # Mock destination client - input set doesn't exist
        self.mock_dest_client.get.return_value = None
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[input_set_data]):
            with patch('src.inputset_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
                mock_yaml_update.return_value = "updated_yaml"
                
                # Act
                result = handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True
        assert self.replication_stats["input_sets"]["success"] == 1
        # Verify no actual API calls were made
        self.mock_dest_client.post.assert_not_called()
        self.mock_dest_client.put.assert_not_called()

    def test_replicate_input_sets_missing_input_set_details(self):
        """Test input set replication handles missing input set details"""
        # Arrange
        pipeline_id = "test_pipeline"
        input_set_data = {
            "identifier": "test_input_set",
            "name": "Test Input Set"
        }
        
        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List input sets response
            {"data": {"content": [input_set_data]}},
            # Get input set details (fails)
            None
        ]
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[input_set_data]):
            # Act
            result = self.handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True  # Method continues despite individual failures
        assert self.replication_stats["input_sets"]["failed"] == 1
        assert self.replication_stats["input_sets"]["success"] == 0

    def test_replicate_input_sets_no_yaml_content(self):
        """Test input set replication handles input sets without YAML content"""
        # Arrange
        pipeline_id = "test_pipeline"
        input_set_data = {
            "identifier": "test_input_set",
            "name": "Test Input Set"
        }
        
        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List input sets response
            {"data": {"content": [input_set_data]}},
            # Get input set details (no YAML content)
            {"identifier": "test_input_set", "name": "Test Input Set"}
        ]
        
        # Mock destination client - input set doesn't exist
        self.mock_dest_client.get.return_value = None
        
        # Mock successful creation
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[input_set_data]):
            # Act
            result = self.handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True
        assert self.replication_stats["input_sets"]["success"] == 1
        # Verify YAML update was not called since no YAML content
        self.mock_dest_client.post.assert_called_once()

    def test_replicate_input_sets_multiple_input_sets(self):
        """Test input set replication with multiple input sets"""
        # Arrange
        pipeline_id = "test_pipeline"
        input_set_data = [
            {"identifier": "input_set_1", "name": "Input Set 1"},
            {"identifier": "input_set_2", "name": "Input Set 2"}
        ]
        
        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List input sets response
            {"data": {"content": input_set_data}},
            # Get input set 1 details
            {"input_set_yaml": "inputSet:\n  name: Input Set 1"},
            # Get input set 2 details
            {"input_set_yaml": "inputSet:\n  name: Input Set 2"}
        ]
        
        # Mock destination client - input sets don't exist
        self.mock_dest_client.get.return_value = None
        
        # Mock successful creation
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=input_set_data):
            with patch('src.inputset_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
                mock_yaml_update.return_value = "updated_yaml"
                with patch('src.inputset_handler.time.sleep'):  # Mock sleep to speed up test
                    # Act
                    result = self.handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True
        assert self.replication_stats["input_sets"]["success"] == 2
        assert self.replication_stats["input_sets"]["failed"] == 0
        assert self.mock_dest_client.post.call_count == 2

    def test_replicate_input_sets_non_dict_details(self):
        """Test input set replication handles non-dict input set details"""
        # Arrange
        pipeline_id = "test_pipeline"
        input_set_data = {
            "identifier": "test_input_set",
            "name": "Test Input Set"
        }
        
        # Mock API responses
        self.mock_source_client.get.side_effect = [
            # List input sets response
            {"data": {"content": [input_set_data]}},
            # Get input set details (non-dict response)
            "invalid_response"
        ]
        
        # Mock destination client - input set doesn't exist
        self.mock_dest_client.get.return_value = None
        
        # Mock successful creation
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[input_set_data]):
            # Act
            result = self.handler.replicate_input_sets(pipeline_id)
        
        # Assert
        assert result is True
        assert self.replication_stats["input_sets"]["success"] == 1
        # Verify post was called with None json_data
        self.mock_dest_client.post.assert_called_once()
        call_args = self.mock_dest_client.post.call_args
        assert call_args[1]['json'] is None
