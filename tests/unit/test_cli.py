"""
Comprehensive unit tests for CLI module

Tests command-line interface functionality with proper mocking and AAA methodology.
"""

import logging
from unittest.mock import Mock, patch
from src.logging_utils import setup_logging
from src.mode_handlers import ModeHandlers
from src.config_validator import ConfigValidator


class TestSetupLogging:
    """Test suite for setup_logging function"""

    def test_setup_logging_debug_false(self):
        """Test setup_logging with debug=False sets INFO level"""
        # Arrange & Act
        with patch('src.logging_utils.setup_output') as mock_setup_output:
            with patch('src.logging_utils.logging.getLogger') as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                setup_logging(debug=False)

        # Assert
        mock_setup_output.assert_called_once()
        mock_logger.setLevel.assert_called_with(logging.INFO)

    def test_setup_logging_debug_true(self):
        """Test setup_logging with debug=True sets DEBUG level"""
        # Arrange & Act
        with patch('src.logging_utils.setup_output') as mock_setup_output:
            with patch('src.logging_utils.logging.getLogger') as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                setup_logging(debug=True)

        # Assert
        mock_setup_output.assert_called_once()
        mock_logger.setLevel.assert_called_with(logging.DEBUG)

    def test_setup_logging_creates_file_handler(self):
        """Test setup_logging creates file handler with timestamp"""
        # Arrange & Act
        with patch('src.logging_utils.setup_output') as mock_setup_output:
            with patch('src.logging_utils.logging.getLogger') as mock_get_logger:
                with patch('src.logging_utils.logging.FileHandler') as mock_file_handler:
                    mock_logger = Mock()
                    mock_get_logger.return_value = mock_logger
                    mock_handler = Mock()
                    mock_file_handler.return_value = mock_handler

                    setup_logging(debug=False)

        # Assert
        mock_setup_output.assert_called_once()
        mock_file_handler.assert_called_once()
        mock_logger.addHandler.assert_called_with(mock_handler)

    def test_setup_logging_creates_stream_handler(self):
        """Test setup_logging sets up output orchestrator"""
        # Arrange & Act
        with patch('src.logging_utils.setup_output') as mock_setup_output:
            with patch('src.logging_utils.OutputType') as mock_output_type:
                setup_logging(debug=False, output_json=False, output_color=True)

        # Assert
        mock_setup_output.assert_called_once_with(mock_output_type.TERMINAL, True)


class TestConfigValidator:
    """Test suite for ConfigValidator class"""

    def test_validate_non_interactive_config_success(self):
        """Test validate_non_interactive_config succeeds with valid config"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }

        # Act
        result = ConfigValidator.validate_non_interactive_config(config_data)

        # Assert
        assert result is True

    def test_validate_non_interactive_config_missing_source_base_url(self):
        """Test validate_non_interactive_config fails with missing source base_url"""
        # Arrange
        config_data = {
            "source": {"api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }

        # Act
        result = ConfigValidator.validate_non_interactive_config(config_data)

        # Assert
        assert result is False

    def test_validate_non_interactive_config_missing_pipelines(self):
        """Test validate_non_interactive_config fails with missing pipelines when no CLI pipelines"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"}
        }

        # Act
        result = ConfigValidator.validate_non_interactive_config(config_data, has_cli_pipelines=False)

        # Assert
        assert result is False

    def test_validate_non_interactive_config_success_with_cli_pipelines(self):
        """Test validate_non_interactive_config succeeds without pipelines when CLI pipelines provided"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"}
        }

        # Act
        result = ConfigValidator.validate_non_interactive_config(config_data, has_cli_pipelines=True)

        # Assert
        assert result is True

    def test_validate_api_credentials_success(self):
        """Test validate_api_credentials succeeds with valid credentials"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }

        # Act
        result = ConfigValidator.validate_api_credentials(config_data)

        # Assert
        assert result is True

    def test_validate_api_credentials_missing_source_base_url(self):
        """Test validate_api_credentials fails with missing source base_url"""
        # Arrange
        config_data = {
            "source": {"api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }

        # Act
        result = ConfigValidator.validate_api_credentials(config_data)

        # Assert
        assert result is False


class TestModeHandlers:
    """Test suite for ModeHandlers class"""

    def test_get_interactive_selections_success(self):
        """Test get_interactive_selections succeeds with valid config"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }
        expected_result = {
            "source": {"org": "source-org", "project": "source-project"},
            "destination": {"org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }
        args = Mock()

        # Act
        with patch('src.config.build_complete_config', return_value=config_data):
            with patch('src.mode_handlers.ConfigValidator.validate_api_credentials', return_value=True):
                with patch('src.mode_handlers.HarnessAPIClient'):
                    with patch('src.ui.get_interactive_selections', return_value=expected_result):
                        result = ModeHandlers.get_interactive_selections("config.json", args)

        # Assert
        assert result == expected_result

    def test_get_interactive_selections_missing_api_credentials(self):
        """Test get_interactive_selections fails with missing API credentials"""
        # Arrange
        config_data = {
            "source": {"api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }
        args = Mock()

        # Act
        with patch('src.config.build_complete_config', return_value=config_data):
            with patch('src.mode_handlers.ConfigValidator.validate_api_credentials', return_value=False):
                with patch('src.mode_handlers.sys.exit', side_effect=SystemExit) as mock_exit:
                    try:
                        ModeHandlers.get_interactive_selections("config.json", args)
                    except SystemExit:
                        pass

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_get_interactive_selections_ui_fails(self):
        """Test get_interactive_selections fails when UI returns None"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }
        args = Mock()

        # Act
        with patch('src.config.build_complete_config', return_value=config_data):
            with patch('src.mode_handlers.ConfigValidator.validate_api_credentials', return_value=True):
                with patch('src.mode_handlers.HarnessAPIClient'):
                    with patch('src.ui.get_interactive_selections', return_value=None):
                        with patch('src.mode_handlers.sys.exit', side_effect=SystemExit) as mock_exit:
                            try:
                                ModeHandlers.get_interactive_selections("config.json", args)
                            except SystemExit:
                                pass

        # Assert
        mock_exit.assert_called_once_with(1)
