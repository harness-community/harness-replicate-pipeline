#!/usr/bin/env python3
"""
Harness Pipeline Replication Tool

Main entry point for the harness-replicate-pipeline tool.
This tool replicates Harness pipelines between organizations and projects.
"""

if __name__ == "__main__":
    from src.cli import main
    main()
