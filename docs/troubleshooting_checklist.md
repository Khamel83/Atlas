# Atlas Troubleshooting Checklist

This checklist helps avoid repeating past mistakes and ensures proper system setup.

## Pre-Development Checklist

### 1. Environment Setup
- [ ] **Testing Environment**: Run `pytest --version` to ensure pytest is installed
- [ ] **Coverage Tools**: Run `pytest --cov=helpers --version` to verify coverage tools
- [ ] **Dependencies**: All packages in `requirements.txt` are installed
- [ ] **Configuration**: `.env` file exists with required variables
- [ ] **Git Branch**: Not on `main` branch (use feature branches)

### 2. Code Quality Checks
- [ ] **Run Tests**: Execute `pytest` to ensure all tests pass
- [ ] **Test Coverage**: Verify coverage meets 80% minimum threshold
- [ ] **Type Hints**: New code includes proper type hints
- [ ] **Documentation**: API documentation updated for new/changed modules

### 3. Architecture Compliance
- [ ] **Use Refactored Modules**: Prefer new modules over legacy ones
  - Use `helpers/article_strategies.py` instead of `helpers/article_fetcher.py`
  - Use `helpers/error_handler.py` for standardized error handling
  - Use `helpers/metadata_manager.py` for metadata operations
  - Use `helpers/path_manager.py` for file path operations
- [ ] **Error Handling**: All operations use `AtlasErrorHandler` for consistent error management
- [ ] **Metadata Structure**: All content uses `ContentMetadata` standardized structure
- [ ] **Path Management**: All file operations use `PathManager` for consistent path handling

## Development Checklist

### 1. Before Making Changes
- [ ] **Read Documentation**: Review relevant API documentation in `docs/api_documentation.md`
- [ ] **Check Tests**: Ensure existing tests cover the area you're modifying
- [ ] **Understand Dependencies**: Review task dependencies in TODO list

### 2. During Development
- [ ] **Write Tests First**: Create tests before implementing functionality (TDD approach)
- [ ] **Use Mocks**: Leverage existing test fixtures and mocks in `tests/conftest.py`
- [ ] **Follow Patterns**: Use established patterns from existing refactored modules
- [ ] **Handle Errors**: Use `AtlasError` and `AtlasErrorHandler` for all error scenarios

### 3. After Making Changes
- [ ] **Run Full Test Suite**: Execute `pytest` to ensure no regressions
- [ ] **Check Coverage**: Verify new code has adequate test coverage
- [ ] **Update Documentation**: Update API docs and README if needed
- [ ] **Commit with Clear Messages**: Use format `[TASK-ID] Brief description`

## Testing Checklist

### 1. Test Categories
- [ ] **Unit Tests**: Fast, isolated tests for individual functions/classes
- [ ] **Integration Tests**: Tests that verify component interactions
- [ ] **Performance Tests**: Benchmarks for large-scale operations
- [ ] **Regression Tests**: Tests for previously fixed bugs

### 2. Test Environment
- [ ] **Isolated Environment**: Tests use temporary directories and mock services
- [ ] **No External Dependencies**: Tests don't require network access or real APIs
- [ ] **Consistent Data**: Use fixtures for repeatable test data
- [ ] **Proper Cleanup**: Tests clean up temporary files and restore environment

### 3. Test Execution
- [ ] **Run Specific Categories**: Use `pytest -m unit` for fast feedback
- [ ] **Check Coverage**: Use `pytest --cov=helpers --cov-report=html`
- [ ] **Performance Testing**: Run `pytest -m performance` for scaling tests
- [ ] **CI/CD Ready**: Tests pass in clean environment

## Common Issues and Solutions

### 1. Import Errors
- **Issue**: Module not found errors
- **Solution**: Ensure project root is in Python path, check `sys.path` in test files

### 2. API Signature Mismatches
- **Issue**: Method signatures don't match documentation
- **Solution**: Check actual implementation in source code, update documentation if needed

### 3. Test Failures
- **Issue**: Tests fail due to environment differences
- **Solution**: Use `test_env` fixture for isolated environment, check mock configurations

### 4. Configuration Issues
- **Issue**: Missing or incorrect configuration values
- **Solution**: Use `helpers/config.py` for centralized config, validate at startup

### 5. Path Management Problems
- **Issue**: Inconsistent file paths across modules
- **Solution**: Use `PathManager` for all file operations, avoid hardcoded paths

## Error Handling Best Practices

### 1. Error Creation
```python
from helpers.error_handler import AtlasError, ErrorCategory, ErrorSeverity

error = AtlasError(
    message="Clear description of what went wrong",
    category=ErrorCategory.NETWORK,  # Appropriate category
    severity=ErrorSeverity.HIGH,     # Appropriate severity
    original_exception=e,            # Include original exception
    error_code="NET_001"            # Unique error code
)
```

### 2. Error Handling
```python
from helpers.error_handler import AtlasErrorHandler

handler = AtlasErrorHandler(log_dir=Path("logs"))
handler.handle_error(error)

if handler.should_retry(error, "operation_name"):
    delay = handler.get_retry_delay("operation_name")
    # Implement retry logic
```

### 3. Context Information
```python
from helpers.error_handler import ErrorContext

context = ErrorContext(
    operation="fetch_article",
    url="https://example.com/article",
    additional_info={"attempt": 1}
)
```

## Performance Considerations

### 1. Large Scale Operations
- [ ] **Batch Processing**: Use batch operations for multiple items
- [ ] **Memory Management**: Monitor memory usage for large datasets
- [ ] **Progress Tracking**: Implement progress bars for long-running operations
- [ ] **Parallel Processing**: Use parallel processing where appropriate

### 2. Testing Performance
- [ ] **Baseline Metrics**: Establish performance baselines for key operations
- [ ] **Scaling Tests**: Test with large datasets (1000+ items)
- [ ] **Memory Profiling**: Monitor memory usage during tests
- [ ] **Bottleneck Identification**: Profile code to identify performance issues

## Documentation Maintenance

### 1. Keep Documentation Current
- [ ] **API Changes**: Update `docs/api_documentation.md` for any API changes
- [ ] **Architecture Changes**: Update README.md for structural changes
- [ ] **Process Changes**: Update this checklist for new procedures

### 2. Documentation Review
- [ ] **Accuracy**: Verify documentation matches actual implementation
- [ ] **Completeness**: Ensure all public APIs are documented
- [ ] **Examples**: Include working code examples
- [ ] **Migration Guides**: Update migration guides for breaking changes

## Pre-Commit Checklist

Before committing changes:
- [ ] All tests pass (`pytest`)
- [ ] Code coverage meets minimum threshold
- [ ] Documentation updated for changes
- [ ] Commit message follows format: `[TASK-ID] Brief description`
- [ ] No debugging code or temporary files included
- [ ] Changes align with project architecture principles

## Emergency Procedures

### 1. Test Failures in CI/CD
1. Run tests locally to reproduce
2. Check for environment differences
3. Review recent changes for breaking modifications
4. Fix issues and re-run full test suite

### 2. Performance Degradation
1. Run performance tests to identify bottlenecks
2. Profile code to find performance issues
3. Implement optimizations
4. Verify improvements with benchmarks

### 3. Configuration Issues
1. Check environment variables and configuration files
2. Validate configuration using `helpers/config.py`
3. Review configuration documentation
4. Test with minimal configuration

---

**Remember**: This checklist is a living document. Update it when you discover new issues or solutions to prevent repeating mistakes. 