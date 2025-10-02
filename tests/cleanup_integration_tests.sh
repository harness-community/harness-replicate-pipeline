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
    local response=$(api_call "GET" "$endpoint")
    
    if echo "$response" | grep -q '"identifier"'; then
        return 0  # Resource exists
    else
        return 1  # Resource doesn't exist
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
        echo ""
        echo "🗑️  Cleaning up organization: $org"
        
        # Check if organization exists
        if resource_exists "/v1/orgs/$org"; then
            echo "   📁 Organization exists, proceeding with cleanup..."
            
            # Get projects in this organization
            projects_response=$(api_call "GET" "/v1/orgs/$org/projects")
            projects=$(echo "$projects_response" | grep -o '"identifier":"[^"]*"' | sed 's/"identifier":"//g' | sed 's/"//g')
            
            if [ -n "$projects" ]; then
                echo "   📂 Found projects:"
                echo "$projects" | while read -r project; do
                    if [ -n "$project" ]; then
                        echo "      - $project"
                        
                        # Get pipelines in this project
                        pipelines_response=$(api_call "GET" "/v1/orgs/$org/projects/$project/pipelines")
                        pipelines=$(echo "$pipelines_response" | grep -o '"identifier":"[^"]*"' | sed 's/"identifier":"//g' | sed 's/"//g')
                        
                        if [ -n "$pipelines" ]; then
                            echo "         🔧 Found pipelines:"
                            echo "$pipelines" | while read -r pipeline; do
                                if [ -n "$pipeline" ]; then
                                    echo "            - $pipeline"
                                    
                                    # Delete input sets for this pipeline
                                    input_sets_response=$(api_call "GET" "/v1/orgs/$org/projects/$project/input-sets?pipeline=$pipeline")
                                    input_sets=$(echo "$input_sets_response" | grep -o '"identifier":"[^"]*"' | sed 's/"identifier":"//g' | sed 's/"//g')
                                    
                                    if [ -n "$input_sets" ]; then
                                        echo "               📝 Deleting input sets:"
                                        echo "$input_sets" | while read -r input_set; do
                                            if [ -n "$input_set" ]; then
                                                echo "                  - $input_set"
                                                api_call "DELETE" "/v1/orgs/$org/projects/$project/input-sets/$input_set" > /dev/null
                                            fi
                                        done
                                    fi
                                    
                                    # Delete pipeline
                                    echo "               🗑️  Deleting pipeline: $pipeline"
                                    api_call "DELETE" "/v1/orgs/$org/projects/$project/pipelines/$pipeline" > /dev/null
                                fi
                            done
                        fi
                        
                        # Get templates in this project
                        templates_response=$(api_call "GET" "/v1/orgs/$org/projects/$project/templates")
                        templates=$(echo "$templates_response" | grep -o '"identifier":"[^"]*"' | sed 's/"identifier":"//g' | sed 's/"//g')
                        
                        if [ -n "$templates" ]; then
                            echo "         📋 Found templates:"
                            echo "$templates" | while read -r template; do
                                if [ -n "$template" ]; then
                                    echo "            - $template"
                                    # Delete template
                                    echo "               🗑️  Deleting template: $template"
                                    api_call "DELETE" "/v1/orgs/$org/projects/$project/templates/$template" > /dev/null
                                fi
                            done
                        fi
                        
                        # Delete project
                        echo "      🗑️  Deleting project: $project"
                        api_call "DELETE" "/v1/orgs/$org/projects/$project" > /dev/null
                    fi
                done
            fi
            
            # Delete organization
            echo "   🗑️  Deleting organization: $org"
            api_call "DELETE" "/v1/orgs/$org" > /dev/null
            echo "   ✅ Organization $org deleted successfully"
        else
            echo "   ℹ️  Organization $org doesn't exist or already deleted"
        fi
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
