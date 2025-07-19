"""
Metadata Manager Module

This module provides standardized metadata structures and management utilities
for all Atlas ingestors, ensuring consistent metadata handling across the system.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from helpers.dedupe import link_uid
from helpers.utils import calculate_hash


class ContentType(Enum):
    """Supported content types in Atlas."""
    ARTICLE = "article"
    PODCAST = "podcast"
    YOUTUBE = "youtube"
    INSTAPAPER = "instapaper"


class ProcessingStatus(Enum):
    """Processing status for content items."""
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    ERROR = "error"
    RETRY = "retry"
    SKIPPED = "skipped"


@dataclass
class FetchAttempt:
    """Represents a single fetch attempt."""
    method: str
    timestamp: str
    result: str  # "success", "failed", "pending"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchDetails:
    """Detailed information about fetch attempts."""
    attempts: List[FetchAttempt] = field(default_factory=list)
    successful_method: Optional[str] = None
    is_truncated: bool = False
    total_attempts: int = 0
    fetch_time: Optional[float] = None
    
    def add_attempt(self, method: str, result: str, error: str = None, metadata: Dict[str, Any] = None):
        """Add a new fetch attempt."""
        attempt = FetchAttempt(
            method=method,
            timestamp=datetime.now().isoformat(),
            result=result,
            error=error,
            metadata=metadata or {}
        )
        self.attempts.append(attempt)
        self.total_attempts += 1
        
        if result == "success":
            self.successful_method = method


@dataclass
class ContentMetadata:
    """Standardized metadata structure for all content types."""
    # Core identification
    uid: str
    content_type: ContentType
    source: str  # URL or source identifier
    title: Optional[str] = None
    
    # Processing information
    status: ProcessingStatus = ProcessingStatus.PENDING
    date: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    
    # File paths (relative to data directory)
    content_path: Optional[str] = None
    html_path: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_path: Optional[str] = None
    
    # Content analysis
    tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    # Fetch details
    fetch_method: str = "unknown"
    fetch_details: FetchDetails = field(default_factory=FetchDetails)
    
    # Categorization metadata
    category_version: Optional[str] = None
    last_tagged_at: Optional[str] = None
    source_hash: Optional[str] = None
    
    # Type-specific metadata
    type_specific: Dict[str, Any] = field(default_factory=dict)
    
    # Processing timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()
    
    def add_tag(self, tag: str):
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.update_timestamp()
    
    def add_note(self, note: str):
        """Add a note."""
        self.notes.append(note)
        self.update_timestamp()
    
    def set_success(self, content_path: str = None):
        """Mark content as successfully processed."""
        self.status = ProcessingStatus.SUCCESS
        self.error = None
        if content_path:
            self.content_path = content_path
        self.update_timestamp()
    
    def set_error(self, error_message: str):
        """Mark content as failed with error."""
        self.status = ProcessingStatus.ERROR
        self.error = error_message
        self.update_timestamp()
    
    def set_retry(self, error_message: str):
        """Mark content for retry."""
        self.status = ProcessingStatus.RETRY
        self.error = error_message
        self.update_timestamp()


class MetadataManager:
    """Manager for content metadata operations."""
    
    def __init__(self, config: Dict[str, Any] = None, metadata_dir: str = None):
        # Support both config dict and direct metadata_dir for test compatibility
        if config is not None:
            self.config = config
            self.data_directory = config.get("data_directory", "output")
        else:
            self.config = {}
            self.data_directory = metadata_dir or "output"
        # For test compatibility
        self.metadata_dir = self.data_directory
        self.metadata_cache = {}
        self.categories = []
    
    def create_metadata(self, 
                       content_type: ContentType, 
                       source: str, 
                       title: str = None,
                       **kwargs) -> ContentMetadata:
        """Create new metadata for content."""
        uid = link_uid(source)
        
        metadata = ContentMetadata(
            uid=uid,
            content_type=content_type,
            source=source,
            title=title,
            **kwargs
        )
        
        return metadata
    
    def load_metadata(self, content_type: ContentType, uid: str) -> Optional[ContentMetadata]:
        """Load existing metadata from file."""
        metadata_path = self.get_metadata_path(content_type, uid)
        
        if not os.path.exists(metadata_path):
            return None
        
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Convert back to proper types
            data["content_type"] = ContentType(data["content_type"])
            data["status"] = ProcessingStatus(data["status"])
            
            # Reconstruct FetchDetails
            if "fetch_details" in data:
                fetch_data = data["fetch_details"]
                attempts = [FetchAttempt(**attempt) for attempt in fetch_data.get("attempts", [])]
                data["fetch_details"] = FetchDetails(
                    attempts=attempts,
                    successful_method=fetch_data.get("successful_method"),
                    is_truncated=fetch_data.get("is_truncated", False),
                    total_attempts=fetch_data.get("total_attempts", 0),
                    fetch_time=fetch_data.get("fetch_time")
                )
            
            return ContentMetadata(**data)
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Handle corrupted metadata gracefully
            return None
    
    def save_metadata(self, metadata: ContentMetadata) -> bool:
        """Save metadata to file."""
        try:
            metadata_path = self.get_metadata_path(metadata.content_type, metadata.uid)
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            
            # Convert to dict for JSON serialization
            data = asdict(metadata)
            
            # Convert enums to strings
            data["content_type"] = metadata.content_type.value
            data["status"] = metadata.status.value
            
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            return False
    
    def get_metadata_path(self, content_type: ContentType, uid: str) -> str:
        """Get the metadata file path for given content type and UID."""
        type_dir = self.get_type_directory(content_type)
        return os.path.join(type_dir, "metadata", f"{uid}.json")
    
    def get_type_directory(self, content_type: ContentType) -> str:
        """Get the base directory for a content type."""
        type_mapping = {
            ContentType.ARTICLE: self.config.get("article_output_path", os.path.join(self.data_directory, "articles")),
            ContentType.PODCAST: self.config.get("podcast_output_path", os.path.join(self.data_directory, "podcasts")),
            ContentType.YOUTUBE: self.config.get("youtube_output_path", os.path.join(self.data_directory, "youtube")),
            ContentType.INSTAPAPER: self.config.get("article_output_path", os.path.join(self.data_directory, "articles"))
        }
        return type_mapping[content_type]
    
    def exists(self, content_type: ContentType, uid: str) -> bool:
        """Check if metadata exists for given content."""
        metadata_path = self.get_metadata_path(content_type, uid)
        return os.path.exists(metadata_path)
    
    def get_content_paths(self, content_type: ContentType, uid: str) -> Dict[str, str]:
        """Get standard file paths for content type."""
        type_dir = self.get_type_directory(content_type)
        
        paths = {
            "metadata": os.path.join(type_dir, "metadata", f"{uid}.json"),
            "markdown": os.path.join(type_dir, "markdown", f"{uid}.md"),
            "log": os.path.join(type_dir, "ingest.log")
        }
        
        # Add type-specific paths
        if content_type == ContentType.ARTICLE:
            paths["html"] = os.path.join(type_dir, "html", f"{uid}.html")
        elif content_type == ContentType.PODCAST:
            paths["audio"] = os.path.join(type_dir, "audio", f"{uid}.mp3")
            paths["transcript"] = os.path.join(type_dir, "transcripts", f"{uid}.txt")
        elif content_type == ContentType.YOUTUBE:
            paths["video"] = os.path.join(type_dir, "videos", f"{uid}.mp4")
            paths["transcript"] = os.path.join(type_dir, "transcripts", f"{uid}.txt")
        
        return paths
    
    def update_categorization(self, 
                            metadata: ContentMetadata, 
                            tier_1_categories: List[str], 
                            tier_2_sub_tags: List[str],
                            category_version: str = "v1.0") -> bool:
        """Update categorization metadata."""
        # Clear existing tags and add new ones
        metadata.tags = []
        metadata.tags.extend(tier_1_categories)
        metadata.tags.extend(tier_2_sub_tags)
        
        # Update categorization metadata
        metadata.category_version = category_version
        metadata.last_tagged_at = datetime.now().isoformat()
        
        # Calculate source hash if content path exists
        if metadata.content_path and os.path.exists(metadata.content_path):
            metadata.source_hash = calculate_hash(metadata.content_path)
        
        metadata.update_timestamp()
        return self.save_metadata(metadata)
    
    def get_all_metadata(self, content_type: ContentType) -> List[ContentMetadata]:
        """Get all metadata for a content type."""
        type_dir = self.get_type_directory(content_type)
        metadata_dir = os.path.join(type_dir, "metadata")
        
        if not os.path.exists(metadata_dir):
            return []
        
        metadata_list = []
        for filename in os.listdir(metadata_dir):
            if filename.endswith(".json"):
                uid = filename[:-5]  # Remove .json extension
                metadata = self.load_metadata(content_type, uid)
                if metadata:
                    metadata_list.append(metadata)
        
        return metadata_list
    
    def get_failed_items(self, content_type: ContentType) -> List[ContentMetadata]:
        """Get all failed items for a content type."""
        all_metadata = self.get_all_metadata(content_type)
        return [m for m in all_metadata if m.status == ProcessingStatus.ERROR]
    
    def get_retry_items(self, content_type: ContentType) -> List[ContentMetadata]:
        """Get all items marked for retry."""
        all_metadata = self.get_all_metadata(content_type)
        return [m for m in all_metadata if m.status == ProcessingStatus.RETRY]
    
    def cleanup_old_metadata(self, content_type: ContentType, days_old: int = 30):
        """Clean up metadata older than specified days."""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        all_metadata = self.get_all_metadata(content_type)
        
        for metadata in all_metadata:
            created_date = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))
            if created_date < cutoff_date and metadata.status == ProcessingStatus.ERROR:
                # Remove old failed items
                metadata_path = self.get_metadata_path(content_type, metadata.uid)
                try:
                    os.remove(metadata_path)
                except OSError:
                    pass

    def get_forgotten_content(self, cutoff_days: int = 30) -> List[ContentMetadata]:
        """
        Return content items (all types) not updated in the last cutoff_days.
        Sorted by updated_at ascending (oldest first).
        """
        from datetime import datetime, timedelta
        forgotten = []
        cutoff = datetime.now() - timedelta(days=cutoff_days)
        for content_type in ContentType:
            all_meta = self.get_all_metadata(content_type)
            for meta in all_meta:
                try:
                    updated = datetime.fromisoformat(meta.updated_at.replace('Z', '+00:00'))
                    if updated < cutoff:
                        forgotten.append(meta)
                except Exception:
                    continue
        forgotten.sort(key=lambda m: m.updated_at)
        return forgotten


def create_metadata_manager(config: Dict[str, Any]) -> MetadataManager:
    """Factory function to create metadata manager."""
    return MetadataManager(config)


# Convenience functions for common operations
def create_article_metadata(source: str, title: str, config: Dict[str, Any]) -> ContentMetadata:
    """Create metadata for an article."""
    manager = create_metadata_manager(config)
    return manager.create_metadata(ContentType.ARTICLE, source, title)


def create_podcast_metadata(source: str, title: str, config: Dict[str, Any], **kwargs) -> ContentMetadata:
    """Create metadata for a podcast episode."""
    manager = create_metadata_manager(config)
    return manager.create_metadata(ContentType.PODCAST, source, title, **kwargs)


def create_youtube_metadata(source: str, title: str, config: Dict[str, Any], **kwargs) -> ContentMetadata:
    """Create metadata for a YouTube video."""
    manager = create_metadata_manager(config)
    return manager.create_metadata(ContentType.YOUTUBE, source, title, **kwargs) 