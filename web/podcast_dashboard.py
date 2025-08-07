#!/usr/bin/env python3
"""
Unified Podcast Management Dashboard

Integrates all Atlas-Podemos podcast processing capabilities into a single
web interface for comprehensive podcast management, monitoring, and control.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Atlas-Podemos integrations
from helpers.config_unified import load_unified_config, is_podcast_processing_enabled
from helpers.podcast_processor_unified import unified_processor
from helpers.podcast_rss_unified import get_unified_rss_ingestor
from helpers.podcast_ad_processor import get_podcast_ad_processor
from helpers.transcript_discovery import get_transcript_discovery_engine
from helpers.atlas_database_helper import get_atlas_database_manager

logger = logging.getLogger(__name__)

class UnifiedPodcastDashboard:
    """
    Unified dashboard for managing all podcast processing capabilities
    """
    
    def __init__(self):
        """Initialize dashboard components"""
        self.config = load_unified_config()
        
        # Initialize core components
        self.atlas_db = get_atlas_database_manager()
        self.rss_ingestor = get_unified_rss_ingestor(self.config) if is_podcast_processing_enabled(self.config) else None
        self.ad_processor = get_podcast_ad_processor() if is_podcast_processing_enabled(self.config) else None
        self.transcript_engine = get_transcript_discovery_engine() if is_podcast_processing_enabled(self.config) else None
        
        logger.info("Unified Podcast Dashboard initialized")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status and capabilities"""
        try:
            return {
                "podcast_processing_enabled": is_podcast_processing_enabled(self.config),
                "integration_mode": self.config.integration_mode,
                "cognitive_analysis_enabled": self.config.cognitive_analysis_enabled,
                "database_enabled": self.atlas_db.database_enabled,
                "components": {
                    "atlas_database": self.atlas_db is not None,
                    "rss_ingestor": self.rss_ingestor is not None,
                    "ad_processor": self.ad_processor is not None,
                    "transcript_discovery": self.transcript_engine is not None
                }
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            if not self.atlas_db:
                return {"error": "Database not available"}
            
            stats = self.atlas_db.get_content_statistics()
            
            # Add podcast-specific statistics
            if self.atlas_db.database_enabled:
                with self.atlas_db.db.session() as session:
                    from database_integration.models import PodcastEpisode
                    
                    podcast_stats = {
                        "total_podcast_episodes": session.query(PodcastEpisode).count(),
                        "processed_episodes": session.query(PodcastEpisode).filter(
                            PodcastEpisode.processing_status.in_(["completed", "processed"])
                        ).count(),
                        "recent_episodes": session.query(PodcastEpisode).filter(
                            PodcastEpisode.created_at >= datetime.now().replace(day=1)
                        ).count()
                    }
                    stats.update(podcast_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {"error": str(e)}
    
    def get_rss_statistics(self) -> Dict[str, Any]:
        """Get RSS processing statistics"""
        try:
            if not self.rss_ingestor:
                return {"error": "RSS ingestor not available"}
            
            return self.rss_ingestor.get_processing_stats()
            
        except Exception as e:
            logger.error(f"Error getting RSS statistics: {e}")
            return {"error": str(e)}
    
    def get_ad_processing_statistics(self) -> Dict[str, Any]:
        """Get ad processing statistics"""
        try:
            if not self.ad_processor:
                return {"error": "Ad processor not available"}
            
            return self.ad_processor.get_processing_statistics()
            
        except Exception as e:
            logger.error(f"Error getting ad processing statistics: {e}")
            return {"error": str(e)}
    
    def get_transcript_discovery_statistics(self) -> Dict[str, Any]:
        """Get transcript discovery statistics"""
        try:
            if not self.transcript_engine:
                return {"error": "Transcript discovery engine not available"}
            
            return self.transcript_engine.get_discovery_statistics()
            
        except Exception as e:
            logger.error(f"Error getting transcript discovery statistics: {e}")
            return {"error": str(e)}
    
    def get_recent_episodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent podcast episodes"""
        try:
            if not self.atlas_db or not self.atlas_db.database_enabled:
                return []
            
            with self.atlas_db.db.session() as session:
                from database_integration.models import PodcastEpisode
                
                episodes = session.query(PodcastEpisode).order_by(
                    PodcastEpisode.created_at.desc()
                ).limit(limit).all()
                
                return [{
                    "id": ep.id,
                    "title": ep.title or "Untitled Episode",
                    "show_author": ep.show_author,
                    "created_at": ep.created_at.isoformat() if ep.created_at else None,
                    "processing_status": ep.processing_status,
                    "original_audio_url": ep.original_audio_url,
                    "file_size": ep.file_size
                } for ep in episodes]
                
        except Exception as e:
            logger.error(f"Error getting recent episodes: {e}")
            return []
    
    def get_processing_queue_status(self) -> Dict[str, Any]:
        """Get current processing queue status"""
        try:
            if not is_podcast_processing_enabled(self.config):
                return {"error": "Podcast processing not enabled"}
            
            # Get episode processing status
            status = unified_processor.get_episode_status()
            
            # Add queue summary
            total = status.get("total", 0)
            processing = len([ep for ep in status.get("episodes", []) if ep.get("status") == "processing"])
            pending = len([ep for ep in status.get("episodes", []) if ep.get("status") == "pending"])
            completed = len([ep for ep in status.get("episodes", []) if ep.get("status") in ["completed", "processed"]])
            
            return {
                "total_episodes": total,
                "processing": processing,
                "pending": pending,
                "completed": completed,
                "queue_health": "healthy" if processing < 5 else "busy"
            }
            
        except Exception as e:
            logger.error(f"Error getting processing queue status: {e}")
            return {"error": str(e)}
    
    def trigger_feed_polling(self, feed_urls: List[str] = None) -> Dict[str, Any]:
        """Trigger RSS feed polling"""
        try:
            if not is_podcast_processing_enabled(self.config):
                return {"success": False, "error": "Podcast processing not enabled"}
            
            from helpers.config_unified import get_podcast_feeds
            
            feeds = feed_urls or get_podcast_feeds(self.config)
            if not feeds:
                return {"success": False, "error": "No feeds configured"}
            
            result = unified_processor.poll_podcast_feeds(feeds)
            
            return {
                "success": True,
                "feeds_processed": len(feeds),
                "successful_feeds": len(result.get("success", [])),
                "failed_feeds": len(result.get("failed", [])),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Error triggering feed polling: {e}")
            return {"success": False, "error": str(e)}
    
    def start_transcript_discovery(self) -> Dict[str, Any]:
        """Start transcript discovery process"""
        try:
            if not self.transcript_engine:
                return {"success": False, "error": "Transcript discovery engine not available"}
            
            # Run discovery in background (simplified for MVP)
            sources = self.transcript_engine.discover_all_transcripts()
            
            return {
                "success": True,
                "sources_discovered": len(sources),
                "sources_with_transcripts": len([s for s in sources if s.has_transcripts]),
                "message": f"Discovered {len(sources)} transcript sources"
            }
            
        except Exception as e:
            logger.error(f"Error starting transcript discovery: {e}")
            return {"success": False, "error": str(e)}
    
    def close(self):
        """Close dashboard and cleanup resources"""
        try:
            if self.atlas_db:
                self.atlas_db.close()
            if self.rss_ingestor:
                self.rss_ingestor.close()
            if self.ad_processor:
                self.ad_processor.close()
            if self.transcript_engine:
                self.transcript_engine.close()
        except Exception as e:
            logger.error(f"Error during dashboard cleanup: {e}")

# Global dashboard instance
_dashboard: Optional[UnifiedPodcastDashboard] = None

def get_podcast_dashboard() -> UnifiedPodcastDashboard:
    """Get global podcast dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = UnifiedPodcastDashboard()
    return _dashboard

def close_podcast_dashboard():
    """Close global podcast dashboard instance"""
    global _dashboard
    if _dashboard:
        _dashboard.close()
        _dashboard = None

# FastAPI integration
templates = Jinja2Templates(directory="web/templates")

def create_podcast_routes(app: FastAPI):
    """Add podcast dashboard routes to FastAPI app"""
    
    @app.get("/podcasts/", response_class=HTMLResponse)
    async def podcast_dashboard_html(request: Request):
        """Main podcast management dashboard"""
        dashboard = get_podcast_dashboard()
        
        # Get all dashboard data
        system_status = dashboard.get_system_status()
        db_stats = dashboard.get_database_statistics()
        rss_stats = dashboard.get_rss_statistics()
        ad_stats = dashboard.get_ad_processing_statistics()
        transcript_stats = dashboard.get_transcript_discovery_statistics()
        recent_episodes = dashboard.get_recent_episodes(10)
        queue_status = dashboard.get_processing_queue_status()
        
        return templates.TemplateResponse(
            "podcast_dashboard.html",
            {
                "request": request,
                "system_status": system_status,
                "db_stats": db_stats,
                "rss_stats": rss_stats,
                "ad_stats": ad_stats,
                "transcript_stats": transcript_stats,
                "recent_episodes": recent_episodes,
                "queue_status": queue_status,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @app.get("/podcasts/api/status", response_class=JSONResponse)
    async def podcast_status_api():
        """API endpoint for system status"""
        dashboard = get_podcast_dashboard()
        return dashboard.get_system_status()
    
    @app.post("/podcasts/api/poll-feeds")
    async def trigger_feed_polling_api():
        """API endpoint to trigger feed polling"""
        dashboard = get_podcast_dashboard()
        return dashboard.trigger_feed_polling()
    
    @app.post("/podcasts/api/discover-transcripts")
    async def start_transcript_discovery_api():
        """API endpoint to start transcript discovery"""
        dashboard = get_podcast_dashboard()
        return dashboard.start_transcript_discovery()
    
    @app.get("/podcasts/api/episodes", response_class=JSONResponse)
    async def recent_episodes_api(limit: int = 10):
        """API endpoint for recent episodes"""
        dashboard = get_podcast_dashboard()
        return {"episodes": dashboard.get_recent_episodes(limit)}

if __name__ == "__main__":
    # Test dashboard initialization
    dashboard = get_podcast_dashboard()
    print("🎙️ Unified Podcast Dashboard Test")
    print("=" * 50)
    
    print("System Status:", dashboard.get_system_status())
    print("Database Stats:", dashboard.get_database_statistics())
    
    dashboard.close()