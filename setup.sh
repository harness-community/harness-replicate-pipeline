#!/bin/bash

# Harness Pipeline Migration - Quick Setup Script

echo "=================================================="
echo "Harness Pipeline Migration Setup"
echo "=================================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version 2>/dev/null || {
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.7 or higher"
    exit 1
}

echo "✓ Python is installed"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt || {
    echo "❌ Error: Failed to install dependencies"
    exit 1
}

echo "✓ Dependencies installed"
echo ""

# Create config file if it doesn't exist
if [ ! -f "config.json" ]; then
    echo "Creating config.json from template..."
    cp config.example.json config.json
    echo "✓ config.json created"
    echo ""
    echo "⚠️  IMPORTANT: Edit config.json with your API keys and account details"
    echo "   Use any text editor: nano config.json OR code config.json"
else
    echo "✓ config.json already exists"
fi

echo ""
echo "=================================================="
echo "Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Edit config.json with your API keys:"
echo "   nano config.json"
echo ""
echo "2. Run a dry-run to test:"
echo "   python3 harness_pipeline_migration.py --config config.json --dry-run"
echo ""
echo "3. Execute the migration:"
echo "   python3 harness_pipeline_migration.py --config config.json"
echo ""
echo "For detailed instructions, see README.md"
echo ""
