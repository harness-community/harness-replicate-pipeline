"""
Integration Tests for Trigger Migration

These tests verify the Harness API endpoints for triggers and test
trigger migration functionality end-to-end.

IMPORTANT: These tests are CREATE-ONLY and require manual cleanup.
Resources created by these tests must be manually deleted.

Setup Requirements:
1. Set INTEGRATION_TEST_DEST_URL and INTEGRATION_TEST_DEST_API_KEY environment variables
2. Or ensure config.json exists with destination configuration
3. Ensure the destination environment is accessible
4. Run tests with: pytest tests/test_trigger_integration.py -v -s

Cleanup Commands (run after tests):
# Delete test organization (this will delete all projects, pipelines, triggers, etc.)
curl -X DELETE "https://your-dest-url/v1/orgs/test-migration-org-{timestamp}" \
  -H "x-api-key: your-api-key"
"""
import json
import os
import time

import pytest

from src.api_client import HarnessAPIClient


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
class TestTriggerIntegration:
    """Integration tests for trigger API endpoints and functionality"""

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
        timestamp = int(time.time())
        self.test_org = f"test_migration_org_{timestamp}"
        self.test_project = f"test_migration_project_{timestamp}"
        self.test_pipeline = f"test_migration_pipeline_{timestamp}"
        self.test_input_set = f"test_migration_inputset_{timestamp}"
        self.test_trigger = f"test_migration_trigger_{timestamp}"

        # Create destination client
        self.dest_client = HarnessAPIClient(self.dest_url, self.dest_api_key)

        # Create test organization and project first
        self._create_test_org_and_project()

        print("\n=== Integration Test Setup ===")
        print(f"Test Org: {self.test_org}")
        print(f"Test Project: {self.test_project}")
        print(f"Test Pipeline: {self.test_pipeline}")
        print(f"Test Trigger: {self.test_trigger}")
        print(f"Destination URL: {self.dest_url}")
        print("=== Manual Cleanup Required ===")
        print("After tests, delete with:")
        print(f'curl -X DELETE "{self.dest_url}/v1/orgs/{self.test_org}" -H "x-api-key: {self.dest_api_key}"')
        print("================================\n")

    def _create_test_org_and_project(self):
        """Create test organization and project for trigger tests"""
        # Create organization
        org_data = {
            "org": {
                "identifier": self.test_org,
                "name": self.test_org.replace("_", " ").title(),
                "description": "Test organization for trigger integration tests"
            }
        }
        org_result = self.dest_client.post("/v1/orgs", json=org_data)
        assert org_result is not None, f"Failed to create test organization {self.test_org}"

        # Create project
        project_data = {
            "project": {
                "orgIdentifier": self.test_org,
                "identifier": self.test_project,
                "name": self.test_project.replace("_", " ").title(),
                "description": "Test project for trigger integration tests"
            }
        }
        project_result = self.dest_client.post(f"/v1/orgs/{self.test_org}/projects", json=project_data)
        assert project_result is not None, f"Failed to create test project {self.test_project}"

    def _create_test_pipeline(self):
        """Create a simple test pipeline for trigger testing"""
        pipeline_yaml = f"""
pipeline:
  orgIdentifier: {self.test_org}
  projectIdentifier: {self.test_project}
  identifier: {self.test_pipeline}
  name: {self.test_pipeline}
  stages:
    - stage:
        identifier: stage1
        name: Test Stage
        type: Custom
        spec:
          execution:
            steps:
              - step:
                  identifier: step1
                  name: Test Step
                  type: ShellScript
                  spec:
                    shell: Bash
                    source:
                      type: Inline
                      spec:
                        script: echo "Hello from trigger test pipeline"
                    environmentVariables: []
                    outputVariables: []
"""

        pipeline_data = {
            "pipeline_yaml": pipeline_yaml.strip(),
            "identifier": self.test_pipeline,
            "name": self.test_pipeline
        }

        result = self.dest_client.post(
            f"/v1/orgs/{self.test_org}/projects/{self.test_project}/pipelines",
            json=pipeline_data
        )
        assert result is not None, f"Failed to create test pipeline {self.test_pipeline}"
        return result

    def _create_test_input_set(self):
        """Create a simple test input set for trigger testing"""
        input_set_yaml = f"""
inputSet:
  orgIdentifier: {self.test_org}
  projectIdentifier: {self.test_project}
  pipeline:
    identifier: {self.test_pipeline}
    orgIdentifier: {self.test_org}
    projectIdentifier: {self.test_project}
  identifier: {self.test_input_set}
  name: {self.test_input_set}
"""

        input_set_data = {
            "input_set_yaml": input_set_yaml.strip(),
            "identifier": self.test_input_set,
            "name": self.test_input_set
        }

        # Try different potential input set creation endpoints
        potential_endpoints = [
            f"/v1/orgs/{self.test_org}/projects/{self.test_project}/input-sets",
            "/pipeline/api/inputSets",
        ]

        result = None
        for endpoint in potential_endpoints:
            try:
                result = self.dest_client.post(
                    endpoint,
                    params={"pipeline": self.test_pipeline},
                    json=input_set_data
                )
                if result is not None:
                    break
            except Exception:
                continue
        assert result is not None, f"Failed to create test input set {self.test_input_set}"
        return result

    def test_trigger_api_endpoints_discovery(self):
        """Test to discover and verify trigger API endpoints"""
        print("\n=== Testing Correct Trigger API Endpoints ===")

        # Test the discovered correct endpoints with required parameters
        correct_endpoints = [
            "/pipeline/api/triggers",
            "/gateway/pipeline/api/triggers",
        ]

        # Required parameters for trigger API
        params = {
            "orgIdentifier": self.test_org,
            "projectIdentifier": self.test_project,
            "targetIdentifier": self.test_pipeline  # Pipeline identifier
        }

        print(f"Using parameters: {params}")

        for endpoint in correct_endpoints:
            try:
                print(f"Testing GET {endpoint}")
                response = self.dest_client.get(endpoint, params=params)
                if response is not None:
                    print(f"✓ SUCCESS: {endpoint} returned: {type(response)}")
                    if isinstance(response, dict):
                        print(f"  Response keys: {list(response.keys())}")
                        if 'data' in response:
                            data = response['data']
                            if isinstance(data, list):
                                print(f"  Data contains {len(data)} trigger(s)")
                                if data:
                                    print(f"  First trigger keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
                            else:
                                print(f"  Data type: {type(data)}")
                        if 'status' in response:
                            print(f"  Status: {response['status']}")
                else:
                    print(f"✗ FAILED: {endpoint} returned None")
            except Exception as e:
                print(f"✗ ERROR: {endpoint} - {str(e)}")

        # Test without targetIdentifier to see if we can list all triggers in project
        print("\n=== Testing Project-Level Trigger Listing ===")
        project_params = {
            "orgIdentifier": self.test_org,
            "projectIdentifier": self.test_project
        }

        for endpoint in correct_endpoints:
            try:
                print(f"Testing GET {endpoint} (project-level)")
                response = self.dest_client.get(endpoint, params=project_params)
                if response is not None:
                    print(f"✓ SUCCESS: {endpoint} returned: {type(response)}")
                    if isinstance(response, dict) and 'data' in response:
                        data = response['data']
                        if isinstance(data, list):
                            print(f"  Found {len(data)} trigger(s) in project")
                else:
                    print(f"✗ FAILED: {endpoint} returned None")
            except Exception as e:
                print(f"✗ ERROR: {endpoint} - {str(e)}")

    def test_create_and_read_trigger(self):
        """Test creating a trigger and then reading it back"""
        # Create prerequisites
        self._create_test_pipeline()

        # Create a simple manual trigger (no external dependencies)
        trigger_yaml = f"""
trigger:
  orgIdentifier: {self.test_org}
  projectIdentifier: {self.test_project}
  pipelineIdentifier: {self.test_pipeline}
  identifier: {self.test_trigger}
  name: {self.test_trigger}
  type: Scheduled
  spec:
    type: Cron
    spec:
      expression: "0 0 * * *"
      timeZone: "America/New_York"
"""

        # Test different potential trigger creation endpoints
        potential_create_endpoints = [
            "/pipeline/api/triggers",
            f"/v1/orgs/{self.test_org}/projects/{self.test_project}/triggers",
        ]

        # Try both JSON and raw YAML approaches
        trigger_json_data = {
            "trigger_yaml": trigger_yaml.strip()
        }
        trigger_yaml_data = trigger_yaml.strip()

        created_trigger = None
        successful_endpoint = None

        print("\n=== Testing Trigger Creation ===")
        for endpoint in potential_create_endpoints:
            try:
                print(f"Testing POST {endpoint}")

                # Try JSON approach with pipeline parameter
                result = self.dest_client.post(
                    endpoint,
                    params={
                        "orgIdentifier": self.test_org,
                        "projectIdentifier": self.test_project,
                        "targetIdentifier": self.test_pipeline
                    },
                    json=trigger_json_data
                )

                if result is not None:
                    print(f"✓ SUCCESS: Created trigger via {endpoint} (JSON)")
                    created_trigger = result
                    successful_endpoint = endpoint
                    break
                else:
                    print(f"✗ FAILED: {endpoint} (JSON) returned None")

                    # Try YAML approach (like our actual code)
                    import requests
                    response = requests.post(
                        f"{self.dest_url}{endpoint}",
                        params={
                            "orgIdentifier": self.test_org,
                            "projectIdentifier": self.test_project,
                            "targetIdentifier": self.test_pipeline
                        },
                        data=trigger_yaml_data,
                        headers={
                            "Content-Type": "application/yaml",
                            "x-api-key": self.dest_api_key
                        }
                    )

                    if response.status_code in [200, 201]:
                        print(f"✓ SUCCESS: Created trigger via {endpoint} (YAML)")
                        created_trigger = response.json() if response.text else {"success": True}
                        successful_endpoint = endpoint
                        break
                    else:
                        print(f"✗ FAILED: {endpoint} (YAML) status {response.status_code}")

            except Exception as e:
                print(f"✗ ERROR: {endpoint} - {str(e)}")

        # If we successfully created a trigger, try to read it back
        if created_trigger and successful_endpoint:
            print("\n=== Testing Trigger Read ===")

            # Try to list triggers
            try:
                list_endpoint = successful_endpoint
                triggers_list = self.dest_client.get(
                    list_endpoint,
                    params={"pipeline": self.test_pipeline}
                )

                if triggers_list is not None:
                    print(f"✓ SUCCESS: Listed triggers via {list_endpoint}")
                    triggers = self.dest_client.normalize_response(triggers_list)
                    print(f"  Found {len(triggers)} trigger(s)")

                    # Look for our trigger
                    trigger_ids = [t.get("identifier") for t in triggers if isinstance(t, dict)]
                    if self.test_trigger in trigger_ids:
                        print(f"✓ SUCCESS: Found our trigger {self.test_trigger} in list")
                    else:
                        print(f"✗ WARNING: Our trigger {self.test_trigger} not found in list")
                        print(f"  Available triggers: {trigger_ids}")
                else:
                    print("✗ FAILED: Could not list triggers")

            except Exception as e:
                print(f"✗ ERROR listing triggers: {str(e)}")

            # Try to get specific trigger
            try:
                get_endpoint = f"{successful_endpoint}/{self.test_trigger}"
                specific_trigger = self.dest_client.get(
                    get_endpoint,
                    params={"pipeline": self.test_pipeline}
                )

                if specific_trigger is not None:
                    print(f"✓ SUCCESS: Retrieved specific trigger via {get_endpoint}")
                    if isinstance(specific_trigger, dict):
                        print(f"  Trigger keys: {list(specific_trigger.keys())}")
                else:
                    print("✗ FAILED: Could not retrieve specific trigger")

            except Exception as e:
                print(f"✗ ERROR retrieving specific trigger: {str(e)}")

        else:
            pytest.skip("Could not create trigger - skipping read tests")

    def test_trigger_list_without_pipeline(self):
        """Test listing all triggers in a project without pipeline filter"""
        # Create prerequisites
        self._create_test_pipeline()

        potential_endpoints = [
            f"/v1/orgs/{self.test_org}/projects/{self.test_project}/triggers",
            "/ng/api/triggers",
        ]

        print("\n=== Testing Trigger List (No Pipeline Filter) ===")
        for endpoint in potential_endpoints:
            try:
                print(f"Testing GET {endpoint}")
                response = self.dest_client.get(endpoint)
                if response is not None:
                    print(f"✓ SUCCESS: {endpoint} returned: {type(response)}")
                    triggers = self.dest_client.normalize_response(response)
                    print(f"  Found {len(triggers)} trigger(s)")
                else:
                    print(f"✗ FAILED: {endpoint} returned None")
            except Exception as e:
                print(f"✗ ERROR: {endpoint} - {str(e)}")

    def test_trigger_yaml_structure_validation(self):
        """Test different trigger YAML structures to understand the API expectations"""
        # Create prerequisites
        self._create_test_pipeline()

        # Test different trigger YAML structures
        trigger_structures = [
            {
                "name": "Simple Webhook Trigger",
                "yaml": f"""
trigger:
  orgIdentifier: {self.test_org}
  projectIdentifier: {self.test_project}
  pipelineIdentifier: {self.test_pipeline}
  identifier: {self.test_trigger}_simple
  name: Simple Test Trigger
  type: Webhook
  spec:
    type: Custom
    spec:
      payloadConditions: []
      headerConditions: []
"""
            },
            {
                "name": "Scheduled Trigger",
                "yaml": f"""
trigger:
  orgIdentifier: {self.test_org}
  projectIdentifier: {self.test_project}
  pipelineIdentifier: {self.test_pipeline}
  identifier: {self.test_trigger}_scheduled
  name: Scheduled Test Trigger
  type: Scheduled
  spec:
    type: Cron
    spec:
      expression: "0 0 * * *"
"""
            }
        ]

        print("\n=== Testing Trigger YAML Structures ===")

        for i, structure in enumerate(trigger_structures):
            print(f"\nTesting {structure['name']}:")

            trigger_data = {
                "trigger_yaml": structure["yaml"].strip()
            }

            # Try the most likely endpoint
            endpoint = f"/v1/orgs/{self.test_org}/projects/{self.test_project}/triggers"

            try:
                result = self.dest_client.post(
                    endpoint,
                    params={"pipeline": self.test_pipeline},
                    json=trigger_data
                )

                if result is not None:
                    print(f"✓ SUCCESS: {structure['name']} created successfully")
                else:
                    print(f"✗ FAILED: {structure['name']} creation failed")

            except Exception as e:
                print(f"✗ ERROR: {structure['name']} - {str(e)}")
