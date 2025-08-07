#!/usr/bin/env python3
"""
Atlas-Podemos Unified RSS Podcast Ingestor

Replaces the Atlas podcast ingestor with enhanced Podemos RSS capabilities
while maintaining integration with Atlas workflows and the unified database.

This module combines:
- Podemos advanced RSS parsing and database storage
- Atlas content management and cognitive analysis workflows
- Unified database integration for real-time operations
- Audio processing integration for complete podcast pipeline

Usage:
    from helpers.podcast_rss_unified import UnifiedPodcastRSSIngestor
    
    # Initialize with database integration
    ingestor = UnifiedPodcastRSSIngestor()
    
    # Process RSS feed with full pipeline
    success = ingestor.ingest_feed_url("https://example.com/podcast.rss")
    
    # Poll multiple feeds
    feeds_processed = ingestor.poll_feeds(feed_urls, limit=10)
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import time

# Standard imports
import feedparser
import requests

# Atlas imports
from helpers.base_ingestor import BaseIngestor, IngestorResult
from helpers.metadata_manager import ContentMetadata, ContentType, ProcessingStatus, MetadataManager
from helpers.atlas_database_helper import get_atlas_database_manager
from helpers.utils import sanitize_filename
from helpers.dedupe import link_uid
from helpers.audio_processor import get_audio_processor

# Database integration
try:
    from database_integration import ContentItem, PodcastEpisode
    from database_integration.database import UnifiedDB
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

logger = logging.getLogger(__name__)

class UnifiedPodcastRSSIngestor(BaseIngestor):
    """
    Unified RSS podcast ingestor combining Podemos and Atlas capabilities
    
    Features:
    - Advanced RSS parsing with Podemos enhancement  
    - Unified database integration for real-time operations
    - Audio processing pipeline with ad detection/removal
    - Atlas content management and cognitive analysis
    - Backward compatibility with existing Atlas workflows
    """
    
    def __init__(self, config: Dict[str, Any] = None, db_path: str = "atlas_unified.db"):
        """
        Initialize unified podcast RSS ingestor
        
        Args:
            config: Atlas configuration dictionary
            db_path: Path to unified database
        """
        # Initialize base ingestor if config provided (Atlas compatibility)
        if config:
            super().__init__(config)
        
        # Initialize database components
        if DATABASE_AVAILABLE:
            self.atlas_db = get_atlas_database_manager(db_path)
            self.db = UnifiedDB(db_path)
            self.database_enabled = True
        else:
            self.atlas_db = None
            self.db = None
            self.database_enabled = False
            logger.warning("Database not available - using file-based operations")
        
        # Initialize audio processing
        self.audio_processor = get_audio_processor()
        
        # Initialize metadata manager
        self.metadata_manager = MetadataManager()
        
        # RSS parsing configuration
        self.user_agent = "Atlas-Podemos-Unified/1.0 (+https://github.com/Khamel83/Atlas)"
        self.request_timeout = 30
        
        logger.info(f"UnifiedPodcastRSSIngestor initialized - Database: {self.database_enabled}")

    def get_content_type(self):
        """Atlas BaseIngestor compatibility"""
        return ContentType.PODCAST

    def get_module_name(self):
        """Atlas BaseIngestor compatibility"""
        return "podcast_rss_unified"
    
    def fetch_content(self, feed_url, metadata):
        """Atlas BaseIngestor compatibility - fetch RSS feed content"""
        try:
            feed = self._parse_feed(feed_url)
            if not feed or not feed.entries:
                return False, None
            return True, feed.entries
        except Exception as e:
            logger.error(f"Failed to fetch content for {feed_url}: {e}")
            return False, None
    
    def process_content(self, entry, metadata):
        """Atlas BaseIngestor compatibility - process individual episode"""
        try:
            feed_url = metadata.get('source', metadata.get('feed_url', ''))
            # Mock feed info for compatibility
            class MockFeedInfo:
                def __init__(self):
                    self.title = metadata.get('show_name', 'Unknown Show')
                    self.author = metadata.get('show_author', None)
                    self.image = None
            
            success = self._process_episode(entry, MockFeedInfo(), feed_url)
            return success
        except Exception as e:
            logger.error(f"Failed to process content: {e}")
            return False
    
    def ingest_feed_url(self, feed_url: str, limit: int = None) -> bool:
        """
        Ingest podcast episodes from RSS feed URL
        
        Args:
            feed_url: RSS feed URL to process
            limit: Maximum number of episodes to process
            
        Returns:
            Success status
        """
        try:
            logger.info(f"Starting RSS feed ingestion: {feed_url}")
            
            # Parse RSS feed with enhanced error handling
            feed = self._parse_feed(feed_url)
            if not feed or not feed.entries:
                logger.error(f"No entries found in feed: {feed_url}")
                return False
            
            # Process episodes
            episodes_processed = 0
            episodes_successful = 0
            
            for entry in feed.entries:
                if limit and episodes_processed >= limit:
                    logger.info(f"Reached processing limit of {limit} episodes")
                    break
                
                try:
                    # Process individual episode
                    success = self._process_episode(entry, feed.feed, feed_url)
                    if success:
                        episodes_successful += 1
                    episodes_processed += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process episode '{entry.get('title', 'Unknown')}': {e}")
                    episodes_processed += 1
            
            logger.info(f"RSS feed processing completed: {episodes_successful}/{episodes_processed} episodes successful")
            return episodes_successful > 0
            
        except Exception as e:
            logger.error(f"RSS feed ingestion failed for {feed_url}: {e}")
            return False
    
    def poll_feeds(self, feed_urls: List[str], limit: int = None) -> Dict[str, Any]:
        """
        Poll multiple RSS feeds for new episodes
        
        Args:
            feed_urls: List of RSS feed URLs to process
            limit: Maximum episodes per feed
            
        Returns:
            Processing summary with statistics
        """
        results = {
            'feeds_processed': 0,
            'feeds_successful': 0,
            'total_episodes': 0,
            'successful_episodes': 0,
            'errors': []
        }
        
        for feed_url in feed_urls:
            try:
                success = self.ingest_feed_url(feed_url, limit)
                results['feeds_processed'] += 1
                if success:
                    results['feeds_successful'] += 1
            except Exception as e:
                results['errors'].append(f"{feed_url}: {str(e)}")
                results['feeds_processed'] += 1
        
        logger.info(f"Feed polling completed: {results['feeds_successful']}/{results['feeds_processed']} feeds successful")
        return results
    
    def _parse_feed(self, feed_url: str) -> feedparser.FeedParserDict:
        """Parse RSS feed with enhanced error handling"""
        try:
            # Parse with custom headers and timeout
            response = requests.get(
                feed_url,
                headers={'User-Agent': self.user_agent},
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            # Parse feed content
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
            
            return feed
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse RSS feed {feed_url}: {e}")
            return None
    
    def _process_episode(self, entry: Dict[str, Any], feed_info: Any, feed_url: str) -> bool:
        """
        Process individual podcast episode with unified pipeline
        
        Args:
            entry: RSS entry data
            feed_info: Feed metadata
            feed_url: Original feed URL
            
        Returns:
            Success status
        """
        try:
            # Extract episode metadata
            episode_data = self._extract_episode_data(entry, feed_info, feed_url)
            if not episode_data:
                return False
            
            # Generate content UID for Atlas compatibility
            content_uid = self._generate_content_uid(episode_data)
            
            # Check if episode already exists
            if self._episode_exists(content_uid, episode_data.get('source_guid')):
                logger.debug(f"Episode already exists, skipping: {episode_data['title']}")
                return True
            
            # Store in unified database
            if self.database_enabled:
                success = self._store_episode_database(content_uid, episode_data)
                if not success:
                    logger.error(f"Failed to store episode in database: {episode_data['title']}")
                    return False
            
            # Create Atlas content entry for cognitive analysis integration
            if self.atlas_db:
                self._create_atlas_content_entry(content_uid, episode_data)
            
            # Queue for audio processing if enabled
            if episode_data.get('original_audio_url'):
                self._queue_audio_processing(content_uid, episode_data)
            
            logger.info(f"Successfully processed episode: {episode_data['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process episode: {e}")
            return False
    
    def _extract_episode_data(self, entry: Dict[str, Any], feed_info: Any, feed_url: str) -> Dict[str, Any]:
        """Extract episode data from RSS entry"""
        try:
            # Basic episode information
            episode_data = {
                'source_guid': entry.get('guid', entry.get('id', '')),
                'title': entry.get('title', 'Untitled Episode'),
                'show_name': getattr(feed_info, 'title', 'Unknown Show'),
                'description': entry.get('summary', entry.get('description', '')),
                'feed_url': feed_url,
            }
            
            # Publication date
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            else:
                pub_date = datetime.now()
            episode_data['pub_date'] = pub_date
            
            # Audio URL and metadata
            audio_url = None
            file_size = None
            
            if hasattr(entry, 'enclosures') and entry.enclosures:
                enclosure = entry.enclosures[0]
                audio_url = enclosure.href
                if hasattr(enclosure, 'length') and enclosure.length:
                    file_size = int(enclosure.length)
            
            elif hasattr(entry, 'links') and entry.links:
                for link in entry.links:
                    if link.get('type', '').startswith('audio'):
                        audio_url = link.get('href')
                        break
            
            episode_data['original_audio_url'] = audio_url
            episode_data['original_file_size'] = file_size
            
            # Additional metadata
            episode_data['show_author'] = getattr(feed_info, 'author', None)
            episode_data['image_url'] = getattr(entry, 'image', {}).get('href')
            episode_data['show_image_url'] = getattr(feed_info, 'image', {}).get('href')
            
            # Chapters (Podcasting 2.0 support)
            if hasattr(entry, 'chapters'):
                episode_data['chapters_json'] = json.dumps(entry.chapters)
            
            # Validate required fields
            if not all([episode_data['source_guid'], episode_data['title'], episode_data['original_audio_url']]):
                logger.warning(f"Episode missing required data: {episode_data['title']}")
                return None
                
            return episode_data
            
        except Exception as e:
            logger.error(f"Failed to extract episode data: {e}")
            return None
    
    def _generate_content_uid(self, episode_data: Dict[str, Any]) -> str:
        """Generate unique content ID for Atlas compatibility"""
        # Use source GUID if available, otherwise generate from URL + title
        if episode_data.get('source_guid'):
            uid_source = f"podcast_{episode_data['source_guid']}"
        else:
            uid_source = f"podcast_{episode_data['original_audio_url']}_{episode_data['title']}"
        
        return hashlib.md5(uid_source.encode()).hexdigest()
    
    def _episode_exists(self, content_uid: str, source_guid: str) -> bool:
        """Check if episode already exists in database"""
        if not self.database_enabled:
            return False
            
        try:
            with self.db.session() as session:
                # Check by content UID first
                content_item = session.query(ContentItem).filter_by(uid=content_uid).first()
                if content_item:
                    return True
                
                # Check by source GUID as backup
                if source_guid:
                    episode = session.query(PodcastEpisode).filter_by(source_guid=source_guid).first()
                    if episode:
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to check episode existence: {e}")
            return False
    
    def _store_episode_database(self, content_uid: str, episode_data: Dict[str, Any]) -> bool:
        """Store episode in unified database"""
        try:
            with self.db.session() as session:
                # Create content item
                content_item = ContentItem(
                    uid=content_uid,
                    content_type='podcast',
                    source_url=episode_data['original_audio_url'],
                    title=episode_data['title'],
                    status='ingested',
                    show_name=episode_data['show_name'],
                    pub_date=episode_data['pub_date'],
                    description=episode_data['description'],
                    tags=['podcast', episode_data['show_name']],
                    created_at=datetime.utcnow()
                )
                session.add(content_item)
                session.flush()  # Get the ID
                
                # Create podcast episode entry
                podcast_episode = PodcastEpisode(
                    content_item_id=content_item.id,
                    source_guid=episode_data['source_guid'],
                    show_author=episode_data.get('show_author'),
                    original_audio_url=episode_data['original_audio_url'],
                    original_file_size=episode_data.get('original_file_size'),
                    image_url=episode_data.get('image_url'),
                    show_image_url=episode_data.get('show_image_url'),
                    chapters_json=episode_data.get('chapters_json')
                )
                session.add(podcast_episode)
                session.commit()
                
                logger.debug(f"Stored episode in database: {episode_data['title']}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store episode in database: {e}")
            return False
    
    def _create_atlas_content_entry(self, content_uid: str, episode_data: Dict[str, Any]):
        """Create Atlas content entry for cognitive analysis integration"""
        try:
            if not self.atlas_db:
                return
            
            # Create content metadata
            metadata = ContentMetadata(
                uid=content_uid,
                title=episode_data['title'],
                url=episode_data['original_audio_url'],
                content_type=ContentType.PODCAST,
                status=ProcessingStatus.READY_FOR_PROCESSING,
                tags=['podcast', episode_data['show_name']],
                created_at=datetime.utcnow(),
                custom_fields={
                    'show_name': episode_data['show_name'],
                    'show_author': episode_data.get('show_author'),
                    'pub_date': episode_data['pub_date'].isoformat() if episode_data['pub_date'] else None,
                    'description': episode_data['description']
                }
            )
            
            # Store content data
            content_data = {
                'title': episode_data['title'],
                'description': episode_data['description'],
                'audio_url': episode_data['original_audio_url'],
                'show_name': episode_data['show_name'],
                'pub_date': episode_data['pub_date']
            }
            
            # Store using Atlas database manager
            success = self.atlas_db.store_content(metadata, content_data)
            if success:
                logger.debug(f"Created Atlas content entry: {episode_data['title']}")
            
        except Exception as e:
            logger.error(f"Failed to create Atlas content entry: {e}")
    
    def _queue_audio_processing(self, content_uid: str, episode_data: Dict[str, Any]):
        """Queue episode for audio processing pipeline"""
        try:
            # Note: Audio processing happens asynchronously
            # The audio_processor can be called when ready to process
            # For now, we just log that it's ready for processing
            
            logger.debug(f"Episode queued for audio processing: {episode_data['title']}")
            
            # You could trigger immediate processing here if desired:
            # result = self.audio_processor.process_audio_url(
            #     episode_data['original_audio_url'],
            #     episode_data['title'],
            #     episode_data['show_name'],
            #     episode_data['description'],
            #     episode_data['pub_date']
            # )
            
        except Exception as e:
            logger.error(f"Failed to queue audio processing: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics from database"""
        if not self.database_enabled:
            return {'error': 'Database not available'}
        
        try:
            with self.db.session() as session:
                # Count podcasts by status
                total_episodes = session.query(ContentItem).filter_by(content_type='podcast').count()
                ingested_episodes = session.query(ContentItem).filter(
                    ContentItem.content_type == 'podcast',
                    ContentItem.status == 'ingested'
                ).count()
                processing_episodes = session.query(ContentItem).filter(
                    ContentItem.content_type == 'podcast', 
                    ContentItem.status == 'processing'
                ).count()
                completed_episodes = session.query(ContentItem).filter(
                    ContentItem.content_type == 'podcast',
                    ContentItem.status == 'completed'
                ).count()
                
                return {
                    'total_episodes': total_episodes,
                    'ingested': ingested_episodes,
                    'processing': processing_episodes,
                    'completed': completed_episodes,
                    'database_enabled': self.database_enabled
                }
                
        except Exception as e:
            logger.error(f"Failed to get processing stats: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Close database connections and cleanup"""
        try:
            if self.atlas_db:
                self.atlas_db.close()
            if self.db:
                self.db.close()
            logger.debug("UnifiedPodcastRSSIngestor closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global instance for easy access
_global_rss_ingestor: Optional[UnifiedPodcastRSSIngestor] = None

def get_unified_rss_ingestor(config: Dict[str, Any] = None, db_path: str = "atlas_unified.db") -> UnifiedPodcastRSSIngestor:
    """
    Get global unified RSS ingestor instance
    
    Args:
        config: Atlas configuration (only used on first call)
        db_path: Database path (only used on first call)
        
    Returns:
        UnifiedPodcastRSSIngestor instance
    """
    global _global_rss_ingestor
    
    if _global_rss_ingestor is None:
        _global_rss_ingestor = UnifiedPodcastRSSIngestor(config, db_path)
    
    return _global_rss_ingestor

def close_global_rss_ingestor():
    """Close global RSS ingestor instance"""
    global _global_rss_ingestor
    
    if _global_rss_ingestor:
        _global_rss_ingestor.close()
        _global_rss_ingestor = None