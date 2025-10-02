"""
Unit tests for output orchestrator and transformers
"""

import json
import logging
from datetime import datetime
from unittest.mock import patch

import pytest

from src.output_orchestrator import (
    OutputLevel,
    OutputMessage,
    OutputOrchestrator,
    OutputType,
    TerminalOutputTransformer,
    JSONOutputTransformer,
    setup_output,
    get_orchestrator
)


class TestOutputMessage:
    """Test suite for OutputMessage class"""

    def test_output_message_creation(self):
        """Test OutputMessage creation with all parameters"""
        timestamp = datetime.now()
        message = OutputMessage(
            level=OutputLevel.INFO,
            message="Test message",
            category="test",
            data={"key": "value"},
            timestamp=timestamp
        )
        
        assert message.level == OutputLevel.INFO
        assert message.message == "Test message"
        assert message.category == "test"
        assert message.data == {"key": "value"}
        assert message.timestamp == timestamp

    def test_output_message_defaults(self):
        """Test OutputMessage creation with default values"""
        message = OutputMessage(OutputLevel.ERROR, "Error message")
        
        assert message.level == OutputLevel.ERROR
        assert message.message == "Error message"
        assert message.category == "general"
        assert message.data == {}
        assert isinstance(message.timestamp, datetime)

    def test_output_message_to_dict(self):
        """Test OutputMessage serialization to dictionary"""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        message = OutputMessage(
            level=OutputLevel.WARNING,
            message="Warning message",
            category="validation",
            data={"field": "value"},
            timestamp=timestamp
        )
        
        result = message.to_dict()
        
        expected = {
            "timestamp": "2023-01-01T12:00:00",
            "level": "warning",
            "category": "validation",
            "message": "Warning message",
            "data": {"field": "value"}
        }
        
        assert result == expected


class TestTerminalOutputTransformer:
    """Test suite for TerminalOutputTransformer"""

    def setup_method(self):
        """Setup test fixtures"""
        self.transformer = TerminalOutputTransformer(use_colors=False)
        self.color_transformer = TerminalOutputTransformer(use_colors=True)

    def test_format_message_without_colors(self):
        """Test message formatting without colors"""
        message = OutputMessage(
            level=OutputLevel.INFO,
            message="Test message",
            category="test",
            timestamp=datetime(2023, 1, 1, 12, 30, 45)
        )
        
        result = self.transformer.format_message(message)
        
        assert "12:30:45" in result
        assert "[INFO]" in result
        assert "[test]" in result
        assert "Test message" in result

    def test_format_message_with_colors(self):
        """Test message formatting with colors"""
        with patch('sys.stdout.isatty', return_value=True):
            transformer = TerminalOutputTransformer(use_colors=True)
            message = OutputMessage(
                level=OutputLevel.ERROR,
                message="Error message",
                timestamp=datetime(2023, 1, 1, 12, 30, 45)
            )
            
            result = transformer.format_message(message)
            
            # Should contain ANSI color codes
            assert "\033[" in result
            assert "12:30:45" in result
            assert "ERROR" in result
            assert "Error message" in result

    def test_format_message_general_category(self):
        """Test message formatting with general category (should not show category)"""
        message = OutputMessage(
            level=OutputLevel.INFO,
            message="General message",
            category="general",
            timestamp=datetime(2023, 1, 1, 12, 30, 45)
        )
        
        result = self.transformer.format_message(message)
        
        assert "[general]" not in result
        assert "General message" in result

    def test_enhance_message_text_without_colors(self):
        """Test message text enhancement without colors"""
        text = 'Variable test_var and "quoted value" with https://example.com'
        result = self.transformer._enhance_message_text(text)
        
        # Without colors, text should remain unchanged
        assert result == text

    def test_enhance_message_text_with_colors(self):
        """Test message text enhancement with colors"""
        with patch('sys.stdout.isatty', return_value=True):
            transformer = TerminalOutputTransformer(use_colors=True)
            text = 'Variable test_var and "quoted value" with https://example.com'
            result = transformer._enhance_message_text(text)
            
            # Should contain color codes for variables, quotes, and URLs
            assert "\033[" in result
            assert "test_var" in result
            assert "quoted value" in result
            assert "https://example.com" in result

    def test_format_summary(self):
        """Test summary formatting"""
        summary_data = {
            "pipelines": {"success": 5, "failed": 1, "skipped": 2},
            "templates": {"success": 3, "failed": 0, "skipped": 1}
        }
        
        result = self.transformer.format_summary(summary_data)
        
        assert "REPLICATION SUMMARY" in result
        assert "PIPELINES:" in result
        assert "Success: 5" in result
        assert "Failed: 1" in result
        assert "Skipped: 2" in result
        assert "TEMPLATES:" in result
        assert "Success: 3" in result

    def test_format_error_schema(self):
        """Test error formatting"""
        error = ValueError("Test error message")
        context = {"pipeline": "test_pipeline", "step": "validation"}
        
        result = self.transformer.format_error_schema(error, context)
        
        assert "ERROR:" in result
        assert "ValueError" in result
        assert "Test error message" in result
        assert "Context:" in result
        assert "pipeline" in result
        assert "test_pipeline" in result
        assert "step" in result
        assert "validation" in result

    def test_format_error_schema_without_context(self):
        """Test error formatting without context"""
        error = RuntimeError("Runtime error")
        
        result = self.transformer.format_error_schema(error)
        
        assert "ERROR:" in result
        assert "RuntimeError" in result
        assert "Runtime error" in result
        assert "Context:" not in result


class TestJSONOutputTransformer:
    """Test suite for JSONOutputTransformer"""

    def setup_method(self):
        """Setup test fixtures"""
        self.transformer = JSONOutputTransformer()

    def test_format_message(self):
        """Test JSON message formatting"""
        message = OutputMessage(
            level=OutputLevel.INFO,
            message="Test message",
            category="test",
            data={"key": "value"},
            timestamp=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        result = self.transformer.format_message(message)
        parsed = json.loads(result)
        
        assert parsed["level"] == "info"
        assert parsed["message"] == "Test message"
        assert parsed["category"] == "test"
        assert parsed["data"] == {"key": "value"}
        assert parsed["timestamp"] == "2023-01-01T12:00:00"

    def test_format_message_collection(self):
        """Test that messages are collected for batch output"""
        message1 = OutputMessage(OutputLevel.INFO, "Message 1")
        message2 = OutputMessage(OutputLevel.ERROR, "Message 2")
        
        self.transformer.format_message(message1)
        self.transformer.format_message(message2)
        
        assert len(self.transformer.messages) == 2
        assert self.transformer.messages[0]["message"] == "Message 1"
        assert self.transformer.messages[1]["message"] == "Message 2"

    def test_format_summary(self):
        """Test JSON summary formatting"""
        # Add some messages first
        message = OutputMessage(OutputLevel.INFO, "Test message")
        self.transformer.format_message(message)
        
        summary_data = {
            "pipelines": {"success": 5, "failed": 1, "skipped": 2}
        }
        
        result = self.transformer.format_summary(summary_data)
        parsed = json.loads(result)
        
        assert parsed["type"] == "summary"
        assert parsed["data"] == summary_data
        assert len(parsed["messages"]) == 1
        assert parsed["messages"][0]["message"] == "Test message"
        assert "timestamp" in parsed

    def test_format_error_schema(self):
        """Test JSON error formatting"""
        error = ValueError("Test error")
        context = {"field": "value"}
        
        result = self.transformer.format_error_schema(error, context)
        parsed = json.loads(result)
        
        assert parsed["type"] == "error"
        assert parsed["error"]["type"] == "ValueError"
        assert parsed["error"]["message"] == "Test error"
        assert parsed["error"]["context"] == context
        assert "timestamp" in parsed


class TestOutputOrchestrator:
    """Test suite for OutputOrchestrator"""

    def setup_method(self):
        """Setup test fixtures"""
        # Reset any existing orchestrator
        import src.output_orchestrator
        src.output_orchestrator._orchestrator = None

    def test_terminal_orchestrator_creation(self):
        """Test terminal orchestrator creation"""
        orchestrator = OutputOrchestrator(OutputType.TERMINAL, use_colors=False)
        
        assert orchestrator.output_type == OutputType.TERMINAL
        assert orchestrator.use_colors is False
        assert isinstance(orchestrator.transformer, TerminalOutputTransformer)

    def test_json_orchestrator_creation(self):
        """Test JSON orchestrator creation"""
        orchestrator = OutputOrchestrator(OutputType.JSON, use_colors=True)
        
        assert orchestrator.output_type == OutputType.JSON
        # Colors should be ignored for JSON output
        assert isinstance(orchestrator.transformer, JSONOutputTransformer)

    @patch('builtins.print')
    def test_terminal_output_methods(self, mock_print):
        """Test terminal output methods"""
        orchestrator = OutputOrchestrator(OutputType.TERMINAL, use_colors=False)
        
        orchestrator.info("Info message", "test")
        orchestrator.warning("Warning message")
        orchestrator.error("Error message")
        orchestrator.success("Success message")
        orchestrator.debug("Debug message")
        
        # Should have called print for each message
        assert mock_print.call_count == 5

    @patch('builtins.print')
    def test_json_output_methods(self, mock_print):
        """Test JSON output methods (should not print immediately)"""
        orchestrator = OutputOrchestrator(OutputType.JSON)
        
        orchestrator.info("Info message")
        orchestrator.error("Error message")
        
        # JSON mode should not print individual messages immediately
        mock_print.assert_not_called()

    @patch('builtins.print')
    def test_output_summary(self, mock_print):
        """Test summary output"""
        orchestrator = OutputOrchestrator(OutputType.TERMINAL, use_colors=False)
        
        summary_data = {"pipelines": {"success": 1, "failed": 0, "skipped": 0}}
        orchestrator.output_summary(summary_data)
        
        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        assert "REPLICATION SUMMARY" in args[0]

    @patch('builtins.print')
    def test_output_error(self, mock_print):
        """Test error output"""
        orchestrator = OutputOrchestrator(OutputType.TERMINAL, use_colors=False)
        
        error = ValueError("Test error")
        context = {"key": "value"}
        orchestrator.output_error(error, context)
        
        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        assert "ValueError" in args[0]
        assert "Test error" in args[0]

    def test_get_collected_output_json(self):
        """Test getting collected output for JSON mode"""
        orchestrator = OutputOrchestrator(OutputType.JSON)
        
        orchestrator.info("Test message")
        result = orchestrator.get_collected_output()
        
        assert result is not None
        parsed = json.loads(result)
        assert "messages" in parsed
        assert len(parsed["messages"]) == 1
        assert parsed["messages"][0]["message"] == "Test message"

    def test_get_collected_output_terminal(self):
        """Test getting collected output for terminal mode (should return None)"""
        orchestrator = OutputOrchestrator(OutputType.TERMINAL)
        
        result = orchestrator.get_collected_output()
        assert result is None

    def test_logging_integration(self):
        """Test integration with Python logging system"""
        OutputOrchestrator(OutputType.TERMINAL, use_colors=False)
        
        # Get a logger and verify it has the orchestrator handler
        logger = logging.getLogger("test_logger")
        
        # Should have at least one handler (the orchestrator handler)
        assert len(logger.handlers) > 0 or len(logging.getLogger().handlers) > 0


class TestGlobalFunctions:
    """Test suite for global orchestrator functions"""

    def setup_method(self):
        """Setup test fixtures"""
        # Reset global orchestrator
        import src.output_orchestrator
        src.output_orchestrator._orchestrator = None

    def test_setup_output(self):
        """Test setup_output function"""
        orchestrator = setup_output(OutputType.JSON, use_colors=False)
        
        assert isinstance(orchestrator, OutputOrchestrator)
        assert orchestrator.output_type == OutputType.JSON

    def test_get_orchestrator_creates_default(self):
        """Test get_orchestrator creates default if none exists"""
        orchestrator = get_orchestrator()
        
        assert isinstance(orchestrator, OutputOrchestrator)
        assert orchestrator.output_type == OutputType.TERMINAL
        assert orchestrator.use_colors is True  # Default when no config provided

    def test_get_orchestrator_returns_existing(self):
        """Test get_orchestrator returns existing orchestrator"""
        original = setup_output(OutputType.JSON)
        retrieved = get_orchestrator()
        
        assert retrieved is original

    @patch('builtins.print')
    def test_convenience_functions(self, mock_print):
        """Test convenience functions use global orchestrator"""
        from src.output_orchestrator import info, warning, error, success, debug
        
        # Setup terminal orchestrator for immediate output
        setup_output(OutputType.TERMINAL, use_colors=False)
        
        info("Info message")
        warning("Warning message")
        error("Error message")
        success("Success message")
        debug("Debug message")
        
        # Should have printed each message
        assert mock_print.call_count == 5


class TestColorHandling:
    """Test suite for color handling in different environments"""

    @patch('sys.stdout.isatty', return_value=True)
    def test_colors_enabled_in_tty(self, mock_isatty):
        """Test colors are enabled when stdout is a TTY"""
        transformer = TerminalOutputTransformer(use_colors=True)
        assert transformer.use_colors is True

    @patch('sys.stdout.isatty', return_value=False)
    def test_colors_disabled_in_non_tty(self, mock_isatty):
        """Test colors are disabled when stdout is not a TTY"""
        transformer = TerminalOutputTransformer(use_colors=True)
        assert transformer.use_colors is False

    def test_colors_explicitly_disabled(self):
        """Test colors can be explicitly disabled"""
        transformer = TerminalOutputTransformer(use_colors=False)
        assert transformer.use_colors is False

    @patch('sys.stdout.isatty', return_value=True)
    def test_colorize_with_colors_enabled(self, mock_isatty):
        """Test colorize method with colors enabled"""
        transformer = TerminalOutputTransformer(use_colors=True)
        result = transformer._colorize("test", "\033[91m")
        
        assert result == "\033[91mtest\033[0m"

    def test_colorize_with_colors_disabled(self):
        """Test colorize method with colors disabled"""
        transformer = TerminalOutputTransformer(use_colors=False)
        result = transformer._colorize("test", "\033[91m")
        
        assert result == "test"


class TestErrorHandling:
    """Test suite for error handling in output system"""

    def test_malformed_summary_data(self):
        """Test handling of malformed summary data"""
        transformer = TerminalOutputTransformer(use_colors=False)
        
        # Test with non-dict stats
        malformed_data = {
            "pipelines": "not_a_dict",
            "templates": {"success": 1, "failed": 0}  # Missing 'skipped'
        }
        
        # Should not raise an exception
        result = transformer.format_summary(malformed_data)
        assert "REPLICATION SUMMARY" in result

    def test_exception_in_error_formatting(self):
        """Test error formatting with complex exception"""
        transformer = TerminalOutputTransformer(use_colors=False)
        
        # Create a complex exception
        try:
            raise ValueError("Original error")
        except ValueError as e:
            try:
                raise RuntimeError("Wrapper error") from e
            except RuntimeError as wrapper_error:
                result = transformer.format_error_schema(wrapper_error)
                
                assert "RuntimeError" in result
                assert "Wrapper error" in result

    def test_unicode_in_messages(self):
        """Test handling of unicode characters in messages"""
        transformer = TerminalOutputTransformer(use_colors=False)
        
        message = OutputMessage(
            level=OutputLevel.INFO,
            message="Unicode test: 你好世界 🌍",
            timestamp=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        result = transformer.format_message(message)
        assert "Unicode test: 你好世界 🌍" in result


if __name__ == "__main__":
    pytest.main([__file__])
