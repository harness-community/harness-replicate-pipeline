# Integration Tests

This directory contains integration tests that require **real Harness API access**. These tests are separate from unit tests and test end-to-end functionality with actual Harness environments.

## 🚨 Important Notes

- **These tests make real API calls** to Harness and will create/modify/delete resources
- **Requires valid Harness API credentials** 
- **Will incur API usage** against your Harness account
- **Creates temporary test resources** with timestamps to avoid conflicts
- **Includes cleanup instructions** to remove test resources

## 📋 Prerequisites

1. **Valid Harness Account** with API access
2. **API Key** with appropriate permissions:
   - Organization: Create, Read, Update, Delete
   - Project: Create, Read, Update, Delete  
   - Pipeline: Create, Read, Update, Delete
   - Template: Create, Read, Update, Delete
   - Input Set: Create, Read, Update, Delete
   - Trigger: Create, Read, Update, Delete

## ⚙️ Configuration

### Option 1: Environment Variables (Recommended)
```bash
export INTEGRATION_TEST_DEST_URL="https://app.harness.io"
export INTEGRATION_TEST_DEST_API_KEY="pat.your-real-api-key.here"
```

### Option 2: Update config.json
```json
{
  "destination": {
    "base_url": "https://app.harness.io",
    "api_key": "pat.your-real-api-key.here",
    "org": "your-org-identifier", 
    "project": "your-project-identifier"
  }
}
```

## 🚀 Running Integration Tests

**Note**: Integration tests are now separated from unit tests. By default, `pytest` only runs unit tests from `tests/unit/`. Integration tests must be run explicitly.

### Quick Start
```bash
# Use the convenience script
./run_integration_tests.sh

# Or run manually from project root
pytest tests/integration/ -v -s
```

### Run All Integration Tests
```bash
# From project root
pytest tests/integration/ -v -s
```

### Run Specific Integration Test Files
```bash
# Basic integration tests
pytest tests/integration/test_integration.py -v -s

# Trigger-specific integration tests  
pytest tests/integration/test_trigger_integration.py -v -s
```

### Run Specific Test Methods
```bash
# Test organization creation
pytest tests/integration/test_integration.py::TestIntegrationMigration::test_create_organization -v -s

# Test trigger API discovery
pytest tests/integration/test_trigger_integration.py::TestTriggerIntegration::test_trigger_api_endpoints_discovery -v -s
```

### Run with Integration Test Marker
```bash
# Run only tests marked as integration
pytest -m integration -v -s
```

## 🧹 Cleanup

Integration tests create temporary resources with timestamps. If tests fail or are interrupted, you may need to manually clean up:

### Automatic Cleanup
Tests include teardown methods that attempt to clean up created resources.

### Manual Cleanup (if needed)
```bash
# List and delete test organizations (this removes all associated resources)
curl -X GET "https://app.harness.io/v1/orgs" \
  -H "x-api-key: your-api-key" | grep "test_migration_org_"

# Delete specific test organization (replace with actual identifier)
curl -X DELETE "https://app.harness.io/v1/orgs/test_migration_org_1234567890" \
  -H "x-api-key: your-api-key"
```

## 📁 Test Structure

```
tests/integration/
├── __init__.py                    # Package initialization
├── README.md                      # This file
├── test_integration.py            # Core integration tests
└── test_trigger_integration.py    # Trigger-specific integration tests
```

## 🔍 What Gets Tested

### test_integration.py
- Organization creation and management
- Project creation and management  
- Template replication
- Pipeline replication
- Input set replication
- End-to-end migration workflows

### test_trigger_integration.py
- Trigger API endpoint discovery
- Trigger creation and reading
- Trigger YAML structure validation
- Trigger listing functionality

## ⚠️ Troubleshooting

### Common Issues

**401 Unauthorized**
- Check your API key is valid and not expired
- Ensure API key has required permissions
- Verify the base URL is correct

**403 Forbidden** 
- API key lacks required permissions
- Check organization/project access rights

**404 Not Found**
- Verify organization and project identifiers exist
- Check API endpoint URLs are correct

**Rate Limiting**
- Harness may rate limit API calls
- Add delays between tests if needed

### Debug Mode
```bash
# Run with verbose output and no capture
pytest tests/integration/ -v -s --tb=long

# Run with debug logging
pytest tests/integration/ -v -s --log-cli-level=DEBUG
```

## 🎯 Best Practices

1. **Always run integration tests in a test environment**
2. **Use dedicated test organization/project** 
3. **Monitor API usage** to avoid unexpected charges
4. **Clean up resources** after testing
5. **Don't run integration tests in CI/CD** unless specifically configured
6. **Use environment variables** for credentials (more secure)

## 🔒 Security

- **Never commit real API keys** to version control
- **Use environment variables** for sensitive data
- **Rotate API keys** regularly
- **Limit API key permissions** to minimum required
- **Use dedicated test accounts** when possible
