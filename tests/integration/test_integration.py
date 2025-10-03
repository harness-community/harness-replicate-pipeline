"""
Integration Tests for Harness Migration Toolkit

These tests create real resources in a destination Harness environment
and verify the migration functionality works end-to-end.

IMPORTANT: These tests create real resources but include automatic cleanup.
Test resources are automatically cleaned up after test completion using the
cleanup script.

Setup Requirements:
1. Either set INTEGRATION_TEST_DEST_URL and INTEGRATION_TEST_DEST_API_KEY
   environment variables
2. Or ensure config.json exists with destination configuration
3. Ensure the destination environment is accessible
4. Run tests with: pytest tests/integration/ -v -s

Note: Integration tests first try environment variables, then fall back to
config.json for destination configuration to provide flexibility in test setup.

Automatic Cleanup: Test resources are automatically cleaned up after tests
complete using tests/cleanup_integration_tests.sh script.
"""
import json
import os
import subprocess
import time

import pytest

from src.api_client import HarnessAPIClient
from src.replicator import HarnessReplicator


def _run_cleanup_script():
    """Run the integration test cleanup script"""
    try:
        script_path = os.path.join(os.path.dirname(__file__), "..", "cleanup_integration_tests.sh")
        result = subprocess.run([script_path], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("\n✅ Automatic cleanup completed successfully")
            if result.stdout:
                print("Cleanup output:")
                print(result.stdout)
        else:
            print(f"\n⚠️  Cleanup script failed with exit code {result.returncode}")
            if result.stderr:
                print("Error output:")
                print(result.stderr)
            if result.stdout:
                print("Standard output:")
                print(result.stdout)
    except subprocess.TimeoutExpired:
        print("\n⚠️  Cleanup script timed out after 5 minutes")
    except Exception as e:
        print(f"\n⚠️  Failed to run cleanup script: {e}")


def _get_destination_config():
    """Get destination configuration from environment variables or config.json"""
    # Try environment variables first
    dest_url = os.getenv("INTEGRATION_TEST_DEST_URL")
    dest_api_key = os.getenv("INTEGRATION_TEST_DEST_API_KEY")

    if dest_url and dest_api_key and _is_valid_config(dest_url, dest_api_key):
        return dest_url, dest_api_key

    # Fall back to config.json
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        dest_config = config.get("destination", {})
        dest_url = dest_config.get("base_url")
        dest_api_key = dest_config.get("api_key")

        if dest_url and dest_api_key and _is_valid_config(dest_url, dest_api_key):
            return dest_url, dest_api_key
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    return None, None


def _is_valid_config(url, api_key):
    """Check if the configuration values are valid (not placeholders)"""
    # Common placeholder values that should be treated as invalid
    invalid_api_keys = {"key", "your-api-key", "test-key", "placeholder", ""}
    invalid_urls = {"https://your-harness-url", ""}
    
    return (
        api_key not in invalid_api_keys and 
        url not in invalid_urls and
        len(api_key) > 10  # Real API keys are longer than placeholder values
    )


@pytest.mark.integration
class TestIntegrationMigration:
    """Integration tests for end-to-end migration functionality"""

    @pytest.fixture(autouse=True)
    def setup_integration_test(self):
        """Setup integration test environment"""
        self.dest_url, self.dest_api_key = _get_destination_config()
        
        if not self.dest_url or not self.dest_api_key:
            pytest.fail(
                "Integration tests require valid Harness configuration.\n"
                "Please set up config.json with valid destination credentials or use environment variables:\n"
                "  INTEGRATION_TEST_DEST_URL=https://app.harness.io\n"
                "  INTEGRATION_TEST_DEST_API_KEY=your-api-key"
            )

        # Test identifiers with timestamp to avoid conflicts
        # Use underscores instead of hyphens to match Harness identifier requirements
        timestamp = int(time.time())
        self.test_org = f"test_migration_org_{timestamp}"
        self.test_project = f"test_migration_project_{timestamp}"
        self.test_pipeline = f"test_migration_pipeline_{timestamp}"
        self.test_template = f"test_migration_template_{timestamp}"
        self.test_input_set = f"test_migration_inputset_{timestamp}"

        # Create destination client
        self.dest_client = HarnessAPIClient(self.dest_url, self.dest_api_key)

        # Test configuration
        self.config = {
            "source": {
                "base_url": "https://app.harness.io",  # Mock source
                "api_key": "mock-source-key",
                "org": "mock-source-org",
                "project": "mock-source-project"
            },
            "destination": {
                "base_url": self.dest_url,
                "api_key": self.dest_api_key,
                "org": self.test_org,
                "project": self.test_project
            },
            "options": {
                "migrate_input_sets": True,
                "skip_existing": False
            },
            "dry_run": False,
            "non_interactive": True
        }

        yield

        # Cleanup is automatic - see teardown_method()
        print(f"\n✅ Integration test setup complete. Test org: {self.test_org}")

    def test_create_organization(self):
        """Test creating a new organization"""
        # Arrange
        org_data = {
            "org": {
                "identifier": self.test_org,
                "name": self.test_org.replace("_", " ").title(),
                "description": "Integration test organization"
            }
        }

        # Act
        result = self.dest_client.post("/v1/orgs", json=org_data)

        # Assert
        assert result is not None, "Organization creation should succeed"

    def test_create_project(self):
        """Test creating a new project"""
        # Arrange - First create organization
        org_data = {
            "org": {
                "identifier": self.test_org,
                "name": self.test_org.replace("_", " ").title(),
                "description": "Integration test organization"
            }
        }
        self.dest_client.post("/v1/orgs", json=org_data)

        project_data = {
            "project": {
                "orgIdentifier": self.test_org,
                "identifier": self.test_project,
                "name": self.test_project.replace("_", " ").title(),
                "description": "Integration test project"
            }
        }

        # Act
        result = self.dest_client.post(f"/v1/orgs/{self.test_org}/projects", json=project_data)

        # Assert
        assert result is not None, "Project creation should succeed"

    def test_create_template(self):
        """Test creating a new template"""
        # Arrange - Create org and project first
        org_data = {"org": {"identifier": self.test_org, "name": self.test_org}}
        self.dest_client.post("/v1/orgs", json=org_data)

        project_data = {"project": {"orgIdentifier": self.test_org, "identifier": self.test_project, "name": self.test_project}}
        self.dest_client.post(f"/v1/orgs/{self.test_org}/projects", json=project_data)

        template_yaml = f"""
template:
  orgIdentifier: {self.test_org}
  projectIdentifier: {self.test_project}
  identifier: {self.test_template}
  name: {self.test_template}
  versionLabel: v1
  type: Step
  spec:
    type: ShellScript
    spec:
      shell: Bash
      onDelegate: true
      source:
        type: Inline
        spec:
          script: echo "Hello from template"
      executionTarget: {{}}
      environmentVariables: []
      outputVariables: []
"""

        template_data = {
            "template_yaml": template_yaml,
            "is_stable": True,
            "comments": "Integration test template"
        }

        # Act
        result = self.dest_client.post(f"/v1/orgs/{self.test_org}/projects/{self.test_project}/templates", json=template_data)

        # Assert
        assert result is not None, "Template creation should succeed"

        # Verify template exists
        templates = self.dest_client.get(f"/v1/orgs/{self.test_org}/projects/{self.test_project}/templates")
        templates_list = self.dest_client.normalize_response(templates)
        template_identifiers = [t.get("identifier") for t in templates_list]
        assert self.test_template in template_identifiers, f"Template {self.test_template} should exist"

    def test_create_pipeline(self):
        """Test creating a new pipeline (requires valid connectors)"""
        # This test is skipped because it requires valid connector references
        # In a real scenario, pipelines need proper infrastructure connectors
        pytest.skip("Pipeline creation requires valid connector references - skipping for integration test")

    def test_create_input_set(self):
        """Test creating a new input set (requires existing pipeline)"""
        # This test is skipped because it requires a valid pipeline to exist first
        # In a real scenario, input sets are created for existing pipelines
        pytest.skip("Input set creation requires an existing pipeline - skipping for integration test")

    def test_migrator_verify_prerequisites(self):
        """Test migrator's prerequisite verification (org/project creation)"""
        # Arrange
        migrator = HarnessReplicator(self.config)

        # Act
        result = migrator.prerequisite_handler.verify_prerequisites()

        # Assert
        assert result is True, "Prerequisites verification should succeed"

        # Verify organization exists
        orgs = self.dest_client.get("/v1/orgs")
        orgs_list = self.dest_client.normalize_response(orgs)
        org_identifiers = [org.get("identifier") for org in orgs_list]
        assert self.test_org in org_identifiers, f"Organization {self.test_org} should be created"

        # Verify project exists
        projects = self.dest_client.get(f"/v1/orgs/{self.test_org}/projects")
        projects_list = self.dest_client.normalize_response(projects)
        project_identifiers = [proj.get("identifier") for proj in projects_list]
        assert self.test_project in project_identifiers, f"Project {self.test_project} should be created"

    def test_migrator_verify_prerequisites_only(self):
        """Test migrator's prerequisite verification (org/project creation)"""
        # Arrange
        migrator = HarnessReplicator(self.config)

        # Act
        result = migrator.prerequisite_handler.verify_prerequisites()

        # Assert
        assert result is True, "Prerequisites verification should succeed"

    def test_end_to_end_migration_simulation(self):
        """Test a complete migration simulation (dry run)"""
        # Arrange - Create source-like data structure
        source_pipeline_data = {
            "identifier": self.test_pipeline,
            "name": self.test_pipeline,
            "pipeline_yaml": f"""
pipeline:
  orgIdentifier: source-org
  projectIdentifier: source-project
  identifier: {self.test_pipeline}
  name: {self.test_pipeline}
  stages:
    - stage:
        identifier: stage1
        name: stage1
        type: CI
        spec:
          execution:
            steps:
              - step:
                  identifier: step1
                  name: step1
                  type: Run
                  spec:
                    command: echo "Hello from migrated pipeline"
"""
        }

        # Create a mock source client that returns our test data
        class MockSourceClient:
            """Mock source client for testing"""

            def get(self, endpoint, **_kwargs):
                if "pipelines" in endpoint:
                    return [source_pipeline_data]
                return None

        # Update config to use mock source
        test_config = self.config.copy()
        test_config["dry_run"] = True  # Enable dry run for safety

        migrator = HarnessReplicator(test_config)
        migrator.source_client = MockSourceClient()

        # Act - This should work in dry run mode
        result = migrator.pipeline_handler.replicate_pipelines(
            migrator.template_handler, migrator.inputset_handler, migrator.trigger_handler)

        # Assert
        assert result is True, "Migration should succeed in dry run mode"

        # In dry run, no actual resources should be created
        # This test verifies the migration logic works without side effects

    def teardown_method(self):
        """Cleanup test resources after each test method"""
        print("\n🧹 Running automatic cleanup...")
        _run_cleanup_script()
