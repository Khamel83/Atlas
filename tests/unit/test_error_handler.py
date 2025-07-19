"""
Unit tests for helpers.error_handler module.

Tests error categorization, severity levels, context tracking, and error handling logic.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
import json
from datetime import datetime
import time
import os

# Import the module under test
from helpers.error_handler import (
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    AtlasError,
    AtlasErrorHandler,
    NetworkErrorHandler,
    FileSystemErrorHandler
)

class TestErrorSeverity:
    """Test the ErrorSeverity enum."""
    
    @pytest.mark.unit
    def test_severity_levels(self):
        """Test all severity levels exist."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"
    
    @pytest.mark.unit
    def test_severity_ordering(self):
        """Test severity level ordering."""
        severities = [ErrorSeverity.LOW, ErrorSeverity.MEDIUM, ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        assert severities == sorted(severities, key=lambda x: x.value)

class TestErrorCategory:
    """Test the ErrorCategory enum."""
    
    @pytest.mark.unit
    def test_all_categories_exist(self):
        """Test all expected error categories exist."""
        expected_categories = [
            "NETWORK", "PARSING", "AUTHENTICATION", "RATE_LIMIT", 
            "FILE_SYSTEM", "CONFIGURATION", "EXTERNAL_SERVICE", 
            "VALIDATION", "PROCESSING", "UNKNOWN"
        ]
        
        for category in expected_categories:
            assert hasattr(ErrorCategory, category)
    
    @pytest.mark.unit
    def test_category_values(self):
        """Test category values are correctly set."""
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.PARSING.value == "parsing"
        assert ErrorCategory.AUTHENTICATION.value == "authentication"

class TestErrorContext:
    """Test the ErrorContext dataclass."""
    
    @pytest.mark.unit
    def test_context_creation(self):
        """Test ErrorContext creation with all fields."""
        context = ErrorContext(
            operation="test_operation",
            url="https://example.com",
            file_path="/test/path",
            additional_info={"key": "value"},
            timestamp=datetime.now(),
            user_agent="test-agent",
            request_id="test-123"
        )
        
        assert context.operation == "test_operation"
        assert context.url == "https://example.com"
        assert context.file_path == "/test/path"
        assert context.additional_info == {"key": "value"}
        assert context.user_agent == "test-agent"
        assert context.request_id == "test-123"
    
    @pytest.mark.unit
    def test_context_defaults(self):
        """Test ErrorContext with default values."""
        context = ErrorContext(operation="test")
        
        assert context.operation == "test"
        assert context.url is None
        assert context.file_path is None
        assert context.additional_info == {}
        assert context.timestamp is not None
        assert context.user_agent is None
        assert context.request_id is None

class TestAtlasError:
    """Test the AtlasError dataclass."""
    
    @pytest.mark.unit
    def test_error_creation(self):
        """Test AtlasError creation with all fields."""
        context = ErrorContext(operation="test_op")
        error = AtlasError(
            message="Test error message",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            context=context,
            original_exception=ValueError("Original error"),
            suggested_action="Try again",
            error_code="TEST_001"
        )
        
        assert error.message == "Test error message"
        assert error.category == ErrorCategory.NETWORK
        assert error.severity == ErrorSeverity.HIGH
        assert error.context == context
        assert isinstance(error.original_exception, ValueError)
        assert error.suggested_action == "Try again"
        assert error.error_code == "TEST_001"
    
    @pytest.mark.unit
    def test_error_defaults(self):
        """Test AtlasError with default values."""
        error = AtlasError(
            message="Test error",
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM
        )
        
        assert error.message == "Test error"
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context is None
        assert error.original_exception is None
        assert error.suggested_action is None
        assert error.error_code is None

class TestAtlasErrorHandler:
    """Test the AtlasErrorHandler class."""
    
    @pytest.fixture
    def handler(self, tmp_path):
        """Create AtlasErrorHandler instance with temporary directory."""
        config = {"data_directory": str(tmp_path)}
        return AtlasErrorHandler(config)
    
    @pytest.fixture
    def sample_error(self):
        """Create sample AtlasError for testing."""
        context = ErrorContext(module="test_module", function="test_function")
        return AtlasError(
            message="Test error message",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            context=context
        )
    
    @pytest.mark.unit
    def test_handler_initialization(self, handler, tmp_path):
        """Test handler initialization."""
        assert handler.data_directory == str(tmp_path)
        assert os.path.exists(handler.data_directory)
        assert handler.error_log_path.endswith("error_log.jsonl")
    
    @pytest.mark.unit
    def test_handle_error_logging(self, handler, sample_error, tmp_path):
        """Test error handling and logging."""
        log_path = os.path.join(str(tmp_path), "test_module.log")
        result = handler.handle_error(sample_error, log_path)
        assert result is False
        # Check that log file was created and contains the error
        with open(log_path, "r") as f:
            log_content = f.read()
            assert "Test error message" in log_content
    
    @pytest.mark.unit
    def test_handle_error_file_logging(self, handler, sample_error, tmp_path):
        """Test error logging to central error log file."""
        log_path = os.path.join(str(tmp_path), "test_module.log")
        handler.handle_error(sample_error, log_path)
        # Check that error log file was created
        error_log_file = os.path.join(str(tmp_path), "error_log.jsonl")
        assert os.path.exists(error_log_file)
        # Verify log content
        with open(error_log_file, 'r') as f:
            lines = f.readlines()
            assert any("Test error message" in line for line in lines)
    
    @pytest.mark.unit
    def test_create_error(self, handler):
        """Test create_error method."""
        context = ErrorContext(module="test_module", function="test_function")
        error = handler.create_error(
            message="Test error",
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            context=context
        )
        assert isinstance(error, AtlasError)
        assert error.message == "Test error"
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context == context
    
    @pytest.mark.unit
    def test_wrap_function(self, handler, tmp_path):
        """Test wrap_function decorator."""
        log_path = os.path.join(str(tmp_path), "test_module.log")
        @handler.wrap_function(
            func=lambda x: 1 / x,
            module_name="test_module",
            function_name="test_func",
            log_path=log_path,
            error_category=ErrorCategory.PROCESSING,
            should_retry=False
        )
        def test_func(x):
            return 1 / x
        # Should return None and log error for division by zero
        result = test_func(0)
        assert result is None
        with open(log_path, "r") as f:
            log_content = f.read()
            assert "division by zero" in log_content
    
    @pytest.mark.unit
    def test_critical_error_updates_troubleshooting(self, handler, tmp_path):
        """Test that critical errors update troubleshooting checklist."""
        # Create a dummy troubleshooting checklist
        checklist_path = os.path.join(os.getcwd(), "docs", "troubleshooting_checklist.md")
        os.makedirs(os.path.dirname(checklist_path), exist_ok=True)
        with open(checklist_path, "w") as f:
            f.write("# Troubleshooting\n\n## Post-Task Checklist:")
        context = ErrorContext(module="test_module", function="test_function")
        error = handler.create_error(
            message="Critical failure",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            context=context
        )
        log_path = os.path.join(str(tmp_path), "test_module.log")
        handler.handle_error(error, log_path)
        # Check that troubleshooting checklist was updated
        with open(checklist_path, "r") as f:
            content = f.read()
            assert "Critical failure" in content

class TestNetworkErrorHandler:
    """Test the NetworkErrorHandler class."""
    
    @pytest.fixture
    def handler(self, temp_dir):
        """Create NetworkErrorHandler instance."""
        return NetworkErrorHandler(log_dir=temp_dir)
    
    @pytest.mark.unit
    def test_categorize_network_error(self, handler):
        """Test network error categorization."""
        # Test timeout error
        timeout_error = Exception("Request timed out")
        atlas_error = handler.categorize_error(timeout_error, "test_op")
        assert atlas_error.category == ErrorCategory.NETWORK
        assert atlas_error.severity == ErrorSeverity.MEDIUM
        
        # Test connection error
        connection_error = Exception("Connection refused")
        atlas_error = handler.categorize_error(connection_error, "test_op")
        assert atlas_error.category == ErrorCategory.NETWORK
        assert atlas_error.severity == ErrorSeverity.HIGH
    
    @pytest.mark.unit
    def test_handle_rate_limit(self, handler):
        """Test rate limit error handling."""
        rate_limit_error = Exception("Rate limit exceeded")
        atlas_error = handler.categorize_error(rate_limit_error, "test_op")
        
        assert atlas_error.category == ErrorCategory.RATE_LIMIT
        assert atlas_error.severity == ErrorSeverity.MEDIUM
        assert "rate limit" in atlas_error.suggested_action.lower()
    
    @pytest.mark.unit
    def test_get_retry_delay_with_jitter(self, handler):
        """Test retry delay with jitter."""
        operation = "test_operation"
        
        # Get multiple delay values to test jitter
        delays = [handler.get_retry_delay(operation) for _ in range(10)]
        
        # All delays should be around base delay but with some variation
        assert all(0.5 <= delay <= 1.5 for delay in delays)
        
        # Not all delays should be exactly the same (jitter effect)
        assert len(set(delays)) > 1

class TestFileSystemErrorHandler:
    """Test the FileSystemErrorHandler class."""
    
    @pytest.fixture
    def handler(self, temp_dir):
        """Create FileSystemErrorHandler instance."""
        return FileSystemErrorHandler(log_dir=temp_dir)
    
    @pytest.mark.unit
    def test_categorize_file_errors(self, handler):
        """Test file system error categorization."""
        # Test permission error
        permission_error = PermissionError("Permission denied")
        atlas_error = handler.categorize_error(permission_error, "test_op")
        assert atlas_error.category == ErrorCategory.FILE_SYSTEM
        assert atlas_error.severity == ErrorSeverity.HIGH
        
        # Test file not found error
        not_found_error = FileNotFoundError("File not found")
        atlas_error = handler.categorize_error(not_found_error, "test_op")
        assert atlas_error.category == ErrorCategory.FILE_SYSTEM
        assert atlas_error.severity == ErrorSeverity.MEDIUM
    
    @pytest.mark.unit
    def test_disk_space_check(self, handler, temp_dir):
        """Test disk space checking."""
        with patch('shutil.disk_usage') as mock_disk_usage:
            # Mock disk usage: total=1000, used=900, free=100
            mock_disk_usage.return_value = (1000, 900, 100)
            
            # Should detect low disk space (10% free)
            error = FileNotFoundError("No space left")
            atlas_error = handler.categorize_error(error, "test_op", file_path=str(temp_dir))
            
            assert "disk space" in atlas_error.suggested_action.lower()
    
    @pytest.mark.unit
    def test_file_permission_suggestions(self, handler):
        """Test file permission error suggestions."""
        permission_error = PermissionError("Permission denied")
        atlas_error = handler.categorize_error(permission_error, "test_op")
        
        assert "permission" in atlas_error.suggested_action.lower()
        assert "chmod" in atlas_error.suggested_action.lower()

class TestErrorHandlerIntegration:
    """Integration tests for error handling system."""
    
    @pytest.mark.integration
    def test_full_error_handling_pipeline(self, temp_dir):
        """Test complete error handling pipeline."""
        handler = AtlasErrorHandler(log_dir=temp_dir)
        
        # Simulate a network error
        try:
            raise ConnectionError("Network connection failed")
        except Exception as e:
            context = ErrorContext(
                operation="fetch_article",
                url="https://example.com/article",
                additional_info={"attempt": 1}
            )
            
            atlas_error = AtlasError(
                message=str(e),
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                context=context,
                original_exception=e,
                error_code="NET_001"
            )
            
            # Handle the error
            result = handler.handle_error(atlas_error)
            
            assert result is True
            assert len(handler.error_history) == 1
            assert handler.should_retry(atlas_error, "fetch_article") is True
            
            # Verify error was logged to file
            error_log_file = temp_dir / "error_log.json"
            assert error_log_file.exists()
    
    @pytest.mark.integration
    def test_retry_exhaustion_scenario(self, temp_dir):
        """Test scenario where retries are exhausted."""
        handler = AtlasErrorHandler(log_dir=temp_dir, max_retries=2)
        
        error = AtlasError(
            message="Persistent error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            error_code="NET_002"
        )
        
        operation = "persistent_operation"
        
        # First retry should be allowed
        assert handler.should_retry(error, operation) is True
        handler._increment_retry_count(operation)
        
        # Second retry should be allowed
        assert handler.should_retry(error, operation) is True
        handler._increment_retry_count(operation)
        
        # Third retry should be denied (max_retries=2)
        assert handler.should_retry(error, operation) is False
        
        # Verify error statistics
        stats = handler.get_error_stats()
        assert stats['total_errors'] == 0  # No errors handled yet, just retry checks
    
    @pytest.mark.integration
    def test_error_recovery_and_reset(self, temp_dir):
        """Test error recovery and retry count reset."""
        handler = AtlasErrorHandler(log_dir=temp_dir)
        
        error = AtlasError(
            message="Temporary error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM
        )
        
        operation = "recovery_test"
        
        # Simulate some failed attempts
        handler._increment_retry_count(operation)
        handler._increment_retry_count(operation)
        assert handler.retry_counts[operation] == 2
        
        # Simulate successful recovery
        handler.reset_retry_count(operation)
        assert handler.retry_counts.get(operation, 0) == 0
        
        # Should be able to retry again
        assert handler.should_retry(error, operation) is True 