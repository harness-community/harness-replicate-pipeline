"""
Comprehensive unit tests for CLI module

Tests command-line interface functionality with proper mocking and AAA methodology.
"""

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
        with patch('src.logging_utils.logging.basicConfig') as mock_basic_config:
            setup_logging(debug=False)

        # Assert
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 20  # INFO level

    def test_setup_logging_debug_true(self):
        """Test setup_logging with debug=True sets DEBUG level"""
        # Arrange & Act
        with patch('src.logging_utils.logging.basicConfig') as mock_basic_config:
            setup_logging(debug=True)

        # Assert
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 10  # DEBUG level

    def test_setup_logging_creates_file_handler(self):
        """Test setup_logging creates file handler with timestamp"""
        # Arrange & Act
        with patch('src.logging_utils.logging.basicConfig') as mock_basic_config:
            with patch('src.logging_utils.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20231201_120000"
                setup_logging(debug=False)

        # Assert
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        handlers = call_args[1]['handlers']
        assert len(handlers) == 2  # FileHandler and StreamHandler

    def test_setup_logging_creates_stream_handler(self):
        """Test setup_logging creates stream handler"""
        # Arrange & Act
        with patch('src.logging_utils.logging.basicConfig') as mock_basic_config:
            setup_logging(debug=False)

        # Assert
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        handlers = call_args[1]['handlers']
        assert len(handlers) == 2  # FileHandler and StreamHandler


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

    def test_non_interactive_mode_success(self):
        """Test non_interactive_mode succeeds with valid config"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }

        # Act
        with patch('src.mode_handlers.load_config', return_value=config_data):
            result = ModeHandlers.non_interactive_mode("config.json")

        # Assert
        assert result == config_data

    def test_non_interactive_mode_config_load_fails(self):
        """Test non_interactive_mode fails when config load fails"""
        # Arrange
        with patch('src.mode_handlers.load_config', return_value={}):
            with patch('src.mode_handlers.sys.exit', side_effect=SystemExit) as mock_exit:
                try:
                    # Act
                    ModeHandlers.non_interactive_mode("config.json")
                except SystemExit:
                    pass

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_interactive_mode_success(self):
        """Test interactive_mode succeeds with valid config"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }
        expected_result = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }

        # Act
        with patch('src.mode_handlers.load_config', return_value=config_data):
            with patch('src.mode_handlers.HarnessAPIClient'):
                with patch('src.ui.get_interactive_selections', return_value=expected_result):
                    result = ModeHandlers.interactive_mode("config.json")

        # Assert
        assert result == expected_result

    def test_interactive_mode_missing_source_base_url(self):
        """Test interactive_mode fails with missing source base_url"""
        # Arrange
        config_data = {
            "source": {"api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }

        # Act
        with patch('src.mode_handlers.load_config', return_value=config_data):
            with patch('src.mode_handlers.sys.exit', side_effect=SystemExit) as mock_exit:
                try:
                    ModeHandlers.interactive_mode("config.json")
                except SystemExit:
                    pass

        # Assert
        mock_exit.assert_called_once_with(1)


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
