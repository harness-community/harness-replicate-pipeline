"""
Comprehensive unit tests for HarnessReplicator

Tests replication functionality with proper mocking and AAA methodology.
"""

from unittest.mock import patch
import yaml

from src.api_client import HarnessAPIClient
from src.replicator import HarnessReplicator


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
                "migrate_input_sets": True,
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
        migrator = HarnessMigrator(self.config)

        # Assert
        assert migrator.source_org == "source-org"
        assert migrator.source_project == "source-project"
        assert migrator.dest_org == "dest-org"
        assert migrator.dest_project == "dest-project"
        assert isinstance(migrator.source_client, HarnessAPIClient)
        assert isinstance(migrator.dest_client, HarnessAPIClient)
        assert migrator.migration_stats == {
            "pipelines": {"success": 0, "failed": 0, "skipped": 0},
            "input_sets": {"success": 0, "failed": 0, "skipped": 0},
            "templates": {"success": 0, "failed": 0, "skipped": 0},
            "triggers": {"success": 0, "failed": 0, "skipped": 0}
        }

    def test_get_option_returns_correct_value(self):
        """Test _get_option returns correct value from config"""
        # Arrange & Act
        result = self.migrator._get_option("migrate_input_sets", False)

        # Assert
        assert result is True

    def test_get_option_returns_default_when_missing(self):
        """Test _get_option returns default when option is missing"""
        # Arrange & Act
        result = self.migrator._get_option("nonexistent_option", "default_value")

        # Assert
        assert result == "default_value"

    def test_is_dry_run_returns_correct_value(self):
        """Test _is_dry_run returns correct value"""
        # Arrange
        self.config["dry_run"] = True

        # Act
        result = self.migrator._is_dry_run()

        # Assert
        assert result is True

    def test_is_interactive_returns_correct_value(self):
        """Test _is_interactive returns correct value"""
        # Arrange
        self.config["non_interactive"] = True

        # Act
        result = self.migrator._is_interactive()

        # Assert
        assert result is False

    def test_build_endpoint_basic(self):
        """Test _build_endpoint builds basic endpoint"""
        # Arrange & Act
        result = self.migrator._build_endpoint("pipelines")

        # Assert
        assert result == "/v1/pipelines"

    def test_build_endpoint_with_org(self):
        """Test _build_endpoint with organization"""
        # Arrange & Act
        result = self.migrator._build_endpoint("pipelines", org="test-org")

        # Assert
        assert result == "/v1/orgs/test-org/pipelines"

    def test_build_endpoint_with_org_and_project(self):
        """Test _build_endpoint with organization and project"""
        # Arrange & Act
        result = self.migrator._build_endpoint("pipelines", org="test-org", project="test-project")

        # Assert
        assert result == "/v1/orgs/test-org/projects/test-project/pipelines"

    def test_build_endpoint_with_resource_id(self):
        """Test _build_endpoint with resource ID"""
        # Arrange & Act
        result = self.migrator._build_endpoint("pipelines", org="test-org", project="test-project", resource_id="pipeline1")

        # Assert
        assert result == "/v1/orgs/test-org/projects/test-project/pipelines/pipeline1"

    def test_build_endpoint_with_sub_resource(self):
        """Test _build_endpoint with sub-resource"""
        # Arrange & Act
        result = self.migrator._build_endpoint("templates", org="test-org", project="test-project", resource_id="template1", sub_resource="versions/v1")

        # Assert
        assert result == "/v1/orgs/test-org/projects/test-project/templates/template1/versions/v1"

    def test_update_yaml_identifiers_success(self):
        """Test _update_yaml_identifiers updates identifiers successfully"""
        # Arrange
        yaml_content = """
        pipeline:
          orgIdentifier: source-org
          projectIdentifier: source-project
          name: test-pipeline
        """
        expected_org = "dest-org"
        expected_project = "dest-project"

        # Act
        result = self.migrator._update_yaml_identifiers(yaml_content, wrapper_key="pipeline")

        # Assert
        parsed = yaml.safe_load(result)
        assert parsed["pipeline"]["orgIdentifier"] == expected_org
        assert parsed["pipeline"]["projectIdentifier"] == expected_project

    def test_update_yaml_identifiers_without_wrapper_key(self):
        """Test _update_yaml_identifiers without wrapper key"""
        # Arrange
        yaml_content = """
        orgIdentifier: source-org
        projectIdentifier: source-project
        name: test-pipeline
        """

        # Act
        result = self.migrator._update_yaml_identifiers(yaml_content)

        # Assert
        parsed = yaml.safe_load(result)
        assert parsed["orgIdentifier"] == "dest-org"
        assert parsed["projectIdentifier"] == "dest-project"

    def test_update_yaml_identifiers_yaml_error_fallback(self):
        """Test _update_yaml_identifiers falls back to string replacement on YAML error"""
        # Arrange
        invalid_yaml = "invalid: yaml: content: [\norgIdentifier: source-org\nprojectIdentifier: source-project"

        # Act
        result = self.migrator._update_yaml_identifiers(invalid_yaml, wrapper_key="pipeline")

        # Assert
        # The fallback should still work with string replacement
        assert "orgIdentifier" in result
        assert "projectIdentifier" in result
        assert "dest-org" in result
        assert "dest-project" in result

    def test_extract_template_refs_finds_templates(self):
        """Test extract_template_refs finds template references"""
        # Arrange
        yaml_content = """
        pipeline:
          stages:
            - stage:
                template:
                  templateRef: my-template
                  versionLabel: v1.0
        """

        # Act
        result = self.migrator.extract_template_refs(yaml_content)

        # Assert
        assert len(result) == 1
        assert result[0] == ("my-template", "v1.0")

    def test_extract_template_refs_finds_multiple_templates(self):
        """Test extract_template_refs finds multiple template references"""
        # Arrange
        yaml_content = """
        pipeline:
          stages:
            - stage:
                template:
                  templateRef: template1
                  versionLabel: v1.0
            - stage:
                template:
                  templateRef: template2
                  versionLabel: v2.0
        """

        # Act
        result = self.migrator.extract_template_refs(yaml_content)

        # Assert
        assert len(result) == 2
        assert ("template1", "v1.0") in result
        assert ("template2", "v2.0") in result

    def test_extract_template_refs_handles_invalid_yaml(self):
        """Test extract_template_refs handles invalid YAML gracefully"""
        # Arrange
        invalid_yaml = "invalid: yaml: content: ["

        # Act
        result = self.migrator.extract_template_refs(invalid_yaml)

        # Assert
        assert not result

    def test_check_template_exists_true(self):
        """Test check_template_exists returns True when template exists"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1.0"
        mock_response = {"template": "data"}

        # Act
        with patch.object(self.migrator.dest_client, 'get', return_value=mock_response):
            result = self.migrator.check_template_exists(template_ref, version_label)

        # Assert
        assert result is True

    def test_check_template_exists_false(self):
        """Test check_template_exists returns False when template doesn't exist"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1.0"

        # Act
        with patch.object(self.migrator.dest_client, 'get', return_value=None):
            result = self.migrator.check_template_exists(template_ref, version_label)

        # Assert
        assert result is False

    def test_migrate_template_success(self):
        """Test migrate_template succeeds with real API response format"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1.0"
        # Use actual API response format that includes nested template.yaml
        template_data = {
            "template": {
                "yaml": """
template:
  orgIdentifier: source-org
  projectIdentifier: source-project
  identifier: my-template
  name: My Template
  versionLabel: v1.0
                """,
                "identifier": "my-template",
                "name": "My Template"
            },
            "inputs": []
        }

        # Act
        with patch.object(self.migrator.source_client, 'get', return_value=template_data):
            with patch.object(self.migrator.dest_client, 'post', return_value={"success": True}):
                result = self.migrator.migrate_template(template_ref, version_label)

        # Assert
        assert result is True
        assert self.migrator.migration_stats["templates"]["success"] == 1

    def test_migrate_template_failure(self):
        """Test migrate_template handles failure"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1.0"

        # Act
        with patch.object(self.migrator.source_client, 'get', return_value=None):
            result = self.migrator.migrate_template(template_ref, version_label)

        # Assert
        assert result is False
        assert self.migrator.migration_stats["templates"]["failed"] == 1

    def test_migrate_template_missing_yaml_content(self):
        """Test migrate_template fails when template has no YAML content"""
        # Arrange
        template_ref = "empty-template"
        version_label = "v1.0"
        # Simulate API response with template object but no yaml field
        template_data = {
            "template": {
                "identifier": "empty-template",
                "name": "Empty Template"
                # Missing "yaml" field - this should cause failure
            },
            "inputs": []
        }

        # Act
        with patch.object(self.migrator.source_client, 'get', return_value=template_data):
            result = self.migrator.migrate_template(template_ref, version_label)

        # Assert
        assert result is False
        assert self.migrator.migration_stats["templates"]["failed"] == 1

    def test_migrate_template_empty_yaml_content(self):
        """Test migrate_template fails when template has empty YAML content"""
        # Arrange
        template_ref = "empty-yaml-template"
        version_label = "v1.0"
        # Simulate API response with empty yaml field
        template_data = {
            "template": {
                "yaml": "",  # Empty YAML should cause failure
                "identifier": "empty-yaml-template",
                "name": "Empty YAML Template"
            },
            "inputs": []
        }

        # Act
        with patch.object(self.migrator.source_client, 'get', return_value=template_data):
            result = self.migrator.migrate_template(template_ref, version_label)

        # Assert
        assert result is False
        assert self.migrator.migration_stats["templates"]["failed"] == 1

    def test_migrate_template_dry_run(self):
        """Test migrate_template in dry run mode with real API response format"""
        # Arrange
        template_ref = "my-template"
        version_label = "v1.0"
        template_data = {
            "template": {
                "yaml": """
template:
  orgIdentifier: source-org
  projectIdentifier: source-project
  identifier: my-template
  name: My Template
  versionLabel: v1.0
                """,
                "identifier": "my-template",
                "name": "My Template"
            },
            "inputs": []
        }
        self.config["dry_run"] = True

        # Act
        with patch.object(self.migrator.source_client, 'get', return_value=template_data):
            result = self.migrator.migrate_template(template_ref, version_label)

        # Assert
        assert result is True
        assert self.migrator.migration_stats["templates"]["success"] == 1

    def test_verify_prerequisites_success(self):
        """Test verify_prerequisites succeeds"""
        # Arrange
        with patch.object(self.migrator, '_create_org_if_missing', return_value=True):
            with patch.object(self.migrator, '_create_project_if_missing', return_value=True):
                # Act
                result = self.migrator.verify_prerequisites()

        # Assert
        assert result is True

    def test_verify_prerequisites_org_creation_fails(self):
        """Test verify_prerequisites fails when org creation fails"""
        # Arrange
        with patch.object(self.migrator, '_create_org_if_missing', return_value=False):
            # Act
            result = self.migrator.verify_prerequisites()

        # Assert
        assert result is False

    def test_verify_prerequisites_project_creation_fails(self):
        """Test verify_prerequisites fails when project creation fails"""
        # Arrange
        with patch.object(self.migrator, '_create_org_if_missing', return_value=True):
            with patch.object(self.migrator, '_create_project_if_missing', return_value=False):
                # Act
                result = self.migrator.verify_prerequisites()

        # Assert
        assert result is False

    def test_create_org_if_missing_org_exists(self):
        """Test _create_org_if_missing when org already exists"""
        # Arrange
        orgs_response = [{"identifier": "dest-org", "name": "Dest Org"}]

        # Act
        with patch.object(self.migrator.dest_client, 'get', return_value=orgs_response):
            result = self.migrator._create_org_if_missing()

        # Assert
        assert result is True

    def test_create_org_if_missing_creates_org(self):
        """Test _create_org_if_missing creates org when it doesn't exist"""
        # Arrange
        orgs_response = [{"identifier": "other-org", "name": "Other Org"}]
        create_response = {"success": True}

        # Act
        with patch.object(self.migrator.dest_client, 'get', return_value=orgs_response):
            with patch.object(self.migrator.dest_client, 'post', return_value=create_response):
                result = self.migrator._create_org_if_missing()

        # Assert
        assert result is True

    def test_create_org_if_missing_creation_fails(self):
        """Test _create_org_if_missing handles creation failure"""
        # Arrange
        orgs_response = [{"identifier": "other-org", "name": "Other Org"}]
        # Mock both the initial check and the fallback check to return same response
        get_responses = [None, orgs_response]  # Direct GET fails, then list GET returns other orgs

        # Act
        with patch.object(self.migrator.dest_client, 'get', side_effect=get_responses):
            with patch.object(self.migrator.dest_client, 'post', return_value=None):
                result = self.migrator._create_org_if_missing()

        # Assert
        assert result is False

    def test_create_project_if_missing_project_exists(self):
        """Test _create_project_if_missing when project already exists"""
        # Arrange
        projects_response = [{"identifier": "dest-project", "name": "Dest Project"}]

        # Act
        with patch.object(self.migrator.dest_client, 'get', return_value=projects_response):
            result = self.migrator._create_project_if_missing()

        # Assert
        assert result is True

    def test_create_project_if_missing_creates_project(self):
        """Test _create_project_if_missing creates project when it doesn't exist"""
        # Arrange
        projects_response = [{"identifier": "other-project", "name": "Other Project"}]
        create_response = {"success": True}

        # Act
        with patch.object(self.migrator.dest_client, 'get', return_value=projects_response):
            with patch.object(self.migrator.dest_client, 'post', return_value=create_response):
                result = self.migrator._create_project_if_missing()

        # Assert
        assert result is True

    def test_create_project_if_missing_creation_fails(self):
        """Test _create_project_if_missing handles creation failure"""
        # Arrange
        projects_response = [{"identifier": "other-project", "name": "Other Project"}]
        # Mock both the initial check and the fallback check to return same response
        get_responses = [None, projects_response]  # Direct GET fails, then list GET returns other projects

        # Act
        with patch.object(self.migrator.dest_client, 'get', side_effect=get_responses):
            with patch.object(self.migrator.dest_client, 'post', return_value=None):
                result = self.migrator._create_project_if_missing()

        # Assert
        assert result is False

    def test_migrate_input_sets_no_input_sets(self):
        """Test migrate_input_sets when no input sets exist"""
        # Arrange
        pipeline_id = "pipeline1"

        # Act
        with patch.object(self.migrator.source_client, 'get', return_value=[]):
            result = self.migrator.migrate_input_sets(pipeline_id)

        # Assert
        assert result is True

    def test_migrate_input_sets_success(self):
        """Test migrate_input_sets succeeds"""
        # Arrange
        pipeline_id = "pipeline1"
        input_sets = [{"identifier": "input-set-1", "name": "Input Set 1"}]
        input_set_details = {
            "input_set_yaml": """
            inputSet:
              orgIdentifier: source-org
              projectIdentifier: source-project
              identifier: input-set-1
            """
        }

        # Act
        with patch.object(self.migrator.source_client, 'get', side_effect=[input_sets, input_set_details]):
            with patch.object(self.migrator.dest_client, 'post', return_value={"success": True}):
                result = self.migrator.migrate_input_sets(pipeline_id)

        # Assert
        assert result is True
        assert self.migrator.migration_stats["input_sets"]["success"] == 1

    def test_migrate_input_sets_dry_run(self):
        """Test migrate_input_sets in dry run mode"""
        # Arrange
        pipeline_id = "pipeline1"
        input_sets = [{"identifier": "input-set-1", "name": "Input Set 1"}]
        input_set_details = {
            "input_set_yaml": """
            inputSet:
              orgIdentifier: source-org
              projectIdentifier: source-project
              identifier: input-set-1
            """
        }
        self.config["dry_run"] = True

        # Act
        with patch.object(self.migrator.source_client, 'get', side_effect=[input_sets, input_set_details]):
            result = self.migrator.migrate_input_sets(pipeline_id)

        # Assert
        assert result is True
        assert self.migrator.migration_stats["input_sets"]["success"] == 1

    def test_migrate_pipelines_no_pipelines(self):
        """Test migrate_pipelines when no pipelines configured"""
        # Arrange
        self.config["pipelines"] = []

        # Act
        result = self.migrator.migrate_pipelines()

        # Assert
        assert result is True

    def test_migrate_pipelines_success(self):
        """Test migrate_pipelines succeeds"""
        # Arrange
        pipeline_details = {
            "pipeline_yaml": """
            pipeline:
              orgIdentifier: source-org
              projectIdentifier: source-project
              identifier: pipeline1
            """
        }

        # Act
        with patch.object(self.migrator.source_client, 'get', return_value=pipeline_details):
            with patch.object(self.migrator, '_create_or_update_pipeline', return_value=True):
                with patch.object(self.migrator, 'migrate_input_sets', return_value=True):
                    result = self.migrator.migrate_pipelines()

        # Assert
        assert result is True
        assert self.migrator.migration_stats["pipelines"]["success"] == 1

    def test_migrate_pipelines_pipeline_skipped(self):
        """Test migrate_pipelines when pipeline is skipped"""
        # Arrange
        pipeline_details = {"pipeline_yaml": "test yaml"}

        # Act
        with patch.object(self.migrator.source_client, 'get', return_value=pipeline_details):
            with patch.object(self.migrator, '_create_or_update_pipeline', return_value=False):
                result = self.migrator.migrate_pipelines()

        # Assert
        assert result is True
        assert self.migrator.migration_stats["pipelines"]["skipped"] == 1

    def test_migrate_pipelines_pipeline_failed(self):
        """Test migrate_pipelines when pipeline fails"""
        # Arrange
        pipeline_details = {"pipeline_yaml": "test yaml"}

        # Act
        with patch.object(self.migrator.source_client, 'get', return_value=pipeline_details):
            with patch.object(self.migrator, '_create_or_update_pipeline', return_value=None):
                result = self.migrator.migrate_pipelines()

        # Assert
        assert result is True
        assert self.migrator.migration_stats["pipelines"]["failed"] == 1

    def test_print_summary(self):
        """Test print_summary displays correct statistics"""
        # Arrange
        self.migrator.migration_stats = {
            "pipelines": {"success": 2, "failed": 1, "skipped": 0},
            "input_sets": {"success": 1, "failed": 0, "skipped": 1},
            "templates": {"success": 0, "failed": 0, "skipped": 2}
        }

        # Act
        with patch('src.harness_migration.migrator.logger') as mock_logger:
            self.migrator.print_summary()

        # Assert
        assert mock_logger.info.call_count >= 6  # At least 6 log calls (summary + stats)
