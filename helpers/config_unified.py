"""
Unified Configuration System - Atlas-Podemos Integration
Combines Atlas environment-aware configuration with Podemos YAML-based configuration
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

# Import Atlas configuration system
from .config import load_config as load_atlas_config

logger = logging.getLogger(__name__)

@dataclass
class UnifiedConfig:
    """Unified configuration combining Atlas and Podemos settings"""
    
    # Atlas Configuration
    atlas_config: Dict[str, Any]
    
    # Podemos Configuration  
    podcast_app_config: Dict[str, Any]
    podcast_shows_config: Dict[str, Dict[str, Any]]
    
    # Integration Settings
    integration_mode: str = "unified"  # unified, atlas_only, podemos_only
    podcast_processing_enabled: bool = True
    cognitive_analysis_enabled: bool = True

class UnifiedConfigLoader:
    """Loads and manages unified configuration from both Atlas and Podemos systems"""
    
    def __init__(self, atlas_root: Optional[Path] = None):
        self.atlas_root = atlas_root or Path(__file__).parent.parent
        self.podcast_config_dir = self.atlas_root / "podcast_config"
        self.atlas_config_dir = self.atlas_root / "config"
        
    def load_unified_config(self) -> UnifiedConfig:
        """Load unified configuration from both systems"""
        try:
            # Load Atlas configuration
            atlas_config = self._load_atlas_config()
            
            # Load Podemos configuration
            podcast_app_config = self._load_podcast_app_config()
            podcast_shows_config = self._load_podcast_shows_config()
            
            # Create unified configuration
            unified_config = UnifiedConfig(
                atlas_config=atlas_config,
                podcast_app_config=podcast_app_config,
                podcast_shows_config=podcast_shows_config,
                integration_mode=os.getenv("ATLAS_INTEGRATION_MODE", "unified"),
                podcast_processing_enabled=os.getenv("PODCAST_PROCESSING_ENABLED", "true").lower() == "true",
                cognitive_analysis_enabled=os.getenv("COGNITIVE_ANALYSIS_ENABLED", "true").lower() == "true"
            )
            
            logger.info("Successfully loaded unified configuration")
            return unified_config
            
        except Exception as e:
            logger.error(f"Failed to load unified configuration: {e}")
            # Return basic configuration as fallback
            return self._create_fallback_config()
    
    def _load_atlas_config(self) -> Dict[str, Any]:
        """Load Atlas configuration using existing system"""
        try:
            atlas_config = load_atlas_config()
            return atlas_config.__dict__ if hasattr(atlas_config, '__dict__') else {}
        except Exception as e:
            logger.warning(f"Failed to load Atlas config: {e}")
            return {}
    
    def _load_podcast_app_config(self) -> Dict[str, Any]:
        """Load Podemos app configuration from YAML"""
        app_config_path = self.podcast_config_dir / "app.yaml"
        
        if not app_config_path.exists():
            logger.warning(f"Podcast app config not found at {app_config_path}")
            return self._create_default_podcast_config()
        
        try:
            with open(app_config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info("Successfully loaded podcast app configuration")
            return config or {}
        except Exception as e:
            logger.error(f"Failed to load podcast app config: {e}")
            return self._create_default_podcast_config()
    
    def _load_podcast_shows_config(self) -> Dict[str, Dict[str, Any]]:
        """Load Podemos show-specific configurations"""
        shows_config_dir = self.podcast_config_dir / "shows"
        shows_config = {}
        
        if not shows_config_dir.exists():
            logger.warning(f"Podcast shows config directory not found at {shows_config_dir}")
            return {"default": self._create_default_show_config()}
        
        try:
            for config_file in shows_config_dir.glob("*.yaml"):
                show_name = config_file.stem
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                shows_config[show_name] = config or {}
            
            logger.info(f"Successfully loaded {len(shows_config)} podcast show configurations")
            return shows_config
            
        except Exception as e:
            logger.error(f"Failed to load podcast shows config: {e}")
            return {"default": self._create_default_show_config()}
    
    def _create_default_podcast_config(self) -> Dict[str, Any]:
        """Create default podcast application configuration"""
        return {
            "feeds": [],
            "server": {
                "host": "0.0.0.0",
                "port": 8080
            },
            "processing": {
                "max_retries": 3,
                "cleanup_days": 30,
                "concurrent_downloads": 2
            },
            "transcription": {
                "model": "base",
                "language": "auto"
            }
        }
    
    def _create_default_show_config(self) -> Dict[str, Any]:
        """Create default show-specific configuration"""
        return {
            "ad_detection": {
                "enabled": True,
                "rules": [
                    "sponsor",
                    "advertisement", 
                    "this episode is brought to you by"
                ]
            },
            "processing": {
                "priority": "normal",
                "cleanup_enabled": True
            }
        }
    
    def _create_fallback_config(self) -> UnifiedConfig:
        """Create minimal fallback configuration"""
        return UnifiedConfig(
            atlas_config={},
            podcast_app_config=self._create_default_podcast_config(),
            podcast_shows_config={"default": self._create_default_show_config()},
            integration_mode="atlas_only",
            podcast_processing_enabled=False,
            cognitive_analysis_enabled=True
        )
    
    def save_unified_config(self, config: UnifiedConfig) -> bool:
        """Save unified configuration back to files"""
        try:
            # Save podcast app configuration
            app_config_path = self.podcast_config_dir / "app.yaml"
            app_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(app_config_path, 'w') as f:
                yaml.dump(config.podcast_app_config, f, default_flow_style=False)
            
            # Save show configurations
            shows_config_dir = self.podcast_config_dir / "shows"
            shows_config_dir.mkdir(parents=True, exist_ok=True)
            
            for show_name, show_config in config.podcast_shows_config.items():
                show_config_path = shows_config_dir / f"{show_name}.yaml"
                with open(show_config_path, 'w') as f:
                    yaml.dump(show_config, f, default_flow_style=False)
            
            logger.info("Successfully saved unified configuration")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save unified configuration: {e}")
            return False
    
    def get_podcast_config_value(self, config: UnifiedConfig, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'server.port')"""
        try:
            keys = key_path.split('.')
            value = config.podcast_app_config
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
        except Exception:
            return default
    
    def get_show_config(self, config: UnifiedConfig, show_id: str) -> Dict[str, Any]:
        """Get configuration for specific show, falling back to default"""
        show_config = config.podcast_shows_config.get(show_id)
        if show_config:
            return show_config
        
        # Fall back to default configuration
        default_config = config.podcast_shows_config.get("default", self._create_default_show_config())
        return default_config

# Global unified configuration loader
unified_config_loader = UnifiedConfigLoader()

def load_unified_config() -> UnifiedConfig:
    """Load unified configuration - main entry point"""
    return unified_config_loader.load_unified_config()

def get_podcast_feeds(config: UnifiedConfig) -> list:
    """Get list of podcast feeds from unified configuration"""
    return config.podcast_app_config.get("feeds", [])

def is_podcast_processing_enabled(config: UnifiedConfig) -> bool:
    """Check if podcast processing is enabled"""
    return config.podcast_processing_enabled and bool(config.podcast_app_config)

def is_cognitive_analysis_enabled(config: UnifiedConfig) -> bool:
    """Check if cognitive analysis is enabled"""
    return config.cognitive_analysis_enabled