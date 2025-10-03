"""
Additional unit tests for HarnessAPIClient to improve coverage

Tests error handling and edge cases in API client functionality.
"""

from unittest.mock import Mock, patch
import requests

from src.api_client import HarnessAPIClient


class TestHarnessAPIClientAdditional:
    """Additional unit tests for HarnessAPIClient class"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.client = HarnessAPIClient("https://test.com", "test-key")

    @patch('src.api_client.requests.Session.put')
    def test_put_with_response_error_details(self, mock_put):
        """Test PUT request with detailed error response logging"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request Details"

        mock_error = requests.exceptions.HTTPError("HTTP Error")
        mock_error.response = mock_response
        mock_put.side_effect = mock_error

        # Act
        with patch('src.api_client.logger') as mock_logger:
            result = self.client.put("/test-endpoint", json={"test": "data"})

        # Assert
        assert result is None
        mock_logger.error.assert_any_call("API Error: %s", mock_error)
        mock_logger.error.assert_any_call("Status: %s", 400)
        mock_logger.error.assert_any_call("URL: %s", "https://test.com/test-endpoint")
        mock_logger.error.assert_any_call("Response Text: %s", "Bad Request Details")

    @patch('src.api_client.requests.Session.put')
    def test_put_with_request_exception_no_response(self, mock_put):
        """Test PUT request with RequestException that has no response"""
        # Arrange
        mock_error = requests.exceptions.RequestException("Network error")
        # No response attribute
        mock_put.side_effect = mock_error

        # Act
        with patch('src.api_client.logger') as mock_logger:
            result = self.client.put("/test-endpoint", json={"test": "data"})

        # Assert
        assert result is None
        mock_logger.error.assert_called_with("API Error: %s", mock_error)

    @patch('src.api_client.requests.Session.delete')
    def test_delete_with_response_error_details(self, mock_delete):
        """Test DELETE request with detailed error response logging"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found Details"

        mock_error = requests.exceptions.HTTPError("HTTP Error")
        mock_error.response = mock_response
        mock_delete.side_effect = mock_error

        # Act
        with patch('src.api_client.logger') as mock_logger:
            result = self.client.delete("/test-endpoint")

        # Assert
        assert result is None
        mock_logger.error.assert_any_call("API Error: %s", mock_error)
        mock_logger.error.assert_any_call("Status: %s", 404)
        mock_logger.error.assert_any_call("URL: %s", "https://test.com/test-endpoint")
        mock_logger.error.assert_any_call("Response Text: %s", "Not Found Details")

    @patch('src.api_client.requests.Session.delete')
    def test_delete_with_request_exception_no_response(self, mock_delete):
        """Test DELETE request with RequestException that has no response"""
        # Arrange
        mock_error = requests.exceptions.RequestException("Network error")
        # No response attribute
        mock_delete.side_effect = mock_error

        # Act
        with patch('src.api_client.logger') as mock_logger:
            result = self.client.delete("/test-endpoint")

        # Assert
        assert result is None
        mock_logger.error.assert_called_with("API Error: %s", mock_error)

    def test_normalize_response_with_non_dict_items_in_list(self):
        """Test normalize_response with list containing non-dict items"""
        # Arrange
        response = [
            {"identifier": "item1", "name": "Item 1"},
            "string_item",  # Non-dict item
            {"identifier": "item2", "name": "Item 2"}
        ]

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        expected = [
            {"identifier": "item1", "name": "Item 1"},
            "string_item",  # Should be preserved as-is
            {"identifier": "item2", "name": "Item 2"}
        ]
        assert result == expected

    def test_normalize_response_with_org_and_project_nested(self):
        """Test normalize_response with both org and project nested objects"""
        # Arrange
        response = [
            {
                "identifier": "item1",
                "org": {"identifier": "org1", "name": "Org 1"},
                "project": {"identifier": "proj1", "name": "Project 1"}
            }
        ]

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        # Should prefer org over project when both exist
        expected = [{"identifier": "org1", "name": "Org 1"}]
        assert result == expected

    def test_normalize_response_with_project_nested_only(self):
        """Test normalize_response with only project nested object"""
        # Arrange
        response = [
            {
                "identifier": "item1",
                "project": {"identifier": "proj1", "name": "Project 1"}
            }
        ]

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        expected = [{"identifier": "proj1", "name": "Project 1"}]
        assert result == expected

    def test_normalize_response_with_non_dict_org_project(self):
        """Test normalize_response with non-dict org/project values"""
        # Arrange
        response = [
            {
                "identifier": "item1",
                "org": "string_org",  # Non-dict org
                "project": "string_project"  # Non-dict project
            }
        ]

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        # Should return the original item since org/project are not dicts
        expected = [{"identifier": "item1", "org": "string_org", "project": "string_project"}]
        assert result == expected

    def test_normalize_response_dict_with_content_key(self):
        """Test normalize_response with dict containing content key"""
        # Arrange
        response = {
            "content": [
                {"identifier": "item1", "name": "Item 1"},
                {"identifier": "item2", "name": "Item 2"}
            ],
            "totalElements": 2
        }

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        expected = [
            {"identifier": "item1", "name": "Item 1"},
            {"identifier": "item2", "name": "Item 2"}
        ]
        assert result == expected

    def test_normalize_response_dict_without_content_key(self):
        """Test normalize_response with dict not containing content key"""
        # Arrange
        response = {
            "data": [
                {"identifier": "item1", "name": "Item 1"}
            ],
            "totalElements": 1
        }

        # Act
        result = HarnessAPIClient.normalize_response(response)

        # Assert
        # Should return empty list when no content key
        assert result == []

    @patch('src.api_client.requests.Session.put')
    def test_put_successful_request(self, mock_put):
        """Test successful PUT request"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"status": "updated"}
        mock_put.return_value = mock_response

        # Act
        result = self.client.put("/test-endpoint", json={"test": "data"})

        # Assert
        assert result == {"status": "updated"}
        mock_put.assert_called_once_with(
            "https://test.com/test-endpoint",
            params=None,
            json={"test": "data"}
        )

    @patch('src.api_client.requests.Session.delete')
    def test_delete_successful_request(self, mock_delete):
        """Test successful DELETE request"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"status": "deleted"}
        mock_delete.return_value = mock_response

        # Act
        result = self.client.delete("/test-endpoint", params={"id": "123"})

        # Assert
        assert result == {"status": "deleted"}
        mock_delete.assert_called_once_with(
            "https://test.com/test-endpoint",
            params={"id": "123"}
        )
