# Testing Guide - Sports League Management System

## Overview

This document describes the regression test suite for the Sports League Management System. The test suite ensures that critical functionality continues to work correctly as the codebase evolves.

## Test Coverage

The regression test suite covers the following areas:

### 1. Authentication Tests
- ✅ Successful login with valid credentials
- ✅ Login failure with wrong password
- ✅ Login failure with non-existent user
- ✅ Logout functionality
- ✅ Password reset request flow
- ✅ Protected route access control

### 2. Tenant Routing Tests
- ✅ Organization detection from custom domain
- ✅ Organization detection from subdomain
- ✅ Organization detection from URL slug
- ✅ Data isolation between organizations

### 3. Live Console API Tests
- ✅ Fetching live games
- ✅ Fetching game details
- ✅ Updating game scores
- ✅ Fetching standings
- ✅ Fetching statistical leaders

### 4. Admin Financial Tests
- ✅ Recording in-person payments
- ✅ Payment audit trail (creator tracking)
- ✅ Revenue tracking
- ✅ Financial report generation

### 5. Integration Tests
- ✅ Complete game flow (schedule → play → complete)
- ✅ User permission enforcement
- ✅ Branding persistence

## Running Tests

### Quick Start

**Windows:**
```bash
run_tests.bat
```

**Linux/Mac:**
```bash
chmod +x run_tests.sh
./run_tests.sh
```

### Manual Execution

Run all tests:
```bash
docker-compose exec web pytest tests/test_regression_suite.py -v
```

Run specific test class:
```bash
docker-compose exec web pytest tests/test_regression_suite.py::TestAuthentication -v
```

Run specific test:
```bash
docker-compose exec web pytest tests/test_regression_suite.py::TestAuthentication::test_login_success -v
```

Run with coverage:
```bash
docker-compose exec web pytest tests/test_regression_suite.py --cov=slms --cov-report=html
```

### Test Options

- `-v` - Verbose output
- `-s` - Show print statements
- `--tb=short` - Shorter traceback format
- `--tb=long` - Detailed traceback
- `-x` - Stop on first failure
- `--pdb` - Drop into debugger on failure
- `-k EXPRESSION` - Run tests matching expression

## Test Structure

### Fixtures

The test suite uses pytest fixtures to set up test data:

- **app** - Flask application instance with test configuration
- **client** - Test client for making requests
- **test_org** - Sample organization
- **test_user** - Sample admin user
- **test_season** - Sample season
- **test_teams** - Sample teams
- **test_game** - Sample game

### Test Classes

Tests are organized into classes by functionality:

- `TestAuthentication` - Auth flows
- `TestTenantRouting` - Multi-tenancy
- `TestLiveConsoleAPIs` - Live game APIs
- `TestAdminFinancial` - Financial operations
- `TestIntegration` - End-to-end flows

## Writing New Tests

### Basic Test Template

```python
class TestNewFeature:
    """Test new feature functionality."""

    def test_feature_success(self, client, app, test_org):
        """Test successful feature operation."""
        with app.app_context():
            response = client.get('/new-endpoint')
            assert response.status_code == 200

    def test_feature_validation(self, client, app):
        """Test feature input validation."""
        with app.app_context():
            response = client.post('/new-endpoint', data={
                'invalid': 'data'
            })
            assert response.status_code == 400
```

### Best Practices

1. **Use descriptive test names** - Test name should describe what is being tested
2. **One assertion per test** - Keep tests focused
3. **Use fixtures** - Don't repeat setup code
4. **Test both success and failure** - Include negative test cases
5. **Clean up after tests** - Use fixtures with proper teardown
6. **Mock external services** - Don't depend on external APIs

## Continuous Integration

### GitHub Actions Setup

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          docker-compose up -d
          docker-compose exec -T web pytest tests/test_regression_suite.py -v
```

## Debugging Failed Tests

### View detailed error:
```bash
docker-compose exec web pytest tests/test_regression_suite.py::TestAuth::test_login -vv --tb=long
```

### Drop into debugger:
```bash
docker-compose exec web pytest tests/test_regression_suite.py --pdb
```

### Check logs:
```bash
docker-compose logs web
```

## Test Database

Tests use an in-memory SQLite database by default. This is reset for each test run.

To use a persistent test database:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@db/slms_test'
```

## Performance Testing

For load testing the live APIs:

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:5000
```

## Code Coverage

Generate coverage report:

```bash
docker-compose exec web pytest tests/test_regression_suite.py --cov=slms --cov-report=html
```

View report:
```bash
open htmlcov/index.html  # Mac/Linux
start htmlcov/index.html # Windows
```

## Test Data Factories

For complex test data, use factories:

```python
from factory import Factory, Faker
from slms.models import User, Organization

class OrganizationFactory(Factory):
    class Meta:
        model = Organization

    name = Faker('company')
    slug = Faker('slug')
    primary_color = '#0d6efd'
```

## Troubleshooting

### Tests fail with "Application context required"
Make sure tests are wrapped with `with app.app_context():`

### Tests fail with database errors
Check that migrations are up to date:
```bash
docker-compose exec web flask db upgrade
```

### Tests are slow
- Use in-memory database (SQLite)
- Mock external API calls
- Use fixtures instead of database queries

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Flask Testing Guide](https://flask.palletsprojects.com/en/latest/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

## Support

For questions about testing:
1. Check this documentation
2. Review existing tests for examples
3. Check pytest documentation
4. Ask the development team
