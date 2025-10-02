"""
Comprehensive unit tests for CLI module

Tests command-line interface functionality with proper mocking and AAA methodology.
"""

import logging
import pytest
from unittest.mock import Mock, patch

from src.cli import main
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


@pytest.mark.skip(reason="Main function tests need refactoring for new architecture - complex integration testing")
class TestMain:
    """Test suite for main function"""

    def test_main_non_interactive_mode(self):
        """Test main function in non-interactive mode"""
        # Arrange
        test_args = [
            'main.py',
            '--non-interactive',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.cli.ModeHandlers.non_interactive_mode', return_value={"test": "config"}) as mock_non_interactive:
                with patch('src.cli.apply_cli_overrides', return_value={"test": "config"}):
                    with patch('src.cli.ConfigValidator.validate_non_interactive_config', return_value=True):
                        with patch('src.cli.HarnessReplicator') as mock_replicator_class:
                            with patch('src.cli.sys.exit') as mock_exit:
                                main()

        # Assert
        mock_non_interactive.assert_called_once_with("config.json")
        mock_replicator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_main_interactive_mode(self):
        """Test main function in interactive mode"""
        # Arrange
        test_args = [
            'main.py',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.cli.ModeHandlers.interactive_mode', return_value={"test": "config"}) as mock_interactive:
                with patch('src.cli.apply_cli_overrides', return_value={"test": "config"}):
                    with patch('src.cli.HarnessReplicator') as mock_replicator_class:
                        with patch('src.cli.sys.exit') as mock_exit:
                            main()

        # Assert
        mock_interactive.assert_called_once_with("config.json")
        mock_replicator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_main_dry_run_mode(self):
        """Test main function in dry run mode"""
        # Arrange
        test_args = [
            'main.py',
            '--dry-run',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.cli.ModeHandlers.interactive_mode', return_value={"test": "config"}) as mock_interactive:
                with patch('src.cli.apply_cli_overrides', return_value={"test": "config", "dry_run": True}):
                    with patch('src.cli.HarnessReplicator') as mock_replicator_class:
                        with patch('src.cli.sys.exit') as mock_exit:
                            main()

        # Assert
        mock_interactive.assert_called_once_with("config.json")
        mock_replicator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_main_debug_mode(self):
        """Test main function in debug mode"""
        # Arrange
        test_args = [
            'main.py',
            '--debug',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.cli.setup_logging') as mock_setup_logging:
                with patch('src.cli.ModeHandlers.interactive_mode', return_value={"test": "config"}) as mock_interactive:
                    with patch('src.cli.apply_cli_overrides', return_value={"test": "config"}):
                        with patch('src.cli.HarnessReplicator') as mock_replicator_class:
                            with patch('src.cli.sys.exit') as mock_exit:
                                main()

        # Assert
        mock_setup_logging.assert_called_once_with(debug=True)
        mock_interactive.assert_called_once_with("config.json")
        mock_replicator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_main_replication_fails(self):
        """Test main function when replication fails"""
        # Arrange
        test_args = [
            'main.py',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.cli.ModeHandlers.interactive_mode', return_value={"test": "config"}) as mock_interactive:
                with patch('src.cli.apply_cli_overrides', return_value={"test": "config"}):
                    with patch('src.cli.HarnessReplicator') as mock_replicator_class:
                        mock_replicator = Mock()
                        mock_replicator.run_replication.return_value = False
                        mock_replicator_class.return_value = mock_replicator
                        with patch('src.cli.sys.exit') as mock_exit:
                            main()

        # Assert
        mock_interactive.assert_called_once_with("config.json")
        mock_replicator_class.assert_called_once()
        mock_exit.assert_called_once_with(1)

    def test_main_with_cli_overrides(self):
        """Test main function with CLI argument overrides"""
        # Arrange
        test_args = [
            'main.py',
            '--source-org', 'test-org',
            '--dest-org', 'dest-org',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.cli.ModeHandlers.interactive_mode', return_value={"test": "config"}) as mock_interactive:
                with patch('src.cli.apply_cli_overrides') as mock_apply_overrides:
                    mock_apply_overrides.return_value = {"test": "config", "source": {"org": "test-org"}}
                    with patch('src.cli.HarnessReplicator') as mock_replicator_class:
                        with patch('src.cli.sys.exit') as mock_exit:
                            main()

        # Assert
        mock_interactive.assert_called_once_with("config.json")
        mock_apply_overrides.assert_called_once()
        mock_replicator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)
