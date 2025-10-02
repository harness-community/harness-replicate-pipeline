#!/usr/bin/env python3
"""
Harness Pipeline Migration Toolkit - Main Entry Point

This is the main entry point for the Harness migration tool.
It provides a simple interface to the modular src/ package.

Usage:
    python harness_migration.py [OPTIONS]

For detailed help:
    python harness_migration.py --help
"""

from src.harness_migration.cli import main

if __name__ == "__main__":
    main()
