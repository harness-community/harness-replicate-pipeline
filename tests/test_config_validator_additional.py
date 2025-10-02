"""
Additional unit tests for ConfigValidator to improve coverage

Tests error cases and edge paths in configuration validation.
"""

from unittest.mock import patch

from src.config_validator import ConfigValidator


class TestConfigValidatorAdditional:
    """Additional unit tests for ConfigValidator class"""

    def test_validate_api_credentials_missing_dest_base_url(self):
        """Test validate_api_credentials fails when destination base_url is missing"""
        # Arrange
        config = {
            "source": {
                "base_url": "https://source.harness.io",
                "api_key": "source-key"
            },
            "destination": {
                "api_key": "dest-key"
                # Missing base_url
            }
        }
        
        # Act
        with patch('src.config_validator.logger') as mock_logger:
            result = ConfigValidator.validate_api_credentials(config)
        
        # Assert
        assert result is False
        mock_logger.error.assert_called_with("Destination base_url and api_key are required")

    def test_validate_api_credentials_missing_dest_api_key(self):
        """Test validate_api_credentials fails when destination api_key is missing"""
        # Arrange
        config = {
            "source": {
                "base_url": "https://source.harness.io",
                "api_key": "source-key"
            },
            "destination": {
                "base_url": "https://dest.harness.io"
                # Missing api_key
            }
        }
        
        # Act
        with patch('src.config_validator.logger') as mock_logger:
            result = ConfigValidator.validate_api_credentials(config)
        
        # Assert
        assert result is False
        mock_logger.error.assert_called_with("Destination base_url and api_key are required")

    def test_validate_api_credentials_empty_dest_base_url(self):
        """Test validate_api_credentials fails when destination base_url is empty"""
        # Arrange
        config = {
            "source": {
                "base_url": "https://source.harness.io",
                "api_key": "source-key"
            },
            "destination": {
                "base_url": "",  # Empty string
                "api_key": "dest-key"
            }
        }
        
        # Act
        with patch('src.config_validator.logger') as mock_logger:
            result = ConfigValidator.validate_api_credentials(config)
        
        # Assert
        assert result is False
        mock_logger.error.assert_called_with("Destination base_url and api_key are required")

    def test_validate_api_credentials_empty_dest_api_key(self):
        """Test validate_api_credentials fails when destination api_key is empty"""
        # Arrange
        config = {
            "source": {
                "base_url": "https://source.harness.io",
                "api_key": "source-key"
            },
            "destination": {
                "base_url": "https://dest.harness.io",
                "api_key": ""  # Empty string
            }
        }
        
        # Act
        with patch('src.config_validator.logger') as mock_logger:
            result = ConfigValidator.validate_api_credentials(config)
        
        # Assert
        assert result is False
        mock_logger.error.assert_called_with("Destination base_url and api_key are required")

    def test_validate_api_credentials_missing_source_base_url(self):
        """Test validate_api_credentials fails when source base_url is missing"""
        # Arrange
        config = {
            "source": {
                "api_key": "source-key"
                # Missing base_url
            },
            "destination": {
                "base_url": "https://dest.harness.io",
                "api_key": "dest-key"
            }
        }
        
        # Act
        with patch('src.config_validator.logger') as mock_logger:
            result = ConfigValidator.validate_api_credentials(config)
        
        # Assert
        assert result is False
        mock_logger.error.assert_called_with("Source base_url and api_key are required")

    def test_validate_api_credentials_missing_source_api_key(self):
        """Test validate_api_credentials fails when source api_key is missing"""
        # Arrange
        config = {
            "source": {
                "base_url": "https://source.harness.io"
                # Missing api_key
            },
            "destination": {
                "base_url": "https://dest.harness.io",
                "api_key": "dest-key"
            }
        }
        
        # Act
        with patch('src.config_validator.logger') as mock_logger:
            result = ConfigValidator.validate_api_credentials(config)
        
        # Assert
        assert result is False
        mock_logger.error.assert_called_with("Source base_url and api_key are required")

    def test_validate_config_missing_source_section(self):
        """Test validate_config fails when source section is missing"""
        # Arrange
        config = {
            "destination": {
                "base_url": "https://dest.harness.io",
                "api_key": "dest-key"
            }
            # Missing source section
        }
        
        # Act
        result = ConfigValidator.validate_config(config)
        
        # Assert
        assert result is False

    def test_validate_config_missing_destination_section(self):
        """Test validate_config fails when destination section is missing"""
        # Arrange
        config = {
            "source": {
                "base_url": "https://source.harness.io",
                "api_key": "source-key"
            }
            # Missing destination section
        }
        
        # Act
        result = ConfigValidator.validate_config(config)
        
        # Assert
        assert result is False

    def test_validate_config_success(self):
        """Test validate_config succeeds with valid configuration"""
        # Arrange
        config = {
            "source": {
                "base_url": "https://source.harness.io",
                "api_key": "source-key"
            },
            "destination": {
                "base_url": "https://dest.harness.io",
                "api_key": "dest-key"
            }
        }
        
        # Act
        result = ConfigValidator.validate_config(config)
        
        # Assert
        assert result is True
