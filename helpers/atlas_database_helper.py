#!/usr/bin/env python3
"""
Atlas Database Integration Helper

Enhanced Atlas helper that integrates the unified database with existing Atlas workflows.
Provides backward compatibility while unlocking database performance benefits.

This helper serves as the bridge between existing Atlas code and the unified database,
enabling gradual migration to database-first operations.

Usage:
    from helpers.atlas_database_helper import AtlasDatabaseManager
    
    # Initialize with database integration
    atlas_db = AtlasDatabaseManager()
    
    # Store content with database + file storage
    success = atlas_db.store_content(metadata, content_data)
    
    # Query content with database performance
    articles = atlas_db.get_articles(limit=100)
    recent_content = atlas_db.get_recent_content(days=7)
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# Atlas imports
from helpers.metadata_manager import ContentMetadata, ContentType, ProcessingStatus, MetadataManager
from helpers.path_manager import PathManager, PathType, create_path_manager
from helpers.utils import log_info, log_error
from helpers.dedupe import link_uid

# Database integration imports
try:
    from database_integration import UnifiedDB, ContentItem
    from database_integration.atlas_integration import AtlasDBHelper
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    log_error("Database integration not available. Falling back to file-based operations.")

class AtlasDatabaseManager:
    """
    Enhanced Atlas content manager with unified database integration
    
    Provides Atlas-compatible interface with database performance benefits.
    Maintains backward compatibility with existing Atlas code while enabling
    database-first operations for improved performance and functionality.
    """
    
    def __init__(self, db_path: str = "atlas_unified.db", enable_database: bool = True):
        """
        Initialize Atlas database manager
        
        Args:
            db_path: Path to unified database file
            enable_database: Whether to use database (falls back to files if False)
        """
        self.database_enabled = enable_database and DATABASE_AVAILABLE
        
        # Initialize Atlas components
        self.path_manager = create_path_manager()
        self.metadata_manager = MetadataManager()
        
        # Initialize database components if available
        if self.database_enabled:
            try:
                self.db = UnifiedDB(db_path)
                self.atlas_db = AtlasDBHelper(db_path)
                log_info(f"Atlas database integration initialized: {db_path}")
            except Exception as e:
                log_error(f"Failed to initialize database: {e}. Falling back to file-based operations.")
                self.database_enabled = False
        
        if not self.database_enabled:
            log_info("Atlas running in file-based mode")
    
    def store_content(
        self, 
        metadata: ContentMetadata, 
        content_data: Dict[str, Any] = None,
        html_content: str = None,
        markdown_content: str = None
    ) -> bool:
        """
        Store content using unified database + file system
        
        Args:
            metadata: Atlas ContentMetadata object
            content_data: Additional content data for database
            html_content: HTML content to store
            markdown_content: Markdown content to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate UID if not present
            if not metadata.uid:
                metadata.uid = link_uid(metadata.url)
            
            # Store in database if enabled
            if self.database_enabled:
                # Convert Atlas metadata to database format
                db_content_data = self._atlas_metadata_to_db_format(metadata, content_data)
                
                # Store in database
                success = self.atlas_db.store_content(
                    uid=metadata.uid,
                    title=metadata.title,
                    content_type=self._map_content_type(metadata.content_type),
                    source_url=metadata.url,
                    content_data=db_content_data,
                    file_paths=self._get_file_paths(metadata.uid)
                )
                
                if not success:
                    log_error(f"Failed to store content in database: {metadata.uid}")
                    # Continue with file storage as fallback
            
            # Store files (always, for backward compatibility)
            file_success = self._store_content_files(metadata, html_content, markdown_content)
            
            if self.database_enabled:
                return success and file_success
            else:
                return file_success
                
        except Exception as e:
            log_error(f"Error storing content {metadata.uid}: {e}")
            return False
    
    def get_content(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get content by UID (database-first with file fallback)
        
        Args:
            uid: Content UID
            
        Returns:
            Content dictionary or None if not found
        """
        try:
            # Try database first
            if self.database_enabled:
                content = self.atlas_db.get_content(uid)
                if content:
                    return content
            
            # Fall back to file-based metadata
            return self._get_content_from_files(uid)
            
        except Exception as e:
            log_error(f"Error getting content {uid}: {e}")
            return None
    
    def get_articles(self, limit: int = None, since_days: int = None) -> List[Dict[str, Any]]:
        """
        Get articles with database performance
        
        Args:
            limit: Maximum number of articles to return
            since_days: Only return articles from last N days
            
        Returns:
            List of article dictionaries
        """
        try:
            if self.database_enabled:
                if since_days:
                    return self.atlas_db.get_recent_content(days=since_days, limit=limit)
                else:
                    return self.atlas_db.get_articles(limit=limit)
            else:
                return self._get_articles_from_files(limit, since_days)
                
        except Exception as e:
            log_error(f"Error getting articles: {e}")
            return []
    
    def get_podcasts(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get podcasts with database performance"""
        try:
            if self.database_enabled:
                return self.atlas_db.get_content_by_type('podcast', limit=limit)
            else:
                return self._get_content_by_type_from_files('podcast', limit)
                
        except Exception as e:
            log_error(f"Error getting podcasts: {e}")
            return []
    
    def get_youtube_content(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get YouTube content with database performance"""
        try:
            if self.database_enabled:
                return self.atlas_db.get_content_by_type('youtube', limit=limit)
            else:
                return self._get_content_by_type_from_files('youtube', limit)
                
        except Exception as e:
            log_error(f"Error getting YouTube content: {e}")
            return []
    
    def search_content(
        self, 
        query: str, 
        content_type: str = None, 
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Search content with database performance
        
        Args:
            query: Search query string
            content_type: Filter by content type (optional)
            limit: Maximum results to return
            
        Returns:
            List of matching content dictionaries
        """
        try:
            if self.database_enabled:
                return self.atlas_db.search_content(query, content_type, limit)
            else:
                return self._search_content_files(query, content_type, limit)
                
        except Exception as e:
            log_error(f"Error searching content: {e}")
            return []
    
    def get_content_statistics(self) -> Dict[str, Any]:
        """Get comprehensive content statistics"""
        try:
            if self.database_enabled:
                return self.atlas_db.get_content_statistics()
            else:
                return self._get_statistics_from_files()
                
        except Exception as e:
            log_error(f"Error getting statistics: {e}")
            return {}
    
    def mark_content_error(self, uid: str, error_message: str) -> bool:
        """Mark content as having an error"""
        try:
            if self.database_enabled:
                return self.atlas_db.mark_content_error(uid, error_message)
            else:
                return self._mark_content_error_in_files(uid, error_message)
                
        except Exception as e:
            log_error(f"Error marking content error {uid}: {e}")
            return False
    
    def mark_content_completed(self, uid: str) -> bool:
        """Mark content as completed"""
        try:
            if self.database_enabled:
                return self.atlas_db.mark_content_completed(uid)
            else:
                return self._mark_content_completed_in_files(uid)
                
        except Exception as e:
            log_error(f"Error marking content completed {uid}: {e}")
            return False
    
    def get_processing_queue(self, status: str = "pending") -> List[Dict[str, Any]]:
        """Get content by processing status (database optimized)"""
        try:
            if self.database_enabled:
                if status == "pending":
                    return self.atlas_db.get_pending_content()
                elif status == "error":
                    return self.atlas_db.get_error_content()
                else:
                    # Use database for efficient status filtering
                    with self.db.session() as session:
                        content_items = session.query(ContentItem).filter_by(status=status).all()
                        return [self.atlas_db._content_to_dict(item) for item in content_items]
            else:
                return self._get_content_by_status_from_files(status)
                
        except Exception as e:
            log_error(f"Error getting processing queue: {e}")
            return []
    
    # Private helper methods
    
    def _atlas_metadata_to_db_format(self, metadata: ContentMetadata, content_data: Dict = None) -> Dict[str, Any]:
        """Convert Atlas ContentMetadata to database format"""
        db_data = {
            'description': metadata.description,
            'author': metadata.author,
            'image_url': getattr(metadata, 'image_url', None),
            'tags': metadata.tags if hasattr(metadata, 'tags') else []
        }
        
        if content_data:
            db_data.update(content_data)
            
        return db_data
    
    def _map_content_type(self, atlas_type: ContentType) -> str:
        """Map Atlas ContentType to database string"""
        if isinstance(atlas_type, ContentType):
            return atlas_type.value
        return str(atlas_type).lower()
    
    def _get_file_paths(self, uid: str) -> Dict[str, str]:
        """Get file paths for content UID"""
        try:
            html_path = self.path_manager.get_path(PathType.HTML, uid)
            markdown_path = self.path_manager.get_path(PathType.MARKDOWN, uid)
            metadata_path = self.path_manager.get_path(PathType.METADATA, uid)
            
            return {
                'html': html_path if os.path.exists(html_path) else None,
                'markdown': markdown_path if os.path.exists(markdown_path) else None,
                'metadata': metadata_path if os.path.exists(metadata_path) else None
            }
        except Exception:
            return {'html': None, 'markdown': None, 'metadata': None}
    
    def _store_content_files(self, metadata: ContentMetadata, html_content: str, markdown_content: str) -> bool:
        """Store content files using existing Atlas file system"""
        try:
            # Use existing Atlas metadata manager
            result = self.metadata_manager.save_metadata(metadata)
            
            # Store HTML content if provided
            if html_content:
                html_path = self.path_manager.get_path(PathType.HTML, metadata.uid)
                os.makedirs(os.path.dirname(html_path), exist_ok=True)
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            # Store Markdown content if provided
            if markdown_content:
                markdown_path = self.path_manager.get_path(PathType.MARKDOWN, metadata.uid)
                os.makedirs(os.path.dirname(markdown_path), exist_ok=True)
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
            
            return result
            
        except Exception as e:
            log_error(f"Error storing content files: {e}")
            return False
    
    def _get_content_from_files(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get content from file system (fallback)"""
        try:
            metadata_path = self.path_manager.get_path(PathType.METADATA, uid)
            if not os.path.exists(metadata_path):
                return None
                
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            # Convert to Atlas-compatible format
            return {
                'uid': metadata.get('uid', uid),
                'title': metadata.get('title', 'Untitled'),
                'content_type': metadata.get('content_type', 'article'),
                'source': metadata.get('source', ''),
                'status': metadata.get('status', 'unknown'),
                'description': metadata.get('description'),
                'author': metadata.get('author'),
                'tags': metadata.get('tags', []),
                'created_at': metadata.get('created_at'),
                'file_paths': self._get_file_paths(uid)
            }
            
        except Exception as e:
            log_error(f"Error loading content from files {uid}: {e}")
            return None
    
    def _get_articles_from_files(self, limit: int = None, since_days: int = None) -> List[Dict[str, Any]]:
        """Get articles from file system (fallback)"""
        try:
            articles = []
            metadata_dir = Path(self.path_manager.get_path(PathType.METADATA, "")).parent
            
            cutoff_date = None
            if since_days:
                cutoff_date = datetime.now() - timedelta(days=since_days)
            
            for metadata_file in metadata_dir.glob("*.json"):
                if limit and len(articles) >= limit:
                    break
                    
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Filter by content type
                    if metadata.get('content_type') != 'article':
                        continue
                    
                    # Filter by date if specified
                    if cutoff_date and metadata.get('created_at'):
                        created_at = datetime.fromisoformat(metadata['created_at'].replace('Z', '+00:00'))
                        if created_at < cutoff_date:
                            continue
                    
                    articles.append({
                        'uid': metadata.get('uid'),
                        'title': metadata.get('title', 'Untitled'),
                        'content_type': metadata.get('content_type', 'article'),
                        'source': metadata.get('source', ''),
                        'status': metadata.get('status', 'unknown'),
                        'created_at': metadata.get('created_at')
                    })
                    
                except Exception as e:
                    continue
            
            return articles
            
        except Exception as e:
            log_error(f"Error getting articles from files: {e}")
            return []
    
    def _get_content_by_type_from_files(self, content_type: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get content by type from files (fallback)"""
        try:
            content = []
            metadata_dir = Path(self.path_manager.get_path(PathType.METADATA, "")).parent
            
            for metadata_file in metadata_dir.glob("*.json"):
                if limit and len(content) >= limit:
                    break
                    
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    if metadata.get('content_type') == content_type:
                        content.append({
                            'uid': metadata.get('uid'),
                            'title': metadata.get('title', 'Untitled'),
                            'content_type': metadata.get('content_type'),
                            'source': metadata.get('source', ''),
                            'status': metadata.get('status', 'unknown'),
                            'created_at': metadata.get('created_at')
                        })
                        
                except Exception:
                    continue
            
            return content
            
        except Exception as e:
            log_error(f"Error getting content by type from files: {e}")
            return []
    
    def _search_content_files(self, query: str, content_type: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Search content in files (fallback)"""
        try:
            results = []
            metadata_dir = Path(self.path_manager.get_path(PathType.METADATA, "")).parent
            query_lower = query.lower()
            
            for metadata_file in metadata_dir.glob("*.json"):
                if limit and len(results) >= limit:
                    break
                    
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Filter by content type if specified
                    if content_type and metadata.get('content_type') != content_type:
                        continue
                    
                    # Search in title and description
                    title = metadata.get('title', '').lower()
                    description = metadata.get('description', '').lower()
                    
                    if query_lower in title or query_lower in description:
                        results.append({
                            'uid': metadata.get('uid'),
                            'title': metadata.get('title', 'Untitled'),
                            'content_type': metadata.get('content_type'),
                            'source': metadata.get('source', ''),
                            'status': metadata.get('status', 'unknown'),
                            'description': metadata.get('description')
                        })
                        
                except Exception:
                    continue
            
            return results
            
        except Exception as e:
            log_error(f"Error searching content files: {e}")
            return []
    
    def _get_statistics_from_files(self) -> Dict[str, Any]:
        """Get statistics from files (fallback)"""
        try:
            stats = {
                'total_content': 0,
                'content_by_type': {},
                'content_by_status': {},
                'content_with_errors': 0
            }
            
            metadata_dir = Path(self.path_manager.get_path(PathType.METADATA, "")).parent
            
            for metadata_file in metadata_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    stats['total_content'] += 1
                    
                    # Count by type
                    content_type = metadata.get('content_type', 'unknown')
                    stats['content_by_type'][content_type] = stats['content_by_type'].get(content_type, 0) + 1
                    
                    # Count by status
                    status = metadata.get('status', 'unknown')
                    stats['content_by_status'][status] = stats['content_by_status'].get(status, 0) + 1
                    
                    # Count errors
                    if status == 'error' or metadata.get('error'):
                        stats['content_with_errors'] += 1
                        
                except Exception:
                    continue
            
            return stats
            
        except Exception as e:
            log_error(f"Error getting statistics from files: {e}")
            return {}
    
    def _mark_content_error_in_files(self, uid: str, error_message: str) -> bool:
        """Mark content error in files (fallback)"""
        try:
            metadata_path = self.path_manager.get_path(PathType.METADATA, uid)
            if not os.path.exists(metadata_path):
                return False
                
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            metadata['status'] = 'error'
            metadata['error'] = error_message
            metadata['updated_at'] = datetime.now().isoformat()
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            log_error(f"Error marking content error in files {uid}: {e}")
            return False
    
    def _mark_content_completed_in_files(self, uid: str) -> bool:
        """Mark content completed in files (fallback)"""
        try:
            metadata_path = self.path_manager.get_path(PathType.METADATA, uid)
            if not os.path.exists(metadata_path):
                return False
                
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            metadata['status'] = 'success'
            metadata['updated_at'] = datetime.now().isoformat()
            metadata.pop('error', None)  # Remove any error messages
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            log_error(f"Error marking content completed in files {uid}: {e}")
            return False
    
    def _get_content_by_status_from_files(self, status: str) -> List[Dict[str, Any]]:
        """Get content by status from files (fallback)"""
        try:
            content = []
            metadata_dir = Path(self.path_manager.get_path(PathType.METADATA, "")).parent
            
            for metadata_file in metadata_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    if metadata.get('status') == status:
                        content.append({
                            'uid': metadata.get('uid'),
                            'title': metadata.get('title', 'Untitled'),
                            'content_type': metadata.get('content_type'),
                            'source': metadata.get('source', ''),
                            'status': metadata.get('status'),
                            'error': metadata.get('error'),
                            'created_at': metadata.get('created_at')
                        })
                        
                except Exception:
                    continue
            
            return content
            
        except Exception as e:
            log_error(f"Error getting content by status from files: {e}")
            return []
    
    def close(self):
        """Close database connections"""
        if self.database_enabled and hasattr(self, 'db'):
            self.db.close()

# Global instance for easy access
_global_atlas_db: Optional[AtlasDatabaseManager] = None

def get_atlas_database_manager(db_path: str = None, enable_database: bool = True) -> AtlasDatabaseManager:
    """
    Get global Atlas database manager instance
    
    Args:
        db_path: Database path (only used on first call)
        enable_database: Whether to enable database features
        
    Returns:
        AtlasDatabaseManager instance
    """
    global _global_atlas_db
    
    if _global_atlas_db is None:
        _global_atlas_db = AtlasDatabaseManager(
            db_path=db_path or "atlas_unified.db",
            enable_database=enable_database
        )
    
    return _global_atlas_db

def close_global_atlas_database():
    """Close global Atlas database manager"""
    global _global_atlas_db
    
    if _global_atlas_db:
        _global_atlas_db.close()
        _global_atlas_db = None