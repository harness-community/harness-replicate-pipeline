"""
Comprehensive unit tests for PipelineHandler

Tests pipeline replication functionality with proper mocking and AAA methodology.
"""

from unittest.mock import Mock, patch

from src.pipeline_handler import PipelineHandler
from src.api_client import HarnessAPIClient


class TestPipelineHandler:
    """Unit tests for PipelineHandler class"""

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
                "update_existing": False,
                "skip_input_sets": False,
                "skip_triggers": False,
                "skip_templates": False
            },
            "pipelines": [
                {"identifier": "pipeline1", "name": "Pipeline 1"}
            ],
            "dry_run": False,
            "non_interactive": True
        }
        
        # Create mock clients
        self.mock_source_client = Mock(spec=HarnessAPIClient)
        self.mock_dest_client = Mock(spec=HarnessAPIClient)
        
        # Create replication stats
        self.replication_stats = {
            "pipelines": {"success": 0, "failed": 0, "skipped": 0},
            "input_sets": {"success": 0, "failed": 0, "skipped": 0},
            "triggers": {"success": 0, "failed": 0, "skipped": 0},
            "templates": {"success": 0, "failed": 0, "skipped": 0}
        }
        
        # Create handler
        self.handler = PipelineHandler(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )
        
        # Create mock handlers
        self.mock_template_handler = Mock()
        self.mock_inputset_handler = Mock()
        self.mock_trigger_handler = Mock()

    def test_replicate_pipelines_no_pipelines_configured(self):
        """Test replicate_pipelines when no pipelines are configured"""
        # Arrange
        self.config["pipelines"] = []
        handler = PipelineHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        # Act
        result = handler.replicate_pipelines(
            self.mock_template_handler,
            self.mock_inputset_handler,
            self.mock_trigger_handler
        )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["success"] == 0
        assert self.replication_stats["pipelines"]["failed"] == 0

    def test_replicate_pipelines_missing_identifier(self):
        """Test replicate_pipelines with pipeline missing identifier"""
        # Arrange
        self.config["pipelines"] = [{"name": "Pipeline Without ID"}]
        handler = PipelineHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        # Act
        result = handler.replicate_pipelines(
            self.mock_template_handler,
            self.mock_inputset_handler,
            self.mock_trigger_handler
        )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["failed"] == 1
        assert self.replication_stats["pipelines"]["success"] == 0

    def test_replicate_pipelines_pipeline_not_found(self):
        """Test replicate_pipelines when pipeline details cannot be retrieved"""
        # Arrange
        self.mock_source_client.get.return_value = None
        
        # Act
        result = self.handler.replicate_pipelines(
            self.mock_template_handler,
            self.mock_inputset_handler,
            self.mock_trigger_handler
        )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["failed"] == 1
        assert self.replication_stats["pipelines"]["success"] == 0

    def test_replicate_pipelines_successful_creation(self):
        """Test successful pipeline replication"""
        # Arrange
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Pipeline 1\n  orgIdentifier: source_org\n  projectIdentifier: source_project"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        self.mock_dest_client.get.return_value = None  # Pipeline doesn't exist
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Mock template handler
        self.mock_template_handler.extract_template_refs.return_value = []
        self.mock_template_handler.handle_missing_templates.return_value = True
        
        # Mock other handlers
        self.mock_inputset_handler.replicate_input_sets.return_value = True
        self.mock_trigger_handler.replicate_triggers.return_value = True
        
        with patch('src.pipeline_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = self.handler.replicate_pipelines(
                self.mock_template_handler, 
                self.mock_inputset_handler, 
                self.mock_trigger_handler
            )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["success"] == 1
        assert self.replication_stats["pipelines"]["failed"] == 0
        self.mock_dest_client.post.assert_called_once()
        self.mock_inputset_handler.replicate_input_sets.assert_called_once_with("pipeline1")
        self.mock_trigger_handler.replicate_triggers.assert_called_once_with("pipeline1")

    def test_replicate_pipelines_skip_existing(self):
        """Test pipeline replication skips existing pipelines when update_existing is False"""
        # Arrange
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Pipeline 1"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        self.mock_dest_client.get.return_value = {"identifier": "pipeline1"}  # Pipeline exists
        
        # Mock template handler
        self.mock_template_handler.extract_template_refs.return_value = []
        self.mock_template_handler.handle_missing_templates.return_value = True
        
        # Act
        result = self.handler.replicate_pipelines(
            self.mock_template_handler,
            self.mock_inputset_handler,
            self.mock_trigger_handler
        )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["skipped"] == 1
        assert self.replication_stats["pipelines"]["success"] == 0
        self.mock_dest_client.post.assert_not_called()
        self.mock_dest_client.put.assert_not_called()
        # Should not replicate input sets or triggers for skipped pipeline
        self.mock_inputset_handler.replicate_input_sets.assert_not_called()
        self.mock_trigger_handler.replicate_triggers.assert_not_called()

    def test_replicate_pipelines_update_existing(self):
        """Test pipeline replication updates existing pipelines when update_existing is True"""
        # Arrange
        self.config["options"]["update_existing"] = True
        handler = PipelineHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Pipeline 1"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        self.mock_dest_client.get.return_value = {"identifier": "pipeline1"}  # Pipeline exists
        self.mock_dest_client.put.return_value = {"status": "SUCCESS"}
        
        # Mock template handler
        self.mock_template_handler.extract_template_refs.return_value = []
        self.mock_template_handler.handle_missing_templates.return_value = True
        
        # Mock other handlers
        self.mock_inputset_handler.replicate_input_sets.return_value = True
        self.mock_trigger_handler.replicate_triggers.return_value = True
        
        with patch('src.pipeline_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = handler.replicate_pipelines(
                self.mock_template_handler, 
                self.mock_inputset_handler, 
                self.mock_trigger_handler
            )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["success"] == 1
        assert self.replication_stats["pipelines"]["failed"] == 0
        self.mock_dest_client.put.assert_called_once()
        self.mock_inputset_handler.replicate_input_sets.assert_called_once_with("pipeline1")
        self.mock_trigger_handler.replicate_triggers.assert_called_once_with("pipeline1")

    def test_replicate_pipelines_creation_fails(self):
        """Test pipeline replication handles creation failures"""
        # Arrange
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Pipeline 1"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        self.mock_dest_client.get.return_value = None  # Pipeline doesn't exist
        self.mock_dest_client.post.return_value = None  # Creation fails
        
        # Mock template handler
        self.mock_template_handler.extract_template_refs.return_value = []
        self.mock_template_handler.handle_missing_templates.return_value = True
        
        with patch('src.pipeline_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = self.handler.replicate_pipelines(
                self.mock_template_handler, 
                self.mock_inputset_handler, 
                self.mock_trigger_handler
            )
        
        # Assert
        assert result is True  # Method continues despite individual failures
        assert self.replication_stats["pipelines"]["failed"] == 1
        assert self.replication_stats["pipelines"]["success"] == 0
        # Should not replicate input sets or triggers for failed pipeline
        self.mock_inputset_handler.replicate_input_sets.assert_not_called()
        self.mock_trigger_handler.replicate_triggers.assert_not_called()

    def test_replicate_pipelines_dry_run_mode(self):
        """Test pipeline replication in dry run mode"""
        # Arrange
        self.config["dry_run"] = True
        handler = PipelineHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Pipeline 1"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        self.mock_dest_client.get.return_value = None  # Pipeline doesn't exist
        
        # Mock template handler
        self.mock_template_handler.extract_template_refs.return_value = []
        self.mock_template_handler.handle_missing_templates.return_value = True
        
        # Mock other handlers
        self.mock_inputset_handler.replicate_input_sets.return_value = True
        self.mock_trigger_handler.replicate_triggers.return_value = True
        
        with patch('src.pipeline_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = handler.replicate_pipelines(
                self.mock_template_handler, 
                self.mock_inputset_handler, 
                self.mock_trigger_handler
            )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["success"] == 1
        # Verify no actual API calls were made
        self.mock_dest_client.post.assert_not_called()
        self.mock_dest_client.put.assert_not_called()
        # Should still replicate input sets and triggers in dry run
        self.mock_inputset_handler.replicate_input_sets.assert_called_once_with("pipeline1")
        self.mock_trigger_handler.replicate_triggers.assert_called_once_with("pipeline1")

    def test_replicate_pipelines_with_templates(self):
        """Test pipeline replication with template dependencies"""
        # Arrange
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Pipeline 1\n  template: my-template"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        self.mock_dest_client.get.return_value = None  # Pipeline doesn't exist
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Mock template handler with templates
        template_refs = [("my-template", "v1")]
        self.mock_template_handler.extract_template_refs.return_value = template_refs
        self.mock_template_handler.handle_missing_templates.return_value = True
        
        # Mock other handlers
        self.mock_inputset_handler.replicate_input_sets.return_value = True
        self.mock_trigger_handler.replicate_triggers.return_value = True
        
        with patch('src.pipeline_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = self.handler.replicate_pipelines(
                self.mock_template_handler, 
                self.mock_inputset_handler, 
                self.mock_trigger_handler
            )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["success"] == 1
        self.mock_template_handler.extract_template_refs.assert_called_once()
        self.mock_template_handler.handle_missing_templates.assert_called_once_with(template_refs, "Pipeline 1")

    def test_replicate_pipelines_template_handling_fails(self):
        """Test pipeline replication when template handling fails"""
        # Arrange
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Pipeline 1\n  template: my-template"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        
        # Mock template handler failure
        template_refs = [("my-template", "v1")]
        self.mock_template_handler.extract_template_refs.return_value = template_refs
        self.mock_template_handler.handle_missing_templates.return_value = False  # Template handling fails
        
        with patch('src.pipeline_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = self.handler.replicate_pipelines(
                self.mock_template_handler, 
                self.mock_inputset_handler, 
                self.mock_trigger_handler
            )
        
        # Assert
        assert result is True  # Method continues despite template failures
        assert self.replication_stats["pipelines"]["failed"] == 1
        assert self.replication_stats["pipelines"]["success"] == 0
        # Should not attempt to create pipeline if template handling fails
        self.mock_dest_client.post.assert_not_called()

    def test_replicate_pipelines_skip_input_sets(self):
        """Test pipeline replication with skip_input_sets option"""
        # Arrange
        self.config["options"]["skip_input_sets"] = True
        handler = PipelineHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Pipeline 1"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        self.mock_dest_client.get.return_value = None  # Pipeline doesn't exist
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Mock template handler
        self.mock_template_handler.extract_template_refs.return_value = []
        self.mock_template_handler.handle_missing_templates.return_value = True
        
        # Mock trigger handler
        self.mock_trigger_handler.replicate_triggers.return_value = True
        
        with patch('src.pipeline_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = handler.replicate_pipelines(
                self.mock_template_handler, 
                self.mock_inputset_handler, 
                self.mock_trigger_handler
            )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["success"] == 1
        # Should not replicate input sets
        self.mock_inputset_handler.replicate_input_sets.assert_not_called()
        # Should still replicate triggers
        self.mock_trigger_handler.replicate_triggers.assert_called_once_with("pipeline1")

    def test_replicate_pipelines_skip_triggers(self):
        """Test pipeline replication with skip_triggers option"""
        # Arrange
        self.config["options"]["skip_triggers"] = True
        handler = PipelineHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Pipeline 1"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        self.mock_dest_client.get.return_value = None  # Pipeline doesn't exist
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Mock template handler
        self.mock_template_handler.extract_template_refs.return_value = []
        self.mock_template_handler.handle_missing_templates.return_value = True
        
        # Mock inputset handler
        self.mock_inputset_handler.replicate_input_sets.return_value = True
        
        with patch('src.pipeline_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = handler.replicate_pipelines(
                self.mock_template_handler, 
                self.mock_inputset_handler, 
                self.mock_trigger_handler
            )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["success"] == 1
        # Should still replicate input sets
        self.mock_inputset_handler.replicate_input_sets.assert_called_once_with("pipeline1")
        # Should not replicate triggers
        self.mock_trigger_handler.replicate_triggers.assert_not_called()

    def test_replicate_pipelines_multiple_pipelines(self):
        """Test pipeline replication with multiple pipelines"""
        # Arrange
        self.config["pipelines"] = [
            {"identifier": "pipeline1", "name": "Pipeline 1"},
            {"identifier": "pipeline2", "name": "Pipeline 2"}
        ]
        handler = PipelineHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        pipeline_details = {
            "pipeline_yaml": "pipeline:\n  name: Test Pipeline"
        }
        
        # Mock API responses
        self.mock_source_client.get.return_value = pipeline_details
        self.mock_dest_client.get.return_value = None  # Pipelines don't exist
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Mock template handler
        self.mock_template_handler.extract_template_refs.return_value = []
        self.mock_template_handler.handle_missing_templates.return_value = True
        
        # Mock other handlers
        self.mock_inputset_handler.replicate_input_sets.return_value = True
        self.mock_trigger_handler.replicate_triggers.return_value = True
        
        with patch('src.pipeline_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = handler.replicate_pipelines(
                self.mock_template_handler, 
                self.mock_inputset_handler, 
                self.mock_trigger_handler
            )
        
        # Assert
        assert result is True
        assert self.replication_stats["pipelines"]["success"] == 2
        assert self.mock_dest_client.post.call_count == 2
        assert self.mock_inputset_handler.replicate_input_sets.call_count == 2
        assert self.mock_trigger_handler.replicate_triggers.call_count == 2
