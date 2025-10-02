"""
Comprehensive unit tests for Config system

Tests configuration merging, environment variables, and edge cases with proper mocking and AAA methodology.
"""

import os
from unittest.mock import Mock, patch, mock_open

from src.config import build_complete_config, save_config, _apply_env_overrides


class TestBuildCompleteConfig:
    """Unit tests for build_complete_config function"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.base_config = {
            "source": {
                "base_url": "https://app.harness.io",
                "api_key": "source-key",
                "org": "source-org",
                "project": "source-project"
            },
            "destination": {
                "base_url": "https://app3.harness.io",
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
            }
        }

    def test_build_complete_config_file_only(self):
        """Test build_complete_config with only config file"""
        # Arrange
        args = Mock()
        args.source_url = None
        args.source_api_key = None
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.skip_input_sets = None
        args.no_skip_input_sets = None
        args.skip_triggers = None
        args.no_skip_triggers = None
        args.skip_templates = None
        args.no_skip_templates = None
        args.update_existing = None
        args.no_update_existing = None
        args.output_json = None
        args.no_output_json = None
        args.output_color = None
        args.no_output_color = None
        args.pipelines = []
        
        with patch('src.config.load_config', return_value=self.base_config):
            with patch.dict(os.environ, {}, clear=True):
                # Act
                result = build_complete_config("config.json", args)
        
        # Assert
        assert result == self.base_config

    def test_build_complete_config_with_env_overrides(self):
        """Test build_complete_config with environment variable overrides"""
        # Arrange
        args = Mock()
        args.source_url = None
        args.source_api_key = None
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.skip_input_sets = None
        args.no_skip_input_sets = None
        args.skip_triggers = None
        args.no_skip_triggers = None
        args.skip_templates = None
        args.no_skip_templates = None
        args.update_existing = None
        args.no_update_existing = None
        args.output_json = None
        args.no_output_json = None
        args.output_color = None
        args.no_output_color = None
        args.pipelines = []
        
        env_vars = {
            "HARNESS_SOURCE_URL": "https://env-source.harness.io",
            "HARNESS_SOURCE_API_KEY": "env-source-key",
            "HARNESS_DEST_URL": "https://env-dest.harness.io",
            "HARNESS_SKIP_INPUT_SETS": "true",
            "HARNESS_UPDATE_EXISTING": "true"
        }
        
        with patch('src.config.load_config', return_value=self.base_config):
            with patch.dict(os.environ, env_vars, clear=True):
                # Act
                result = build_complete_config("config.json", args)
        
        # Assert
        assert result["source"]["base_url"] == "https://env-source.harness.io"
        assert result["source"]["api_key"] == "env-source-key"
        assert result["destination"]["base_url"] == "https://env-dest.harness.io"
        assert result["options"]["skip_input_sets"] is True
        assert result["options"]["update_existing"] is True

    def test_build_complete_config_with_cli_overrides(self):
        """Test build_complete_config with CLI argument overrides"""
        # Arrange
        args = Mock()
        args.source_url = "https://cli-source.harness.io"
        args.source_api_key = "cli-source-key"
        args.source_org = "cli-source-org"
        args.source_project = "cli-source-project"
        args.dest_url = "https://cli-dest.harness.io"
        args.dest_api_key = "cli-dest-key"
        args.dest_org = "cli-dest-org"
        args.dest_project = "cli-dest-project"
        args.skip_input_sets = True
        args.no_skip_input_sets = None
        args.skip_triggers = None
        args.no_skip_triggers = True
        args.skip_templates = True
        args.no_skip_templates = None
        args.update_existing = None
        args.no_update_existing = True
        args.output_json = True
        args.no_output_json = None
        args.output_color = None
        args.no_output_color = True
        args.pipelines = [{"identifier": "cli-pipeline"}]
        
        with patch('src.config.load_config', return_value=self.base_config):
            with patch.dict(os.environ, {}, clear=True):
                # Act
                result = build_complete_config("config.json", args)
        
        # Assert
        assert result["source"]["base_url"] == "https://cli-source.harness.io"
        assert result["source"]["api_key"] == "cli-source-key"
        assert result["source"]["org"] == "cli-source-org"
        assert result["source"]["project"] == "cli-source-project"
        assert result["destination"]["base_url"] == "https://cli-dest.harness.io"
        assert result["destination"]["api_key"] == "cli-dest-key"
        assert result["destination"]["org"] == "cli-dest-org"
        assert result["destination"]["project"] == "cli-dest-project"
        assert result["options"]["skip_input_sets"] is True
        assert result["options"]["skip_triggers"] is False
        assert result["options"]["skip_templates"] is True
        assert result["options"]["update_existing"] is False
        assert result["options"]["output_json"] is True
        assert result["options"]["output_color"] is False
        assert result["pipelines"] == [{"identifier": "cli-pipeline"}]

    def test_build_complete_config_priority_order(self):
        """Test build_complete_config respects priority order: CLI > Env > Config"""
        # Arrange
        args = Mock()
        args.source_url = "https://cli-source.harness.io"  # CLI override
        args.source_api_key = None  # No CLI override
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.skip_input_sets = None
        args.no_skip_input_sets = None
        args.skip_triggers = None
        args.no_skip_triggers = None
        args.skip_templates = None
        args.no_skip_templates = None
        args.update_existing = None
        args.no_update_existing = None
        args.output_json = None
        args.no_output_json = None
        args.output_color = None
        args.no_output_color = None
        args.pipelines = []
        
        env_vars = {
            "HARNESS_SOURCE_URL": "https://env-source.harness.io",  # Should be overridden by CLI
            "HARNESS_SOURCE_API_KEY": "env-source-key",  # Should be used (no CLI override)
            "HARNESS_SKIP_INPUT_SETS": "true"  # Should be used (no CLI override)
        }
        
        with patch('src.config.load_config', return_value=self.base_config):
            with patch.dict(os.environ, env_vars, clear=True):
                # Act
                result = build_complete_config("config.json", args)
        
        # Assert
        # CLI takes precedence over env
        assert result["source"]["base_url"] == "https://cli-source.harness.io"
        # Env takes precedence over config
        assert result["source"]["api_key"] == "env-source-key"
        assert result["options"]["skip_input_sets"] is True
        # Config value used when no overrides
        assert result["destination"]["base_url"] == "https://app3.harness.io"

    def test_build_complete_config_empty_config_file(self):
        """Test build_complete_config with empty config file"""
        # Arrange
        args = Mock()
        args.source_url = "https://cli-source.harness.io"
        args.source_api_key = "cli-source-key"
        args.source_org = "cli-source-org"
        args.source_project = "cli-source-project"
        args.dest_url = "https://cli-dest.harness.io"
        args.dest_api_key = "cli-dest-key"
        args.dest_org = "cli-dest-org"
        args.dest_project = "cli-dest-project"
        args.skip_input_sets = None
        args.no_skip_input_sets = None
        args.skip_triggers = None
        args.no_skip_triggers = None
        args.skip_templates = None
        args.no_skip_templates = None
        args.update_existing = None
        args.no_update_existing = None
        args.output_json = None
        args.no_output_json = None
        args.output_color = None
        args.no_output_color = None
        args.pipelines = []
        
        with patch('src.config.load_config', return_value={}):
            with patch.dict(os.environ, {}, clear=True):
                # Act
                result = build_complete_config("config.json", args)
        
        # Assert
        assert result["source"]["base_url"] == "https://cli-source.harness.io"
        assert result["source"]["api_key"] == "cli-source-key"
        assert result["source"]["org"] == "cli-source-org"
        assert result["source"]["project"] == "cli-source-project"
        assert result["destination"]["base_url"] == "https://cli-dest.harness.io"
        assert result["destination"]["api_key"] == "cli-dest-key"
        assert result["destination"]["org"] == "cli-dest-org"
        assert result["destination"]["project"] == "cli-dest-project"


class TestApplyEnvOverrides:
    """Unit tests for _apply_env_overrides function"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.base_config = {
            "source": {
                "base_url": "https://app.harness.io",
                "api_key": "source-key"
            },
            "destination": {
                "base_url": "https://app3.harness.io",
                "api_key": "dest-key"
            },
            "options": {
                "skip_input_sets": False,
                "update_existing": False
            }
        }

    def test_apply_env_overrides_all_variables(self):
        """Test _apply_env_overrides with all environment variables set"""
        # Arrange
        env_vars = {
            "HARNESS_SOURCE_URL": "https://env-source.harness.io",
            "HARNESS_SOURCE_API_KEY": "env-source-key",
            "HARNESS_SOURCE_ORG": "env-source-org",
            "HARNESS_SOURCE_PROJECT": "env-source-project",
            "HARNESS_DEST_URL": "https://env-dest.harness.io",
            "HARNESS_DEST_API_KEY": "env-dest-key",
            "HARNESS_DEST_ORG": "env-dest-org",
            "HARNESS_DEST_PROJECT": "env-dest-project",
            "HARNESS_SKIP_INPUT_SETS": "true",
            "HARNESS_SKIP_TRIGGERS": "false",
            "HARNESS_SKIP_TEMPLATES": "true",
            "HARNESS_UPDATE_EXISTING": "true",
            "HARNESS_OUTPUT_JSON": "true",
            "HARNESS_OUTPUT_COLOR": "false"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Act
            result = _apply_env_overrides(self.base_config)
        
        # Assert
        assert result["source"]["base_url"] == "https://env-source.harness.io"
        assert result["source"]["api_key"] == "env-source-key"
        assert result["source"]["org"] == "env-source-org"
        assert result["source"]["project"] == "env-source-project"
        assert result["destination"]["base_url"] == "https://env-dest.harness.io"
        assert result["destination"]["api_key"] == "env-dest-key"
        assert result["destination"]["org"] == "env-dest-org"
        assert result["destination"]["project"] == "env-dest-project"
        assert result["options"]["skip_input_sets"] is True
        assert result["options"]["skip_triggers"] is False
        assert result["options"]["skip_templates"] is True
        assert result["options"]["update_existing"] is True
        assert result["options"]["output_json"] is True
        assert result["options"]["output_color"] is False

    def test_apply_env_overrides_boolean_parsing(self):
        """Test _apply_env_overrides correctly parses boolean values"""
        # Arrange
        env_vars = {
            "HARNESS_SKIP_INPUT_SETS": "True",
            "HARNESS_SKIP_TRIGGERS": "FALSE",
            "HARNESS_SKIP_TEMPLATES": "1",
            "HARNESS_UPDATE_EXISTING": "0",
            "HARNESS_OUTPUT_JSON": "yes",
            "HARNESS_OUTPUT_COLOR": "no"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Act
            result = _apply_env_overrides(self.base_config)
        
        # Assert
        assert result["options"]["skip_input_sets"] is True
        assert result["options"]["skip_triggers"] is False
        assert result["options"]["skip_templates"] is True
        assert result["options"]["update_existing"] is False
        assert result["options"]["output_json"] is True
        assert result["options"]["output_color"] is False

    def test_apply_env_overrides_no_env_variables(self):
        """Test _apply_env_overrides with no environment variables"""
        # Arrange
        with patch.dict(os.environ, {}, clear=True):
            # Act
            result = _apply_env_overrides(self.base_config)
        
        # Assert
        assert result == self.base_config

    def test_apply_env_overrides_partial_variables(self):
        """Test _apply_env_overrides with only some environment variables"""
        # Arrange
        env_vars = {
            "HARNESS_SOURCE_URL": "https://env-source.harness.io",
            "HARNESS_SKIP_INPUT_SETS": "true"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Act
            result = _apply_env_overrides(self.base_config)
        
        # Assert
        assert result["source"]["base_url"] == "https://env-source.harness.io"
        assert result["source"]["api_key"] == "source-key"  # Unchanged
        assert result["options"]["skip_input_sets"] is True
        assert result["options"]["update_existing"] is False  # Unchanged

    def test_apply_env_overrides_creates_missing_sections(self):
        """Test _apply_env_overrides creates missing config sections"""
        # Arrange
        minimal_config = {}
        env_vars = {
            "HARNESS_SOURCE_URL": "https://env-source.harness.io",
            "HARNESS_DEST_API_KEY": "env-dest-key",
            "HARNESS_SKIP_INPUT_SETS": "true"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Act
            result = _apply_env_overrides(minimal_config)
        
        # Assert
        assert result["source"]["base_url"] == "https://env-source.harness.io"
        assert result["destination"]["api_key"] == "env-dest-key"
        assert result["options"]["skip_input_sets"] is True


class TestSaveConfigScenarios:
    """Unit tests for save_config edge cases and scenarios"""

    def test_save_config_creates_directory(self):
        """Test save_config creates directory if it doesn't exist"""
        # Arrange
        config_data = {"test": "data"}
        config_path = "nonexistent/dir/config.json"
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("os.makedirs") as mock_makedirs:
                with patch("os.path.dirname", return_value="nonexistent/dir"):
                    with patch("os.path.exists", return_value=False):
                        # Act
                        save_config(config_data, config_path)
        
        # Assert
        mock_makedirs.assert_called_once_with("nonexistent/dir", exist_ok=True)
        mock_file.assert_called_once_with(config_path, 'w', encoding='utf-8')

    def test_save_config_directory_exists(self):
        """Test save_config when directory already exists"""
        # Arrange
        config_data = {"test": "data"}
        config_path = "existing/dir/config.json"
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("os.makedirs") as mock_makedirs:
                with patch("os.path.dirname", return_value="existing/dir"):
                    with patch("os.path.exists", return_value=True):
                        # Act
                        save_config(config_data, config_path)
        
        # Assert
        mock_makedirs.assert_not_called()
        mock_file.assert_called_once_with(config_path, 'w', encoding='utf-8')

    def test_save_config_complex_data_structure(self):
        """Test save_config with complex nested data structure"""
        # Arrange
        config_data = {
            "source": {
                "base_url": "https://app.harness.io",
                "api_key": "key",
                "nested": {
                    "deep": {
                        "value": "test"
                    }
                }
            },
            "options": {
                "flags": [True, False, True],
                "mapping": {
                    "key1": "value1",
                    "key2": "value2"
                }
            }
        }
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("os.makedirs"):
                with patch("os.path.dirname", return_value="dir"):
                    with patch("os.path.exists", return_value=True):
                        # Act
                        save_config(config_data, "config.json")
        
        # Assert
        mock_file.assert_called_once()
        # Verify JSON was written
        handle = mock_file()
        written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
        import json
        parsed_data = json.loads(written_content)
        assert parsed_data == config_data
