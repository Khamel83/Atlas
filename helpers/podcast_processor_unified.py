"""
Unified Podcast Processor - Atlas-Podemos Integration
Integrates Podemos advanced podcast processing with Atlas cognitive amplification
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add podcast_processing to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'podcast_processing'))

try:
    from podcast_processing.processor.episode_processor import process_episode, perform_full_transcription
    from podcast_processing.ingest.rss_poll import poll_feed
    from podcast_processing.ingest.opml_import import import_opml
    from podcast_processing.store.db import init_db, get_session
    from podcast_processing.store.models import Episode
    from podcast_processing.config.config_loader import load_app_config
except ImportError as e:
    logging.warning(f"Podemos components not available: {e}")
    # Fallback to basic Atlas podcast processing
    from .podcast_ingestor import ingest_podcasts

logger = logging.getLogger(__name__)

class UnifiedPodcastProcessor:
    """
    Unified processor that combines Podemos advanced processing 
    with Atlas cognitive amplification capabilities
    """
    
    def __init__(self, use_podemos: bool = True):
        self.use_podemos = use_podemos
        self.podemos_available = self._check_podemos_availability()
        
        if self.use_podemos and not self.podemos_available:
            logger.warning("Podemos components not available, falling back to Atlas basic processing")
            self.use_podemos = False
    
    def _check_podemos_availability(self) -> bool:
        """Check if Podemos components are properly integrated"""
        try:
            from podcast_processing.processor.episode_processor import process_episode
            return True
        except ImportError:
            return False
    
    def initialize_database(self) -> bool:
        """Initialize the unified database for podcast processing"""
        if self.use_podemos:
            try:
                init_db()
                logger.info("Podemos database initialized successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize Podemos database: {e}")
                return False
        else:
            logger.info("Using Atlas basic podcast processing - no additional DB needed")
            return True
    
    def poll_podcast_feeds(self, feeds: List[str]) -> Dict[str, Any]:
        """Poll RSS feeds for new episodes"""
        results = {"success": [], "failed": []}
        
        if self.use_podemos:
            for feed_url in feeds:
                try:
                    poll_feed(feed_url)
                    results["success"].append(feed_url)
                    logger.info(f"Successfully polled feed: {feed_url}")
                except Exception as e:
                    results["failed"].append({"url": feed_url, "error": str(e)})
                    logger.error(f"Failed to poll feed {feed_url}: {e}")
        else:
            # Use basic Atlas processing
            logger.info("Using Atlas basic feed processing")
            # Implement basic feed polling here
            
        return results
    
    def process_episode_advanced(self, episode_id: int) -> Dict[str, Any]:
        """Process episode with advanced Podemos capabilities"""
        if not self.use_podemos:
            raise NotImplementedError("Advanced processing requires Podemos integration")
        
        try:
            # Use Podemos advanced processing (ad removal, etc.)
            result = process_episode(episode_id)
            logger.info(f"Successfully processed episode {episode_id} with advanced features")
            
            # After Podemos processing, apply Atlas cognitive analysis
            self._apply_cognitive_analysis(episode_id)
            
            return {"success": True, "episode_id": episode_id, "result": result}
        except Exception as e:
            logger.error(f"Failed to process episode {episode_id}: {e}")
            return {"success": False, "episode_id": episode_id, "error": str(e)}
    
    def _apply_cognitive_analysis(self, episode_id: int):
        """Apply Atlas cognitive analysis to processed episode"""
        try:
            # Get the processed transcript
            with get_session() as session:
                episode = session.query(Episode).filter(Episode.id == episode_id).first()
                if episode and episode.transcript_path:
                    # Apply Atlas cognitive engines here
                    logger.info(f"Applying cognitive analysis to episode {episode_id}")
                    # TODO: Integrate with Atlas cognitive engines
                    # - ProactiveSurfacer
                    # - TemporalEngine  
                    # - QuestionEngine
                    # - RecallEngine
                    # - PatternDetector
        except Exception as e:
            logger.error(f"Failed to apply cognitive analysis to episode {episode_id}: {e}")
    
    def import_opml_feeds(self, opml_path: str, poll_limit: int = 5) -> Dict[str, Any]:
        """Import podcast feeds from OPML file"""
        if self.use_podemos:
            try:
                result = import_opml(opml_path, poll_limit)
                logger.info(f"Successfully imported OPML from {opml_path}")
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"Failed to import OPML from {opml_path}: {e}")
                return {"success": False, "error": str(e)}
        else:
            # Use Atlas basic OPML processing
            logger.info("Using Atlas basic OPML processing")
            return {"success": False, "error": "Advanced OPML processing requires Podemos integration"}
    
    def get_episode_status(self, episode_id: Optional[int] = None) -> Dict[str, Any]:
        """Get processing status of episodes"""
        if not self.use_podemos:
            return {"episodes": [], "total": 0}
        
        try:
            with get_session() as session:
                if episode_id:
                    episodes = session.query(Episode).filter(Episode.id == episode_id).all()
                else:
                    episodes = session.query(Episode).all()
                
                episode_data = []
                for ep in episodes:
                    episode_data.append({
                        "id": ep.id,
                        "title": ep.title,
                        "status": ep.status,
                        "retry_count": ep.retry_count,
                        "last_error": ep.last_error
                    })
                
                return {"episodes": episode_data, "total": len(episode_data)}
        except Exception as e:
            logger.error(f"Failed to get episode status: {e}")
            return {"episodes": [], "total": 0, "error": str(e)}

# Global instance
unified_processor = UnifiedPodcastProcessor()

# Convenience functions for backwards compatibility
def process_podcasts_unified(feeds: List[str]) -> Dict[str, Any]:
    """Main function for unified podcast processing"""
    return unified_processor.poll_podcast_feeds(feeds)

def initialize_podcast_database() -> bool:
    """Initialize the unified podcast database"""
    return unified_processor.initialize_database()