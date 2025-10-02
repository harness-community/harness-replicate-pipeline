"""
Output Orchestrator

Central orchestrator that manages all output formatting and coordinates individual transformers.
This orchestrator translates internal state into the desired display format.
"""

import json
import logging
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class OutputLevel(Enum):
    """Output severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class OutputType(Enum):
    """Output format types"""
    TERMINAL = "terminal"
    JSON = "json"


class OutputMessage:
    """Standardized output message structure"""
    
    def __init__(
        self,
        level: OutputLevel,
        message: str,
        category: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.level = level
        self.message = message
        self.category = category or "general"
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category,
            "message": self.message,
            "data": self.data
        }


class OutputTransformer(ABC):
    """Abstract base class for output transformers"""
    
    @abstractmethod
    def format_message(self, message: OutputMessage) -> str:
        """Format a single message for output"""
    
    @abstractmethod
    def format_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format summary data for output"""
    
    @abstractmethod
    def format_error_schema(self, exc: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """Format error with standardized schema"""


class TerminalOutputTransformer(OutputTransformer):
    """Terminal output transformer with color support"""
    
    # ANSI color codes
    COLORS = {
        OutputLevel.DEBUG: "\033[90m",      # Gray
        OutputLevel.INFO: "\033[94m",       # Blue
        OutputLevel.WARNING: "\033[93m",    # Yellow
        OutputLevel.ERROR: "\033[91m",      # Red
        OutputLevel.SUCCESS: "\033[92m",    # Green
    }
    
    # Special formatting
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"
    
    # Data type colors
    VARIABLE_COLOR = "\033[96m"  # Cyan
    VALUE_COLOR = "\033[95m"     # Magenta
    URL_COLOR = "\033[94m"       # Blue
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def _colorize(self, text: str, color_code: str) -> str:
        """Apply color to text if colors are enabled"""
        if not self.use_colors:
            return text
        return f"{color_code}{text}{self.RESET}"
    
    def _format_level_prefix(self, level: OutputLevel) -> str:
        """Format level prefix with appropriate color"""
        level_text = level.value.upper()
        if self.use_colors:
            color = self.COLORS.get(level, "")
            return f"{color}[{level_text}]{self.RESET}"
        return f"[{level_text}]"
    
    def _format_timestamp(self, timestamp: datetime) -> str:
        """Format timestamp"""
        time_str = timestamp.strftime("%H:%M:%S")
        return self._colorize(time_str, "\033[90m")  # Gray
    
    def _enhance_message_text(self, text: str) -> str:
        """Enhance message text with colors for variables, URLs, etc."""
        if not self.use_colors:
            return text
        
        # Color variables (words with underscores or in quotes)
        import re
        text = re.sub(r'\b\w+_\w+\b', lambda m: self._colorize(m.group(), self.VARIABLE_COLOR), text)
        text = re.sub(r'"([^"]*)"', lambda m: f'"{self._colorize(m.group(1), self.VALUE_COLOR)}"', text)
        text = re.sub(r"'([^']*)'", lambda m: f"'{self._colorize(m.group(1), self.VALUE_COLOR)}'", text)
        
        # Color URLs
        text = re.sub(r'https?://[^\s]+', lambda m: self._colorize(m.group(), self.URL_COLOR), text)
        
        return text
    
    def format_message(self, message: OutputMessage) -> str:
        """Format a single message for terminal output"""
        timestamp = self._format_timestamp(message.timestamp)
        level_prefix = self._format_level_prefix(message.level)
        enhanced_text = self._enhance_message_text(message.message)
        
        # Add category if not general
        category_part = ""
        if message.category != "general":
            category_part = f" [{self._colorize(message.category, self.VARIABLE_COLOR)}]"
        
        return f"{timestamp} {level_prefix}{category_part} {enhanced_text}"
    
    def format_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format summary data for terminal output"""
        lines = []
        
        # Header
        header = "REPLICATION SUMMARY"
        separator = "=" * 50
        lines.append(self._colorize(separator, self.BOLD))
        lines.append(self._colorize(header, self.BOLD))
        lines.append(self._colorize(separator, self.BOLD))
        lines.append("")
        
        # Resource statistics
        for resource_type, stats in summary_data.items():
            if isinstance(stats, dict) and all(k in stats for k in ['success', 'failed', 'skipped']):
                resource_title = self._colorize(f"{resource_type.upper()}:", self.BOLD)
                lines.append(resource_title)
                
                success_text = f"  Success: {self._colorize(str(stats['success']), self.COLORS[OutputLevel.SUCCESS])}"
                failed_text = f"  Failed: {self._colorize(str(stats['failed']), self.COLORS[OutputLevel.ERROR])}"
                skipped_text = f"  Skipped: {self._colorize(str(stats['skipped']), self.COLORS[OutputLevel.WARNING])}"
                
                lines.extend([success_text, failed_text, skipped_text, ""])
        
        lines.append(self._colorize(separator, self.BOLD))
        return "\n".join(lines)
    
    def format_error_schema(self, exc: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """Format error with standardized schema for terminal"""
        error_type = self._colorize(type(exc).__name__, self.COLORS[OutputLevel.ERROR])
        error_msg = self._enhance_message_text(str(exc))
        
        lines = [f"{self._colorize('ERROR:', self.BOLD)} {error_type}: {error_msg}"]
        
        if context:
            lines.append(f"{self._colorize('Context:', self.BOLD)}")
            for key, value in context.items():
                key_colored = self._colorize(key, self.VARIABLE_COLOR)
                value_colored = self._colorize(str(value), self.VALUE_COLOR)
                lines.append(f"  {key_colored}: {value_colored}")
        
        return "\n".join(lines)


class JSONOutputTransformer(OutputTransformer):
    """JSON output transformer for automation integration"""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
    
    def format_message(self, message: OutputMessage) -> str:
        """Format a single message for JSON output (store for batch output)"""
        message_dict = message.to_dict()
        self.messages.append(message_dict)
        
        # For JSON mode, we typically don't output individual messages immediately
        # Instead, we collect them and output at the end
        return json.dumps(message_dict)
    
    def format_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format summary data for JSON output"""
        summary_output = {
            "timestamp": datetime.now().isoformat(),
            "type": "summary",
            "data": summary_data,
            "messages": self.messages
        }
        return json.dumps(summary_output, indent=2)
    
    def format_error_schema(self, exc: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """Format error with standardized schema for JSON"""
        error_output = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "context": context or {}
            }
        }
        return json.dumps(error_output, indent=2)


class OutputOrchestrator:
    """Central orchestrator for all output formatting"""
    
    def __init__(self, output_type: OutputType = OutputType.TERMINAL, use_colors: bool = True):
        self.output_type = output_type
        self.use_colors = use_colors
        
        # Initialize appropriate transformer
        if output_type == OutputType.JSON:
            self.transformer = JSONOutputTransformer()
        else:
            self.transformer = TerminalOutputTransformer(use_colors)
        
        # Set up logging integration
        self._setup_logging_integration()
    
    def _setup_logging_integration(self):
        """Set up integration with Python logging system"""
        # Create custom handler that routes through orchestrator
        class OrchestatorHandler(logging.Handler):
            def __init__(self, orchestrator):
                super().__init__()
                self.orchestrator = orchestrator
            
            def emit(self, record):
                # Map logging levels to output levels
                level_mapping = {
                    logging.DEBUG: OutputLevel.DEBUG,
                    logging.INFO: OutputLevel.INFO,
                    logging.WARNING: OutputLevel.WARNING,
                    logging.ERROR: OutputLevel.ERROR,
                }
                
                output_level = level_mapping.get(record.levelno, OutputLevel.INFO)
                message = self.format(record)
                
                # Extract category from logger name
                category = record.name.split('.')[-1] if '.' in record.name else record.name
                
                self.orchestrator._output_message(OutputMessage(
                    level=output_level,
                    message=message,
                    category=category
                ))
        
        # Replace existing handlers with orchestrator handler
        root_logger = logging.getLogger()
        
        # Remove existing handlers to avoid duplicate output
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add orchestrator handler
        orchestrator_handler = OrchestatorHandler(self)
        if self.output_type == OutputType.TERMINAL:
            orchestrator_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(orchestrator_handler)
    
    def _output_message(self, message: OutputMessage):
        """Internal method to output a message"""
        formatted = self.transformer.format_message(message)
        
        if self.output_type == OutputType.TERMINAL:
            # For terminal output, print immediately
            print(formatted)
        # For JSON output, messages are collected and output at the end
    
    def debug(self, message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
        """Output debug message"""
        self._output_message(OutputMessage(OutputLevel.DEBUG, message, category, data))
    
    def info(self, message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
        """Output info message"""
        self._output_message(OutputMessage(OutputLevel.INFO, message, category, data))
    
    def warning(self, message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
        """Output warning message"""
        self._output_message(OutputMessage(OutputLevel.WARNING, message, category, data))
    
    def error(self, message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
        """Output error message"""
        self._output_message(OutputMessage(OutputLevel.ERROR, message, category, data))
    
    def success(self, message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
        """Output success message"""
        self._output_message(OutputMessage(OutputLevel.SUCCESS, message, category, data))
    
    def output_summary(self, summary_data: Dict[str, Any]):
        """Output formatted summary"""
        formatted = self.transformer.format_summary(summary_data)
        print(formatted)
    
    def output_error(self, exc: Exception, context: Optional[Dict[str, Any]] = None):
        """Output formatted error"""
        formatted = self.transformer.format_error_schema(exc, context)
        print(formatted)
    
    def get_collected_output(self) -> Optional[str]:
        """Get collected output for JSON mode"""
        if isinstance(self.transformer, JSONOutputTransformer):
            return json.dumps({
                "timestamp": datetime.now().isoformat(),
                "messages": self.transformer.messages
            }, indent=2)
        return None


# Global orchestrator instance (will be initialized by setup_output)
_orchestrator: Optional[OutputOrchestrator] = None


def setup_output(output_type: OutputType = OutputType.TERMINAL, use_colors: bool = True) -> OutputOrchestrator:
    """Setup global output orchestrator"""
    global _orchestrator
    _orchestrator = OutputOrchestrator(output_type, use_colors)
    return _orchestrator


def get_orchestrator() -> OutputOrchestrator:
    """Get the global output orchestrator"""
    if _orchestrator is None:
        return setup_output()
    return _orchestrator


# Convenience functions for direct use
def debug(message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
    """Output debug message using global orchestrator"""
    get_orchestrator().debug(message, category, data)


def info(message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
    """Output info message using global orchestrator"""
    get_orchestrator().info(message, category, data)


def warning(message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
    """Output warning message using global orchestrator"""
    get_orchestrator().warning(message, category, data)


def error(message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
    """Output error message using global orchestrator"""
    get_orchestrator().error(message, category, data)


def success(message: str, category: str = "general", data: Optional[Dict[str, Any]] = None):
    """Output success message using global orchestrator"""
    get_orchestrator().success(message, category, data)
