"""
Atlas-Podemos Database Integration Package

Unified database models and connection management for Atlas content ingestion
and Podemos podcast processing systems.

This package provides:
- Unified SQLAlchemy models for all content types
- Database connection management and session handling
- Migration scripts for existing Atlas and Podemos data
- Data validation and integrity checking tools

Quick Start:
    # Import main components
    from database_integration import UnifiedDB, ContentItem, PodcastEpisode
    
    # Initialize database
    db = UnifiedDB("atlas_unified.db")
    
    # Query content
    articles = db.get_articles()
    podcasts = db.get_podcasts()
    
    # Add new content
    with db.session() as session:
        content = ContentItem(
            uid="abc123",
            title="New Article", 
            content_type="article",
            source_url="https://example.com/article"
        )
        session.add(content)
        session.commit()

Available Models:
    - ContentItem: Main content table (articles, podcasts, youtube, etc.)
    - PodcastEpisode: Extended podcast-specific data
    - ProcessingJob: Unified job processing system
    - ContentAnalysis: Content analysis and cognitive processing results
    - ContentTag: Normalized content tags
    - SystemMetadata: System configuration storage

Database Management:
    - UnifiedDB: High-level database operations and connection management
    - Migration scripts in database_integration/ directory
    - Validation tools for data integrity checking
"""

# Import main classes for convenience
from .models import (
    # SQLAlchemy models
    ContentItem,
    PodcastEpisode,
    ProcessingJob,
    ContentAnalysis,
    ContentTag,
    SystemMetadata,
    Base,
    
    # Database functions
    init_database,
    get_engine,
    get_session,
    create_all_tables,
    
    # Convenience query functions
    get_content_by_type,
    get_podcast_episodes_with_content,
    get_content_by_status,
    get_content_with_errors,
    find_content_by_uid,
    find_content_by_guid
)

from .database import (
    # Database connection manager
    UnifiedDB,
    get_unified_db,
    close_global_db
)

# Package metadata
__version__ = "1.0.0"
__author__ = "Atlas-Podemos Integration"
__description__ = "Unified database integration for Atlas and Podemos systems"

# Default database path
DEFAULT_DB_PATH = "atlas_unified.db"

# Export all public components
__all__ = [
    # Models
    'ContentItem',
    'PodcastEpisode', 
    'ProcessingJob',
    'ContentAnalysis',
    'ContentTag',
    'SystemMetadata',
    'Base',
    
    # Database management
    'UnifiedDB',
    'get_unified_db',
    'close_global_db',
    
    # Database functions
    'init_database',
    'get_engine', 
    'get_session',
    'create_all_tables',
    
    # Query functions
    'get_content_by_type',
    'get_podcast_episodes_with_content',
    'get_content_by_status',
    'get_content_with_errors',
    'find_content_by_uid',
    'find_content_by_guid',
    
    # Constants
    'DEFAULT_DB_PATH'
]