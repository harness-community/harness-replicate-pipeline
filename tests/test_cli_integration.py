"""
Comprehensive integration tests for CLI

Tests full CLI workflow integration with proper mocking and AAA methodology.
"""

import pytest
from unittest.mock import Mock, patch
import sys

from src.cli import main


class TestCLIIntegration:
    """Integration tests for CLI main function"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.config_data = {
            "source": {
                "base_url": "https://source.harness.io",
                "api_key": "source-key",
                "org": "source-org",
                "project": "source-project"
            },
            "destination": {
                "base_url": "https://dest.harness.io",
                "api_key": "dest-key",
                "org": "dest-org",
                "project": "dest-project"
            },
            "options": {
                "skip_input_sets": False,
                "skip_triggers": False,
                "skip_templates": False,
                "update_existing": False,
                "output_json": False,
                "output_color": False
            },
            "pipelines": [
                {"identifier": "pipeline1", "name": "Pipeline 1"}
            ],
            "dry_run": False,
            "non_interactive": True
        }

    @patch('src.cli.HarnessReplicator')
    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_non_interactive_success(self, mock_setup_logging, mock_arg_parser,
                                          mock_build_config, mock_replicator):
        """Test main function with successful non-interactive execution"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = False
        mock_args.non_interactive = True
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        mock_build_config.return_value = self.config_data
        
        mock_replicator_instance = Mock()
        mock_replicator_instance.replicate.return_value = True
        mock_replicator.return_value = mock_replicator_instance
        
        test_args = ["config.json", "--non-interactive"]
        
        with patch.object(sys, 'argv', ['cli.py'] + test_args):
            # Act
            result = main()
        
        # Assert
        assert result == 0
        mock_setup_logging.assert_called_once_with(False, False, True)
        mock_build_config.assert_called_once_with("config.json", mock_args)
        mock_replicator.assert_called_once_with(self.config_data)
        mock_replicator_instance.replicate.assert_called_once()

    @patch('src.cli.ModeHandlers')
    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_interactive_success(self, mock_setup_logging, mock_arg_parser, 
                                    mock_build_config, mock_mode_handlers):
        """Test main function with successful interactive execution"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = False
        mock_args.non_interactive = False
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        mock_build_config.return_value = self.config_data
        
        interactive_config = self.config_data.copy()
        interactive_config["pipelines"] = [{"identifier": "selected-pipeline"}]
        
        mock_mode_handlers.get_interactive_selections.return_value = interactive_config
        
        with patch('src.cli.HarnessReplicator') as mock_replicator:
            mock_replicator_instance = Mock()
            mock_replicator_instance.replicate.return_value = True
            mock_replicator.return_value = mock_replicator_instance
            
            test_args = ["config.json"]
            
            with patch.object(sys, 'argv', ['cli.py'] + test_args):
                # Act
                result = main()
        
        # Assert
        assert result == 0
        mock_mode_handlers.get_interactive_selections.assert_called_once_with("config.json", mock_args)

    @patch('src.cli.ConfigValidator')
    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_config_validation_fails(self, mock_setup_logging, mock_arg_parser, 
                                        mock_build_config, mock_config_validator):
        """Test main function when config validation fails"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = False
        mock_args.non_interactive = True
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        mock_build_config.return_value = self.config_data
        
        mock_config_validator.validate_config.return_value = False
        
        with patch('src.cli.sys.exit') as mock_exit:
            test_args = ["config.json", "--non-interactive"]
            
            with patch.object(sys, 'argv', ['cli.py'] + test_args):
                # Act
                main()
        
        # Assert
        mock_exit.assert_called_once_with(1)

    @patch('src.cli.HarnessReplicator')
    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_replication_fails(self, mock_setup_logging, mock_arg_parser, 
                                  mock_build_config, mock_replicator):
        """Test main function when replication fails"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = False
        mock_args.non_interactive = True
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        mock_build_config.return_value = self.config_data
        
        mock_replicator_instance = Mock()
        mock_replicator_instance.replicate.return_value = False
        mock_replicator.return_value = mock_replicator_instance
        
        test_args = ["config.json", "--non-interactive"]
        
        with patch.object(sys, 'argv', ['cli.py'] + test_args):
            # Act
            result = main()
        
        # Assert
        assert result == 1

    @patch('src.cli.save_config')
    @patch('src.cli.HarnessReplicator')
    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_with_save_config_flag(self, mock_setup_logging, mock_arg_parser, 
                                      mock_build_config, mock_replicator, mock_save_config):
        """Test main function with save-config flag"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = False
        mock_args.non_interactive = True
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = True
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        mock_build_config.return_value = self.config_data
        
        mock_replicator_instance = Mock()
        mock_replicator_instance.replicate.return_value = True
        mock_replicator.return_value = mock_replicator_instance
        
        test_args = ["config.json", "--non-interactive", "--save-config"]
        
        with patch.object(sys, 'argv', ['cli.py'] + test_args):
            # Act
            result = main()
        
        # Assert
        assert result == 0
        mock_save_config.assert_called_once_with(self.config_data, "config.json")

    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_debug_mode(self, mock_setup_logging, mock_arg_parser, mock_build_config):
        """Test main function with debug mode enabled"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = True
        mock_args.dry_run = False
        mock_args.non_interactive = True
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        mock_build_config.return_value = self.config_data
        
        with patch('src.cli.HarnessReplicator') as mock_replicator:
            mock_replicator_instance = Mock()
            mock_replicator_instance.replicate.return_value = True
            mock_replicator.return_value = mock_replicator_instance
            
            test_args = ["config.json", "--debug", "--non-interactive"]
            
            with patch.object(sys, 'argv', ['cli.py'] + test_args):
                # Act
                result = main()
        
        # Assert
        assert result == 0
        mock_setup_logging.assert_called_once_with(True, False, True)

    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_output_json_mode(self, mock_setup_logging, mock_arg_parser, mock_build_config):
        """Test main function with JSON output mode"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = False
        mock_args.non_interactive = True
        mock_args.output_json = True
        mock_args.output_color = False
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        mock_build_config.return_value = self.config_data
        
        with patch('src.cli.HarnessReplicator') as mock_replicator:
            mock_replicator_instance = Mock()
            mock_replicator_instance.replicate.return_value = True
            mock_replicator.return_value = mock_replicator_instance
            
            test_args = ["config.json", "--output-json", "--non-interactive"]
            
            with patch.object(sys, 'argv', ['cli.py'] + test_args):
                # Act
                result = main()
        
        # Assert
        assert result == 0
        mock_setup_logging.assert_called_once_with(False, True, False)

    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_dry_run_mode(self, mock_setup_logging, mock_arg_parser, mock_build_config):
        """Test main function with dry run mode"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = True
        mock_args.non_interactive = True
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        dry_run_config = self.config_data.copy()
        dry_run_config["dry_run"] = True
        mock_build_config.return_value = dry_run_config
        
        with patch('src.cli.HarnessReplicator') as mock_replicator:
            mock_replicator_instance = Mock()
            mock_replicator_instance.replicate.return_value = True
            mock_replicator.return_value = mock_replicator_instance
            
            test_args = ["config.json", "--dry-run", "--non-interactive"]
            
            with patch.object(sys, 'argv', ['cli.py'] + test_args):
                # Act
                result = main()
        
        # Assert
        assert result == 0
        mock_replicator.assert_called_once_with(dry_run_config)

    @patch('src.cli.ArgumentParser')
    def test_main_argument_parsing_error(self, mock_arg_parser):
        """Test main function when argument parsing fails"""
        # Arrange
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.side_effect = SystemExit(2)
        mock_arg_parser.return_value = mock_parser_instance
        
        test_args = ["--invalid-argument"]
        
        with patch.object(sys, 'argv', ['cli.py'] + test_args):
            # Act & Assert
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 2

    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_exception_handling(self, mock_setup_logging, mock_arg_parser, mock_build_config):
        """Test main function handles unexpected exceptions"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = False
        mock_args.non_interactive = True
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        mock_build_config.side_effect = Exception("Unexpected error")
        
        test_args = ["config.json", "--non-interactive"]
        
        with patch.object(sys, 'argv', ['cli.py'] + test_args):
            # Act
            result = main()
        
        # Assert
        assert result == 1

    @patch('src.cli.ModeHandlers')
    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_interactive_mode_fails(self, mock_setup_logging, mock_arg_parser, 
                                       mock_build_config, mock_mode_handlers):
        """Test main function when interactive mode fails"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = False
        mock_args.non_interactive = False
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        mock_build_config.return_value = self.config_data
        
        mock_mode_handlers.get_interactive_selections.return_value = None
        
        with patch('src.cli.sys.exit') as mock_exit:
            test_args = ["config.json"]
            
            with patch.object(sys, 'argv', ['cli.py'] + test_args):
                # Act
                main()
        
        # Assert
        mock_exit.assert_called_once_with(1)

    @patch('src.cli.load_config')
    @patch('src.cli.save_config')
    @patch('src.cli.HarnessReplicator')
    @patch('src.cli.build_complete_config')
    @patch('src.cli.ArgumentParser')
    @patch('src.cli.setup_logging')
    def test_main_intelligent_config_saving(self, mock_setup_logging, mock_arg_parser, 
                                           mock_build_config, mock_replicator, 
                                           mock_save_config, mock_load_config):
        """Test main function with intelligent config saving (only when different)"""
        # Arrange
        mock_args = Mock()
        mock_args.config_file = "config.json"
        mock_args.debug = False
        mock_args.dry_run = False
        mock_args.non_interactive = True
        mock_args.output_json = False
        mock_args.output_color = True
        mock_args.save_config = False
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_arg_parser.return_value = mock_parser_instance
        
        # Mock different configs to trigger saving
        original_config = {"source": {"api_key": "old-key"}}
        updated_config = {"source": {"api_key": "new-key"}}
        
        mock_load_config.return_value = original_config
        mock_build_config.return_value = updated_config
        
        mock_replicator_instance = Mock()
        mock_replicator_instance.replicate.return_value = True
        mock_replicator.return_value = mock_replicator_instance
        
        test_args = ["config.json", "--non-interactive"]
        
        with patch.object(sys, 'argv', ['cli.py'] + test_args):
            # Act
            result = main()
        
        # Assert
        assert result == 0
        # Config should be saved because it's different
        mock_save_config.assert_called_once_with(updated_config, "config.json")
