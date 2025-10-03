#!/bin/bash

# Integration Test Runner for Harness Replication Toolkit
# 
# This script runs integration tests that require real Harness API access.
# Make sure you have valid credentials configured before running.

set -e  # Exit on any error

echo "🚀 Harness Replication Toolkit - Integration Test Runner"
echo "========================================================"

# Check if integration tests directory exists
if [ ! -d "tests/integration" ]; then
    echo "❌ Error: Integration tests directory not found!"
    echo "   Expected: tests/integration/"
    exit 1
fi

# Check for configuration
echo "🔍 Checking configuration..."

# Check environment variables first
if [ -n "$INTEGRATION_TEST_DEST_URL" ] && [ -n "$INTEGRATION_TEST_DEST_API_KEY" ]; then
    echo "✅ Found environment variable configuration"
    echo "   URL: $INTEGRATION_TEST_DEST_URL"
    echo "   API Key: ${INTEGRATION_TEST_DEST_API_KEY:0:10}..."
elif [ -f "config.json" ]; then
    echo "✅ Found config.json file"
    # Check if it has valid-looking credentials (not placeholders)
    if grep -q '"api_key": "key"' config.json; then
        echo "⚠️  Warning: config.json appears to contain placeholder values"
        echo "   Please update with real Harness credentials or use environment variables"
        echo ""
        echo "Environment variable setup:"
        echo "  export INTEGRATION_TEST_DEST_URL=\"https://app.harness.io\""
        echo "  export INTEGRATION_TEST_DEST_API_KEY=\"your-real-api-key\""
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Aborted by user"
            exit 1
        fi
    fi
else
    echo "❌ Error: No configuration found!"
    echo ""
    echo "Please set up configuration using one of these methods:"
    echo ""
    echo "Method 1 - Environment Variables (Recommended):"
    echo "  export INTEGRATION_TEST_DEST_URL=\"https://app.harness.io\""
    echo "  export INTEGRATION_TEST_DEST_API_KEY=\"your-real-api-key\""
    echo ""
    echo "Method 2 - config.json file:"
    echo "  Create config.json with valid destination credentials"
    echo "  See tests/integration/README.md for details"
    exit 1
fi

echo ""
echo "⚠️  IMPORTANT WARNINGS:"
echo "   • These tests make REAL API calls to Harness"
echo "   • Test resources will be created in your Harness account"
echo "   • You are responsible for cleaning up test resources"
echo "   • API usage may count against your account limits"
echo ""

# Prompt for confirmation unless --yes flag is provided
if [ "$1" != "--yes" ] && [ "$1" != "-y" ]; then
    read -p "Do you want to proceed? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted by user"
        exit 1
    fi
fi

echo ""
echo "🧪 Running integration tests..."
echo ""

# Run the integration tests
if pytest tests/integration/ -v -s; then
    echo ""
    echo "✅ Integration tests completed successfully!"
    echo ""
    echo "🧹 CLEANUP REMINDER:"
    echo "   Don't forget to clean up test resources created during testing."
    echo "   See tests/integration/README.md for cleanup instructions."
else
    echo ""
    echo "❌ Integration tests failed!"
    echo ""
    echo "🧹 CLEANUP REMINDER:"
    echo "   Test resources may have been created even though tests failed."
    echo "   Check your Harness account and clean up any test resources."
    echo "   See tests/integration/README.md for cleanup instructions."
    exit 1
fi
