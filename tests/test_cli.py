"""
Comprehensive unit tests for CLI module

Tests command-line interface functionality with proper mocking and AAA methodology.
"""

from unittest.mock import Mock, patch

from src.harness_migration.cli import (
    setup_logging, non_interactive_mode, hybrid_mode, main
)


class TestSetupLogging:
    """Test suite for setup_logging function"""

    def test_setup_logging_debug_false(self):
        """Test setup_logging with debug=False sets INFO level"""
        # Arrange & Act
        with patch('src.harness_migration.cli.logging.basicConfig') as mock_basic_config:
            setup_logging(debug=False)

        # Assert
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 20  # INFO level

    def test_setup_logging_debug_true(self):
        """Test setup_logging with debug=True sets DEBUG level"""
        # Arrange & Act
        with patch('src.harness_migration.cli.logging.basicConfig') as mock_basic_config:
            setup_logging(debug=True)

        # Assert
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 10  # DEBUG level

    def test_setup_logging_creates_file_handler(self):
        """Test setup_logging creates file handler with timestamp"""
        # Arrange & Act
        with patch('src.harness_migration.cli.logging.basicConfig') as mock_basic_config:
            with patch('src.harness_migration.cli.datetime') as mock_datetime:
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
        with patch('src.harness_migration.cli.logging.basicConfig') as mock_basic_config:
            setup_logging(debug=False)

        # Assert
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        handlers = call_args[1]['handlers']
        assert len(handlers) == 2  # FileHandler and StreamHandler


class TestNonInteractiveMode:
    """Test suite for non_interactive_mode function"""

    def test_non_interactive_mode_success(self):
        """Test non_interactive_mode succeeds with valid config"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            result = non_interactive_mode("config.json")

        # Assert
        assert result == config_data

    def test_non_interactive_mode_missing_source_base_url(self):
        """Test non_interactive_mode fails with missing source base_url"""
        # Arrange
        config_data = {
            "source": {"api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                non_interactive_mode("config.json")

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_non_interactive_mode_missing_source_api_key(self):
        """Test non_interactive_mode fails with missing source api_key"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                non_interactive_mode("config.json")

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_non_interactive_mode_missing_destination_base_url(self):
        """Test non_interactive_mode fails with missing destination base_url"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"api_key": "test-key2", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                non_interactive_mode("config.json")

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_non_interactive_mode_missing_destination_api_key(self):
        """Test non_interactive_mode fails with missing destination api_key"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "org": "dest-org", "project": "dest-project"},
            "pipelines": [{"identifier": "pipeline1"}]
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                non_interactive_mode("config.json")

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_non_interactive_mode_missing_pipelines(self):
        """Test non_interactive_mode fails with missing pipelines"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key", "org": "source-org", "project": "source-project"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2", "org": "dest-org", "project": "dest-project"}
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                non_interactive_mode("config.json")

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_non_interactive_mode_config_load_fails(self):
        """Test non_interactive_mode fails when config load fails"""
        # Arrange
        with patch('src.harness_migration.cli.load_config', return_value={}):
            with patch('src.harness_migration.cli.sys.exit', side_effect=SystemExit) as mock_exit:
                try:
                    # Act
                    non_interactive_mode("config.json")
                except SystemExit:
                    pass

        # Assert
        mock_exit.assert_called_once_with(1)


class TestHybridMode:
    """Test suite for hybrid_mode function"""

    def test_hybrid_mode_success(self):
        """Test hybrid_mode succeeds with valid config"""
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
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.HarnessAPIClient'):
                with patch('src.harness_migration.cli.get_selections_from_clients', return_value=expected_result):
                    result = hybrid_mode("config.json")

        # Assert
        assert result == expected_result

    def test_hybrid_mode_missing_source_base_url(self):
        """Test hybrid_mode fails with missing source base_url"""
        # Arrange
        config_data = {
            "source": {"api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.sys.exit', side_effect=SystemExit) as mock_exit:
                try:
                    hybrid_mode("config.json")
                except SystemExit:
                    pass

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_hybrid_mode_missing_source_api_key(self):
        """Test hybrid_mode fails with missing source api_key"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.sys.exit', side_effect=SystemExit) as mock_exit:
                try:
                    hybrid_mode("config.json")
                except SystemExit:
                    pass

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_hybrid_mode_missing_destination_base_url(self):
        """Test hybrid_mode fails with missing destination base_url"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"api_key": "test-key2"}
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.sys.exit', side_effect=SystemExit) as mock_exit:
                try:
                    hybrid_mode("config.json")
                except SystemExit:
                    pass

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_hybrid_mode_missing_destination_api_key(self):
        """Test hybrid_mode fails with missing destination api_key"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io"}
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.sys.exit', side_effect=SystemExit) as mock_exit:
                try:
                    hybrid_mode("config.json")
                except SystemExit:
                    pass

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_hybrid_mode_selections_fail(self):
        """Test hybrid_mode fails when selections fail"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }

        # Act
        with patch('src.harness_migration.cli.load_config', return_value=config_data):
            with patch('src.harness_migration.cli.HarnessAPIClient'):
                with patch('src.harness_migration.cli.get_selections_from_clients', return_value={}):
                    with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                        hybrid_mode("config.json")

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_hybrid_mode_config_load_fails(self):
        """Test hybrid_mode fails when config load fails"""
        # Arrange
        with patch('src.harness_migration.cli.load_config', return_value={}):
            with patch('src.harness_migration.cli.sys.exit', side_effect=SystemExit) as mock_exit:
                try:
                    # Act
                    hybrid_mode("config.json")
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
            'harness_migration.py',
            '--non-interactive',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.harness_migration.cli.non_interactive_mode', return_value={"test": "config"}) as mock_non_interactive:
                with patch('src.harness_migration.cli.apply_cli_overrides', return_value={"test": "config"}):
                    with patch('src.harness_migration.cli.HarnessMigrator') as mock_migrator_class:
                        with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                            main()

        # Assert
        mock_non_interactive.assert_called_once_with("config.json")
        mock_migrator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_main_hybrid_mode(self):
        """Test main function in hybrid mode"""
        # Arrange
        test_args = [
            'harness_migration.py',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.harness_migration.cli.hybrid_mode', return_value={"test": "config"}) as mock_hybrid:
                with patch('src.harness_migration.cli.apply_cli_overrides', return_value={"test": "config"}):
                    with patch('src.harness_migration.cli.HarnessMigrator') as mock_migrator_class:
                        with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                            main()

        # Assert
        mock_hybrid.assert_called_once_with("config.json")
        mock_migrator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_main_dry_run_mode(self):
        """Test main function in dry run mode"""
        # Arrange
        test_args = [
            'harness_migration.py',
            '--dry-run',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.harness_migration.cli.hybrid_mode', return_value={"test": "config"}) as mock_hybrid:
                with patch('src.harness_migration.cli.apply_cli_overrides', return_value={"test": "config", "dry_run": True}):
                    with patch('src.harness_migration.cli.HarnessMigrator') as mock_migrator_class:
                        with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                            main()

        # Assert
        mock_hybrid.assert_called_once_with("config.json")
        mock_migrator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_main_debug_mode(self):
        """Test main function in debug mode"""
        # Arrange
        test_args = [
            'harness_migration.py',
            '--debug',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.harness_migration.cli.setup_logging') as mock_setup_logging:
                with patch('src.harness_migration.cli.hybrid_mode', return_value={"test": "config"}) as mock_hybrid:
                    with patch('src.harness_migration.cli.apply_cli_overrides', return_value={"test": "config"}):
                        with patch('src.harness_migration.cli.HarnessMigrator') as mock_migrator_class:
                            with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                                main()

        # Assert
        mock_setup_logging.assert_called_once_with(debug=True)
        mock_hybrid.assert_called_once_with("config.json")
        mock_migrator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_main_migration_fails(self):
        """Test main function when migration fails"""
        # Arrange
        test_args = [
            'harness_migration.py',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.harness_migration.cli.hybrid_mode', return_value={"test": "config"}) as mock_hybrid:
                with patch('src.harness_migration.cli.apply_cli_overrides', return_value={"test": "config"}):
                    with patch('src.harness_migration.cli.HarnessMigrator') as mock_migrator_class:
                        mock_migrator = Mock()
                        mock_migrator.run_migration.return_value = False
                        mock_migrator_class.return_value = mock_migrator
                        with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                            main()

        # Assert
        mock_hybrid.assert_called_once_with("config.json")
        mock_migrator_class.assert_called_once()
        mock_exit.assert_called_once_with(1)

    def test_main_with_cli_overrides(self):
        """Test main function with CLI argument overrides"""
        # Arrange
        test_args = [
            'harness_migration.py',
            '--source-org', 'test-org',
            '--dest-org', 'dest-org',
            '--config', 'config.json'
        ]

        # Act
        with patch('sys.argv', test_args):
            with patch('src.harness_migration.cli.hybrid_mode', return_value={"test": "config"}) as mock_hybrid:
                with patch('src.harness_migration.cli.apply_cli_overrides') as mock_apply_overrides:
                    mock_apply_overrides.return_value = {"test": "config", "source": {"org": "test-org"}}
                    with patch('src.harness_migration.cli.HarnessMigrator') as mock_migrator_class:
                        with patch('src.harness_migration.cli.sys.exit') as mock_exit:
                            main()

        # Assert
        mock_hybrid.assert_called_once_with("config.json")
        mock_apply_overrides.assert_called_once()
        mock_migrator_class.assert_called_once()
        mock_exit.assert_called_once_with(0)
