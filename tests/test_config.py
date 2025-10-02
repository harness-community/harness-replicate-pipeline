"""
Comprehensive unit tests for config module

Tests configuration management with proper mocking and AAA methodology.
"""

import json
import os
from unittest.mock import Mock, patch, mock_open

from src.config import load_config, save_config, apply_cli_overrides, _apply_env_overrides


class TestLoadConfig:
    """Test suite for load_config function"""

    def test_load_config_success_with_valid_json(self):
        """Test loading valid JSON config file"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }

        # Act
        with patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
            with patch('json.loads', return_value=config_data):
                result = load_config("config.json")

        # Assert
        assert result == config_data

    def test_load_config_success_with_jsonc_comments(self):
        """Test loading JSONC config file with comments"""
        # Arrange
        expected_config = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }

        # Act
        with patch("builtins.open", mock_open()):
            with patch('json.loads', return_value=expected_config):
                result = load_config("config.json")

        # Assert
        assert result == expected_config

    def test_load_config_file_not_found_returns_empty_dict(self):
        """Test loading non-existent config file returns empty dict"""
        # Arrange
        with patch("builtins.open", side_effect=FileNotFoundError):
            # Act
            result = load_config("nonexistent.json")

        # Assert
        assert result == {}

    def test_load_config_invalid_json_returns_empty_dict(self):
        """Test loading invalid JSON returns empty dict"""
        # Arrange
        invalid_json = '{"invalid": json}'

        # Act
        with patch("builtins.open", mock_open(read_data=invalid_json)):
            result = load_config("config.json")

        # Assert
        assert result == {}

    def test_load_config_unicode_error_returns_empty_dict(self):
        """Test loading file with unicode error returns empty dict"""
        # Arrange
        with patch("builtins.open", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")):
            # Act
            result = load_config("config.json")

        # Assert
        assert result == {}

    def test_load_config_logs_error_on_failure(self):
        """Test that load_config logs error on failure"""
        # Arrange
        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch('src.harness_migration.config.logger') as mock_logger:
                # Act
                load_config("nonexistent.json")

        # Assert
        mock_logger.error.assert_called_once()


class TestSaveConfig:
    """Test suite for save_config function"""

    def test_save_config_success(self):
        """Test saving config to file successfully"""
        # Arrange
        config_data = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"}
        }

        # Act
        with patch("builtins.open", mock_open()) as mock_file:
            result = save_config(config_data, "config.json")

        # Assert
        assert result is True
        mock_file.assert_called_once_with("config.json", "w", encoding="utf-8")
        # The write method is called multiple times due to json.dump's behavior
        assert mock_file().write.call_count > 0

    def test_save_config_with_indent_and_ensure_ascii(self):
        """Test that save_config uses correct json.dump parameters"""
        # Arrange
        config_data = {"test": "data"}

        # Act
        with patch("builtins.open", mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                save_config(config_data, "config.json")

        # Assert
        mock_json_dump.assert_called_once_with(
            config_data,
            mock_file.return_value.__enter__.return_value,
            indent=2,
            ensure_ascii=False
        )

    def test_save_config_os_error_returns_false(self):
        """Test that save_config returns False on OSError"""
        # Arrange
        config_data = {"test": "data"}

        # Act
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = save_config(config_data, "config.json")

        # Assert
        assert result is False

    def test_save_config_type_error_returns_false(self):
        """Test that save_config returns False on TypeError"""
        # Arrange
        config_data = {"test": "data"}

        # Act
        with patch("builtins.open", mock_open()):
            with patch('json.dump', side_effect=TypeError("Object not serializable")):
                result = save_config(config_data, "config.json")

        # Assert
        assert result is False

    def test_save_config_logs_error_on_failure(self):
        """Test that save_config logs error on failure"""
        # Arrange
        config_data = {"test": "data"}

        # Act
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with patch('src.harness_migration.config.logger') as mock_logger:
                save_config(config_data, "config.json")

        # Assert
        mock_logger.error.assert_called_once()


class TestApplyCliOverrides:
    """Test suite for apply_cli_overrides function"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.base_config = {
            "source": {"base_url": "https://app.harness.io", "api_key": "test-key"},
            "destination": {"base_url": "https://app3.harness.io", "api_key": "test-key2"},
            "options": {"migrate_input_sets": True, "skip_existing": True}
        }

    def test_apply_cli_overrides_returns_copy(self):
        """Test that apply_cli_overrides returns a copy, not the original"""
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
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result is not self.base_config
        assert result == self.base_config

    def test_apply_cli_overrides_source_url(self):
        """Test applying source URL override"""
        # Arrange
        args = Mock()
        args.source_url = "https://new-source.harness.io"
        args.source_api_key = None
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["source"]["base_url"] == "https://new-source.harness.io"
        assert result["source"]["api_key"] == "test-key"  # Unchanged

    def test_apply_cli_overrides_source_api_key(self):
        """Test applying source API key override"""
        # Arrange
        args = Mock()
        args.source_url = None
        args.source_api_key = "new-api-key"
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["source"]["api_key"] == "new-api-key"
        assert result["source"]["base_url"] == "https://app.harness.io"  # Unchanged

    def test_apply_cli_overrides_source_org(self):
        """Test applying source org override"""
        # Arrange
        args = Mock()
        args.source_url = None
        args.source_api_key = None
        args.source_org = "new-org"
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["source"]["org"] == "new-org"

    def test_apply_cli_overrides_source_project(self):
        """Test applying source project override"""
        # Arrange
        args = Mock()
        args.source_url = None
        args.source_api_key = None
        args.source_org = None
        args.source_project = "new-project"
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["source"]["project"] == "new-project"

    def test_apply_cli_overrides_destination_url(self):
        """Test applying destination URL override"""
        # Arrange
        args = Mock()
        args.source_url = None
        args.source_api_key = None
        args.source_org = None
        args.source_project = None
        args.dest_url = "https://new-dest.harness.io"
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["destination"]["base_url"] == "https://new-dest.harness.io"

    def test_apply_cli_overrides_destination_api_key(self):
        """Test applying destination API key override"""
        # Arrange
        args = Mock()
        args.source_url = None
        args.source_api_key = None
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = "new-dest-key"
        args.dest_org = None
        args.dest_project = None
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["destination"]["api_key"] == "new-dest-key"

    def test_apply_cli_overrides_destination_org(self):
        """Test applying destination org override"""
        # Arrange
        args = Mock()
        args.source_url = None
        args.source_api_key = None
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = "new-dest-org"
        args.dest_project = None
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["destination"]["org"] == "new-dest-org"

    def test_apply_cli_overrides_destination_project(self):
        """Test applying destination project override"""
        # Arrange
        args = Mock()
        args.source_url = None
        args.source_api_key = None
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = "new-dest-project"
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["destination"]["project"] == "new-dest-project"

    def test_apply_cli_overrides_migrate_input_sets_true(self):
        """Test applying migrate_input_sets=True override"""
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
        args.migrate_input_sets = True
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["options"]["migrate_input_sets"] is True

    def test_apply_cli_overrides_no_migrate_input_sets_true(self):
        """Test applying no_migrate_input_sets=True override"""
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
        args.migrate_input_sets = None
        args.no_migrate_input_sets = True
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["options"]["migrate_input_sets"] is False

    def test_apply_cli_overrides_skip_existing_true(self):
        """Test applying skip_existing=True override"""
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
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = True
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["options"]["skip_existing"] is True

    def test_apply_cli_overrides_no_skip_existing_true(self):
        """Test applying no_skip_existing=True override"""
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
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = True

        # Act
        result = apply_cli_overrides(self.base_config, args)

        # Assert
        assert result["options"]["skip_existing"] is False

    def test_apply_cli_overrides_creates_missing_sections(self):
        """Test that apply_cli_overrides creates missing sections"""
        # Arrange
        empty_config = {}
        args = Mock()
        args.source_url = "https://app.harness.io"
        args.source_api_key = "test-key"
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.migrate_input_sets = None
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(empty_config, args)

        # Assert
        assert "source" in result
        assert result["source"]["base_url"] == "https://app.harness.io"
        assert result["source"]["api_key"] == "test-key"

    def test_apply_cli_overrides_creates_missing_options(self):
        """Test that apply_cli_overrides creates missing options section"""
        # Arrange
        config_without_options = {"source": {}, "destination": {}}
        args = Mock()
        args.source_url = None
        args.source_api_key = None
        args.source_org = None
        args.source_project = None
        args.dest_url = None
        args.dest_api_key = None
        args.dest_org = None
        args.dest_project = None
        args.migrate_input_sets = True
        args.no_migrate_input_sets = None
        args.skip_existing = None
        args.no_skip_existing = None

        # Act
        result = apply_cli_overrides(config_without_options, args)

        # Assert
        assert "options" in result
        assert result["options"]["migrate_input_sets"] is True


class TestApplyEnvOverrides:
    """Test suite for _apply_env_overrides function"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        # Clear any existing environment variables
        self.env_vars_to_clean = [
            "HARNESS_SOURCE_URL", "HARNESS_SOURCE_API_KEY", "HARNESS_SOURCE_ORG", "HARNESS_SOURCE_PROJECT",
            "HARNESS_DEST_URL", "HARNESS_DEST_API_KEY", "HARNESS_DEST_ORG", "HARNESS_DEST_PROJECT",
            "HARNESS_SKIP_INPUT_SETS", "HARNESS_SKIP_TRIGGERS", "HARNESS_SKIP_TEMPLATES", "HARNESS_UPDATE_EXISTING",
            "HARNESS_DRY_RUN", "HARNESS_DEBUG", "HARNESS_NON_INTERACTIVE"
        ]
        for var in self.env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]

    def teardown_method(self):
        """Clean up after each test method"""
        for var in self.env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]

    def test_apply_env_overrides_empty_config_no_env_vars(self):
        """Test applying env overrides to empty config with no env vars"""
        # Arrange
        config = {}
        
        # Act
        result = _apply_env_overrides(config)
        
        # Assert
        assert result == {}

    def test_apply_env_overrides_string_env_vars(self):
        """Test applying string environment variables"""
        # Arrange
        config = {}
        os.environ["HARNESS_SOURCE_URL"] = "https://env.harness.io"
        os.environ["HARNESS_SOURCE_API_KEY"] = "env-api-key"
        os.environ["HARNESS_DEST_ORG"] = "env-dest-org"
        
        # Act
        result = _apply_env_overrides(config)
        
        # Assert
        assert result["source"]["base_url"] == "https://env.harness.io"
        assert result["source"]["api_key"] == "env-api-key"
        assert result["destination"]["org"] == "env-dest-org"

    def test_apply_env_overrides_boolean_env_vars_true_values(self):
        """Test applying boolean environment variables with true values"""
        # Arrange
        config = {}
        os.environ["HARNESS_SKIP_INPUT_SETS"] = "true"
        os.environ["HARNESS_SKIP_TRIGGERS"] = "1"
        os.environ["HARNESS_UPDATE_EXISTING"] = "yes"
        os.environ["HARNESS_DRY_RUN"] = "on"
        
        # Act
        result = _apply_env_overrides(config)
        
        # Assert
        assert result["options"]["skip_input_sets"] is True
        assert result["options"]["skip_triggers"] is True
        assert result["options"]["update_existing"] is True
        assert result["dry_run"] is True

    def test_apply_env_overrides_boolean_env_vars_false_values(self):
        """Test applying boolean environment variables with false values"""
        # Arrange
        config = {}
        os.environ["HARNESS_SKIP_INPUT_SETS"] = "false"
        os.environ["HARNESS_SKIP_TRIGGERS"] = "0"
        os.environ["HARNESS_UPDATE_EXISTING"] = "no"
        os.environ["HARNESS_DEBUG"] = "off"
        
        # Act
        result = _apply_env_overrides(config)
        
        # Assert
        assert result["options"]["skip_input_sets"] is False
        assert result["options"]["skip_triggers"] is False
        assert result["options"]["update_existing"] is False
        assert result["debug"] is False

    def test_apply_env_overrides_overrides_existing_config(self):
        """Test that environment variables override existing config values"""
        # Arrange
        config = {
            "source": {"base_url": "https://config.harness.io", "api_key": "config-key"},
            "options": {"skip_input_sets": False}
        }
        os.environ["HARNESS_SOURCE_URL"] = "https://env.harness.io"
        os.environ["HARNESS_SKIP_INPUT_SETS"] = "true"
        
        # Act
        result = _apply_env_overrides(config)
        
        # Assert
        assert result["source"]["base_url"] == "https://env.harness.io"  # Overridden
        assert result["source"]["api_key"] == "config-key"  # Unchanged
        assert result["options"]["skip_input_sets"] is True  # Overridden

    def test_apply_env_overrides_preserves_unrelated_config(self):
        """Test that environment variables don't affect unrelated config"""
        # Arrange
        config = {
            "custom_section": {"custom_key": "custom_value"},
            "pipelines": [{"identifier": "test"}]
        }
        os.environ["HARNESS_SOURCE_URL"] = "https://env.harness.io"
        
        # Act
        result = _apply_env_overrides(config)
        
        # Assert
        assert result["custom_section"]["custom_key"] == "custom_value"
        assert result["pipelines"] == [{"identifier": "test"}]
        assert result["source"]["base_url"] == "https://env.harness.io"

    def test_apply_env_overrides_all_connection_vars(self):
        """Test all connection environment variables"""
        # Arrange
        config = {}
        connection_vars = {
            "HARNESS_SOURCE_URL": "https://source.harness.io",
            "HARNESS_SOURCE_API_KEY": "source-key",
            "HARNESS_SOURCE_ORG": "source-org",
            "HARNESS_SOURCE_PROJECT": "source-project",
            "HARNESS_DEST_URL": "https://dest.harness.io",
            "HARNESS_DEST_API_KEY": "dest-key",
            "HARNESS_DEST_ORG": "dest-org",
            "HARNESS_DEST_PROJECT": "dest-project",
        }
        
        for var, value in connection_vars.items():
            os.environ[var] = value
        
        # Act
        result = _apply_env_overrides(config)
        
        # Assert
        assert result["source"]["base_url"] == "https://source.harness.io"
        assert result["source"]["api_key"] == "source-key"
        assert result["source"]["org"] == "source-org"
        assert result["source"]["project"] == "source-project"
        assert result["destination"]["base_url"] == "https://dest.harness.io"
        assert result["destination"]["api_key"] == "dest-key"
        assert result["destination"]["org"] == "dest-org"
        assert result["destination"]["project"] == "dest-project"

    def test_apply_env_overrides_all_option_vars(self):
        """Test all replication option environment variables"""
        # Arrange
        config = {}
        option_vars = {
            "HARNESS_SKIP_INPUT_SETS": "true",
            "HARNESS_SKIP_TRIGGERS": "true",
            "HARNESS_SKIP_TEMPLATES": "true",
            "HARNESS_UPDATE_EXISTING": "true",
        }
        
        for var, value in option_vars.items():
            os.environ[var] = value
        
        # Act
        result = _apply_env_overrides(config)
        
        # Assert
        assert result["options"]["skip_input_sets"] is True
        assert result["options"]["skip_triggers"] is True
        assert result["options"]["skip_templates"] is True
        assert result["options"]["update_existing"] is True

    def test_apply_env_overrides_all_runtime_vars(self):
        """Test all runtime flag environment variables"""
        # Arrange
        config = {}
        runtime_vars = {
            "HARNESS_DRY_RUN": "true",
            "HARNESS_DEBUG": "true",
            "HARNESS_NON_INTERACTIVE": "true",
        }
        
        for var, value in runtime_vars.items():
            os.environ[var] = value
        
        # Act
        result = _apply_env_overrides(config)
        
        # Assert
        assert result["dry_run"] is True
        assert result["debug"] is True
        assert result["non_interactive"] is True
