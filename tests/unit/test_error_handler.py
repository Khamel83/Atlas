"""
Tests for error handling and logging systems.

This module provides comprehensive tests for the Atlas error handling infrastructure,
including error categorization, logging, retry mechanisms, and recovery systems.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from helpers.error_handler import (
    AtlasError,
    AtlasErrorHandler,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    FileSystemErrorHandler,
    NetworkErrorHandler,
    create_error_handler,
    handle_file_system_error,
    handle_network_error,
)


class TestErrorContext(unittest.TestCase):
    """Test error context data structure."""

    def test_error_context_creation(self):
        """Test creating error context with required fields."""
        context = ErrorContext(module="test_module", function="test_function")
        
        self.assertEqual(context.module, "test_module")
        self.assertEqual(context.function, "test_function")
        self.assertIsNone(context.url)
        self.assertIsNone(context.file_path)
        self.assertEqual(context.metadata, {})
        self.assertIsInstance(context.timestamp, str)

    def test_error_context_with_optional_fields(self):
        """Test creating error context with optional fields."""
        metadata = {"key": "value", "count": 42}
        context = ErrorContext(
            module="test_module",
            function="test_function",
            url="https://example.com",
            file_path="/path/to/file.txt",
            metadata=metadata
        )
        
        self.assertEqual(context.url, "https://example.com")
        self.assertEqual(context.file_path, "/path/to/file.txt")
        self.assertEqual(context.metadata, metadata)

    def test_timestamp_generation(self):
        """Test that timestamp is automatically generated."""
        context = ErrorContext(module="test", function="test")
        
        # Should be a valid ISO format timestamp
        try:
            datetime.fromisoformat(context.timestamp)
        except ValueError:
            self.fail("Timestamp should be in ISO format")


class TestAtlasError(unittest.TestCase):
    """Test AtlasError data structure."""

    def setUp(self):
        """Set up test fixtures."""
        self.context = ErrorContext(module="test_module", function="test_function")

    def test_atlas_error_creation(self):
        """Test creating AtlasError with required fields."""
        error = AtlasError(
            message="Test error message",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            context=self.context
        )
        
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.category, ErrorCategory.PROCESSING)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(error.context, self.context)
        self.assertIsNone(error.original_exception)
        self.assertIsNone(error.traceback_str)
        self.assertFalse(error.should_retry)
        self.assertEqual(error.retry_count, 0)
        self.assertEqual(error.max_retries, 3)

    def test_atlas_error_with_exception(self):
        """Test AtlasError with original exception."""
        original_exception = ValueError("Original error")
        
        with patch('traceback.format_exc', return_value="Mock traceback"):
            error = AtlasError(
                message="Test error",
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.HIGH,
                context=self.context,
                original_exception=original_exception
            )
        
        self.assertEqual(error.original_exception, original_exception)
        self.assertEqual(error.traceback_str, "Mock traceback")

    def test_atlas_error_retry_configuration(self):
        """Test AtlasError retry configuration."""
        error = AtlasError(
            message="Retryable error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=self.context,
            should_retry=True,
            max_retries=5
        )
        
        self.assertTrue(error.should_retry)
        self.assertEqual(error.max_retries, 5)


class TestNetworkErrorHandler(unittest.TestCase):
    """Test network error handling utilities."""

    def test_categorize_http_error_client_errors(self):
        """Test categorization of client errors (4xx)."""
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(400), ErrorSeverity.MEDIUM
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(401), ErrorSeverity.MEDIUM
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(403), ErrorSeverity.MEDIUM
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(404), ErrorSeverity.MEDIUM
        )

    def test_categorize_http_error_server_errors(self):
        """Test categorization of server errors (5xx)."""
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(500), ErrorSeverity.HIGH
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(502), ErrorSeverity.HIGH
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(503), ErrorSeverity.HIGH
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(504), ErrorSeverity.HIGH
        )

    def test_categorize_http_error_rate_limiting(self):
        """Test categorization of rate limiting (429)."""
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(429), ErrorSeverity.LOW
        )

    def test_categorize_http_error_unknown(self):
        """Test categorization of unknown status codes."""
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(418), ErrorSeverity.MEDIUM  # I'm a teapot
        )

    def test_should_retry_http_error_retryable(self):
        """Test retry logic for retryable HTTP errors."""
        self.assertTrue(NetworkErrorHandler.should_retry_http_error(429))  # Rate limit
        self.assertTrue(NetworkErrorHandler.should_retry_http_error(500))  # Server error
        self.assertTrue(NetworkErrorHandler.should_retry_http_error(502))  # Bad gateway
        self.assertTrue(NetworkErrorHandler.should_retry_http_error(503))  # Service unavailable
        self.assertTrue(NetworkErrorHandler.should_retry_http_error(504))  # Gateway timeout

    def test_should_retry_http_error_non_retryable(self):
        """Test retry logic for non-retryable HTTP errors."""
        self.assertFalse(NetworkErrorHandler.should_retry_http_error(400))  # Bad request
        self.assertFalse(NetworkErrorHandler.should_retry_http_error(401))  # Unauthorized
        self.assertFalse(NetworkErrorHandler.should_retry_http_error(403))  # Forbidden
        self.assertFalse(NetworkErrorHandler.should_retry_http_error(404))  # Not found


class TestFileSystemErrorHandler(unittest.TestCase):
    """Test file system error handling utilities."""

    def test_categorize_fs_error_permission(self):
        """Test categorization of permission errors."""
        self.assertEqual(
            FileSystemErrorHandler.categorize_fs_error(PermissionError()),
            ErrorSeverity.HIGH,
        )

    def test_categorize_fs_error_not_found(self):
        """Test categorization of file not found errors."""
        self.assertEqual(
            FileSystemErrorHandler.categorize_fs_error(FileNotFoundError()),
            ErrorSeverity.MEDIUM,
        )

    def test_categorize_fs_error_os_error(self):
        """Test categorization of OS errors."""
        self.assertEqual(
            FileSystemErrorHandler.categorize_fs_error(OSError()),
            ErrorSeverity.HIGH,
        )

    def test_categorize_fs_error_unknown(self):
        """Test categorization of unknown file system errors."""
        self.assertEqual(
            FileSystemErrorHandler.categorize_fs_error(ValueError()),
            ErrorSeverity.MEDIUM,
        )

    def test_should_retry_fs_error_non_retryable(self):
        """Test retry logic for non-retryable file system errors."""
        self.assertFalse(
            FileSystemErrorHandler.should_retry_fs_error(PermissionError())
        )
        self.assertFalse(
            FileSystemErrorHandler.should_retry_fs_error(FileNotFoundError())
        )

    def test_should_retry_fs_error_retryable(self):
        """Test retry logic for retryable file system errors."""
        self.assertTrue(
            FileSystemErrorHandler.should_retry_fs_error(OSError())
        )
        self.assertTrue(
            FileSystemErrorHandler.should_retry_fs_error(IOError())
        )


class TestAtlasErrorHandler(unittest.TestCase):
    """Test AtlasErrorHandler functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "data_directory": self.temp_dir,
            "environment": "test",
            "log_level": "DEBUG"
        }
        self.handler = AtlasErrorHandler(self.config)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_handler_initialization(self):
        """Test error handler initialization."""
        self.assertEqual(self.handler.data_directory, self.temp_dir)
        self.assertEqual(self.handler.environment, "test")
        self.assertEqual(self.handler.log_level, "DEBUG")
        
        # Check that log directories are created
        self.assertTrue(os.path.exists(os.path.dirname(self.handler.error_log_path)))
        self.assertTrue(os.path.exists(os.path.dirname(self.handler.validation_log_path)))

    def test_create_error(self):
        """Test creating AtlasError through handler."""
        context = ErrorContext(module="test", function="test_func")
        error = self.handler.create_error(
            message="Test error",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            context=context,
        )
        
        self.assertIsInstance(error, AtlasError)
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.category, ErrorCategory.PROCESSING)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(error.context, context)

    def test_create_error_with_retry(self):
        """Test creating retryable error."""
        context = ErrorContext(module="test", function="test_func")
        error = self.handler.create_error(
            message="Retryable error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            should_retry=True,
            max_retries=5
        )
        
        self.assertTrue(error.should_retry)
        self.assertEqual(error.max_retries, 5)

    @patch('helpers.utils.log_error')
    def test_log_to_module(self, mock_log_error):
        """Test logging to module-specific log."""
        context = ErrorContext(
            module="test_module", 
            function="test_func",
            url="https://example.com",
            file_path="/test/file.txt"
        )
        error = AtlasError(
            message="Test error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context
        )
        
        self.handler._log_to_module(error, "test.log")
        
        # Verify log_error was called with expected message
        mock_log_error.assert_called()
        call_args = mock_log_error.call_args[0]
        self.assertEqual(call_args[0], "test.log")
        self.assertIn("NETWORK", call_args[1])
        self.assertIn("Test error", call_args[1])
        self.assertIn("https://example.com", call_args[1])
        self.assertIn("/test/file.txt", call_args[1])

    def test_log_to_central(self):
        """Test logging to centralized error log."""
        context = ErrorContext(module="test_module", function="test_func")
        error = AtlasError(
            message="Centralized error",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.HIGH,
            context=context,
            should_retry=True,
            max_retries=3
        )
        
        self.handler._log_to_central(error)
        
        # Verify log file was created and contains expected data
        self.assertTrue(os.path.exists(self.handler.error_log_path))
        
        with open(self.handler.error_log_path, 'r') as f:
            log_line = f.readline().strip()
            log_data = json.loads(log_line)
        
        self.assertEqual(log_data["message"], "Centralized error")
        self.assertEqual(log_data["category"], "processing")
        self.assertEqual(log_data["severity"], "high")
        self.assertEqual(log_data["module"], "test_module")
        self.assertEqual(log_data["function"], "test_func")
        self.assertTrue(log_data["should_retry"])
        self.assertEqual(log_data["max_retries"], 3)

    @patch('helpers.retry_queue.enqueue')
    def test_handle_retry(self, mock_enqueue):
        """Test retry handling logic."""
        context = ErrorContext(
            module="test_module", 
            function="test_func",
            url="https://example.com"
        )
        error = AtlasError(
            message="Retryable error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            should_retry=True,
            retry_count=1,
            max_retries=3
        )
        
        result = self.handler._handle_retry(error)
        
        self.assertTrue(result)
        mock_enqueue.assert_called_once()
        
        # Verify retry task structure
        retry_task = mock_enqueue.call_args[0][0]
        self.assertEqual(retry_task["type"], "test_module")
        self.assertEqual(retry_task["error"], "Retryable error")
        self.assertEqual(retry_task["category"], "network")
        self.assertEqual(retry_task["url"], "https://example.com")

    @patch('helpers.utils.log_error')
    @patch('helpers.retry_queue.enqueue')
    def test_handle_error_retryable(self, mock_enqueue, mock_log_error):
        """Test handling retryable error."""
        context = ErrorContext(module="test_module", function="test_func")
        error = AtlasError(
            message="Retryable error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            should_retry=True,
            retry_count=1,
            max_retries=3
        )
        
        result = self.handler.handle_error(error, "test.log")
        
        self.assertTrue(result)  # Should return True for successful retry
        mock_enqueue.assert_called_once()
        mock_log_error.assert_called()

    @patch('helpers.utils.log_error')
    def test_handle_error_non_retryable(self, mock_log_error):
        """Test handling non-retryable error."""
        context = ErrorContext(module="test_module", function="test_func")
        error = AtlasError(
            message="Non-retryable error",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            should_retry=False
        )
        
        result = self.handler.handle_error(error, "test.log")
        
        self.assertFalse(result)  # Should return False for non-retryable
        mock_log_error.assert_called()

    @patch('helpers.utils.log_error')
    def test_handle_error_max_retries_exceeded(self, mock_log_error):
        """Test handling error when max retries exceeded."""
        context = ErrorContext(module="test_module", function="test_func")
        error = AtlasError(
            message="Max retries exceeded",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            should_retry=True,
            retry_count=3,
            max_retries=3
        )
        
        result = self.handler.handle_error(error, "test.log")
        
        self.assertFalse(result)  # Should return False when retries exhausted

    def test_log_validation_errors(self):
        """Test logging validation errors."""
        # Mock validation errors and warnings
        errors = [
            MagicMock(
                field="test_field",
                message="Test error",
                severity="error",
                guidance="Test guidance",
                fix_command="test command",
                documentation_url="https://docs.example.com"
            )
        ]
        warnings = [
            MagicMock(
                field="warning_field",
                message="Test warning",
                severity="warning",
                guidance="Warning guidance",
                fix_command="warning command",
                documentation_url="https://docs.example.com/warning"
            )
        ]
        
        self.handler.log_validation_errors(errors, warnings)
        
        # Verify log file was created and contains expected data
        self.assertTrue(os.path.exists(self.handler.validation_log_path))
        
        with open(self.handler.validation_log_path, 'r') as f:
            log_line = f.readline().strip()
            log_data = json.loads(log_line)
        
        self.assertEqual(log_data["environment"], "test")
        self.assertEqual(log_data["validation_results"]["error_count"], 1)
        self.assertEqual(log_data["validation_results"]["warning_count"], 1)
        
        # Check error details
        error_data = log_data["validation_results"]["errors"][0]
        self.assertEqual(error_data["field"], "test_field")
        self.assertEqual(error_data["message"], "Test error")

    def test_get_error_summary_empty(self):
        """Test getting error summary when no errors exist."""
        summary = self.handler.get_error_summary(days=7)
        
        self.assertEqual(summary["total_errors"], 0)
        self.assertEqual(summary["error_categories"], {})
        self.assertEqual(summary["recent_errors"], [])
        self.assertEqual(summary["environment"], "test")

    def test_get_error_summary_with_data(self):
        """Test getting error summary with existing errors."""
        # Create test error data
        now = datetime.now()
        error_data = [
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "category": "network",
                "severity": "high",
                "message": "Network error 1"
            },
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "category": "processing",
                "severity": "medium",
                "message": "Processing error 1"
            },
            {
                "timestamp": (now - timedelta(days=8)).isoformat(),  # Too old
                "category": "network",
                "severity": "low",
                "message": "Old error"
            }
        ]
        
        # Write test data to error log
        with open(self.handler.error_log_path, 'w') as f:
            for error in error_data:
                f.write(json.dumps(error) + '\n')
        
        summary = self.handler.get_error_summary(days=7)
        
        self.assertEqual(summary["total_errors"], 2)  # Only recent errors
        self.assertEqual(summary["error_categories"]["network"], 1)
        self.assertEqual(summary["error_categories"]["processing"], 1)
        self.assertEqual(summary["severity_distribution"]["high"], 1)
        self.assertEqual(summary["severity_distribution"]["medium"], 1)
        self.assertEqual(len(summary["recent_errors"]), 2)

    def test_wrap_function_success(self):
        """Test function wrapper for successful execution."""
        def test_function(x, y):
            return x + y
        
        wrapped = self.handler.wrap_function(
            test_function,
            "test_module",
            "test_function",
            "test.log",
            ErrorCategory.PROCESSING
        )
        
        result = wrapped(2, 3)
        self.assertEqual(result, 5)

    @patch('helpers.utils.log_error')
    def test_wrap_function_exception(self, mock_log_error):
        """Test function wrapper handling exceptions."""
        def failing_function():
            raise ValueError("Test exception")
        
        wrapped = self.handler.wrap_function(
            failing_function,
            "test_module",
            "failing_function",
            "test.log",
            ErrorCategory.PROCESSING
        )
        
        result = wrapped()
        
        self.assertIsNone(result)  # Should return None on exception
        mock_log_error.assert_called()

    def test_update_troubleshooting_checklist_missing_file(self):
        """Test updating troubleshooting checklist when file doesn't exist."""
        context = ErrorContext(module="test_module", function="test_func")
        error = AtlasError(
            message="Critical error",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.CRITICAL,
            context=context
        )
        
        # Should not raise exception when file doesn't exist
        self.handler._update_troubleshooting_checklist(error)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {"data_directory": self.temp_dir, "environment": "test"}

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_error_handler(self):
        """Test error handler factory function."""
        handler = create_error_handler(self.config)
        
        self.assertIsInstance(handler, AtlasErrorHandler)
        self.assertEqual(handler.data_directory, self.temp_dir)
        self.assertEqual(handler.environment, "test")

    @patch('helpers.utils.log_error')
    @patch('helpers.retry_queue.enqueue')
    def test_handle_network_error(self, mock_enqueue, mock_log_error):
        """Test network error convenience function."""
        handler = create_error_handler(self.config)
        
        result = handle_network_error(
            url="https://example.com",
            status_code=503,
            error_handler=handler,
            log_path="test.log",
            module_name="test_module",
            function_name="test_function"
        )
        
        self.assertTrue(result)  # 503 should be retryable
        mock_enqueue.assert_called_once()
        mock_log_error.assert_called()

    @patch('helpers.utils.log_error')
    def test_handle_network_error_non_retryable(self, mock_log_error):
        """Test network error convenience function for non-retryable error."""
        handler = create_error_handler(self.config)
        
        result = handle_network_error(
            url="https://example.com",
            status_code=404,
            error_handler=handler,
            log_path="test.log",
            module_name="test_module",
            function_name="test_function"
        )
        
        self.assertFalse(result)  # 404 should not be retryable
        mock_log_error.assert_called()

    @patch('helpers.utils.log_error')
    def test_handle_file_system_error(self, mock_log_error):
        """Test file system error convenience function."""
        handler = create_error_handler(self.config)
        exception = PermissionError("Access denied")
        
        result = handle_file_system_error(
            file_path="/test/file.txt",
            exception=exception,
            error_handler=handler,
            log_path="test.log",
            module_name="test_module",
            function_name="test_function"
        )
        
        self.assertFalse(result)  # Permission errors should not be retryable
        mock_log_error.assert_called()

    @patch('helpers.utils.log_error')
    @patch('helpers.retry_queue.enqueue')
    def test_handle_file_system_error_retryable(self, mock_enqueue, mock_log_error):
        """Test file system error convenience function for retryable error."""
        handler = create_error_handler(self.config)
        exception = OSError("Temporary failure")
        
        result = handle_file_system_error(
            file_path="/test/file.txt",
            exception=exception,
            error_handler=handler,
            log_path="test.log",
            module_name="test_module",
            function_name="test_function"
        )
        
        self.assertTrue(result)  # OS errors should be retryable
        mock_enqueue.assert_called_once()
        mock_log_error.assert_called()


if __name__ == "__main__":
    unittest.main()
