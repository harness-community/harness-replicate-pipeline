"""
Harness Pipeline Replication Tool

A comprehensive tool for replicating Harness pipelines, input sets, and templates
between accounts with support for interactive and non-interactive modes.
"""

__version__ = "1.0.0"
__author__ = "Harness Pipeline Replication Tool"

from .api_client import HarnessAPIClient
from .replicator import HarnessReplicator
from .cli import main

__all__ = ["HarnessAPIClient", "HarnessReplicator", "main"]
