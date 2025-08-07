#!/usr/bin/env python3
"""
Atlas Database Integration Helper

Provides compatibility layer for integrating the unified database 
with existing Atlas helpers and workflows.

This module allows existing Atlas code to gradually adopt the unified database
while maintaining backward compatibility with file-based operations.

Usage:
    from database_integration.atlas_integration import AtlasDBHelper
    
    # Initialize with unified database
    atlas_db = AtlasDBHelper("atlas_unified.db")
    
    # Use like existing Atlas helpers
    atlas_db.store_content(uid, title, content_type, source_url)
    content = atlas_db.get_content(uid)
    articles = atlas_db.get_articles()
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .database import UnifiedDB
from .models import ContentItem

class AtlasDBHelper:
    """
    Atlas database integration helper
    
    Provides Atlas-compatible interface for the unified database,
    allowing existing Atlas code to work with database storage
    while maintaining file-based operations as needed.
    """
    
    def __init__(self, db_path: str = "atlas_unified.db"):
        """Initialize Atlas database helper"""
        self.db = UnifiedDB(db_path)
        self.output_dir = Path("output/articles")
        
    def store_content(
        self, 
        uid: str, 
        title: str, 
        content_type: str, 
        source_url: str,
        content_data: Dict = None,
        file_paths: Dict = None
    ) -> bool:
        """
        Store content in unified database (Atlas-compatible interface)
        
        Args:
            uid: Atlas UID
            title: Content title
            content_type: Type of content (article, youtube, etc.)
            source_url: Original source URL
            content_data: Additional content metadata
            file_paths: Dictionary of file paths (html, markdown, metadata)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.session() as session:
                # Check if content already exists
                existing = session.query(ContentItem).filter_by(uid=uid).first()
                
                if existing:
                    # Update existing content
                    existing.title = title
                    existing.content_type = content_type
                    existing.source_url = source_url
                    existing.updated_at = datetime.utcnow()
                    
                    if content_data:
                        existing.description = content_data.get('description')
                        existing.author = content_data.get('author')
                        existing.image_url = content_data.get('image_url')
                        if content_data.get('tags'):
                            existing.tags = content_data['tags']
                    
                    if file_paths:
                        existing.file_path_html = file_paths.get('html')
                        existing.file_path_markdown = file_paths.get('markdown')
                        existing.file_path_metadata = file_paths.get('metadata')
                    
                    content_item = existing
                else:
                    # Create new content
                    content_item = ContentItem(
                        uid=uid,
                        title=title,
                        content_type=content_type,
                        source_url=source_url,
                        status='completed',
                        description=content_data.get('description') if content_data else None,
                        author=content_data.get('author') if content_data else None,
                        image_url=content_data.get('image_url') if content_data else None,
                        file_path_html=file_paths.get('html') if file_paths else None,
                        file_path_markdown=file_paths.get('markdown') if file_paths else None,
                        file_path_metadata=file_paths.get('metadata') if file_paths else None
                    )
                    
                    if content_data and content_data.get('tags'):
                        content_item.tags = content_data['tags']
                    
                    session.add(content_item)
                
                session.commit()
                return True
                
        except Exception as e:
            print(f"Error storing content {uid}: {e}")
            return False
    
    def get_content(self, uid: str) -> Optional[Dict]:
        """
        Get content by UID (Atlas-compatible interface)
        
        Returns content as dictionary similar to Atlas JSON metadata format
        """
        content = self.db.find_content_by_uid(uid)
        if not content:
            return None
        
        return {
            'uid': content.uid,
            'title': content.title,
            'content_type': content.content_type,
            'source': content.source_url,
            'status': content.status,
            'description': content.description,
            'author': content.author,
            'image_url': content.image_url,
            'tags': content.tags,
            'created_at': content.created_at.isoformat() if content.created_at else None,
            'updated_at': content.updated_at.isoformat() if content.updated_at else None,
            'file_paths': content.get_file_paths(),
            'files_exist': content.files_exist(),
            'error': content.last_error,
            'retry_count': content.retry_count
        }
    
    def get_articles(self, limit: int = None) -> List[Dict]:
        """Get all articles (Atlas-compatible format)"""
        articles = self.db.get_articles(limit)
        return [self._content_to_dict(article) for article in articles]
    
    def get_content_by_type(self, content_type: str, limit: int = None) -> List[Dict]:
        """Get content by type (Atlas-compatible format)"""
        content_items = self.db.get_content_by_type(content_type, limit)
        return [self._content_to_dict(item) for item in content_items]
    
    def get_recent_content(self, days: int = 7, limit: int = None) -> List[Dict]:
        """Get recent content (Atlas-compatible format)"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with self.db.session() as session:
            query = session.query(ContentItem).filter(
                ContentItem.created_at >= cutoff_date
            ).order_by(ContentItem.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            content_items = query.all()
            
        return [self._content_to_dict(item) for item in content_items]
    
    def search_content(self, query: str, content_type: str = None, limit: int = None) -> List[Dict]:
        """Search content by title or description"""
        with self.db.session() as session:
            search_query = session.query(ContentItem).filter(
                (ContentItem.title.contains(query)) |
                (ContentItem.description.contains(query))
            )
            
            if content_type:
                search_query = search_query.filter(ContentItem.content_type == content_type)
            
            search_query = search_query.order_by(ContentItem.created_at.desc())
            
            if limit:
                search_query = search_query.limit(limit)
            
            content_items = search_query.all()
        
        return [self._content_to_dict(item) for item in content_items]
    
    def mark_content_error(self, uid: str, error_message: str) -> bool:
        """Mark content as having an error"""
        return self.db.update_content_status(uid, 'error', error_message)
    
    def mark_content_completed(self, uid: str) -> bool:
        """Mark content as completed"""
        return self.db.mark_processing_completed(uid)
    
    def get_content_statistics(self) -> Dict[str, Any]:
        """Get content statistics (Atlas-compatible format)"""
        stats = self.db.get_content_statistics()
        
        # Add Atlas-specific statistics
        with self.db.session() as session:
            # Count content with files
            content_with_files = session.query(ContentItem).filter(
                (ContentItem.file_path_html.isnot(None)) |
                (ContentItem.file_path_markdown.isnot(None)) |
                (ContentItem.file_path_metadata.isnot(None))
            ).count()
            
            stats['content_with_files'] = content_with_files
            stats['atlas_file_coverage'] = round(
                (content_with_files / stats['total_content']) * 100, 2
            ) if stats['total_content'] > 0 else 0
        
        return stats
    
    def _content_to_dict(self, content: ContentItem) -> Dict:
        """Convert ContentItem to Atlas-compatible dictionary"""
        return {
            'uid': content.uid,
            'title': content.title,
            'content_type': content.content_type,
            'source': content.source_url,
            'status': content.status,
            'description': content.description,
            'author': content.author,
            'image_url': content.image_url,
            'tags': content.tags,
            'created_at': content.created_at.isoformat() if content.created_at else None,
            'updated_at': content.updated_at.isoformat() if content.updated_at else None,
            'file_paths': content.get_file_paths(),
            'error': content.last_error,
            'retry_count': content.retry_count
        }
    
    def migrate_from_files(self, metadata_dir: str = None) -> Dict[str, Any]:
        """
        Migrate Atlas file-based content to database
        
        This is a convenience method that calls the migration script
        """
        if metadata_dir is None:
            metadata_dir = self.output_dir / "metadata"
        
        from . import migrate_atlas_content
        
        migrator = migrate_atlas_content.AtlasContentMigrator(
            self.db.db_path, 
            str(metadata_dir.parent.parent)
        )
        
        success = migrator.migrate_all_content()
        return {
            'success': success,
            'stats': migrator.stats
        }
    
    def close(self):
        """Close database connections"""
        self.db.close()

# Compatibility functions for existing Atlas code
def get_atlas_db_helper(db_path: str = None) -> AtlasDBHelper:
    """Get Atlas database helper instance"""
    return AtlasDBHelper(db_path or "atlas_unified.db")

def migrate_existing_atlas_content(db_path: str = None) -> bool:
    """Migrate existing Atlas file-based content to database"""
    helper = get_atlas_db_helper(db_path)
    result = helper.migrate_from_files()
    helper.close()
    return result['success']