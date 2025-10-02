#!/bin/bash
# Integration Test Cleanup Script
# 
# This script cleans up resources created by integration tests.
# Run this after integration tests to remove test data.
#
# Usage:
#   ./tests/cleanup_integration_tests.sh
#
# Environment Variables Required:
#   INTEGRATION_TEST_DEST_URL - Destination Harness URL
#   INTEGRATION_TEST_DEST_API_KEY - Destination API key

set -e

# Check required environment variables
if [ -z "$INTEGRATION_TEST_DEST_URL" ] || [ -z "$INTEGRATION_TEST_DEST_API_KEY" ]; then
    echo "❌ Error: Required environment variables not set"
    echo "   INTEGRATION_TEST_DEST_URL: $INTEGRATION_TEST_DEST_URL"
    echo "   INTEGRATION_TEST_DEST_API_KEY: ${INTEGRATION_TEST_DEST_API_KEY:0:10}..."
    echo ""
    echo "Please set these variables and run again:"
    echo "   export INTEGRATION_TEST_DEST_URL='https://your-harness-url.com'"
    echo "   export INTEGRATION_TEST_DEST_API_KEY='your-api-key'"
    exit 1
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
    api_call "DELETE" "$endpoint" > /dev/null
}

# Function to list and process resources
process_resources() {
    local resource_type="$1"
    local endpoint="$2"
    local indent="$3"
    local callback="$4"
    
    local response
    local resources
    response=$(api_call "GET" "$endpoint")
    resources=$(extract_identifiers "$response")
    
    if [ -n "$resources" ]; then
        echo "${indent}📋 Found $resource_type:"
        echo "$resources" | while read -r resource; do
            if [ -n "$resource" ]; then
                echo "${indent}   - $resource"
                if [ -n "$callback" ]; then
                    $callback "$resource"
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
        "delete_resource 'input set' \$resource '/v1/orgs/$org/projects/$project/input-sets/\$resource' '                  '"
}

# Function to clean up pipelines in a project
cleanup_pipelines() {
    local org="$1"
    local project="$2"
    
    local pipelines_response
    local pipelines
    pipelines_response=$(api_call "GET" "/v1/orgs/$org/projects/$project/pipelines")
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
    fi
}

# Function to clean up templates in a project
cleanup_templates() {
    local org="$1"
    local project="$2"
    
    process_resources "templates" "/v1/orgs/$org/projects/$project/templates" "         " \
        "delete_resource 'template' \$resource '/v1/orgs/$org/projects/$project/templates/\$resource' '               '"
}

# Function to clean up projects in an organization
cleanup_projects() {
    local org="$1"
    
    local projects_response
    local projects
    projects_response=$(api_call "GET" "/v1/orgs/$org/projects")
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
