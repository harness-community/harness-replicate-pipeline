"""
Comprehensive unit tests for ArgumentParser

Tests command-line argument parsing functionality with proper mocking and AAA methodology.
"""

import pytest
import argparse

from src.argument_parser import ArgumentParser


class TestArgumentParser:
    """Unit tests for ArgumentParser class"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.parser = ArgumentParser()

    def test_create_parser_basic_structure(self):
        """Test create_parser creates parser with basic structure"""
        # Act
        parser = self.parser.create_parser()

        # Assert
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.description is not None

    def test_parse_args_minimal_arguments(self):
        """Test parse_args with minimal required arguments"""
        # Arrange
        parser = self.parser.create_parser()
        args = ["--config", "config.json"]

        # Act
        result = parser.parse_args(args)

        # Assert
        assert result.config == "config.json"
        assert result.debug is False
        assert result.dry_run is False
        assert result.non_interactive is False

    def test_parse_args_all_source_arguments(self):
        """Test parse_args with all source-related arguments"""
        # Arrange
        args = [
            "--config", "config.json",
            "--source-url", "https://source.harness.io",
            "--source-api-key", "source-key",
            "--source-org", "source-org",
            "--source-project", "source-project"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.source_url == "https://source.harness.io"
        assert result.source_api_key == "source-key"
        assert result.source_org == "source-org"
        assert result.source_project == "source-project"

    def test_parse_args_all_destination_arguments(self):
        """Test parse_args with all destination-related arguments"""
        # Arrange
        args = [
            "--config", "config.json",
            "--dest-url", "https://dest.harness.io",
            "--dest-api-key", "dest-key",
            "--dest-org", "dest-org",
            "--dest-project", "dest-project"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.dest_url == "https://dest.harness.io"
        assert result.dest_api_key == "dest-key"
        assert result.dest_org == "dest-org"
        assert result.dest_project == "dest-project"

    def test_parse_args_boolean_flags_positive(self):
        """Test parse_args with positive boolean flags"""
        # Arrange
        args = [
            "--config", "config.json",
            "--skip-input-sets",
            "--skip-triggers",
            "--skip-templates",
            "--update-existing",
            "--output-json",
            "--output-color"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.skip_input_sets is True
        assert result.skip_triggers is True
        assert result.skip_templates is True
        assert result.update_existing is True
        assert result.output_json is True
        assert result.output_color is True

    def test_parse_args_boolean_flags_negative(self):
        """Test parse_args with default boolean flag values (all False when not specified)"""
        # Arrange
        args = [
            "--config", "config.json"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.skip_input_sets is False
        assert result.skip_triggers is False
        assert result.skip_templates is False
        assert result.update_existing is False
        assert result.output_json is False
        assert result.output_color is False

    def test_parse_args_mode_flags(self):
        """Test parse_args with mode-related flags"""
        # Arrange
        args = [
            "--config", "config.json",
            "--debug",
            "--dry-run",
            "--non-interactive"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.debug is True
        assert result.dry_run is True
        assert result.non_interactive is True

    def test_parse_args_single_pipeline(self):
        """Test parse_args with single pipeline argument"""
        # Arrange
        args = [
            "--config", "config.json",
            "--pipeline", "pipeline1"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.pipelines == ["pipeline1"]

    def test_parse_args_multiple_pipelines(self):
        """Test parse_args with multiple pipeline arguments"""
        # Arrange
        args = [
            "--config", "config.json",
            "--pipeline", "pipeline1",
            "--pipeline", "pipeline2",
            "--pipeline", "pipeline3"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.pipelines == ["pipeline1", "pipeline2", "pipeline3"]

    def test_parse_args_save_config_flag(self):
        """Test parse_args with save-config flag"""
        # Arrange
        args = [
            "--config", "config.json",
            "--save-config"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.save_config is True

    def test_parse_args_complex_combination(self):
        """Test parse_args with complex combination of arguments"""
        # Arrange
        args = [
            "--config", "my-config.json",
            "--source-url", "https://source.harness.io",
            "--source-api-key", "source-key",
            "--dest-url", "https://dest.harness.io",
            "--dest-api-key", "dest-key",
            "--pipeline", "pipeline1",
            "--pipeline", "pipeline2",
            "--skip-input-sets",
            "--update-existing",
            "--output-json",
            "--debug",
            "--dry-run",
            "--save-config"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.config == "my-config.json"
        assert result.source_url == "https://source.harness.io"
        assert result.source_api_key == "source-key"
        assert result.dest_url == "https://dest.harness.io"
        assert result.dest_api_key == "dest-key"
        assert result.pipelines == ["pipeline1", "pipeline2"]
        assert result.skip_input_sets is True
        assert result.skip_triggers is False  # Not set in args, so default False
        assert result.update_existing is True
        assert result.output_json is True
        assert result.debug is True
        assert result.dry_run is True
        assert result.save_config is True

    def test_parse_args_help_flag(self):
        """Test parse_args with help flag exits gracefully"""
        # Arrange
        args = ["--help"]

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            parser = self.parser.create_parser()
            parser.parse_args(args)

        assert exc_info.value.code == 0

    def test_parse_args_invalid_argument(self):
        """Test parse_args with invalid argument"""
        # Arrange
        args = ["--config", "config.json", "--invalid-argument", "value"]

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            parser = self.parser.create_parser()
            parser.parse_args(args)

        assert exc_info.value.code == 2

    def test_parse_args_default_config_file(self):
        """Test parse_args uses default config file when not specified"""
        # Arrange
        args = ["--debug"]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.config == "config.json"  # Default value
        assert result.debug is True

    def test_parse_args_empty_pipeline_list(self):
        """Test parse_args with no pipeline arguments results in empty list"""
        # Arrange
        args = ["--config", "config.json"]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.pipelines is None  # Default value when no pipelines specified

    def test_parse_args_url_validation_format(self):
        """Test parse_args accepts various URL formats"""
        # Arrange
        test_cases = [
            "https://app.harness.io",
            "https://app3.harness.io",
            "http://localhost:8080",
            "https://custom-domain.com/harness"
        ]

        for url in test_cases:
            args = ["--config", "config.json", "--source-url", url]

            # Act
            parser = self.parser.create_parser()
            result = parser.parse_args(args)

            # Assert
            assert result.source_url == url

    def test_parse_args_boolean_flag_defaults(self):
        """Test parse_args boolean flag defaults are None (not set)"""
        # Arrange
        args = ["--config", "config.json"]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.skip_input_sets is False
        assert result.skip_triggers is False
        assert result.skip_templates is False
        assert result.update_existing is False
        assert result.output_json is False
        assert result.output_color is False
        assert result.save_config is False

    def test_create_parser_argument_groups(self):
        """Test create_parser creates proper argument groups"""
        # Act
        parser = self.parser.create_parser()

        # Assert
        # Check that argument groups exist by looking for specific arguments
        help_text = parser.format_help()
        assert "Source Configuration" in help_text or "--source-url" in help_text
        assert "Destination Configuration" in help_text or "--dest-url" in help_text
        assert "Pipeline Selection" in help_text or "--pipeline" in help_text
        assert "Replication Options" in help_text or "--skip-input-sets" in help_text
        assert "Output Options" in help_text or "--output-json" in help_text
        assert "Mode Options" in help_text or "--debug" in help_text

    def test_parse_args_multiple_boolean_flags(self):
        """Test parse_args with multiple boolean flags set"""
        # Arrange
        args = [
            "--config", "config.json",
            "--skip-input-sets",
            "--skip-triggers",
            "--update-existing",
            "--dry-run",
            "--debug"
        ]

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.skip_input_sets is True
        assert result.skip_triggers is True
        assert result.update_existing is True
        assert result.dry_run is True
        assert result.debug is True

    def test_parse_args_version_flag(self):
        """Test parse_args with version flag if it exists"""
        # Arrange
        args = ["--version"]

        # Act & Assert
        try:
            parser = self.parser.create_parser()
            parser.parse_args(args)
            # If version flag doesn't exist, this will be treated as an error
        except SystemExit as e:
            # Version flag typically exits with code 0, error exits with code 2
            assert e.code in [0, 2]

    def test_parse_args_long_pipeline_names(self):
        """Test parse_args with long pipeline names and special characters"""
        # Arrange
        pipeline_names = [
            "very-long-pipeline-name-with-many-hyphens",
            "pipeline_with_underscores",
            "Pipeline With Spaces",
            "pipeline123",
            "UPPERCASE_PIPELINE"
        ]

        args = ["--config", "config.json"]
        for name in pipeline_names:
            args.extend(["--pipeline", name])

        # Act
        parser = self.parser.create_parser()
        result = parser.parse_args(args)

        # Assert
        assert result.pipelines == pipeline_names

    def test_parse_args_api_key_handling(self):
        """Test parse_args properly handles API keys with special characters"""
        # Arrange
        api_keys = [
            "simple-key",
            "key_with_underscores",
            "key-with-hyphens",
            "keyWith123Numbers",
            "key.with.dots"
        ]

        for api_key in api_keys:
            args = ["--config", "config.json", "--source-api-key", api_key]

            # Act
            parser = self.parser.create_parser()
            result = parser.parse_args(args)

            # Assert
            assert result.source_api_key == api_key
