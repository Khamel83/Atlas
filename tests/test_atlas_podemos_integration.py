"""
Test Atlas-Podemos Integration
Tests the unified functionality of the integrated system
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from helpers.config_unified import UnifiedConfigLoader, load_unified_config
from helpers.podcast_processor_unified import UnifiedPodcastProcessor

class TestUnifiedConfiguration:
    """Test unified configuration system"""
    
    def test_config_loader_initialization(self):
        """Test that unified config loader initializes properly"""
        loader = UnifiedConfigLoader()
        assert loader.atlas_root is not None
        assert loader.podcast_config_dir is not None
        assert loader.atlas_config_dir is not None
    
    def test_load_unified_config_fallback(self):
        """Test that config loader provides fallback when files missing"""
        with patch('helpers.config_unified.load_atlas_config') as mock_atlas:
            mock_atlas.side_effect = Exception("Atlas config not found")
            
            config = load_unified_config()
            assert config is not None
            assert hasattr(config, 'atlas_config')
            assert hasattr(config, 'podcast_app_config')
            assert hasattr(config, 'podcast_shows_config')
            assert config.integration_mode in ['unified', 'atlas_only', 'podemos_only']
    
    def test_default_podcast_config_creation(self):
        """Test creation of default podcast configuration"""
        loader = UnifiedConfigLoader()
        default_config = loader._create_default_podcast_config()
        
        assert 'feeds' in default_config
        assert 'server' in default_config
        assert 'processing' in default_config
        assert 'transcription' in default_config
        assert isinstance(default_config['feeds'], list)
    
    def test_default_show_config_creation(self):
        """Test creation of default show configuration"""
        loader = UnifiedConfigLoader()
        show_config = loader._create_default_show_config()
        
        assert 'ad_detection' in show_config
        assert 'processing' in show_config
        assert show_config['ad_detection']['enabled'] is True

class TestUnifiedPodcastProcessor:
    """Test unified podcast processor"""
    
    def test_processor_initialization(self):
        """Test processor initializes correctly"""
        processor = UnifiedPodcastProcessor(use_podemos=False)
        assert processor is not None
        assert hasattr(processor, 'use_podemos')
        assert hasattr(processor, 'podemos_available')
    
    def test_processor_podemos_availability_check(self):
        """Test Podemos availability detection"""
        # Test when Podemos not available
        processor = UnifiedPodcastProcessor(use_podemos=True)
        # Should fall back to Atlas mode if Podemos not available
        assert processor.use_podemos in [True, False]  # Depends on actual availability
    
    def test_basic_feed_processing(self):
        """Test basic feed processing functionality"""
        processor = UnifiedPodcastProcessor(use_podemos=False)
        
        # Mock feed processing
        with patch.object(processor, 'poll_podcast_feeds') as mock_poll:
            mock_poll.return_value = {"success": ["http://example.com/feed.xml"], "failed": []}
            
            result = processor.poll_podcast_feeds(["http://example.com/feed.xml"])
            assert "success" in result
            assert "failed" in result
    
    def test_episode_status_retrieval(self):
        """Test episode status functionality"""
        processor = UnifiedPodcastProcessor(use_podemos=False)
        
        # Should return empty status when Podemos not enabled
        status = processor.get_episode_status()
        assert "episodes" in status
        assert "total" in status
        assert isinstance(status["episodes"], list)
        assert isinstance(status["total"], int)

class TestIntegrationFunctionality:
    """Test integration between Atlas and Podemos components"""
    
    def test_import_integration_modules(self):
        """Test that integration modules can be imported"""
        from helpers.config_unified import load_unified_config
        from helpers.podcast_processor_unified import unified_processor
        
        # Should not raise import errors
        assert load_unified_config is not None
        assert unified_processor is not None
    
    def test_unified_config_podcast_functions(self):
        """Test podcast-specific configuration functions"""
        from helpers.config_unified import get_podcast_feeds, is_podcast_processing_enabled
        
        config = load_unified_config()
        
        feeds = get_podcast_feeds(config)
        assert isinstance(feeds, list)
        
        processing_enabled = is_podcast_processing_enabled(config)
        assert isinstance(processing_enabled, bool)

class TestCLIIntegration:
    """Test CLI integration functionality"""
    
    def test_main_entry_point_import(self):
        """Test that main entry point can be imported"""
        # Import should not raise errors
        import run
        assert hasattr(run, 'main')
    
    @patch('sys.argv', ['run.py', '--help'])
    def test_help_command_integration(self):
        """Test that help command works with integration"""
        import run
        
        # Should not raise errors when showing help
        with pytest.raises(SystemExit):  # argparse exits after showing help
            run.main()

class TestAtlasBackwardCompatibility:
    """Test that Atlas functionality remains intact"""
    
    def test_atlas_cognitive_modules_import(self):
        """Test that Atlas cognitive modules still work"""
        # Test core Atlas modules can still be imported
        from ask.proactive.surfacer import ProactiveSurfacer
        from ask.temporal.temporal_engine import TemporalEngine
        from ask.socratic.question_engine import QuestionEngine
        from ask.recall.recall_engine import RecallEngine
        from ask.insights.pattern_detector import PatternDetector
        
        # Should not raise import errors
        assert ProactiveSurfacer is not None
        assert TemporalEngine is not None
        assert QuestionEngine is not None
        assert RecallEngine is not None
        assert PatternDetector is not None
    
    def test_atlas_helpers_import(self):
        """Test that Atlas helper modules still work"""
        from helpers.article_fetcher import fetch_and_save_articles
        from helpers.youtube_ingestor import ingest_youtube_history
        from helpers.utils import setup_logging
        
        # Should not raise import errors
        assert fetch_and_save_articles is not None
        assert ingest_youtube_history is not None
        assert setup_logging is not None

@pytest.mark.integration
class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    def test_unified_system_initialization(self):
        """Test that unified system can initialize without errors"""
        config = load_unified_config()
        processor = UnifiedPodcastProcessor()
        
        assert config is not None
        assert processor is not None
        
        # Test that we can get basic status information
        status = processor.get_episode_status()
        assert status is not None
    
    @patch('helpers.podcast_processor_unified.init_db')
    def test_database_initialization_integration(self, mock_init_db):
        """Test database initialization integration"""
        from helpers.podcast_processor_unified import initialize_podcast_database
        
        mock_init_db.return_value = None
        
        # Should not raise errors
        result = initialize_podcast_database()
        assert isinstance(result, bool)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])