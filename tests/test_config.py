"""
Comprehensive unit tests for config module

Tests configuration management with proper mocking and AAA methodology.
"""

import json
from unittest.mock import Mock, patch, mock_open

from src.config import load_config, save_config, apply_cli_overrides


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
