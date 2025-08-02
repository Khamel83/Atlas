import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from helpers.error_handler import (
    AtlasError,
    AtlasErrorHandler,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    FileSystemErrorHandler,
    NetworkErrorHandler,
)


class TestErrorHandlers(unittest.TestCase):

    def test_categorize_http_error(self):
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(404), ErrorSeverity.MEDIUM
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(500), ErrorSeverity.HIGH
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(429), ErrorSeverity.LOW
        )

    def test_should_retry_http_error(self):
        self.assertTrue(NetworkErrorHandler.should_retry_http_error(503))
        self.assertFalse(NetworkErrorHandler.should_retry_http_error(404))

    def test_categorize_fs_error(self):
        self.assertEqual(
            FileSystemErrorHandler.categorize_fs_error(PermissionError()),
            ErrorSeverity.HIGH,
        )
        self.assertEqual(
            FileSystemErrorHandler.categorize_fs_error(FileNotFoundError()),
            ErrorSeverity.MEDIUM,
        )

    def test_should_retry_fs_error(self):
        self.assertFalse(
            FileSystemErrorHandler.should_retry_fs_error(PermissionError())
        )
        self.assertTrue(FileSystemErrorHandler.should_retry_fs_error(OSError()))


class TestAtlasErrorHandler(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(self.id().split(".")[-1])
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        (self.tmp_dir / "retries").mkdir(parents=True, exist_ok=True)
        self.config = {
            "data_directory": str(self.tmp_dir),
            "retry_queue_path": str(self.tmp_dir / "retries" / "queue.jsonl"),
        }
        self.handler = AtlasErrorHandler(self.config)

    def tearDown(self):
        if self.tmp_dir.exists():
            import shutil

            shutil.rmtree(self.tmp_dir)

    def test_create_error(self):
        context = ErrorContext(module="test", function="test_func")
        error = self.handler.create_error(
            message="Test error",
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            context=context,
        )
        self.assertIsInstance(error, AtlasError)
        self.assertEqual(error.message, "Test error")


if __name__ == "__main__":
    unittest.main()
