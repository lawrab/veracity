# Testing Documentation

## Overview

The Veracity backend uses a comprehensive testing strategy with three levels of testing:

1. **Unit Tests** - Test individual functions and classes in isolation
2. **Integration Tests** - Test interactions with databases and external services
3. **End-to-End Tests** - Test complete workflows and user scenarios

## Running Tests

### Quick Start

```bash
# Run all tests
make test

# Run specific test types
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-e2e          # End-to-end tests only
make test-cov          # With coverage report
```

### Using the Test Runner

```bash
# Run all tests with proper setup
python run_tests.py

# Run specific test type
python run_tests.py unit
python run_tests.py integration
python run_tests.py e2e
python run_tests.py coverage

# Run linters
python run_tests.py lint
```

### Direct pytest usage

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/services/test_trend_service.py

# Run tests matching pattern
pytest tests/ -k "test_detect_trends"

# Run tests with specific marker
pytest tests/ -m unit
pytest tests/ -m "not slow"
```

## Test Structure

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── api/                # API endpoint tests
│   ├── models/             # Database model tests
│   └── services/           # Service layer tests
├── integration/            # Tests with real dependencies
│   ├── database/          # Database integration tests
│   └── external/          # External API tests
├── e2e/                    # Complete workflow tests
└── conftest.py            # Shared fixtures and configuration
```

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.unit` - Unit tests (no external dependencies)
- `@pytest.mark.integration` - Integration tests (requires services)
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.requires_api` - Tests requiring API credentials

## Fixtures

Common fixtures are defined in `conftest.py`:

### Database Fixtures
- `db_session` - Async PostgreSQL session
- `mongodb_client` - MongoDB test client
- `seed_test_data` - Pre-populated test data

### Mock Fixtures
- `mock_redis` - Mocked Redis client
- `mock_kafka_producer` - Mocked Kafka producer
- `mock_ml_model` - Mocked ML model

### Data Fixtures
- `sample_social_post` - Sample social media post
- `sample_news_article` - Sample news article
- `auth_headers` - Authentication headers

### Client Fixtures
- `client` - Synchronous FastAPI test client
- `async_client` - Asynchronous FastAPI test client

## Writing Tests

### Unit Test Example

```python
@pytest.mark.unit
async def test_calculate_trend_score(trend_service):
    """Test trend score calculation."""
    cluster = {"posts": [...], "growth_rate": 0.5}
    score = await trend_service._calculate_trend_score(cluster)
    
    assert 0 <= score <= 1
    assert isinstance(score, float)
```

### Integration Test Example

```python
@pytest.mark.integration
async def test_store_posts_in_mongodb(reddit_collector, mongodb_client):
    """Test storing posts in MongoDB."""
    posts = [{"content": "test", "platform": "reddit"}]
    stored = await reddit_collector.store_posts(posts)
    
    assert stored == 1
    doc = await mongodb_client.social_posts.find_one()
    assert doc is not None
```

### E2E Test Example

```python
@pytest.mark.e2e
@pytest.mark.slow
async def test_complete_pipeline(setup_services):
    """Test data flow from ingestion to scoring."""
    # Collect data
    posts = await collect_social_media_data()
    # Process with NLP
    processed = await process_posts(posts)
    # Detect trends
    trends = await detect_trends(processed)
    # Calculate trust scores
    scores = await calculate_scores(trends)
    
    assert all validations pass
```

## Test Coverage

We aim for:
- **80%+ overall coverage**
- **90%+ coverage for core algorithms** (trust scoring, trend detection)
- **100% coverage for critical security code**

View coverage reports:
```bash
# Generate HTML report
make test-cov

# Open in browser
open htmlcov/index.html
```

## Mocking External Services

For unit tests, mock external dependencies:

```python
from unittest.mock import patch, AsyncMock

@patch('app.services.reddit_api.fetch_posts')
async def test_with_mock(mock_fetch):
    mock_fetch.return_value = [{"id": 1, "content": "test"}]
    result = await service.process()
    mock_fetch.assert_called_once()
```

## Test Database

Tests use a separate `test_veracity` database that is:
- Created automatically when running integration tests
- Isolated from development data
- Reset between test runs
- Cleaned up after tests complete

## Continuous Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request
- Can be triggered manually via GitHub Actions

The CI pipeline:
1. Sets up test databases
2. Runs linters (black, isort, flake8)
3. Runs unit tests
4. Runs integration tests
5. Generates coverage report
6. Uploads to Codecov

## Performance Testing

For performance-critical code:

```python
@pytest.mark.slow
def test_performance(benchmark):
    """Test function performance."""
    result = benchmark(expensive_function, arg1, arg2)
    assert benchmark.stats["mean"] < 0.1  # Under 100ms
```

## Debugging Tests

```bash
# Run with verbose output
pytest -vv tests/

# Show print statements
pytest -s tests/

# Drop into debugger on failure
pytest --pdb tests/

# Run specific test with full traceback
pytest tests/unit/test_file.py::test_function -vv --tb=long
```

## Best Practices

1. **Keep tests fast** - Mock external dependencies in unit tests
2. **Use descriptive names** - `test_detect_trends_identifies_clusters`
3. **Test one thing** - Each test should verify a single behavior
4. **Use fixtures** - Reuse common setup code
5. **Clean up** - Ensure tests don't leave artifacts
6. **Document complex tests** - Add docstrings explaining the scenario
7. **Test edge cases** - Empty inputs, None values, exceptions
8. **Use appropriate markers** - Help others run relevant tests