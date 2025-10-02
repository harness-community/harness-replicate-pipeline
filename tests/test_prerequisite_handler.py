"""
Comprehensive unit tests for PrerequisiteHandler

Tests organization and project creation functionality with proper mocking and AAA methodology.
"""

from unittest.mock import Mock, patch

from src.prerequisite_handler import PrerequisiteHandler
from src.api_client import HarnessAPIClient


class TestPrerequisiteHandler:
    """Unit tests for PrerequisiteHandler class"""

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
            "dry_run": False,
            "non_interactive": True
        }
        
        # Create mock clients
        self.mock_source_client = Mock(spec=HarnessAPIClient)
        self.mock_dest_client = Mock(spec=HarnessAPIClient)
        
        # Create replication stats
        self.replication_stats = {}
        
        # Create handler
        self.handler = PrerequisiteHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )

    def test_verify_prerequisites_both_exist(self):
        """Test verify_prerequisites when both org and project exist"""
        # Arrange
        # Mock org exists
        self.mock_dest_client.get.side_effect = [
            {"identifier": "dest_org"},  # Org exists
            {"identifier": "dest_project"}  # Project exists
        ]
        
        # Act
        result = self.handler.verify_prerequisites()
        
        # Assert
        assert result is True
        assert self.mock_dest_client.get.call_count == 2
        self.mock_dest_client.post.assert_not_called()

    def test_verify_prerequisites_org_creation_fails(self):
        """Test verify_prerequisites when org creation fails"""
        # Arrange
        # Mock org doesn't exist
        self.mock_dest_client.get.side_effect = [
            None,  # Org doesn't exist
            None,  # Org list check returns None
        ]
        # Mock org creation fails
        self.mock_dest_client.post.return_value = None
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[]):
            # Act
            result = self.handler.verify_prerequisites()
        
        # Assert
        assert result is False
        self.mock_dest_client.post.assert_called_once()

    def test_verify_prerequisites_project_creation_fails(self):
        """Test verify_prerequisites when project creation fails"""
        # Arrange
        # Mock org exists, project doesn't
        self.mock_dest_client.get.side_effect = [
            {"identifier": "dest_org"},  # Org exists
            None,  # Project doesn't exist
            None   # Project list check returns None
        ]
        # Mock project creation fails
        self.mock_dest_client.post.return_value = None
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[]):
            # Act
            result = self.handler.verify_prerequisites()
        
        # Assert
        assert result is False
        self.mock_dest_client.post.assert_called_once()

    def test_create_org_if_missing_org_exists(self):
        """Test _create_org_if_missing when org already exists"""
        # Arrange
        self.mock_dest_client.get.return_value = {"identifier": "dest_org"}
        
        # Act
        result = self.handler._create_org_if_missing()
        
        # Assert
        assert result is True
        self.mock_dest_client.get.assert_called_once_with("/v1/orgs/dest_org")
        self.mock_dest_client.post.assert_not_called()

    def test_create_org_if_missing_successful_creation(self):
        """Test _create_org_if_missing with successful org creation"""
        # Arrange
        self.mock_dest_client.get.side_effect = [
            None,  # Org doesn't exist
        ]
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Act
        result = self.handler._create_org_if_missing()
        
        # Assert
        assert result is True
        self.mock_dest_client.post.assert_called_once()
        call_args = self.mock_dest_client.post.call_args
        assert call_args[1]['json']['org']['identifier'] == 'dest_org'
        assert call_args[1]['json']['org']['name'] == 'Dest Org'
        assert 'replication tool' in call_args[1]['json']['org']['description']

    def test_create_org_if_missing_creation_fails_but_exists_concurrently(self):
        """Test _create_org_if_missing when creation fails but org exists due to race condition"""
        # Arrange
        self.mock_dest_client.get.side_effect = [
            None,  # Org doesn't exist initially
        ]
        self.mock_dest_client.post.return_value = None  # Creation fails
        
        # Mock the list check to find the org
        orgs_list_response = {"data": {"content": [{"identifier": "dest_org"}]}}
        self.mock_dest_client.get.side_effect = [
            None,  # Initial check - org doesn't exist
            orgs_list_response  # List check - org found
        ]
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[{"identifier": "dest_org"}]):
            # Act
            result = self.handler._create_org_if_missing()
        
        # Assert
        assert result is True
        self.mock_dest_client.post.assert_called_once()

    def test_create_org_if_missing_creation_fails_completely(self):
        """Test _create_org_if_missing when creation fails and org doesn't exist"""
        # Arrange
        self.mock_dest_client.get.side_effect = [
            None,  # Org doesn't exist initially
            None   # List check also returns None
        ]
        self.mock_dest_client.post.return_value = None  # Creation fails
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[]):
            # Act
            result = self.handler._create_org_if_missing()
        
        # Assert
        assert result is False
        self.mock_dest_client.post.assert_called_once()

    def test_create_project_if_missing_project_exists(self):
        """Test _create_project_if_missing when project already exists"""
        # Arrange
        self.mock_dest_client.get.return_value = {"identifier": "dest_project"}
        
        # Act
        result = self.handler._create_project_if_missing()
        
        # Assert
        assert result is True
        self.mock_dest_client.get.assert_called_once_with("/v1/orgs/dest_org/projects/dest_project")
        self.mock_dest_client.post.assert_not_called()

    def test_create_project_if_missing_successful_creation(self):
        """Test _create_project_if_missing with successful project creation"""
        # Arrange
        self.mock_dest_client.get.side_effect = [
            None,  # Project doesn't exist
        ]
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Act
        result = self.handler._create_project_if_missing()
        
        # Assert
        assert result is True
        self.mock_dest_client.post.assert_called_once()
        call_args = self.mock_dest_client.post.call_args
        assert call_args[1]['json']['project']['identifier'] == 'dest_project'
        assert call_args[1]['json']['project']['orgIdentifier'] == 'dest_org'
        assert call_args[1]['json']['project']['name'] == 'Dest Project'
        assert 'replication tool' in call_args[1]['json']['project']['description']

    def test_create_project_if_missing_creation_fails_but_exists_concurrently(self):
        """Test _create_project_if_missing when creation fails but project exists due to race condition"""
        # Arrange
        self.mock_dest_client.get.side_effect = [
            None,  # Project doesn't exist initially
        ]
        self.mock_dest_client.post.return_value = None  # Creation fails
        
        # Mock the list check to find the project
        projects_list_response = {"data": {"content": [{"identifier": "dest_project"}]}}
        self.mock_dest_client.get.side_effect = [
            None,  # Initial check - project doesn't exist
            projects_list_response  # List check - project found
        ]
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[{"identifier": "dest_project"}]):
            # Act
            result = self.handler._create_project_if_missing()
        
        # Assert
        assert result is True
        self.mock_dest_client.post.assert_called_once()

    def test_create_project_if_missing_creation_fails_completely(self):
        """Test _create_project_if_missing when creation fails and project doesn't exist"""
        # Arrange
        self.mock_dest_client.get.side_effect = [
            None,  # Project doesn't exist initially
            None   # List check also returns None
        ]
        self.mock_dest_client.post.return_value = None  # Creation fails
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[]):
            # Act
            result = self.handler._create_project_if_missing()
        
        # Assert
        assert result is False
        self.mock_dest_client.post.assert_called_once()

    def test_verify_prerequisites_creates_both_org_and_project(self):
        """Test verify_prerequisites creates both org and project when neither exist"""
        # Arrange
        self.mock_dest_client.get.side_effect = [
            None,  # Org doesn't exist
            None,  # Project doesn't exist
        ]
        self.mock_dest_client.post.side_effect = [
            {"status": "SUCCESS"},  # Org creation succeeds
            {"status": "SUCCESS"}   # Project creation succeeds
        ]
        
        # Act
        result = self.handler.verify_prerequisites()
        
        # Assert
        assert result is True
        assert self.mock_dest_client.post.call_count == 2
        
        # Verify org creation call
        org_call = self.mock_dest_client.post.call_args_list[0]
        assert org_call[1]['json']['org']['identifier'] == 'dest_org'
        
        # Verify project creation call
        project_call = self.mock_dest_client.post.call_args_list[1]
        assert project_call[1]['json']['project']['identifier'] == 'dest_project'
        assert project_call[1]['json']['project']['orgIdentifier'] == 'dest_org'

    def test_create_org_name_formatting(self):
        """Test org name formatting with underscores and special characters"""
        # Arrange
        self.config["destination"]["org"] = "my_test_org"
        handler = PrerequisiteHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        self.mock_dest_client.get.return_value = None  # Org doesn't exist
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Act
        result = handler._create_org_if_missing()
        
        # Assert
        assert result is True
        call_args = self.mock_dest_client.post.call_args
        assert call_args[1]['json']['org']['name'] == 'My Test Org'

    def test_create_project_name_formatting(self):
        """Test project name formatting with underscores and special characters"""
        # Arrange
        self.config["destination"]["project"] = "my_test_project"
        handler = PrerequisiteHandler(
            self.config, 
            self.mock_source_client, 
            self.mock_dest_client, 
            self.replication_stats
        )
        
        self.mock_dest_client.get.return_value = None  # Project doesn't exist
        self.mock_dest_client.post.return_value = {"status": "SUCCESS"}
        
        # Act
        result = handler._create_project_if_missing()
        
        # Assert
        assert result is True
        call_args = self.mock_dest_client.post.call_args
        assert call_args[1]['json']['project']['name'] == 'My Test Project'

    def test_create_org_if_missing_race_condition_not_found_in_list(self):
        """Test _create_org_if_missing when creation fails and org not found in concurrent list"""
        # Arrange
        self.mock_dest_client.get.side_effect = [
            None,  # Org doesn't exist initially
            {"data": {"content": []}}  # List check - empty list
        ]
        self.mock_dest_client.post.return_value = None  # Creation fails
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[]):
            # Act
            result = self.handler._create_org_if_missing()
        
        # Assert
        assert result is False

    def test_create_project_if_missing_race_condition_not_found_in_list(self):
        """Test _create_project_if_missing when creation fails and project not found in concurrent list"""
        # Arrange
        self.mock_dest_client.get.side_effect = [
            None,  # Project doesn't exist initially
            {"data": {"content": []}}  # List check - empty list
        ]
        self.mock_dest_client.post.return_value = None  # Creation fails
        
        with patch.object(HarnessAPIClient, 'normalize_response', return_value=[]):
            # Act
            result = self.handler._create_project_if_missing()
        
        # Assert
        assert result is False
