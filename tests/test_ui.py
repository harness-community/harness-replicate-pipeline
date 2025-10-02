"""
Comprehensive unit tests for UI module

Tests interactive UI functionality with proper mocking and AAA methodology.
"""

from unittest.mock import Mock, patch

from src.ui import (
    select_organization, select_project, select_pipelines,
    select_or_create_organization, select_or_create_project,
    create_organization, create_project, get_selections_from_clients
)


class TestSelectOrganization:
    """Test suite for select_organization function"""

    def test_select_organization_success(self):
        """Test select_organization succeeds with valid response"""
        # Arrange
        mock_client = Mock()
        mock_client.get.return_value = [{"identifier": "org1", "name": "Org 1"}]
        mock_client.normalize_response.return_value = [{"identifier": "org1", "name": "Org 1"}]

        # Act
        with patch('src.harness_migration.ui.radiolist_dialog') as mock_dialog:
            mock_dialog.return_value.run.return_value = "org1"
            result = select_organization(mock_client)

        # Assert
        assert result == "org1"
        mock_client.get.assert_called_once_with("/v1/orgs")

    def test_select_organization_no_orgs_shows_error(self):
        """Test select_organization shows error when no orgs found"""
        # Arrange
        mock_client = Mock()
        mock_client.get.return_value = []
        mock_client.normalize_response.return_value = []

        # Act
        with patch('src.harness_migration.ui.message_dialog') as mock_message:
            with patch('src.harness_migration.ui.radiolist_dialog') as mock_dialog:
                mock_dialog.return_value.run.return_value = None
                result = select_organization(mock_client)

        # Assert
        assert result is None
        mock_message.assert_called_once()

    def test_select_organization_api_error_shows_error(self):
        """Test select_organization shows error on API failure"""
        # Arrange
        mock_client = Mock()
        mock_client.get.side_effect = Exception("API Error")

        # Act
        with patch('src.harness_migration.ui.message_dialog') as mock_message:
            result = select_organization(mock_client)

        # Assert
        assert result is None
        mock_message.assert_called_once()

    def test_select_organization_cancelled_returns_none(self):
        """Test select_organization returns None when cancelled"""
        # Arrange
        mock_client = Mock()
        mock_client.get.return_value = [{"identifier": "org1", "name": "Org 1"}]
        mock_client.normalize_response.return_value = [{"identifier": "org1", "name": "Org 1"}]

        # Act
        with patch('src.harness_migration.ui.radiolist_dialog') as mock_dialog:
            mock_dialog.return_value.run.return_value = None
            result = select_organization(mock_client)

        # Assert
        assert result is None


class TestSelectProject:
    """Test suite for select_project function"""

    def test_select_project_success(self):
        """Test select_project succeeds with valid response"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        mock_client.get.return_value = [{"identifier": "proj1", "name": "Project 1"}]
        mock_client.normalize_response.return_value = [{"identifier": "proj1", "name": "Project 1"}]

        # Act
        with patch('src.harness_migration.ui.radiolist_dialog') as mock_dialog:
            mock_dialog.return_value.run.return_value = "proj1"
            result = select_project(mock_client, org)

        # Assert
        assert result == "proj1"
        mock_client.get.assert_called_once_with(f"/v1/orgs/{org}/projects")

    def test_select_project_no_projects_shows_error(self):
        """Test select_project shows error when no projects found"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        mock_client.get.return_value = []
        mock_client.normalize_response.return_value = []

        # Act
        with patch('src.harness_migration.ui.message_dialog') as mock_message:
            with patch('src.harness_migration.ui.radiolist_dialog') as mock_dialog:
                mock_dialog.return_value.run.return_value = None
                result = select_project(mock_client, org)

        # Assert
        assert result is None
        mock_message.assert_called_once()

    def test_select_project_api_error_shows_error(self):
        """Test select_project shows error on API failure"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        mock_client.get.side_effect = Exception("API Error")

        # Act
        with patch('src.harness_migration.ui.message_dialog') as mock_message:
            result = select_project(mock_client, org)

        # Assert
        assert result is None
        mock_message.assert_called_once()


class TestSelectPipelines:
    """Test suite for select_pipelines function"""

    def test_select_pipelines_success(self):
        """Test select_pipelines succeeds with valid response"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        project = "test-project"
        pipelines = [
            {"identifier": "pipeline1", "name": "Pipeline 1"},
            {"identifier": "pipeline2", "name": "Pipeline 2"}
        ]
        mock_client.get.return_value = pipelines
        mock_client.normalize_response.return_value = pipelines

        # Act
        with patch('src.harness_migration.ui.checkboxlist_dialog') as mock_dialog:
            mock_dialog.return_value.run.return_value = ["pipeline1", "pipeline2"]
            result = select_pipelines(mock_client, org, project)

        # Assert
        assert len(result) == 2
        assert result[0]["identifier"] == "pipeline1"
        assert result[1]["identifier"] == "pipeline2"
        mock_client.get.assert_called_once_with(f"/v1/orgs/{org}/projects/{project}/pipelines")

    def test_select_pipelines_no_pipelines_shows_error(self):
        """Test select_pipelines shows error when no pipelines found"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        project = "test-project"
        mock_client.get.return_value = []
        mock_client.normalize_response.return_value = []

        # Act
        with patch('src.harness_migration.ui.message_dialog') as mock_message:
            with patch('src.harness_migration.ui.checkboxlist_dialog') as mock_dialog:
                mock_dialog.return_value.run.return_value = None
                result = select_pipelines(mock_client, org, project)

        # Assert
        assert not result
        mock_message.assert_called_once()

    def test_select_pipelines_api_error_shows_error(self):
        """Test select_pipelines shows error on API failure"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        project = "test-project"
        mock_client.get.side_effect = Exception("API Error")

        # Act
        with patch('src.harness_migration.ui.message_dialog') as mock_message:
            result = select_pipelines(mock_client, org, project)

        # Assert
        assert not result
        mock_message.assert_called_once()

    def test_select_pipelines_cancelled_returns_empty_list(self):
        """Test select_pipelines returns empty list when cancelled"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        project = "test-project"
        pipelines = [{"identifier": "pipeline1", "name": "Pipeline 1"}]
        mock_client.get.return_value = pipelines
        mock_client.normalize_response.return_value = pipelines

        # Act
        with patch('src.harness_migration.ui.checkboxlist_dialog') as mock_dialog:
            mock_dialog.return_value.run.return_value = None
            result = select_pipelines(mock_client, org, project)

        # Assert
        assert not result


class TestSelectOrCreateOrganization:
    """Test suite for select_or_create_organization function"""

    def test_select_or_create_organization_existing_org(self):
        """Test select_or_create_organization with existing orgs"""
        # Arrange
        mock_client = Mock()
        orgs = [{"identifier": "org1", "name": "Org 1"}]
        mock_client.get.return_value = orgs
        mock_client.normalize_response.return_value = orgs

        # Act
        with patch('src.harness_migration.ui.radiolist_dialog') as mock_dialog:
            mock_dialog.return_value.run.return_value = "org1"
            result = select_or_create_organization(mock_client)

        # Assert
        assert result == "org1"

    def test_select_or_create_organization_create_new(self):
        """Test select_or_create_organization creates new org"""
        # Arrange
        mock_client = Mock()
        orgs = [{"identifier": "org1", "name": "Org 1"}]
        mock_client.get.return_value = orgs
        mock_client.normalize_response.return_value = orgs

        # Act
        with patch('src.harness_migration.ui.radiolist_dialog') as mock_dialog:
            mock_dialog.return_value.run.return_value = "__create_new__"
            with patch('src.harness_migration.ui.create_organization', return_value="new-org"):
                result = select_or_create_organization(mock_client)

        # Assert
        assert result == "new-org"

    def test_select_or_create_organization_no_orgs_creates_new(self):
        """Test select_or_create_organization creates new org when none exist"""
        # Arrange
        mock_client = Mock()
        mock_client.get.return_value = []
        mock_client.normalize_response.return_value = []

        # Act
        with patch('src.harness_migration.ui.create_organization', return_value="new-org"):
            result = select_or_create_organization(mock_client)

        # Assert
        assert result == "new-org"

    def test_select_or_create_organization_api_error(self):
        """Test select_or_create_organization handles API error"""
        # Arrange
        mock_client = Mock()
        mock_client.get.side_effect = Exception("API Error")

        # Act
        with patch('src.harness_migration.ui.message_dialog') as mock_message:
            result = select_or_create_organization(mock_client)

        # Assert
        assert result is None
        mock_message.assert_called_once()


class TestSelectOrCreateProject:
    """Test suite for select_or_create_project function"""

    def test_select_or_create_project_existing_project(self):
        """Test select_or_create_project with existing projects"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        projects = [{"identifier": "proj1", "name": "Project 1"}]
        mock_client.get.return_value = projects
        mock_client.normalize_response.return_value = projects

        # Act
        with patch('src.harness_migration.ui.radiolist_dialog') as mock_dialog:
            mock_dialog.return_value.run.return_value = "proj1"
            result = select_or_create_project(mock_client, org)

        # Assert
        assert result == "proj1"

    def test_select_or_create_project_create_new(self):
        """Test select_or_create_project creates new project"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        projects = [{"identifier": "proj1", "name": "Project 1"}]
        mock_client.get.return_value = projects
        mock_client.normalize_response.return_value = projects

        # Act
        with patch('src.harness_migration.ui.radiolist_dialog') as mock_dialog:
            mock_dialog.return_value.run.return_value = "__create_new__"
            with patch('src.harness_migration.ui.create_project', return_value="new-project"):
                result = select_or_create_project(mock_client, org)

        # Assert
        assert result == "new-project"

    def test_select_or_create_project_no_projects_creates_new(self):
        """Test select_or_create_project creates new project when none exist"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        mock_client.get.return_value = []
        mock_client.normalize_response.return_value = []

        # Act
        with patch('src.harness_migration.ui.create_project', return_value="new-project"):
            result = select_or_create_project(mock_client, org)

        # Assert
        assert result == "new-project"

    def test_select_or_create_project_api_error(self):
        """Test select_or_create_project handles API error"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        mock_client.get.side_effect = Exception("API Error")

        # Act
        with patch('src.harness_migration.ui.message_dialog') as mock_message:
            result = select_or_create_project(mock_client, org)

        # Assert
        assert result is None
        mock_message.assert_called_once()


class TestCreateOrganization:
    """Test suite for create_organization function"""

    def test_create_organization_success(self):
        """Test create_organization succeeds"""
        # Arrange
        mock_client = Mock()
        mock_client.post.return_value = {"success": True}

        # Act
        with patch('prompt_toolkit.prompt', return_value="new-org"):
            result = create_organization(mock_client)

        # Assert
        assert result == "new-org"
        mock_client.post.assert_called_once()

    def test_create_organization_empty_name_returns_none(self):
        """Test create_organization returns None with empty name"""
        # Arrange
        mock_client = Mock()

        # Act
        with patch('prompt_toolkit.prompt', return_value=""):
            result = create_organization(mock_client)

        # Assert
        assert result is None

    def test_create_organization_api_failure_shows_error(self):
        """Test create_organization shows error on API failure"""
        # Arrange
        mock_client = Mock()
        mock_client.post.return_value = None

        # Act
        with patch('prompt_toolkit.prompt', return_value="new-org"):
            with patch('src.harness_migration.ui.message_dialog') as mock_message:
                result = create_organization(mock_client)

        # Assert
        assert result is None
        mock_message.assert_called_once()

    def test_create_organization_exception_shows_error(self):
        """Test create_organization handles exception"""
        # Arrange
        mock_client = Mock()
        mock_client.post.side_effect = Exception("API Error")

        # Act
        with patch('prompt_toolkit.prompt', return_value="new-org"):
            with patch('src.harness_migration.ui.message_dialog') as mock_message:
                result = create_organization(mock_client)

        # Assert
        assert result is None
        mock_message.assert_called_once()


class TestCreateProject:
    """Test suite for create_project function"""

    def test_create_project_success(self):
        """Test create_project succeeds"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        mock_client.post.return_value = {"success": True}

        # Act
        with patch('prompt_toolkit.prompt', return_value="new-project"):
            result = create_project(mock_client, org)

        # Assert
        assert result == "new-project"
        mock_client.post.assert_called_once()

    def test_create_project_empty_name_returns_none(self):
        """Test create_project returns None with empty name"""
        # Arrange
        mock_client = Mock()
        org = "test-org"

        # Act
        with patch('prompt_toolkit.prompt', return_value=""):
            result = create_project(mock_client, org)

        # Assert
        assert result is None

    def test_create_project_api_failure_shows_error(self):
        """Test create_project shows error on API failure"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        mock_client.post.return_value = None

        # Act
        with patch('prompt_toolkit.prompt', return_value="new-project"):
            with patch('src.harness_migration.ui.message_dialog') as mock_message:
                result = create_project(mock_client, org)

        # Assert
        assert result is None
        mock_message.assert_called_once()

    def test_create_project_exception_shows_error(self):
        """Test create_project handles exception"""
        # Arrange
        mock_client = Mock()
        org = "test-org"
        mock_client.post.side_effect = Exception("API Error")

        # Act
        with patch('prompt_toolkit.prompt', return_value="new-project"):
            with patch('src.harness_migration.ui.message_dialog') as mock_message:
                result = create_project(mock_client, org)

        # Assert
        assert result is None
        mock_message.assert_called_once()


class TestGetSelectionsFromClients:
    """Test suite for get_selections_from_clients function"""

    def test_get_selections_from_clients_all_missing(self):
        """Test get_selections_from_clients when all selections are missing"""
        # Arrange
        base_config = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }
        source_client = Mock()
        dest_client = Mock()

        # Act
        with patch('src.harness_migration.ui.select_organization', return_value="source-org"):
            with patch('src.harness_migration.ui.select_project', return_value="source-project"):
                with patch('src.harness_migration.ui.select_pipelines', return_value=[{"identifier": "pipeline1"}]):
                    with patch('src.harness_migration.ui.select_or_create_organization', return_value="dest-org"):
                        with patch('src.harness_migration.ui.select_or_create_project', return_value="dest-project"):
                            with patch('src.harness_migration.config.save_config') as mock_save:
                                result = get_selections_from_clients(source_client, dest_client, base_config, "config.json")

        # Assert
        assert result["source"]["org"] == "source-org"
        assert result["source"]["project"] == "source-project"
        assert result["destination"]["org"] == "dest-org"
        assert result["destination"]["project"] == "dest-project"
        assert result["pipelines"] == [{"identifier": "pipeline1"}]
        assert mock_save.call_count == 5  # Called for each selection

    def test_get_selections_from_clients_all_present(self):
        """Test get_selections_from_clients when all selections are present"""
        # Arrange
        base_config = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }
        source_client = Mock()
        dest_client = Mock()

        # Act
        with patch('src.harness_migration.config.save_config') as mock_save:
            result = get_selections_from_clients(source_client, dest_client, base_config, "config.json")

        # Assert
        assert result == base_config
        assert mock_save.call_count == 0  # No saves needed

    def test_get_selections_from_clients_partial_missing(self):
        """Test get_selections_from_clients when some selections are missing"""
        # Arrange
        base_config = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }
        source_client = Mock()
        dest_client = Mock()

        # Act
        with patch('src.harness_migration.ui.select_project', return_value="source-project"):
            with patch('src.harness_migration.ui.select_pipelines', return_value=[{"identifier": "pipeline1"}]):
                with patch('src.harness_migration.ui.select_or_create_organization', return_value="dest-org"):
                    with patch('src.harness_migration.ui.select_or_create_project', return_value="dest-project"):
                        with patch('src.harness_migration.config.save_config') as mock_save:
                            result = get_selections_from_clients(source_client, dest_client, base_config, "config.json")

        # Assert
        assert result["source"]["org"] == "source-org"  # Already present
        assert result["source"]["project"] == "source-project"  # Selected
        assert result["destination"]["org"] == "dest-org"  # Selected
        assert result["destination"]["project"] == "dest-project"  # Selected
        assert result["pipelines"] == [{"identifier": "pipeline1"}]  # Selected
        assert mock_save.call_count == 4  # Called for each missing selection

    def test_get_selections_from_clients_selection_fails(self):
        """Test get_selections_from_clients when selection fails"""
        # Arrange
        base_config = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }
        source_client = Mock()
        dest_client = Mock()

        # Act
        with patch('src.harness_migration.ui.select_organization', return_value=None):
            result = get_selections_from_clients(source_client, dest_client, base_config, "config.json")

        # Assert
        assert not result
