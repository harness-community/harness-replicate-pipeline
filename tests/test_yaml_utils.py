"""
Comprehensive unit tests for YAMLUtils

Tests YAML manipulation utilities with proper mocking and AAA methodology.
"""

from unittest.mock import patch
import yaml

from src.yaml_utils import YAMLUtils


class TestYAMLUtils:
    """Unit tests for YAMLUtils class"""

    def test_update_identifiers_basic_yaml(self):
        """Test update_identifiers with basic YAML structure"""
        # Arrange
        yaml_content = """
pipeline:
  name: Test Pipeline
  orgIdentifier: old_org
  projectIdentifier: old_project
"""
        dest_org = "new_org"
        dest_project = "new_project"
        
        # Act
        result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project, "pipeline")
        
        # Assert
        data = yaml.safe_load(result)
        assert data["pipeline"]["orgIdentifier"] == dest_org
        assert data["pipeline"]["projectIdentifier"] == dest_project
        assert data["pipeline"]["name"] == "Test Pipeline"

    def test_update_identifiers_with_wrapper_key(self):
        """Test update_identifiers with wrapper key"""
        # Arrange
        yaml_content = """
inputSet:
  name: Test Input Set
  orgIdentifier: old_org
  projectIdentifier: old_project
"""
        dest_org = "new_org"
        dest_project = "new_project"
        wrapper_key = "inputSet"
        
        # Act
        result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project, wrapper_key)
        
        # Assert
        data = yaml.safe_load(result)
        assert data["inputSet"]["orgIdentifier"] == dest_org
        assert data["inputSet"]["projectIdentifier"] == dest_project
        assert data["inputSet"]["name"] == "Test Input Set"

    def test_update_identifiers_no_wrapper_key(self):
        """Test update_identifiers without wrapper key (root level)"""
        # Arrange
        yaml_content = """
name: Test Template
orgIdentifier: old_org
projectIdentifier: old_project
"""
        dest_org = "new_org"
        dest_project = "new_project"
        
        # Act
        result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project)
        
        # Assert
        data = yaml.safe_load(result)
        assert data["orgIdentifier"] == dest_org
        assert data["projectIdentifier"] == dest_project
        assert data["name"] == "Test Template"

    def test_update_identifiers_invalid_yaml_fallback(self):
        """Test update_identifiers falls back to regex replacement for invalid YAML"""
        # Arrange
        yaml_content = """
invalid: yaml: content: [
  orgIdentifier: old_org
  projectIdentifier: old_project
"""
        dest_org = "new_org"
        dest_project = "new_project"
        
        # Act
        result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project)
        
        # Assert
        assert f'orgIdentifier: "{dest_org}"' in result
        assert f'projectIdentifier: "{dest_project}"' in result

    def test_update_identifiers_regex_fallback_quoted_values(self):
        """Test update_identifiers regex fallback with quoted values"""
        # Arrange
        yaml_content = """
pipeline:
  orgIdentifier: "old_org"
  projectIdentifier: 'old_project'
"""
        dest_org = "new_org"
        dest_project = "new_project"
        
        with patch('src.yaml_utils.yaml.safe_load', side_effect=yaml.YAMLError("Parse error")):
            # Act
            result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project)
        
        # Assert
        assert f'orgIdentifier: "{dest_org}"' in result
        assert f'projectIdentifier: "{dest_project}"' in result

    def test_update_identifiers_missing_wrapper_key(self):
        """Test update_identifiers with non-existent wrapper key"""
        # Arrange
        yaml_content = """
pipeline:
  name: Test Pipeline
  orgIdentifier: old_org
  projectIdentifier: old_project
"""
        dest_org = "new_org"
        dest_project = "new_project"
        wrapper_key = "nonexistent"
        
        # Act
        result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project, wrapper_key)
        
        # Assert
        data = yaml.safe_load(result)
        # Should update at root level when wrapper key doesn't exist
        assert data["orgIdentifier"] == dest_org
        assert data["projectIdentifier"] == dest_project

    def test_extract_template_refs_single_template(self):
        """Test extract_template_refs with single template reference"""
        # Arrange
        yaml_content = """
pipeline:
  name: Test Pipeline
  template:
    templateRef: my-template
    versionLabel: v1
"""
        
        # Act
        result = YAMLUtils.extract_template_refs(yaml_content)
        
        # Assert
        assert result == [("my-template", "v1")]

    def test_extract_template_refs_multiple_templates(self):
        """Test extract_template_refs with multiple template references"""
        # Arrange
        yaml_content = """
pipeline:
  name: Test Pipeline
  template:
    templateRef: pipeline-template
    versionLabel: v1
  stages:
    - stage:
        template:
          templateRef: stage-template
          versionLabel: v2
    - stage:
        template:
          templateRef: another-template
"""
        
        # Act
        result = YAMLUtils.extract_template_refs(yaml_content)
        
        # Assert
        expected = [
            ("pipeline-template", "v1"),
            ("stage-template", "v2"),
            ("another-template", None)
        ]
        assert result == expected

    def test_extract_template_refs_nested_templates(self):
        """Test extract_template_refs with deeply nested template references"""
        # Arrange
        yaml_content = """
pipeline:
  stages:
    - stage:
        spec:
          execution:
            steps:
              - step:
                  template:
                    templateRef: step-template
                    versionLabel: v3
"""
        
        # Act
        result = YAMLUtils.extract_template_refs(yaml_content)
        
        # Assert
        assert result == [("step-template", "v3")]

    def test_extract_template_refs_no_templates(self):
        """Test extract_template_refs with YAML containing no templates"""
        # Arrange
        yaml_content = """
pipeline:
  name: Test Pipeline
  stages:
    - stage:
        name: Test Stage
        spec:
          execution:
            steps:
              - step:
                  name: Test Step
"""
        
        # Act
        result = YAMLUtils.extract_template_refs(yaml_content)
        
        # Assert
        assert result == []

    def test_extract_template_refs_invalid_yaml(self):
        """Test extract_template_refs with invalid YAML"""
        # Arrange
        yaml_content = """
invalid: yaml: content: [
  template:
    templateRef: my-template
"""
        
        # Act
        result = YAMLUtils.extract_template_refs(yaml_content)
        
        # Assert
        assert result == []

    def test_extract_template_refs_template_in_list(self):
        """Test extract_template_refs with templates in list structures"""
        # Arrange
        yaml_content = """
pipeline:
  stages:
    - stage:
        template:
          templateRef: stage-template-1
          versionLabel: v1
    - stage:
        template:
          templateRef: stage-template-2
          versionLabel: v2
"""
        
        # Act
        result = YAMLUtils.extract_template_refs(yaml_content)
        
        # Assert
        expected = [
            ("stage-template-1", "v1"),
            ("stage-template-2", "v2")
        ]
        assert result == expected

    def test_set_template_version_with_version(self):
        """Test set_template_version with specific version label"""
        # Arrange
        yaml_content = """
template:
  name: Test Template
  versionLabel: old_version
"""
        version_label = "v2.0"
        
        # Act
        result = YAMLUtils.set_template_version(yaml_content, version_label)
        
        # Assert
        data = yaml.safe_load(result)
        assert data["template"]["versionLabel"] == version_label
        assert data["template"]["name"] == "Test Template"

    def test_set_template_version_default_stable(self):
        """Test set_template_version with default stable version"""
        # Arrange
        yaml_content = """
template:
  name: Test Template
"""
        
        # Act
        result = YAMLUtils.set_template_version(yaml_content)
        
        # Assert
        data = yaml.safe_load(result)
        assert data["template"]["versionLabel"] == "stable"
        assert data["template"]["name"] == "Test Template"

    def test_set_template_version_no_template_key(self):
        """Test set_template_version with YAML without template key"""
        # Arrange
        yaml_content = """
name: Test Template
identifier: test-template
"""
        
        # Act
        result = YAMLUtils.set_template_version(yaml_content, "v1")
        
        # Assert
        data = yaml.safe_load(result)
        # Should not add versionLabel if no template key exists
        assert "versionLabel" not in data
        assert data["name"] == "Test Template"

    def test_set_template_version_invalid_yaml(self):
        """Test set_template_version with invalid YAML returns original"""
        # Arrange
        yaml_content = """
invalid: yaml: content: [
  template:
    name: Test Template
"""
        
        # Act
        result = YAMLUtils.set_template_version(yaml_content, "v1")
        
        # Assert
        assert result == yaml_content  # Should return original content

    def test_update_identifiers_empty_yaml(self):
        """Test update_identifiers with empty YAML"""
        # Arrange
        yaml_content = ""
        dest_org = "new_org"
        dest_project = "new_project"
        
        # Act
        result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project)
        
        # Assert
        # Should fall back to regex replacement for empty content
        # Empty content will result in empty string after regex replacement
        assert result == ""

    def test_update_identifiers_preserves_other_fields(self):
        """Test update_identifiers preserves all other fields"""
        # Arrange
        yaml_content = """
pipeline:
  name: Test Pipeline
  identifier: test-pipeline
  orgIdentifier: old_org
  projectIdentifier: old_project
  description: This is a test pipeline
  tags:
    env: test
    team: engineering
"""
        dest_org = "new_org"
        dest_project = "new_project"
        
        # Act
        result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project, "pipeline")
        
        # Assert
        data = yaml.safe_load(result)
        pipeline = data["pipeline"]
        assert pipeline["orgIdentifier"] == dest_org
        assert pipeline["projectIdentifier"] == dest_project
        assert pipeline["name"] == "Test Pipeline"
        assert pipeline["identifier"] == "test-pipeline"
        assert pipeline["description"] == "This is a test pipeline"
        assert pipeline["tags"]["env"] == "test"
        assert pipeline["tags"]["team"] == "engineering"

    def test_extract_template_refs_complex_structure(self):
        """Test extract_template_refs with complex nested structure"""
        # Arrange
        yaml_content = """
pipeline:
  template:
    templateRef: main-template
    versionLabel: v1
  stages:
    - stage:
        name: Build
        template:
          templateRef: build-template
          versionLabel: v2
        spec:
          execution:
            steps:
              - step:
                  template:
                    templateRef: step-template
              - parallel:
                  - step:
                      template:
                        templateRef: parallel-step-1
                        versionLabel: latest
                  - step:
                      template:
                        templateRef: parallel-step-2
                        versionLabel: v3
"""
        
        # Act
        result = YAMLUtils.extract_template_refs(yaml_content)
        
        # Assert
        expected = [
            ("main-template", "v1"),
            ("build-template", "v2"),
            ("step-template", None),
            ("parallel-step-1", "latest"),
            ("parallel-step-2", "v3")
        ]
        assert result == expected

    def test_update_identifiers_type_error_fallback(self):
        """Test update_identifiers handles TypeError and falls back to regex"""
        # Arrange
        yaml_content = """
pipeline:
  orgIdentifier: old_org
  projectIdentifier: old_project
"""
        dest_org = "new_org"
        dest_project = "new_project"
        
        with patch('src.yaml_utils.yaml.safe_load', side_effect=TypeError("Type error")):
            # Act
            result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project)
        
        # Assert
        assert f'orgIdentifier: "{dest_org}"' in result
        assert f'projectIdentifier: "{dest_project}"' in result

    def test_update_identifiers_key_error_fallback(self):
        """Test update_identifiers handles KeyError and falls back to regex"""
        # Arrange
        yaml_content = """
pipeline:
  orgIdentifier: old_org
  projectIdentifier: old_project
"""
        dest_org = "new_org"
        dest_project = "new_project"
        
        # Mock yaml.safe_load to return data that causes KeyError
        with patch('src.yaml_utils.yaml.safe_load', return_value={}):
            # Act
            result = YAMLUtils.update_identifiers(yaml_content, dest_org, dest_project)
        
        # Assert
        assert f'orgIdentifier: "{dest_org}"' in result
        assert f'projectIdentifier: "{dest_project}"' in result
