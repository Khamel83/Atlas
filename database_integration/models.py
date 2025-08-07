#!/usr/bin/env python3
"""
Unified Database Models - Atlas + Podemos Integration

SQLAlchemy ORM models for the unified database schema supporting both 
Atlas file-based content and Podemos podcast processing functionality.

Usage:
    from database_integration.models import ContentItem, PodcastEpisode, get_session
    
    with get_session() as session:
        articles = session.query(ContentItem).filter_by(content_type='article').all()
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

# Base class for all models
Base = declarative_base()

# Default database path
DEFAULT_DB_PATH = "atlas_unified.db"

class ContentItem(Base):
    """
    Unified content model supporting all content types (articles, podcasts, youtube, etc.)
    
    This model serves as the central content registry for both Atlas and Podemos,
    providing unified tracking of processing status, metadata, and file locations.
    """
    __tablename__ = 'content_items'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Atlas UID system (32-character hash)
    uid = Column(String(32), unique=True, nullable=False, index=True)
    
    # Content classification
    content_type = Column(String(50), nullable=False, index=True)  # article, podcast, youtube, etc.
    source_url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, default='pending', index=True)  # pending, processing, completed, error
    
    # Atlas compatibility - file-based storage
    file_path_html = Column(String)      # Path to HTML file
    file_path_markdown = Column(String)  # Path to Markdown file  
    file_path_metadata = Column(String)  # Path to JSON metadata
    
    # Podemos compatibility - podcast-specific fields
    source_guid = Column(String, index=True)  # RSS GUID for podcasts
    show_name = Column(String, index=True)    # For podcast episodes
    pub_date = Column(DateTime)
    
    # Common metadata
    description = Column(Text)
    image_url = Column(String)
    author = Column(String)
    tags_json = Column(Text)  # JSON array of tags
    
    # Processing tracking
    retry_count = Column(Integer, default=0)
    last_error = Column(Text)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    podcast_episode = relationship("PodcastEpisode", back_populates="content_item", uselist=False, cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="content_item", cascade="all, delete-orphan")
    content_analysis = relationship("ContentAnalysis", back_populates="content_item", cascade="all, delete-orphan")
    content_tags = relationship("ContentTag", back_populates="content_item", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ContentItem(uid='{self.uid}', type='{self.content_type}', title='{self.title[:50]}...')>"
    
    @property
    def tags(self) -> List[str]:
        """Get tags as list from JSON string"""
        if self.tags_json:
            try:
                return json.loads(self.tags_json)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @tags.setter
    def tags(self, tag_list: List[str]):
        """Set tags from list to JSON string"""
        if tag_list:
            self.tags_json = json.dumps(tag_list)
        else:
            self.tags_json = None
    
    @property
    def is_atlas_content(self) -> bool:
        """Check if this is Atlas file-based content"""
        return bool(self.file_path_html or self.file_path_markdown or self.file_path_metadata)
    
    @property
    def is_podemos_content(self) -> bool:
        """Check if this is Podemos podcast content"""
        return self.content_type == 'podcast' and bool(self.source_guid)
    
    def get_file_paths(self) -> Dict[str, Optional[str]]:
        """Get all file paths as dictionary"""
        return {
            'html': self.file_path_html,
            'markdown': self.file_path_markdown,
            'metadata': self.file_path_metadata
        }
    
    def files_exist(self) -> Dict[str, bool]:
        """Check which files exist on filesystem"""
        paths = self.get_file_paths()
        return {
            key: bool(path and os.path.exists(path))
            for key, path in paths.items()
        }

class PodcastEpisode(Base):
    """
    Extended podcast-specific data model
    
    This model stores detailed podcast processing information including
    audio files, transcripts, and ad segment data from Podemos processing.
    """
    __tablename__ = 'podcast_episodes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_item_id = Column(Integer, ForeignKey('content_items.id'), nullable=False, index=True)
    
    # Audio processing
    original_audio_url = Column(String, nullable=False, index=True)
    original_file_path = Column(String, unique=True)
    original_duration = Column(Float, index=True)  # Duration in seconds
    original_file_size = Column(Integer)  # File size in bytes
    cleaned_file_path = Column(String, unique=True)
    cleaned_duration = Column(Float)  # Duration after ad removal
    cleaned_file_size = Column(Integer)  # Size after processing
    cleaned_ready_at = Column(DateTime)
    
    # Show metadata
    show_image_url = Column(String)
    show_author = Column(String)
    
    # Processing data (JSON storage)
    ad_segments_json = Column(Text)       # Detected ad segments
    transcript_json = Column(Text)        # Full transcript
    fast_transcript_json = Column(Text)   # Fast/rough transcript
    cleaned_chapters_json = Column(Text)  # Chapters after ad removal
    chapters_json = Column(Text)          # Original chapters from RSS
    md_transcript_file_path = Column(String)  # Path to Markdown transcript
    
    # Relationship back to content item
    content_item = relationship("ContentItem", back_populates="podcast_episode")
    
    def __repr__(self):
        return f"<PodcastEpisode(content_item_id={self.content_item_id}, duration={self.original_duration})>"
    
    @property
    def ad_segments(self) -> List[Dict]:
        """Get ad segments as list from JSON"""
        if self.ad_segments_json:
            try:
                return json.loads(self.ad_segments_json)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @ad_segments.setter
    def ad_segments(self, segments: List[Dict]):
        """Set ad segments from list to JSON"""
        if segments:
            self.ad_segments_json = json.dumps(segments)
        else:
            self.ad_segments_json = None
    
    @property
    def transcript(self) -> Dict:
        """Get transcript as dict from JSON"""
        if self.transcript_json:
            try:
                return json.loads(self.transcript_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @transcript.setter
    def transcript(self, transcript_data: Dict):
        """Set transcript from dict to JSON"""
        if transcript_data:
            self.transcript_json = json.dumps(transcript_data)
        else:
            self.transcript_json = None
    
    @property
    def chapters(self) -> List[Dict]:
        """Get chapters as list from JSON"""
        if self.chapters_json:
            try:
                return json.loads(self.chapters_json)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @chapters.setter  
    def chapters(self, chapters_data: List[Dict]):
        """Set chapters from list to JSON"""
        if chapters_data:
            self.chapters_json = json.dumps(chapters_data)
        else:
            self.chapters_json = None
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Get original duration in minutes"""
        if self.original_duration:
            return round(self.original_duration / 60.0, 2)
        return None
    
    @property
    def size_mb(self) -> Optional[float]:
        """Get original file size in MB"""
        if self.original_file_size:
            return round(self.original_file_size / (1024 * 1024), 2)
        return None

class ProcessingJob(Base):
    """
    Unified job processing system
    
    Supports both Atlas scheduled jobs and Podemos processing pipeline jobs.
    Provides centralized job scheduling and tracking across both systems.
    """
    __tablename__ = 'processing_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(50), nullable=False, index=True)  # ingest, transcribe, analyze, etc.
    content_item_id = Column(Integer, ForeignKey('content_items.id'), index=True)  # Optional: specific content
    command = Column(Text, nullable=False)
    schedule_expression = Column(String)  # Cron expression or interval
    status = Column(String, default='scheduled', index=True)
    
    # Job execution tracking
    last_run_at = Column(DateTime, index=True)
    next_run_at = Column(DateTime, index=True)
    run_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_error = Column(Text)
    
    # Job configuration
    enabled = Column(Boolean, default=True, index=True)
    priority = Column(Integer, default=0)
    timeout_seconds = Column(Integer, default=3600)  # 1 hour default
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to content item (optional)
    content_item = relationship("ContentItem", back_populates="processing_jobs")
    
    def __repr__(self):
        return f"<ProcessingJob(type='{self.job_type}', status='{self.status}')>"

class ContentAnalysis(Base):
    """
    Content analysis and cognitive processing results
    
    Stores results from Atlas cognitive analysis, pattern detection,
    and similarity analysis for all content types.
    """
    __tablename__ = 'content_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_item_id = Column(Integer, ForeignKey('content_items.id'), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False, index=True)  # cognitive, pattern, similarity
    analysis_data_json = Column(Text)  # Analysis results
    confidence_score = Column(Float, index=True)
    model_version = Column(String(50))  # Track model used for analysis
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to content item
    content_item = relationship("ContentItem", back_populates="content_analysis")
    
    def __repr__(self):
        return f"<ContentAnalysis(type='{self.analysis_type}', confidence={self.confidence_score})>"
    
    @property
    def analysis_data(self) -> Dict:
        """Get analysis data as dict from JSON"""
        if self.analysis_data_json:
            try:
                return json.loads(self.analysis_data_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @analysis_data.setter
    def analysis_data(self, data: Dict):
        """Set analysis data from dict to JSON"""
        if data:
            self.analysis_data_json = json.dumps(data)
        else:
            self.analysis_data_json = None

class ContentTag(Base):
    """
    Normalized content tags for better querying and organization
    
    Supports manual, automatic, and cognitive tagging systems
    from both Atlas and Podemos processing.
    """
    __tablename__ = 'content_tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_item_id = Column(Integer, ForeignKey('content_items.id'), nullable=False, index=True)
    tag = Column(String(100), nullable=False, index=True)
    tag_type = Column(String(50), default='manual', index=True)  # manual, auto, cognitive
    confidence_score = Column(Float, default=1.0, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to content item
    content_item = relationship("ContentItem", back_populates="content_tags")
    
    # Unique constraint on content_item_id + tag + tag_type
    __table_args__ = (
        {'sqlite_autoincrement': True}  # For SQLite compatibility
    )
    
    def __repr__(self):
        return f"<ContentTag(tag='{self.tag}', type='{self.tag_type}')>"

class SystemMetadata(Base):
    """
    System configuration and metadata storage
    
    Stores system-wide configuration, migration status, and 
    operational metadata for the unified database system.
    """
    __tablename__ = 'system_metadata'
    
    key = Column(String(100), primary_key=True)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemMetadata(key='{self.key}', value='{self.value[:50]}...')>"

# Database connection and session management
_engine = None
_SessionLocal = None

def init_database(db_path: str = None, echo: bool = False) -> None:
    """
    Initialize database connection and session factory
    
    Args:
        db_path: Path to SQLite database file
        echo: Whether to echo SQL statements (for debugging)
    """
    global _engine, _SessionLocal
    
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    # Ensure directory exists
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir:
        Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    # Create engine
    _engine = create_engine(
        f'sqlite:///{db_path}',
        echo=echo,
        poolclass=StaticPool,
        pool_pre_ping=True,
        connect_args={'check_same_thread': False}  # Allow multi-threading
    )
    
    # Create session factory
    _SessionLocal = sessionmaker(bind=_engine)

def get_engine():
    """Get the database engine"""
    if _engine is None:
        init_database()
    return _engine

def get_session() -> Session:
    """
    Get a database session
    
    Usage:
        with get_session() as session:
            content = session.query(ContentItem).all()
    """
    if _SessionLocal is None:
        init_database()
    return _SessionLocal()

def create_all_tables(db_path: str = None) -> None:
    """
    Create all database tables
    
    Args:
        db_path: Path to database file
    """
    if db_path:
        init_database(db_path)
    
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

# Convenience query functions
def get_content_by_type(content_type: str, session: Session = None) -> List[ContentItem]:
    """Get all content items of a specific type"""
    if session is None:
        with get_session() as session:
            return session.query(ContentItem).filter_by(content_type=content_type).all()
    return session.query(ContentItem).filter_by(content_type=content_type).all()

def get_podcast_episodes_with_content(session: Session = None) -> List[tuple]:
    """Get podcast episodes joined with their content items"""
    if session is None:
        with get_session() as session:
            return session.query(ContentItem, PodcastEpisode).join(PodcastEpisode).all()
    return session.query(ContentItem, PodcastEpisode).join(PodcastEpisode).all()

def get_content_by_status(status: str, session: Session = None) -> List[ContentItem]:
    """Get all content items with specific status"""
    if session is None:
        with get_session() as session:
            return session.query(ContentItem).filter_by(status=status).all()
    return session.query(ContentItem).filter_by(status=status).all()

def get_content_with_errors(session: Session = None) -> List[ContentItem]:
    """Get all content items with errors"""
    if session is None:
        with get_session() as session:
            return session.query(ContentItem).filter(
                (ContentItem.status == 'error') | 
                (ContentItem.last_error.isnot(None))
            ).all()
    return session.query(ContentItem).filter(
        (ContentItem.status == 'error') | 
        (ContentItem.last_error.isnot(None))
    ).all()

# Migration and compatibility helpers
def find_content_by_uid(uid: str, session: Session = None) -> Optional[ContentItem]:
    """Find content item by Atlas UID"""
    if session is None:
        with get_session() as session:
            return session.query(ContentItem).filter_by(uid=uid).first()
    return session.query(ContentItem).filter_by(uid=uid).first()

def find_content_by_guid(source_guid: str, session: Session = None) -> Optional[ContentItem]:
    """Find content item by Podemos source GUID"""
    if session is None:
        with get_session() as session:
            return session.query(ContentItem).filter_by(source_guid=source_guid).first()
    return session.query(ContentItem).filter_by(source_guid=source_guid).first()

# Auto-initialize if imported
if _engine is None:
    try:
        init_database()
    except Exception:
        pass  # Will be initialized when needed