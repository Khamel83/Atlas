"""
Configuration Hot-Reloading for Development

This module provides file system monitoring and automatic configuration reloading
for development environments to enable rapid iteration without server restarts.
"""

import os
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer

from helpers.config import load_config


class ConfigReloadHandler(FileSystemEventHandler):
    """File system event handler for configuration file changes."""

    def __init__(self, callback: Callable[[str], None], config_files: Set[str]):
        """
        Initialize the configuration reload handler.

        Args:
            callback: Function to call when configuration changes
            config_files: Set of configuration file paths to monitor
        """
        self.callback = callback
        self.config_files = config_files
        self.last_reload = {}
        self.debounce_delay = 1.0  # 1 second debounce

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = os.path.abspath(event.src_path)
        
        # Check if the modified file is one we're monitoring
        if file_path in self.config_files:
            now = time.time()
            last_reload_time = self.last_reload.get(file_path, 0)
            
            # Debounce rapid file changes
            if now - last_reload_time > self.debounce_delay:
                self.last_reload[file_path] = now
                print(f"📄 Configuration file changed: {file_path}")
                
                # Call the reload callback
                try:
                    self.callback(file_path)
                except Exception as e:
                    print(f"❌ Error reloading configuration: {e}")


class ConfigHotReloader:
    """Manages hot-reloading of configuration files during development."""

    def __init__(self, reload_callback: Optional[Callable[[Dict], None]] = None):
        """
        Initialize the configuration hot-reloader.

        Args:
            reload_callback: Optional callback function called after config reload
        """
        self.observer: Optional[Observer] = None
        self.reload_callback = reload_callback
        self.current_config: Optional[Dict] = None
        self.is_running = False
        self._lock = threading.Lock()
        
        # Configuration files to monitor
        self.config_files = self._get_config_files()
        
    def _get_config_files(self) -> Set[str]:
        """Get set of configuration files to monitor."""
        config_files = set()
        
        # Environment files
        env_patterns = [
            "config/.env",
            "config/.env.development", 
            "config/.env.test",
            "config/.env.production",
            ".env",  # Root .env for backward compatibility
        ]
        
        # YAML configuration files
        yaml_patterns = [
            "config/environments.yaml",
            "config/categories.yaml",
        ]
        
        # Add existing files to monitoring set
        for pattern in env_patterns + yaml_patterns:
            if os.path.exists(pattern):
                config_files.add(os.path.abspath(pattern))
                
        return config_files
    
    def _reload_config(self, changed_file: str):
        """
        Reload configuration when files change.
        
        Args:
            changed_file: Path to the file that changed
        """
        with self._lock:
            try:
                # Reload the configuration
                new_config = load_config()
                
                # Check if configuration actually changed
                if new_config != self.current_config:
                    print(f"🔄 Configuration reloaded from {os.path.basename(changed_file)}")
                    
                    # Update current config
                    old_config = self.current_config
                    self.current_config = new_config
                    
                    # Log configuration change for auditing
                    try:
                        from helpers.config_audit import log_config_change
                        log_config_change(old_config, new_config, changed_file, "hot_reload")
                    except ImportError:
                        pass  # Auditing is optional
                    
                    # Call user callback if provided
                    if self.reload_callback:
                        try:
                            self.reload_callback(new_config)
                        except Exception as e:
                            print(f"⚠️  Error in reload callback: {e}")
                    
                    # Log significant changes
                    self._log_config_changes(old_config, new_config)
                else:
                    print(f"📄 File {os.path.basename(changed_file)} changed but configuration unchanged")
                    
                    # Still log unchanged reload for auditing if configured
                    try:
                        from helpers.config_audit import log_config_change
                        log_config_change(self.current_config, new_config, changed_file, "hot_reload")
                    except ImportError:
                        pass  # Auditing is optional
                    
            except Exception as e:
                print(f"❌ Failed to reload configuration: {e}")
    
    def _log_config_changes(self, old_config: Optional[Dict], new_config: Dict):
        """
        Log significant configuration changes.
        
        Args:
            old_config: Previous configuration (can be None)
            new_config: New configuration
        """
        if not old_config:
            return
            
        # Check for important changes
        important_keys = [
            "llm_provider", "llm_model", "data_directory", "environment",
            "log_level", "max_retries", "processing_timeout"
        ]
        
        changes = []
        for key in important_keys:
            old_val = old_config.get(key)
            new_val = new_config.get(key)
            if old_val != new_val:
                changes.append(f"{key}: {old_val} → {new_val}")
        
        if changes:
            print("📝 Key configuration changes:")
            for change in changes:
                print(f"   • {change}")
    
    def start(self) -> bool:
        """
        Start monitoring configuration files for changes.
        
        Returns:
            True if monitoring started successfully, False otherwise
        """
        if self.is_running:
            print("⚠️  Hot-reloader is already running")
            return False
            
        if not self.config_files:
            print("⚠️  No configuration files found to monitor")
            return False
        
        try:
            # Load initial configuration
            self.current_config = load_config()
            
            # Set up file system observer
            self.observer = Observer()
            handler = ConfigReloadHandler(self._reload_config, self.config_files)
            
            # Watch configuration directories
            watched_dirs = set()
            for config_file in self.config_files:
                config_dir = os.path.dirname(config_file)
                if config_dir not in watched_dirs:
                    self.observer.schedule(handler, config_dir, recursive=False)
                    watched_dirs.add(config_dir)
            
            # Start monitoring
            self.observer.start()
            self.is_running = True
            
            print(f"🔥 Configuration hot-reloader started")
            print(f"📁 Monitoring {len(self.config_files)} configuration files:")
            for config_file in sorted(self.config_files):
                print(f"   • {os.path.relpath(config_file)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start configuration hot-reloader: {e}")
            return False
    
    def stop(self):
        """Stop monitoring configuration files."""
        if not self.is_running:
            return
            
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        
        self.is_running = False
        print("🛑 Configuration hot-reloader stopped")
    
    def is_active(self) -> bool:
        """Check if hot-reloader is currently active."""
        return self.is_running and self.observer is not None
    
    def get_current_config(self) -> Optional[Dict]:
        """Get the current configuration."""
        with self._lock:
            return self.current_config.copy() if self.current_config else None


# Global hot-reloader instance
_global_reloader: Optional[ConfigHotReloader] = None


def start_config_hotreload(reload_callback: Optional[Callable[[Dict], None]] = None) -> bool:
    """
    Start global configuration hot-reloading.
    
    Args:
        reload_callback: Optional callback function called after config reload
        
    Returns:
        True if started successfully, False otherwise
    """
    global _global_reloader
    
    # Only enable in development environment
    current_env = os.environ.get("ATLAS_ENVIRONMENT", "development")
    if current_env not in ["development", "local-with-apis"]:
        print(f"🔒 Hot-reloader disabled in {current_env} environment")
        return False
    
    if _global_reloader is not None:
        print("⚠️  Global hot-reloader already exists")
        return _global_reloader.is_active()
    
    try:
        _global_reloader = ConfigHotReloader(reload_callback)
        return _global_reloader.start()
    except ImportError:
        print("⚠️  watchdog package not available - hot-reloading disabled")
        print("   Install with: pip install watchdog")
        return False


def stop_config_hotreload():
    """Stop global configuration hot-reloading."""
    global _global_reloader
    
    if _global_reloader:
        _global_reloader.stop()
        _global_reloader = None


def get_current_config() -> Optional[Dict]:
    """Get current configuration from global hot-reloader."""
    global _global_reloader
    
    if _global_reloader:
        return _global_reloader.get_current_config()
    
    # Fallback to regular config loading
    try:
        from helpers.config import load_config
        return load_config()
    except Exception:
        return None


def is_hotreload_active() -> bool:
    """Check if configuration hot-reloading is currently active."""
    global _global_reloader
    return _global_reloader is not None and _global_reloader.is_active()


# Context manager for temporary hot-reloading
class ConfigHotReloadContext:
    """Context manager for temporary configuration hot-reloading."""
    
    def __init__(self, reload_callback: Optional[Callable[[Dict], None]] = None):
        self.reload_callback = reload_callback
        self.started = False
    
    def __enter__(self):
        self.started = start_config_hotreload(self.reload_callback)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.started:
            stop_config_hotreload()


# Example usage and testing
if __name__ == "__main__":
    def on_config_change(config):
        """Example callback for configuration changes."""
        print(f"🔧 Configuration updated - LLM Provider: {config.get('llm_provider')}")
    
    # Start hot-reloading with callback
    if start_config_hotreload(on_config_change):
        print("Hot-reloader started. Modify configuration files to see changes.")
        try:
            # Keep the program running to monitor changes
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            stop_config_hotreload()
    else:
        print("Failed to start hot-reloader")