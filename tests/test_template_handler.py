"""
Comprehensive unit tests for TemplateHandler

Tests template replication functionality with proper mocking and AAA methodology.
"""

from unittest.mock import Mock, patch

from src.template_handler import TemplateHandler
from src.api_client import HarnessAPIClient
from src.yaml_utils import YAMLUtils


class TestTemplateHandler:
    """Unit tests for TemplateHandler class"""

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
            "templates": {"success": 0, "failed": 0, "skipped": 0}
        }
        
        # Create handler
        self.handler = TemplateHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )

    def test_check_template_exists_template_found(self):
        """Test check_template_exists returns True when template exists"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1"
        self.mock_dest_client.get.return_value = {"identifier": template_ref}
        
        # Act
        result = self.handler.check_template_exists(template_ref, version_label)
        
        # Assert
        assert result is True
        self.mock_dest_client.get.assert_called_once()

    def test_check_template_exists_template_not_found(self):
        """Test check_template_exists returns False when template doesn't exist"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1"
        self.mock_dest_client.get.return_value = None
        
        # Act
        result = self.handler.check_template_exists(template_ref, version_label)
        
        # Assert
        assert result is False
        self.mock_dest_client.get.assert_called_once()

    def test_check_template_exists_no_version(self):
        """Test check_template_exists without version label"""
        # Arrange
        template_ref = "my-template"
        self.mock_dest_client.get.return_value = {"identifier": template_ref}
        
        # Act
        result = self.handler.check_template_exists(template_ref)
        
        # Assert
        assert result is True
        # Verify endpoint was built without sub_resource
        call_args = self.mock_dest_client.get.call_args[0][0]
        assert "versions" not in call_args

    def test_replicate_template_successful(self):
        """Test successful template replication"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1"
        template_data = {
            "template": {
                "yaml": "template:\n  name: My Template\n  orgIdentifier: source_org\n  projectIdentifier: source_project"
            }
        }
        
        # Mock source client returns template data
        self.mock_source_client.get.return_value = template_data
        
        # Mock destination client successful creation
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        with patch('src.template_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = self.handler.replicate_template(template_ref, version_label)
        
        # Assert
        assert result is True
        assert self.replication_stats["templates"]["success"] == 1
        self.mock_source_client.get.assert_called_once()
        self.mock_dest_client.post.assert_called_once()

    def test_replicate_template_source_not_found(self):
        """Test template replication when source template not found"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1"
        
        # Mock source client returns None
        self.mock_source_client.get.return_value = None
        
        # Act
        result = self.handler.replicate_template(template_ref, version_label)
        
        # Assert
        assert result is False
        assert self.replication_stats["templates"]["failed"] == 1
        self.mock_dest_client.post.assert_not_called()

    def test_replicate_template_creation_fails(self):
        """Test template replication when destination creation fails"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1"
        template_data = {
            "template": {
                "yaml": "template:\n  name: My Template"
            }
        }
        
        # Mock source client returns template data
        self.mock_source_client.get.return_value = template_data
        
        # Mock destination client failed creation
        self.mock_dest_client.post.return_value = None
        
        with patch('src.template_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = self.handler.replicate_template(template_ref, version_label)
        
        # Assert
        assert result is False
        assert self.replication_stats["templates"]["failed"] == 1

    def test_replicate_template_dry_run_mode(self):
        """Test template replication in dry run mode"""
        # Arrange
        self.config["dry_run"] = True
        handler = TemplateHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        template_ref = "my-template"
        version_label = "v1"
        template_data = {
            "template": {
                "yaml": "template:\n  name: My Template"
            }
        }
        
        # Mock source client returns template data
        self.mock_source_client.get.return_value = template_data
        
        with patch('src.template_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = handler.replicate_template(template_ref, version_label)
        
        # Assert
        assert result is True
        assert self.replication_stats["templates"]["success"] == 1
        # Verify no actual API call was made
        self.mock_dest_client.post.assert_not_called()

    def test_replicate_template_no_yaml_content(self):
        """Test template replication with template data without YAML content"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1"
        template_data = {
            "identifier": template_ref,
            "name": "My Template"
        }
        
        # Mock source client returns template data without YAML
        self.mock_source_client.get.return_value = template_data
        
        # Mock destination client successful creation
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Act
        result = self.handler.replicate_template(template_ref, version_label)
        
        # Assert
        assert result is False  # Should fail when template has no YAML content
        assert self.replication_stats["templates"]["failed"] == 1
        # Verify no API call was made since template has no YAML
        self.mock_dest_client.post.assert_not_called()

    def test_extract_template_refs_with_templates(self):
        """Test extract_template_refs finds template references in YAML"""
        # Arrange
        yaml_content = """
pipeline:
  name: Test Pipeline
  template:
    templateRef: my-template
    versionLabel: v1
  stages:
    - stage:
        template:
          templateRef: stage-template
          versionLabel: v2
"""
        
        with patch('src.template_handler.YAMLUtils.extract_template_refs') as mock_extract:
            mock_extract.return_value = [("my-template", "v1"), ("stage-template", "v2")]
            
            # Act
            result = YAMLUtils.extract_template_refs(yaml_content)
        
        # Assert
        assert result == [("my-template", "v1"), ("stage-template", "v2")]
        mock_extract.assert_called_once_with(yaml_content)

    def test_extract_template_refs_no_templates(self):
        """Test extract_template_refs with YAML containing no templates"""
        # Arrange
        yaml_content = """
pipeline:
  name: Test Pipeline
  stages:
    - stage:
        name: Test Stage
"""
        
        with patch('src.template_handler.YAMLUtils.extract_template_refs') as mock_extract:
            mock_extract.return_value = []
            
            # Act
            result = YAMLUtils.extract_template_refs(yaml_content)
        
        # Assert
        assert result == []
        mock_extract.assert_called_once_with(yaml_content)

    def test_handle_missing_templates_all_exist(self):
        """Test handle_missing_templates when all templates exist"""
        # Arrange
        template_refs = [("template1", "v1"), ("template2", "v2")]
        pipeline_name = "Test Pipeline"
        
        # Mock all templates exist
        self.mock_dest_client.get.return_value = {"identifier": "template"}
        
        # Act
        result = self.handler.handle_missing_templates(template_refs, pipeline_name)
        
        # Assert
        assert result is True
        assert self.mock_dest_client.get.call_count == 2

    def test_handle_missing_templates_some_missing_replicated(self):
        """Test handle_missing_templates when some templates are missing but can be replicated"""
        # Arrange
        template_refs = [("template1", "v1"), ("template2", "v2")]
        pipeline_name = "Test Pipeline"
        
        # Mock first template exists, second doesn't
        self.mock_dest_client.get.side_effect = [
            {"identifier": "template1"},  # First template exists
            None  # Second template doesn't exist
        ]
        
        # Mock source template data for replication
        self.mock_source_client.get.return_value = {
            "template": {
                "yaml": "template:\n  name: Template 2"
            }
        }
        
        # Mock successful replication
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        with patch('src.template_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            with patch('src.template_handler.time.sleep'):  # Mock sleep to speed up test
                # Act
                result = self.handler.handle_missing_templates(template_refs, pipeline_name)
        
        # Assert
        assert result is True
        assert self.replication_stats["templates"]["success"] == 1

    def test_handle_missing_templates_replication_fails(self):
        """Test handle_missing_templates when template replication fails"""
        # Arrange
        template_refs = [("template1", "v1")]
        pipeline_name = "Test Pipeline"
        
        # Mock template doesn't exist
        self.mock_dest_client.get.return_value = None
        
        # Mock source template not found
        self.mock_source_client.get.return_value = None
        
        # Act
        result = self.handler.handle_missing_templates(template_refs, pipeline_name)
        
        # Assert
        assert result is True  # handle_missing_templates always returns True
        assert self.replication_stats["templates"]["failed"] == 1

    def test_handle_missing_templates_empty_list(self):
        """Test handle_missing_templates with empty template list"""
        # Arrange
        template_refs = []
        pipeline_name = "Test Pipeline"
        
        # Act
        result = self.handler.handle_missing_templates(template_refs, pipeline_name)
        
        # Assert
        assert result is True
        self.mock_dest_client.get.assert_not_called()

    def test_handle_missing_templates_skip_templates_option(self):
        """Test handle_missing_templates with skip_templates option"""
        # Arrange
        self.config["options"]["skip_templates"] = True
        handler = TemplateHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        template_refs = [("template1", "v1")]
        pipeline_name = "Test Pipeline"
        
        # Act
        result = handler.handle_missing_templates(template_refs, pipeline_name)
        
        # Assert
        assert result is True
        # Should check if templates exist but not replicate them
        self.mock_dest_client.get.assert_called_once()
        # Should not replicate templates (no source client calls)
        self.mock_source_client.get.assert_not_called()

    def test_replicate_template_with_no_version_label(self):
        """Test template replication without version label"""
        # Arrange
        template_ref = "my-template"
        template_data = {
            "template": {
                "yaml": "template:\n  name: My Template"
            }
        }
        
        # Mock source client returns template data
        self.mock_source_client.get.return_value = template_data
        
        # Mock destination client successful creation
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        with patch('src.template_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            
            # Act
            result = self.handler.replicate_template(template_ref)
        
        # Assert
        assert result is True
        assert self.replication_stats["templates"]["success"] == 1
        # Verify endpoint was built without sub_resource
        source_call_args = self.mock_source_client.get.call_args[0][0]
        assert "versions" not in source_call_args

    def test_handle_missing_templates_mixed_results(self):
        """Test handle_missing_templates with mixed success and failure"""
        # Arrange
        template_refs = [("template1", "v1"), ("template2", "v2"), ("template3", "v3")]
        pipeline_name = "Test Pipeline"
        
        # Mock first template exists, second can be replicated, third fails
        self.mock_dest_client.get.side_effect = [
            {"identifier": "template1"},  # First exists
            None,  # Second doesn't exist
            None   # Third doesn't exist
        ]
        
        # Mock source responses for replication attempts
        self.mock_source_client.get.side_effect = [
            {"template": {"yaml": "template:\n  name: Template 2"}},  # Second template found
            None  # Third template not found in source
        ]
        
        # Mock successful creation for second template
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        with patch('src.template_handler.YAMLUtils.update_identifiers') as mock_yaml_update:
            mock_yaml_update.return_value = "updated_yaml"
            with patch('src.template_handler.time.sleep'):  # Mock sleep to speed up test
                # Act
                result = self.handler.handle_missing_templates(template_refs, pipeline_name)
        
        # Assert
        assert result is True  # handle_missing_templates always returns True
        assert self.replication_stats["templates"]["success"] == 1  # Second template succeeded
        assert self.replication_stats["templates"]["failed"] == 1   # Third template failed

    def test_replicate_template_non_dict_data(self):
        """Test template replication with non-dict template data"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1"
        
        # Mock source client returns non-dict data
        self.mock_source_client.get.return_value = "invalid_data"
        
        # Mock destination client successful creation
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Act
        result = self.handler.replicate_template(template_ref, version_label)
        
        # Assert
        assert result is False  # Should fail when template data is not a dict
        assert self.replication_stats["templates"]["failed"] == 1
        # Verify no API call was made since data is invalid
        self.mock_dest_client.post.assert_not_called()
