#!/usr/bin/env python3
"""
Unified Database Connection Manager

Provides centralized database connection management for Atlas-Podemos integration.
Handles connection pooling, session management, and database operations.

Usage:
    from database_integration.database import UnifiedDB
    
    db = UnifiedDB("atlas_unified.db")
    
    # Query content
    articles = db.get_articles()
    podcasts = db.get_podcasts()
    
    # Add new content
    with db.session() as session:
        content = ContentItem(uid="abc123", title="New Article", content_type="article")
        session.add(content)
        session.commit()
"""

import os
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator
from datetime import datetime

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Base, ContentItem, PodcastEpisode, ProcessingJob, 
    ContentAnalysis, ContentTag, SystemMetadata
)

logger = logging.getLogger(__name__)

class UnifiedDB:
    """
    Unified database connection manager for Atlas-Podemos integration
    
    Provides high-level database operations, connection management,
    and convenience methods for common queries and operations.
    """
    
    def __init__(self, db_path: str = "atlas_unified.db", echo: bool = False):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
            echo: Whether to echo SQL statements (for debugging)
        """
        self.db_path = os.path.abspath(db_path)
        self.echo = echo
        
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
        
        # Create engine and session factory
        self.engine = create_engine(
            f'sqlite:///{self.db_path}',
            echo=echo,
            poolclass=StaticPool,
            pool_pre_ping=True,
            connect_args={
                'check_same_thread': False,  # Allow multi-threading
                'timeout': 30  # 30 second timeout
            }
        )
        
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize database if needed
        self._initialize_database()
        
        logger.info(f"Initialized unified database: {self.db_path}")
    
    def _initialize_database(self):
        """Initialize database tables if they don't exist"""
        try:
            # Check if database is already initialized
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='content_items';"))
                if not result.fetchone():
                    logger.info("Creating database tables...")
                    Base.metadata.create_all(bind=self.engine)
                    self._insert_initial_metadata()
                    logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _insert_initial_metadata(self):
        """Insert initial system metadata"""
        try:
            with self.session() as session:
                metadata_entries = [
                    SystemMetadata(key='schema_version', value='1.0', description='Database schema version'),
                    SystemMetadata(key='created_at', value=datetime.utcnow().isoformat(), description='Database creation timestamp'),
                    SystemMetadata(key='atlas_integration', value='enabled', description='Atlas integration status'),
                    SystemMetadata(key='podemos_integration', value='enabled', description='Podemos integration status')
                ]
                
                for entry in metadata_entries:
                    existing = session.query(SystemMetadata).filter_by(key=entry.key).first()
                    if not existing:
                        session.add(entry)
                
                session.commit()
                logger.info("Initial system metadata inserted")
        except Exception as e:
            logger.warning(f"Failed to insert initial metadata: {e}")
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions
        
        Usage:
            with db.session() as session:
                content = session.query(ContentItem).all()
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session(self) -> Session:
        """Get a new database session (remember to close it)"""
        return self.SessionLocal()
    
    # Content queries
    def get_all_content(self, limit: int = None) -> List[ContentItem]:
        """Get all content items"""
        with self.session() as session:
            query = session.query(ContentItem).order_by(ContentItem.created_at.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
    
    def get_content_by_type(self, content_type: str, limit: int = None) -> List[ContentItem]:
        """Get content items by type"""
        with self.session() as session:
            query = session.query(ContentItem).filter_by(content_type=content_type)
            query = query.order_by(ContentItem.created_at.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
    
    def get_articles(self, limit: int = None) -> List[ContentItem]:
        """Get all article content"""
        return self.get_content_by_type('article', limit)
    
    def get_podcasts(self, limit: int = None) -> List[ContentItem]:
        """Get all podcast content"""
        return self.get_content_by_type('podcast', limit)
    
    def get_youtube_content(self, limit: int = None) -> List[ContentItem]:
        """Get all YouTube content"""
        return self.get_content_by_type('youtube', limit)
    
    def get_content_by_status(self, status: str, limit: int = None) -> List[ContentItem]:
        """Get content items by status"""
        with self.session() as session:
            query = session.query(ContentItem).filter_by(status=status)
            query = query.order_by(ContentItem.created_at.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
    
    def get_pending_content(self, limit: int = None) -> List[ContentItem]:
        """Get all pending content items"""
        return self.get_content_by_status('pending', limit)
    
    def get_completed_content(self, limit: int = None) -> List[ContentItem]:
        """Get all completed content items"""
        return self.get_content_by_status('completed', limit)
    
    def get_error_content(self, limit: int = None) -> List[ContentItem]:
        """Get all content items with errors"""
        with self.session() as session:
            query = session.query(ContentItem).filter(
                (ContentItem.status == 'error') | 
                (ContentItem.last_error.isnot(None))
            )
            query = query.order_by(ContentItem.created_at.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
    
    # Content lookup
    def find_content_by_uid(self, uid: str) -> Optional[ContentItem]:
        """Find content item by Atlas UID"""
        with self.session() as session:
            return session.query(ContentItem).filter_by(uid=uid).first()
    
    def find_content_by_guid(self, source_guid: str) -> Optional[ContentItem]:
        """Find content item by Podemos source GUID"""
        with self.session() as session:
            return session.query(ContentItem).filter_by(source_guid=source_guid).first()
    
    def find_content_by_url(self, source_url: str) -> Optional[ContentItem]:
        """Find content item by source URL"""
        with self.session() as session:
            return session.query(ContentItem).filter_by(source_url=source_url).first()
    
    # Podcast-specific queries
    def get_podcast_episodes_with_details(self, limit: int = None) -> List[tuple]:
        """Get podcast episodes with their content item details"""
        with self.session() as session:
            query = session.query(ContentItem, PodcastEpisode).join(PodcastEpisode)
            query = query.order_by(ContentItem.pub_date.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
    
    def get_podcast_by_show(self, show_name: str, limit: int = None) -> List[ContentItem]:
        """Get all episodes from a specific podcast show"""
        with self.session() as session:
            query = session.query(ContentItem).filter_by(
                content_type='podcast', 
                show_name=show_name
            )
            query = query.order_by(ContentItem.pub_date.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
    
    def get_podcast_shows(self) -> List[Dict[str, Any]]:
        """Get list of all podcast shows with episode counts"""
        with self.session() as session:
            result = session.query(
                ContentItem.show_name,
                func.count(ContentItem.id).label('episode_count'),
                func.max(ContentItem.pub_date).label('latest_episode')
            ).filter_by(content_type='podcast').group_by(ContentItem.show_name).all()
            
            return [
                {
                    'show_name': row.show_name,
                    'episode_count': row.episode_count,
                    'latest_episode': row.latest_episode
                }
                for row in result
            ]
    
    # Content operations
    def add_content(self, content_item: ContentItem) -> ContentItem:
        """Add new content item to database"""
        with self.session() as session:
            session.add(content_item)
            session.commit()
            session.refresh(content_item)
            return content_item
    
    def update_content_status(self, uid: str, status: str, error: str = None) -> bool:
        """Update content item status"""
        with self.session() as session:
            content = session.query(ContentItem).filter_by(uid=uid).first()
            if content:
                content.status = status
                content.updated_at = datetime.utcnow()
                if error:
                    content.last_error = error
                    content.retry_count += 1
                session.commit()
                return True
            return False
    
    def mark_processing_started(self, uid: str) -> bool:
        """Mark content as processing started"""
        with self.session() as session:
            content = session.query(ContentItem).filter_by(uid=uid).first()
            if content:
                content.status = 'processing'
                content.processing_started_at = datetime.utcnow()
                content.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
    
    def mark_processing_completed(self, uid: str) -> bool:
        """Mark content as processing completed"""
        with self.session() as session:
            content = session.query(ContentItem).filter_by(uid=uid).first()
            if content:
                content.status = 'completed'
                content.processing_completed_at = datetime.utcnow()
                content.updated_at = datetime.utcnow()
                content.last_error = None  # Clear any previous errors
                session.commit()
                return True
            return False
    
    # Statistics and reporting
    def get_content_statistics(self) -> Dict[str, Any]:
        """Get comprehensive content statistics"""
        with self.session() as session:
            # Total counts
            total_content = session.query(ContentItem).count()
            
            # Counts by type
            type_counts = dict(
                session.query(ContentItem.content_type, func.count(ContentItem.id))
                .group_by(ContentItem.content_type).all()
            )
            
            # Counts by status
            status_counts = dict(
                session.query(ContentItem.status, func.count(ContentItem.id))
                .group_by(ContentItem.status).all()
            )
            
            # Recent activity
            recent_content = session.query(func.count(ContentItem.id)).filter(
                ContentItem.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ).scalar()
            
            # Error counts
            error_count = session.query(ContentItem).filter(
                (ContentItem.status == 'error') | 
                (ContentItem.last_error.isnot(None))
            ).count()
            
            return {
                'total_content': total_content,
                'content_by_type': type_counts,
                'content_by_status': status_counts,
                'content_today': recent_content,
                'content_with_errors': error_count,
                'error_rate': round((error_count / total_content) * 100, 2) if total_content > 0 else 0
            }
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing job statistics"""
        with self.session() as session:
            total_jobs = session.query(ProcessingJob).count()
            enabled_jobs = session.query(ProcessingJob).filter_by(enabled=True).count()
            
            # Job counts by status
            status_counts = dict(
                session.query(ProcessingJob.status, func.count(ProcessingJob.id))
                .group_by(ProcessingJob.status).all()
            )
            
            # Job counts by type
            type_counts = dict(
                session.query(ProcessingJob.job_type, func.count(ProcessingJob.id))
                .group_by(ProcessingJob.job_type).all()
            )
            
            return {
                'total_jobs': total_jobs,
                'enabled_jobs': enabled_jobs,
                'jobs_by_status': status_counts,
                'jobs_by_type': type_counts
            }
    
    # Database maintenance
    def optimize_database(self):
        """Run database optimization (VACUUM and ANALYZE)"""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("VACUUM;"))
                connection.execute(text("ANALYZE;"))
            logger.info("Database optimization completed")
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database file information"""
        try:
            file_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
            
            with self.session() as session:
                content_count = session.query(ContentItem).count()
                podcast_count = session.query(PodcastEpisode).count()
                job_count = session.query(ProcessingJob).count()
            
            return {
                'database_path': self.db_path,
                'file_size_mb': round(file_size, 2),
                'content_items': content_count,
                'podcast_episodes': podcast_count,
                'processing_jobs': job_count,
                'engine_info': str(self.engine.url)
            }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

# Global database instance for convenience
_global_db: Optional[UnifiedDB] = None

def get_unified_db(db_path: str = None) -> UnifiedDB:
    """
    Get global unified database instance
    
    Args:
        db_path: Path to database file (only used on first call)
    """
    global _global_db
    
    if _global_db is None:
        _global_db = UnifiedDB(db_path or "atlas_unified.db")
    
    return _global_db

def close_global_db():
    """Close global database instance"""
    global _global_db
    
    if _global_db:
        _global_db.close()
        _global_db = None