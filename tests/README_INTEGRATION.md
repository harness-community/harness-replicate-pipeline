# Integration Testing Guide

This guide explains how to run integration tests for the Harness Migration Toolkit. These tests create real resources in a destination Harness environment to verify end-to-end functionality.

## ⚠️ Important Safety Notes

- **CREATE-ONLY**: Integration tests only create resources, never delete them
- **MANUAL CLEANUP**: You must manually clean up test resources after running tests
- **DESTINATION ENVIRONMENT**: Tests require a real Harness destination environment
- **API RATE LIMITS**: Tests include delays to respect API rate limits

## 🚀 Quick Start

### 1. Set Environment Variables

```bash
export INTEGRATION_TEST_DEST_URL="https://your-harness-url.com"
export INTEGRATION_TEST_DEST_API_KEY="your-api-key"
```

**Note**: Integration tests use environment variables for destination configuration instead of the standard `config.json` file to avoid conflicts with existing configurations.

### 2. Run Integration Tests

```bash
# Run all integration tests
pytest tests/test_integration.py -v -s

# Run specific test
pytest tests/test_integration.py::TestIntegrationMigration::test_create_organization -v -s

# Run with coverage
pytest tests/test_integration.py --cov=src --cov-report=term-missing
```

### 3. Clean Up Test Resources

```bash
# Automated cleanup (recommended)
./tests/cleanup_integration_tests.sh

# Manual cleanup (if automated fails)
# See "Manual Cleanup" section below
```

## 📋 Test Coverage

The integration tests cover:

### Core Resource Creation
- ✅ **Organizations**: Create new organizations
- ✅ **Projects**: Create projects within organizations  
- ✅ **Templates**: Create step templates with YAML
- ✅ **Pipelines**: Create CI/CD pipelines with stages
- ✅ **Input Sets**: Create input sets for pipelines

### Migration Functionality
- ✅ **Prerequisites Verification**: Test org/project creation logic
- ✅ **Template Migration**: Test template creation via migrator
- ✅ **End-to-End Simulation**: Test complete migration flow (dry run)

### API Client Testing
- ✅ **Authentication**: Verify API key authentication
- ✅ **Endpoint Construction**: Test URL building logic
- ✅ **Response Handling**: Test API response normalization
- ✅ **Error Handling**: Test API error scenarios

## 🔧 Test Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `INTEGRATION_TEST_DEST_URL` | Destination Harness URL | `https://app.harness.io` |
| `INTEGRATION_TEST_DEST_API_KEY` | Destination API key | `sat.xxxxx.xxxxx.xxxxx` |

### Test Data

Tests create resources with predictable names:
- **Organizations**: `test-migration-org-{timestamp}`
- **Projects**: `test-migration-project-{timestamp}`
- **Pipelines**: `test-migration-pipeline-{timestamp}`
- **Templates**: `test-migration-template-{timestamp}`
- **Input Sets**: `test-migration-inputset-{timestamp}`

## 🧹 Cleanup Methods

### Automated Cleanup (Recommended)

The cleanup script automatically finds and removes all test resources:

```bash
./tests/cleanup_integration_tests.sh
```

**What it does:**
1. Finds all organizations starting with `test-migration-org`
2. Deletes all projects within those organizations
3. Deletes all pipelines, templates, and input sets
4. Deletes the test organizations
5. Provides detailed progress and summary

### Manual Cleanup

If automated cleanup fails, use these curl commands:

```bash
# Set your environment
DEST_URL="https://your-harness-url.com"
API_KEY="your-api-key"

# Find test organizations
curl -H "x-api-key: $API_KEY" "$DEST_URL/v1/orgs" | grep "test-migration-org"

# Delete specific organization (this cascades to all resources)
curl -X DELETE -H "x-api-key: $API_KEY" "$DEST_URL/v1/orgs/test-migration-org-1234567890"
```

### Cleanup Verification

Verify cleanup was successful:

```bash
# Check no test organizations remain
curl -H "x-api-key: $API_KEY" "$DEST_URL/v1/orgs" | grep "test-migration-org"
# Should return empty result
```

## 🎯 Test Scenarios

### 1. Basic Resource Creation

```python
def test_create_organization(self):
    """Test creating a new organization"""
    # Creates org with test data
    # Verifies org exists
    # Provides cleanup info
```

### 2. Hierarchical Resource Creation

```python
def test_create_project(self):
    """Test creating a new project"""
    # Creates org first
    # Creates project within org
    # Verifies both exist
```

### 3. Complex Resource Creation

```python
def test_create_pipeline(self):
    """Test creating a new pipeline"""
    # Creates org and project
    # Creates pipeline with YAML
    # Verifies pipeline exists
```

### 4. Migration Logic Testing

```python
def test_migrator_verify_prerequisites(self):
    """Test migrator's prerequisite verification"""
    # Tests org/project creation logic
    # Verifies migrator can create resources
    # Tests error handling
```

## 🚨 Troubleshooting

### Common Issues

**1. Authentication Failures**
```
Error: 401 Unauthorized
```
- Check API key is correct
- Verify API key has necessary permissions
- Ensure destination URL is accessible

**2. Resource Creation Failures**
```
Error: 400 Bad Request
```
- Check YAML format is valid
- Verify required fields are present
- Check for naming conflicts

**3. Cleanup Failures**
```
Error: 404 Not Found
```
- Resources may already be deleted
- Check organization name is correct
- Verify API permissions for deletion

### Debug Mode

Run tests with debug logging:

```bash
pytest tests/test_integration.py -v -s --log-cli-level=DEBUG
```

### Test Isolation

Each test uses unique timestamps to avoid conflicts:

```python
timestamp = int(time.time())
self.test_org = f"test-migration-org-{timestamp}"
```

## 📊 Test Results

### Expected Output

```
tests/test_integration.py::TestIntegrationMigration::test_create_organization PASSED
tests/test_integration.py::TestIntegrationMigration::test_create_project PASSED
tests/test_integration.py::TestIntegrationMigration::test_create_template PASSED
tests/test_integration.py::TestIntegrationMigration::test_create_pipeline PASSED
tests/test_integration.py::TestIntegrationMigration::test_create_input_set PASSED
tests/test_integration.py::TestIntegrationMigration::test_migrator_verify_prerequisites PASSED
tests/test_integration.py::TestIntegrationMigration::test_migrator_create_template PASSED
tests/test_integration.py::TestIntegrationMigration::test_end_to_end_migration_simulation PASSED

🧹 MANUAL CLEANUP REQUIRED:
   Delete test organization: curl -X DELETE 'https://your-dest-url/v1/orgs/test-migration-org-1234567890' -H 'x-api-key: sat.xxxxx...'
```

### Coverage Report

```
Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
src/harness_migration/api_client.py      75     15    80%   54-60, 71-77, 88-94
src/harness_migration/migrator.py       313     45    85%   165-167, 178-179, 199-200
-------------------------------------------------------------------
TOTAL                                   388     60    85%
```

## 🔄 Continuous Integration

### GitHub Actions Example

```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        env:
          INTEGRATION_TEST_DEST_URL: ${{ secrets.HARNESS_DEST_URL }}
          INTEGRATION_TEST_DEST_API_KEY: ${{ secrets.HARNESS_DEST_API_KEY }}
        run: pytest tests/test_integration.py -v
      - name: Cleanup test resources
        run: ./tests/cleanup_integration_tests.sh
```

## 📝 Best Practices

### 1. Test Environment
- Use dedicated test Harness environment
- Never run on production data
- Use separate API keys for testing

### 2. Resource Naming
- Use predictable naming patterns
- Include timestamps for uniqueness
- Prefix with `test-migration-` for easy identification

### 3. Cleanup Strategy
- Always clean up after tests
- Use automated cleanup when possible
- Verify cleanup was successful

### 4. Error Handling
- Test both success and failure scenarios
- Verify error messages are helpful
- Test API rate limiting behavior

## 🎉 Benefits

Integration tests provide:

- **Real-world validation**: Tests actual Harness API interactions
- **End-to-end verification**: Confirms complete migration workflow
- **API compatibility**: Ensures tool works with current Harness versions
- **Regression prevention**: Catches breaking changes in Harness API
- **Documentation**: Serves as living documentation of API usage

## 📚 Related Documentation

- [Unit Testing Guide](README.md#testing)
- [API Client Documentation](src/harness_migration/api_client.py)
- [Migration Logic Documentation](src/harness_migration/migrator.py)
- [Harness API Documentation](https://docs.harness.io/category/9j6u8u5zts-harness-api)
