"""
Comprehensive unit tests for HarnessAPIClient

Tests API client functionality with proper mocking and AAA methodology.
"""

from unittest.mock import Mock, patch

from requests.exceptions import RequestException, HTTPError

from src.api_client import HarnessAPIClient


@pytest.mark.unit
class TestHarnessAPIClient:
    """Test suite for HarnessAPIClient"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        # pylint: disable=attribute-defined-outside-init
        self.base_url = "https://app.harness.io"
        self.api_key = "sat.test.key.12345"
        self.client = HarnessAPIClient(self.base_url, self.api_key)

    def test_init_sets_correct_attributes(self):
        """Test that initialization sets correct attributes"""
        # Arrange & Act
        client = HarnessAPIClient("https://test.com", "test-key")

        # Assert
        assert client.base_url == "https://test.com"
        assert client.api_key == "test-key"
        assert client.session.headers["x-api-key"] == "test-key"
        assert client.session.headers["Content-Type"] == "application/json"

    def test_init_strips_trailing_slash_from_base_url(self):
        """Test that trailing slash is removed from base_url"""
        # Arrange & Act
        client = HarnessAPIClient("https://test.com/", "test-key")

        # Assert
        assert client.base_url == "https://test.com"

    @patch('src.api_client.requests.Session.get')
    def test_get_success_returns_json_response(self, mock_get):
        """Test successful GET request returns JSON response"""
        # Arrange
        expected_response = {"data": "test"}
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = self.client.get("/test-endpoint")

        # Assert
        assert result == expected_response
        mock_get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @patch('src.api_client.requests.Session.get')
    def test_get_with_params_passes_them_correctly(self, mock_get):
        """Test GET request with parameters"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        params = {"org": "test-org", "project": "test-project"}

        # Act
        self.client.get("/test-endpoint", params=params)

        # Assert
        mock_get.assert_called_once_with(
            "https://app.harness.io/test-endpoint",
            params=params
        )

    @patch('src.api_client.requests.Session.get')
    def test_get_request_exception_returns_none(self, mock_get):
        """Test GET request with RequestException returns None"""
        # Arrange
        mock_get.side_effect = RequestException("Network error")

        # Act
        result = self.client.get("/test-endpoint")

        # Assert
        assert result is None

    @patch('src.api_client.requests.Session.get')
    def test_get_http_error_logs_and_returns_none(self, mock_get):
        """Test GET request with HTTP error logs details and returns None"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.url = "https://app.harness.io/test-endpoint"
        http_error = HTTPError("404 Client Error")
        http_error.response = mock_response
        mock_get.side_effect = http_error

        # Act
        result = self.client.get("/test-endpoint")

        # Assert
        assert result is None

    @patch('src.api_client.requests.Session.post')
    def test_post_success_returns_json_response(self, mock_post):
        """Test successful POST request returns JSON response"""
        # Arrange
        expected_response = {"id": "123", "status": "created"}
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        payload = {"name": "test"}

        # Act
        result = self.client.post("/test-endpoint", json=payload)

        # Assert
        assert result == expected_response
        mock_post.assert_called_once_with(
            "https://app.harness.io/test-endpoint",
            params=None,
            json=payload
        )

    @patch('src.api_client.requests.Session.post')
    def test_post_with_params_and_json(self, mock_post):
        """Test POST request with both params and json data"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        params = {"org": "test-org"}
        json_data = {"name": "test"}

        # Act
        self.client.post("/test-endpoint", params=params, json=json_data)

        # Assert
        mock_post.assert_called_once_with(
            "https://app.harness.io/test-endpoint",
            params=params,
            json=json_data
        )

    @patch('src.api_client.requests.Session.put')
    def test_put_success_returns_json_response(self, mock_put):
        """Test successful PUT request returns JSON response"""
        # Arrange
        expected_response = {"id": "123", "status": "updated"}
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_put.return_value = mock_response
        payload = {"name": "updated"}

        # Act
        result = self.client.put("/test-endpoint", json=payload)

        # Assert
        assert result == expected_response
        mock_put.assert_called_once_with(
            "https://app.harness.io/test-endpoint",
            params=None,
            json=payload
        )

    @patch('src.api_client.requests.Session.delete')
    def test_delete_success_returns_json_response(self, mock_delete):
        """Test successful DELETE request returns JSON response"""
        # Arrange
        expected_response = {"status": "deleted"}
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_delete.return_value = mock_response

        # Act
        result = self.client.delete("/test-endpoint")

        # Assert
        assert result == expected_response
        mock_delete.assert_called_once_with(
            "https://app.harness.io/test-endpoint",
            params=None
        )

    def test_normalize_response_with_list(self):
        """Test normalize_response with list input"""
        # Arrange
        response = [{"id": "1"}, {"id": "2"}]

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        assert result == response

    def test_normalize_response_with_dict_content(self):
        """Test normalize_response with dict containing content key"""
        # Arrange
        response = {"content": [{"id": "1"}, {"id": "2"}]}

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        assert result == [{"id": "1"}, {"id": "2"}]

    def test_normalize_response_with_none(self):
        """Test normalize_response with None input"""
        # Arrange
        response = None

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        assert result == []

    def test_normalize_response_with_empty_dict(self):
        """Test normalize_response with empty dict"""
        # Arrange
        response = {}

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        assert result == []

    def test_normalize_response_with_dict_no_content(self):
        """Test normalize_response with dict without content key"""
        # Arrange
        response = {"data": "test"}

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        assert result == []

    def test_normalize_response_with_nested_org_objects(self):
        """Test normalize_response extracts nested org objects from Harness API format"""
        # Arrange - Real Harness API format for organizations
        response = [
            {
                "org": {
                    "identifier": "tf_organization",
                    "name": "TF Organization",
                    "description": "Test org"
                },
                "created": 1728910106483,
                "updated": 1728910106484
            },
            {
                "org": {
                    "identifier": "default",
                    "name": "Default",
                    "description": "Default org"
                },
                "created": 1728910106483,
                "updated": 1728910106484
            }
        ]

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        expected = [
            {
                "identifier": "tf_organization",
                "name": "TF Organization",
                "description": "Test org"
            },
            {
                "identifier": "default",
                "name": "Default",
                "description": "Default org"
            }
        ]
        assert result == expected

    def test_normalize_response_with_nested_project_objects(self):
        """Test normalize_response extracts nested project objects from Harness API format"""
        # Arrange - Real Harness API format for projects
        response = [
            {
                "project": {
                    "identifier": "sandbox",
                    "name": "Sandbox",
                    "orgIdentifier": "tf_organization"
                },
                "created": 1728910106483,
                "updated": 1728910106484
            }
        ]

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        expected = [
            {
                "identifier": "sandbox",
                "name": "Sandbox",
                "orgIdentifier": "tf_organization"
            }
        ]
        assert result == expected

    def test_normalize_response_with_mixed_nested_and_direct_objects(self):
        """Test normalize_response handles mix of nested and direct objects"""
        # Arrange - Mix of formats
        response = [
            {
                "org": {
                    "identifier": "nested_org",
                    "name": "Nested Org"
                }
            },
            {
                "identifier": "direct_item",
                "name": "Direct Item"
            }
        ]

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        expected = [
            {
                "identifier": "nested_org",
                "name": "Nested Org"
            },
            {
                "identifier": "direct_item",
                "name": "Direct Item"
            }
        ]
        assert result == expected

    def test_normalize_response_with_string_org_field(self):
        """Test normalize_response handles string org field (not nested object)"""
        # Arrange - Template format where org is a string identifier
        response = [
            {
                "org": "tf_organization",  # String, not object
                "identifier": "template1",
                "name": "Template 1"
            }
        ]

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert - Should return item as-is since org is not a nested object
        expected = [
            {
                "org": "tf_organization",
                "identifier": "template1",
                "name": "Template 1"
            }
        ]
        assert result == expected

    @patch('src.api_client.requests.Session.get')
    def test_get_logs_debug_message(self, mock_get):
        """Test that GET request logs debug message"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        with patch('src.api_client.logger') as mock_logger:
            self.client.get("/test-endpoint")

        # Assert
        mock_logger.debug.assert_called_once()

    @patch('src.api_client.requests.Session.get')
    def test_get_error_logs_error_message(self, mock_get):
        """Test that GET request error logs error message"""
        # Arrange
        mock_get.side_effect = RequestException("Network error")

        # Act
        with patch('src.api_client.logger') as mock_logger:
            self.client.get("/test-endpoint")

        # Assert
        mock_logger.error.assert_called()
