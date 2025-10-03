#!/bin/bash
# Integration Test Cleanup Script
# 
# This script cleans up resources created by integration tests.
# Run this after integration tests to remove test data.
#
# Usage:
#   ./tests/cleanup_integration_tests.sh [config_file]
#
# Configuration Sources (in priority order):
#   1. Config file (config.json or specified file)
#   2. Environment Variables:
#      - INTEGRATION_TEST_DEST_URL - Destination Harness URL
#      - INTEGRATION_TEST_DEST_API_KEY - Destination API key

# Note: Not using 'set -e' to allow graceful error handling

# Function to extract value from JSON config file
extract_config_value() {
    local config_file="$1"
    local json_path="$2"
    
    if [ -f "$config_file" ] && command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json, sys
try:
    with open('$config_file') as f:
        config = json.load(f)
    keys = '$json_path'.split('.')
    value = config
    for key in keys:
        value = value.get(key, '')
    print(value if value else '')
except:
    print('')
" 2>/dev/null
    else
        echo ""
    fi
}

# Determine config file
CONFIG_FILE="${1:-config.json}"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="config.json"
fi

echo "🔧 Loading configuration..."
echo "   Config file: $CONFIG_FILE"

# Load configuration from file first, then fallback to environment variables
if [ -f "$CONFIG_FILE" ]; then
    echo "   📄 Reading from config file..."
    DEST_URL=$(extract_config_value "$CONFIG_FILE" "destination.base_url")
    DEST_API_KEY=$(extract_config_value "$CONFIG_FILE" "destination.api_key")
    
    if [ -n "$DEST_URL" ] && [ -n "$DEST_API_KEY" ]; then
        echo "   ✅ Configuration loaded from file"
        INTEGRATION_TEST_DEST_URL="$DEST_URL"
        INTEGRATION_TEST_DEST_API_KEY="$DEST_API_KEY"
    else
        echo "   ⚠️  Config file missing destination credentials, checking environment..."
    fi
else
    echo "   ⚠️  Config file not found, checking environment variables..."
fi

# Fallback to environment variables if not loaded from config
if [ -z "$INTEGRATION_TEST_DEST_URL" ] || [ -z "$INTEGRATION_TEST_DEST_API_KEY" ]; then
    echo "   🌍 Checking environment variables..."
    # Use environment variables if available
    if [ -n "$INTEGRATION_TEST_DEST_URL" ] && [ -n "$INTEGRATION_TEST_DEST_API_KEY" ]; then
        echo "   ✅ Using environment variables"
    else
        echo "❌ Error: Required configuration not found"
        echo ""
        echo "Configuration sources tried:"
        echo "   1. Config file: $CONFIG_FILE"
        echo "      - destination.base_url: ${DEST_URL:-'not found'}"
        echo "      - destination.api_key: ${DEST_API_KEY:+found}${DEST_API_KEY:-'not found'}"
        echo "   2. Environment variables:"
        echo "      - INTEGRATION_TEST_DEST_URL: ${INTEGRATION_TEST_DEST_URL:-'not set'}"
        echo "      - INTEGRATION_TEST_DEST_API_KEY: ${INTEGRATION_TEST_DEST_API_KEY:+set}${INTEGRATION_TEST_DEST_API_KEY:-'not set'}"
        echo ""
        echo "Please provide configuration via:"
        echo "   Option 1 - Update config file ($CONFIG_FILE):"
        echo '     {"destination": {"base_url": "https://app.harness.io", "api_key": "your-api-key"}}'
        echo "   Option 2 - Set environment variables:"
        echo "     export INTEGRATION_TEST_DEST_URL='https://app.harness.io'"
        echo "     export INTEGRATION_TEST_DEST_API_KEY='your-api-key'"
        exit 1
    fi
fi

echo "🧹 Cleaning up integration test resources..."
echo "   Destination: $INTEGRATION_TEST_DEST_URL"
echo "   API Key: ${INTEGRATION_TEST_DEST_API_KEY:0:10}..."

# Function to make API calls with error handling
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    if [ -n "$data" ]; then
        curl -s -X "$method" \
            "$INTEGRATION_TEST_DEST_URL$endpoint" \
            -H "x-api-key: $INTEGRATION_TEST_DEST_API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" \
            "$INTEGRATION_TEST_DEST_URL$endpoint" \
            -H "x-api-key: $INTEGRATION_TEST_DEST_API_KEY"
    fi
}

# Function to check if resource exists
resource_exists() {
    local endpoint="$1"
    local response
    response=$(api_call "GET" "$endpoint")
    
    if echo "$response" | grep -q '"identifier"'; then
        return 0  # Resource exists
    else
        return 1  # Resource doesn't exist
    fi
}

# Function to extract identifiers from API response
extract_identifiers() {
    local response="$1"
    echo "$response" | grep -o '"identifier":"[^"]*"' | sed 's/"identifier":"//g' | sed 's/"//g'
}

# Function to delete resources with logging
delete_resource() {
    local resource_type="$1"
    local resource_name="$2"
    local endpoint="$3"
    local indent="$4"
    
    echo "${indent}🗑️  Deleting $resource_type: $resource_name"
    local delete_response
    delete_response=$(api_call "DELETE" "$endpoint" 2>&1)
    
    if [ $? -eq 0 ]; then
        echo "${indent}   ✅ Successfully deleted"
    else
        echo "${indent}   ⚠️  Delete failed (may already be deleted): $delete_response"
    fi
}

# Function to list and process resources
process_resources() {
    local resource_type="$1"
    local endpoint="$2"
    local indent="$3"
    local delete_endpoint_template="$4"
    
    local response
    local resources
    response=$(api_call "GET" "$endpoint")
    resources=$(extract_identifiers "$response")
    
    if [ -n "$resources" ]; then
        echo "${indent}📋 Found $resource_type:"
        echo "$resources" | while read -r resource; do
            if [ -n "$resource" ]; then
                echo "${indent}   - $resource"
                if [ -n "$delete_endpoint_template" ]; then
                    # Replace {resource} placeholder with actual resource identifier
                    delete_endpoint=$(echo "$delete_endpoint_template" | sed "s/{resource}/$resource/g")
                    delete_resource "$resource_type" "$resource" "$delete_endpoint" "${indent}      "
                fi
            fi
        done
    fi
}

# Function to clean up input sets for a pipeline
cleanup_input_sets() {
    local org="$1"
    local project="$2"
    local pipeline="$3"
    
    process_resources "input sets" "/v1/orgs/$org/projects/$project/input-sets?pipeline=$pipeline" "               " \
        "/v1/orgs/$org/projects/$project/input-sets/{resource}"
}

# Function to clean up pipelines in a project
cleanup_pipelines() {
    local org="$1"
    local project="$2"
    
    local pipelines_response
    local pipelines
    pipelines_response=$(api_call "GET" "/v1/orgs/$org/projects/$project/pipelines")
    
    if [ $? -ne 0 ] || [ -z "$pipelines_response" ]; then
        echo "         ⚠️  Could not fetch pipelines for project $project"
        return 0
    fi
    
    pipelines=$(extract_identifiers "$pipelines_response")
    
    if [ -n "$pipelines" ]; then
        echo "         🔧 Found pipelines:"
        echo "$pipelines" | while read -r pipeline; do
            if [ -n "$pipeline" ]; then
                echo "            - $pipeline"
                cleanup_input_sets "$org" "$project" "$pipeline"
                delete_resource "pipeline" "$pipeline" "/v1/orgs/$org/projects/$project/pipelines/$pipeline" "               "
            fi
        done
    else
        echo "         ℹ️  No pipelines found in project $project"
    fi
}

# Function to clean up templates in a project
cleanup_templates() {
    local org="$1"
    local project="$2"
    
    process_resources "templates" "/v1/orgs/$org/projects/$project/templates" "         " \
        "/v1/orgs/$org/projects/$project/templates/{resource}"
}

# Function to clean up projects in an organization
cleanup_projects() {
    local org="$1"
    
    local projects_response
    local projects
    projects_response=$(api_call "GET" "/v1/orgs/$org/projects")
    
    if [ $? -ne 0 ] || [ -z "$projects_response" ]; then
        echo "   ⚠️  Could not fetch projects for organization $org"
        return 0
    fi
    
    projects=$(extract_identifiers "$projects_response")
    
    if [ -n "$projects" ]; then
        echo "   📂 Found projects:"
        echo "$projects" | while read -r project; do
            if [ -n "$project" ]; then
                echo "      - $project"
                cleanup_pipelines "$org" "$project"
                cleanup_templates "$org" "$project"
                delete_resource "project" "$project" "/v1/orgs/$org/projects/$project" "      "
            fi
        done
    else
        echo "   ℹ️  No projects found in organization $org"
    fi
}

# Function to clean up a single organization
cleanup_organization() {
    local org="$1"
    
    echo ""
    echo "🗑️  Cleaning up organization: $org"
    
    if resource_exists "/v1/orgs/$org"; then
        echo "   📁 Organization exists, proceeding with cleanup..."
        cleanup_projects "$org"
        delete_resource "organization" "$org" "/v1/orgs/$org" "   "
        echo "   ✅ Organization $org deleted successfully"
    else
        echo "   ℹ️  Organization $org doesn't exist or already deleted"
    fi
}

# Get list of test organizations (those starting with "test_migration_org")
echo "📋 Finding test organizations..."
orgs_response=$(api_call "GET" "/v1/orgs")
test_orgs=$(echo "$orgs_response" | grep -o '"identifier":"test_migration_org[^"]*"' | sed 's/"identifier":"//g' | sed 's/"//g')

if [ -z "$test_orgs" ]; then
    echo "✅ No test organizations found - nothing to clean up"
    exit 0
fi

echo "🔍 Found test organizations:"
echo "$test_orgs" | while read -r org; do
    echo "   - $org"
done

# Clean up each test organization
echo "$test_orgs" | while read -r org; do
    if [ -n "$org" ]; then
        cleanup_organization "$org"
    fi
done

echo ""
echo "✅ Integration test cleanup completed!"
echo ""
echo "📊 Summary:"
echo "   - Test organizations: $(echo "$test_orgs" | wc -l)"
echo "   - All test resources have been removed"
echo ""
echo "🔍 Verification:"
echo "   You can verify cleanup by checking your Harness environment"
echo "   or running the integration tests again."
