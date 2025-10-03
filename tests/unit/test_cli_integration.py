"""
Simple CLI integration tests

Tests core CLI functionality with minimal mocking.
"""

import pytest
from unittest.mock import Mock, patch
import sys

from src.cli import main, _validate_final_config, _handle_config_saving


@pytest.mark.unit
class TestCLISimple:
    """Simple CLI tests focusing on core functionality"""

    def test_validate_final_config_success(self):
        """Test _validate_final_config with valid config"""
        config = {
            "source": {
                "base_url": "https://app.harness.io",
                "api_key": "key",
                "org": "org",
                "project": "project"
            },
            "destination": {
                "base_url": "https://app.harness.io",
                "api_key": "key",
                "org": "org",
                "project": "project"
            },
            "pipelines": [{"identifier": "test"}]
        }
        
        result = _validate_final_config(config, True, True)
        assert result is True

    def test_validate_final_config_missing_source_url(self):
        """Test _validate_final_config with missing source URL"""
        config = {
            "source": {
                "api_key": "key",
                "org": "org",
                "project": "project"
            },
            "destination": {
                "base_url": "https://app.harness.io",
                "api_key": "key",
                "org": "org",
                "project": "project"
            }
        }
        
        result = _validate_final_config(config, True, False)
        assert result is False

    def test_validate_final_config_interactive_mode_missing_pipelines(self):
        """Test _validate_final_config in interactive mode without pipelines"""
        config = {
            "source": {
                "base_url": "https://app.harness.io",
                "api_key": "key",
                "org": "org",
                "project": "project"
            },
            "destination": {
                "base_url": "https://app.harness.io",
                "api_key": "key",
                "org": "org",
                "project": "project"
            }
        }
        
        # Interactive mode doesn't require pipelines to be pre-configured
        result = _validate_final_config(config, False, False)
        assert result is True

    def test_handle_config_saving_no_changes(self):
        """Test _handle_config_saving when no changes detected"""
        config = {"test": "value"}
        original_config = {"test": "value"}
        args = Mock()
        args.save_config = False
        
        with patch('src.cli.save_config') as mock_save:
            _handle_config_saving(config, original_config, args)
            mock_save.assert_not_called()

    def test_handle_config_saving_with_save_flag(self):
        """Test _handle_config_saving with save flag enabled"""
        config = {"test": "new_value"}
        original_config = {"test": "old_value"}
        args = Mock()
        args.save_config = True
        args.config = "config.json"
        
        with patch('src.cli.save_config', return_value=True) as mock_save:
            _handle_config_saving(config, original_config, args)
            mock_save.assert_called_once()

    @patch('src.cli.ArgumentParser')
    def test_main_argument_parsing_error(self, mock_arg_parser):
        """Test main function when argument parsing fails"""
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.side_effect = SystemExit(2)
        mock_arg_parser.create_parser.return_value = mock_parser_instance
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    @patch('src.cli.HarnessReplicator')
    @patch('src.cli.build_complete_config')
    @patch('src.cli.load_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_basic_flow(self, mock_setup_logging, mock_arg_parser, mock_load_config,
                            mock_build_config, mock_replicator):
        """Test basic main function flow"""
        # Arrange
        mock_args = Mock()
        mock_args.config = "config.json"
        mock_args.non_interactive = True
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.create_parser.return_value = mock_parser_instance
        
        mock_load_config.return_value = {}
        
        valid_config = {
            "source": {"base_url": "https://app.harness.io", "api_key": "key", "org": "org", "project": "project"},
            "destination": {"base_url": "https://app.harness.io", "api_key": "key", "org": "org", "project": "project"},
            "pipelines": [{"identifier": "test"}],
            "debug": False,
            "output_json": False,
            "output_color": True,
            "non_interactive": True
        }
        mock_build_config.return_value = valid_config
        
        mock_replicator_instance = Mock()
        mock_replicator_instance.run_replication.return_value = True
        mock_replicator.return_value = mock_replicator_instance
        
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        
        # Verify calls
        mock_setup_logging.assert_called_once()
        mock_replicator_instance.run_replication.assert_called_once()
