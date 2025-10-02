"""
Unit tests for BaseReplicator

Tests the base replicator functionality.
"""

from unittest.mock import Mock

from src.base_replicator import BaseReplicator
from src.api_client import HarnessAPIClient


class TestBaseReplicator:
    """Unit tests for BaseReplicator class"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.config = {
            "source": {
                "org": "source_org",
                "project": "source_project"
            },
            "destination": {
                "org": "dest_org",
                "project": "dest_project"
            },
            "dry_run": False,
            "non_interactive": False
        }
        
        # Create mock clients
        self.mock_source_client = Mock(spec=HarnessAPIClient)
        self.mock_dest_client = Mock(spec=HarnessAPIClient)
        
        # Create replication stats
        self.replication_stats = {}
        
        # Create base replicator
        self.base_replicator = BaseReplicator(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )

    def test_is_dry_run_true(self):
        """Test _is_dry_run returns True when dry_run is True"""
        # Arrange
        self.config["dry_run"] = True
        base_replicator = BaseReplicator(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )
        
        # Act
        result = base_replicator._is_dry_run()
        
        # Assert
        assert result is True

    def test_is_dry_run_false(self):
        """Test _is_dry_run returns False when dry_run is False"""
        # Arrange
        self.config["dry_run"] = False
        
        # Act
        result = self.base_replicator._is_dry_run()
        
        # Assert
        assert result is False

    def test_is_dry_run_default(self):
        """Test _is_dry_run returns False when dry_run is not set"""
        # Arrange
        config_without_dry_run = {
            "source": {"org": "source_org", "project": "source_project"},
            "destination": {"org": "dest_org", "project": "dest_project"}
        }
        base_replicator = BaseReplicator(
            config_without_dry_run,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )
        
        # Act
        result = base_replicator._is_dry_run()
        
        # Assert
        assert result is False

    def test_is_interactive_true(self):
        """Test _is_interactive returns True when non_interactive is False"""
        # Arrange
        self.config["non_interactive"] = False
        
        # Act
        result = self.base_replicator._is_interactive()
        
        # Assert
        assert result is True

    def test_is_interactive_false(self):
        """Test _is_interactive returns False when non_interactive is True"""
        # Arrange
        self.config["non_interactive"] = True
        base_replicator = BaseReplicator(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )
        
        # Act
        result = base_replicator._is_interactive()
        
        # Assert
        assert result is False

    def test_is_interactive_default(self):
        """Test _is_interactive returns True when non_interactive is not set"""
        # Arrange
        config_without_non_interactive = {
            "source": {"org": "source_org", "project": "source_project"},
            "destination": {"org": "dest_org", "project": "dest_project"}
        }
        base_replicator = BaseReplicator(
            config_without_non_interactive,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )
        
        # Act
        result = base_replicator._is_interactive()
        
        # Assert
        assert result is True

    def test_get_option_with_value(self):
        """Test _get_option returns the option value when it exists"""
        # Arrange
        self.config["options"] = {"test_option": "test_value"}
        base_replicator = BaseReplicator(
            self.config,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )
        
        # Act
        result = base_replicator._get_option("test_option", "default")
        
        # Assert
        assert result == "test_value"

    def test_get_option_with_default(self):
        """Test _get_option returns default when option doesn't exist"""
        # Act
        result = self.base_replicator._get_option("nonexistent_option", "default_value")
        
        # Assert
        assert result == "default_value"

    def test_get_option_no_options_section(self):
        """Test _get_option returns default when options section doesn't exist"""
        # Arrange
        config_without_options = {
            "source": {"org": "source_org", "project": "source_project"},
            "destination": {"org": "dest_org", "project": "dest_project"}
        }
        base_replicator = BaseReplicator(
            config_without_options,
            self.mock_source_client,
            self.mock_dest_client,
            self.replication_stats
        )
        
        # Act
        result = base_replicator._get_option("test_option", "default_value")
        
        # Assert
        assert result == "default_value"

    def test_build_endpoint_basic(self):
        """Test _build_endpoint builds basic endpoint"""
        # Act
        result = self.base_replicator._build_endpoint("pipelines")
        
        # Assert
        assert result == "/v1/pipelines"

    def test_build_endpoint_with_org(self):
        """Test _build_endpoint builds endpoint with org"""
        # Act
        result = self.base_replicator._build_endpoint("pipelines", org="test_org")
        
        # Assert
        assert result == "/v1/orgs/test_org/pipelines"

    def test_build_endpoint_with_org_and_project(self):
        """Test _build_endpoint builds endpoint with org and project"""
        # Act
        result = self.base_replicator._build_endpoint("pipelines", org="test_org", project="test_project")
        
        # Assert
        assert result == "/v1/orgs/test_org/projects/test_project/pipelines"

    def test_build_endpoint_with_resource_id(self):
        """Test _build_endpoint builds endpoint with resource ID"""
        # Act
        result = self.base_replicator._build_endpoint(
            "pipelines", 
            org="test_org", 
            project="test_project", 
            resource_id="pipeline123"
        )
        
        # Assert
        assert result == "/v1/orgs/test_org/projects/test_project/pipelines/pipeline123"

    def test_build_endpoint_with_sub_resource(self):
        """Test _build_endpoint builds endpoint with sub-resource"""
        # Act
        result = self.base_replicator._build_endpoint(
            "templates", 
            org="test_org", 
            project="test_project", 
            resource_id="template123",
            sub_resource="versions/v1"
        )
        
        # Assert
        assert result == "/v1/orgs/test_org/projects/test_project/templates/template123/versions/v1"

    def test_build_endpoint_no_resource(self):
        """Test _build_endpoint builds endpoint without resource"""
        # Act
        result = self.base_replicator._build_endpoint(org="test_org", project="test_project")
        
        # Assert
        assert result == "/v1/orgs/test_org/projects/test_project"
