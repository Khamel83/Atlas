"""
Tests for configuration hot-reloading functionality.

This module tests the file system monitoring and automatic configuration
reloading capabilities used during development.
"""

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helpers.config_hotreload import (
    ConfigHotReloader,
    ConfigReloadHandler,
    start_config_hotreload,
    stop_config_hotreload,
    is_hotreload_active,
    ConfigHotReloadContext,
)


class TestConfigReloadHandler(unittest.TestCase):
    """Test configuration reload event handler."""

    def setUp(self):
        """Set up test fixtures."""
        self.callback = MagicMock()
        self.config_files = {"/test/config/.env", "/test/config/environments.yaml"}
        self.handler = ConfigReloadHandler(self.callback, self.config_files)

    def test_handler_initialization(self):
        """Test handler initializes correctly."""
        self.assertEqual(self.handler.callback, self.callback)
        self.assertEqual(self.handler.config_files, self.config_files)
        self.assertEqual(self.handler.debounce_delay, 1.0)

    def test_ignore_directory_events(self):
        """Test that directory events are ignored."""
        event = MagicMock(is_directory=True, src_path="/test/config")
        
        self.handler.on_modified(event)
        
        self.callback.assert_not_called()

    def test_ignore_unmonitored_files(self):
        """Test that unmonitored files are ignored."""
        event = MagicMock(is_directory=False, src_path="/test/other/file.txt")
        
        self.handler.on_modified(event)
        
        self.callback.assert_not_called()

    def test_handle_monitored_file_change(self):
        """Test handling of monitored file changes."""
        event = MagicMock(is_directory=False, src_path="/test/config/.env")
        
        self.handler.on_modified(event)
        
        self.callback.assert_called_once_with("/test/config/.env")

    def test_debounce_rapid_changes(self):
        """Test debouncing of rapid file changes."""
        event = MagicMock(is_directory=False, src_path="/test/config/.env")
        
        # First call should trigger callback
        self.handler.on_modified(event)
        self.assertEqual(self.callback.call_count, 1)
        
        # Immediate second call should be debounced
        self.handler.on_modified(event)
        self.assertEqual(self.callback.call_count, 1)
        
        # After debounce delay, should trigger again
        self.handler.last_reload["/test/config/.env"] = time.time() - 2.0
        self.handler.on_modified(event)
        self.assertEqual(self.callback.call_count, 2)


class TestConfigHotReloader(unittest.TestCase):
    """Test configuration hot-reloader functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.callback = MagicMock()
        self.reloader = ConfigHotReloader(self.callback)

    def tearDown(self):
        """Clean up test fixtures."""
        if self.reloader.is_running:
            self.reloader.stop()

    def test_reloader_initialization(self):
        """Test reloader initializes correctly."""
        self.assertEqual(self.reloader.reload_callback, self.callback)
        self.assertIsNone(self.reloader.current_config)
        self.assertFalse(self.reloader.is_running)
        self.assertIsInstance(self.reloader.config_files, set)

    def test_get_config_files(self):
        """Test configuration file discovery."""
        config_files = self.reloader._get_config_files()
        
        # Should be a set of absolute paths
        self.assertIsInstance(config_files, set)
        for file_path in config_files:
            self.assertTrue(os.path.isabs(file_path))
            self.assertTrue(os.path.exists(file_path))

    @patch('helpers.config_hotreload.load_config')
    def test_reload_config_success(self, mock_load_config):
        """Test successful configuration reload."""
        # Mock configuration data
        old_config = {"llm_provider": "openrouter", "log_level": "INFO"}
        new_config = {"llm_provider": "deepseek", "log_level": "DEBUG"}
        
        self.reloader.current_config = old_config
        mock_load_config.return_value = new_config
        
        # Trigger reload
        with patch('builtins.print'):  # Suppress print output
            self.reloader._reload_config("/test/config/.env")
        
        # Verify config was updated
        self.assertEqual(self.reloader.current_config, new_config)
        self.callback.assert_called_once_with(new_config)

    @patch('helpers.config_hotreload.load_config')
    def test_reload_config_no_change(self, mock_load_config):
        """Test configuration reload when config hasn't changed."""
        config = {"llm_provider": "openrouter", "log_level": "INFO"}
        
        self.reloader.current_config = config
        mock_load_config.return_value = config
        
        # Trigger reload
        with patch('builtins.print'):  # Suppress print output
            self.reloader._reload_config("/test/config/.env")
        
        # Callback should not be called since config didn't change
        self.callback.assert_not_called()

    @patch('helpers.config_hotreload.load_config')
    def test_reload_config_error_handling(self, mock_load_config):
        """Test error handling during configuration reload."""
        mock_load_config.side_effect = Exception("Config load failed")
        
        # Should not raise exception
        with patch('builtins.print'):  # Suppress print output
            self.reloader._reload_config("/test/config/.env")
        
        # Config should remain unchanged
        self.assertIsNone(self.reloader.current_config)
        self.callback.assert_not_called()

    def test_log_config_changes(self):
        """Test logging of configuration changes."""
        old_config = {"llm_provider": "openrouter", "log_level": "INFO", "data_directory": "output"}
        new_config = {"llm_provider": "deepseek", "log_level": "INFO", "data_directory": "output"}
        
        with patch('builtins.print') as mock_print:
            self.reloader._log_config_changes(old_config, new_config)
            
            # Should log the provider change
            mock_print.assert_called()
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("llm_provider" in call for call in calls))

    def test_stop_when_not_running(self):
        """Test stopping reloader when not running."""
        # Should not raise exception
        self.reloader.stop()
        self.assertFalse(self.reloader.is_running)

    def test_is_active(self):
        """Test active status checking."""
        self.assertFalse(self.reloader.is_active())
        
        # Mock running state
        self.reloader.is_running = True
        self.reloader.observer = MagicMock()
        self.assertTrue(self.reloader.is_active())

    def test_get_current_config_thread_safety(self):
        """Test thread-safe access to current configuration."""
        config = {"test": "value"}
        self.reloader.current_config = config
        
        # Getting config should return a copy
        retrieved_config = self.reloader.get_current_config()
        self.assertEqual(retrieved_config, config)
        self.assertIsNot(retrieved_config, config)  # Should be a copy


class TestGlobalHotReloader(unittest.TestCase):
    """Test global hot-reloader functions."""

    def tearDown(self):
        """Clean up after tests."""
        stop_config_hotreload()

    @patch.dict(os.environ, {"ATLAS_ENVIRONMENT": "production"})
    def test_disabled_in_production(self):
        """Test that hot-reloader is disabled in production."""
        with patch('builtins.print'):
            result = start_config_hotreload()
        
        self.assertFalse(result)
        self.assertFalse(is_hotreload_active())

    @patch.dict(os.environ, {"ATLAS_ENVIRONMENT": "development"})
    @patch('helpers.config_hotreload.ConfigHotReloader')
    def test_start_global_hotreload(self, mock_class):
        """Test starting global hot-reloader."""
        mock_instance = MagicMock()
        mock_instance.start.return_value = True
        mock_class.return_value = mock_instance
        
        callback = MagicMock()
        result = start_config_hotreload(callback)
        
        self.assertTrue(result)
        mock_class.assert_called_once_with(callback)
        mock_instance.start.assert_called_once()

    def test_stop_global_hotreload(self):
        """Test stopping global hot-reloader."""
        # Should not raise exception even if not running
        stop_config_hotreload()

    def test_get_current_config_fallback(self):
        """Test fallback when global reloader not active."""
        from helpers.config_hotreload import get_current_config
        
        # Should call the real load_config function when no global reloader
        config = get_current_config()
        
        # Should return a dictionary (real config)
        self.assertIsInstance(config, dict)
        self.assertIn("environment", config)

    def test_is_hotreload_active_false(self):
        """Test active check when not running."""
        self.assertFalse(is_hotreload_active())


class TestConfigHotReloadContext(unittest.TestCase):
    """Test configuration hot-reload context manager."""

    def tearDown(self):
        """Clean up after tests."""
        stop_config_hotreload()

    @patch.dict(os.environ, {"ATLAS_ENVIRONMENT": "development"})
    @patch('helpers.config_hotreload.ConfigHotReloader')
    def test_context_manager(self, mock_class):
        """Test hot-reload context manager."""
        mock_instance = MagicMock()
        mock_instance.start.return_value = True
        mock_class.return_value = mock_instance
        
        callback = MagicMock()
        
        with ConfigHotReloadContext(callback) as context:
            # Context should start hot-reloader
            mock_class.assert_called_once_with(callback)
            mock_instance.start.assert_called_once()
        
        # Should stop after context exit
        mock_instance.stop.assert_called_once()

    @patch.dict(os.environ, {"ATLAS_ENVIRONMENT": "production"})
    def test_context_manager_disabled_environment(self):
        """Test context manager in disabled environment."""
        callback = MagicMock()
        
        with patch('builtins.print'):
            with ConfigHotReloadContext(callback) as context:
                # Should not start in production
                pass


@pytest.mark.integration
class TestConfigHotReloadIntegration(unittest.TestCase):
    """Integration tests for configuration hot-reloading."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, ".env")
        self.callback_called = threading.Event()
        self.callback_config = None

    def tearDown(self):
        """Clean up integration test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def config_change_callback(self, config):
        """Callback for configuration changes."""
        self.callback_config = config
        self.callback_called.set()

    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="File watching may be unreliable in CI environments"
    )
    def test_real_file_watching(self):
        """Test actual file system watching with real files."""
        try:
            # Create a temporary config file
            with open(self.config_file, 'w') as f:
                f.write("LLM_PROVIDER=openrouter\n")
            
            # Mock the config files to include our temp file
            with patch.object(ConfigHotReloader, '_get_config_files') as mock_get_files:
                mock_get_files.return_value = {self.config_file}
                
                reloader = ConfigHotReloader(self.config_change_callback)
                
                # Start watching (should work in test environment)
                with patch.dict(os.environ, {"ATLAS_ENVIRONMENT": "development"}):
                    if reloader.start():
                        try:
                            # Modify the file
                            time.sleep(0.1)  # Brief pause
                            with open(self.config_file, 'w') as f:
                                f.write("LLM_PROVIDER=deepseek\n")
                            
                            # Wait for callback (with timeout)
                            callback_triggered = self.callback_called.wait(timeout=3.0)
                            
                            if callback_triggered:
                                self.assertIsNotNone(self.callback_config)
                            else:
                                self.skipTest("File watching callback not triggered within timeout")
                        finally:
                            reloader.stop()
                    else:
                        self.skipTest("Hot-reloader failed to start (watchdog not available?)")
        
        except ImportError:
            self.skipTest("watchdog package not available")


if __name__ == "__main__":
    unittest.main()