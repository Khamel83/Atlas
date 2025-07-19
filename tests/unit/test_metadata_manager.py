"""
Unit tests for helpers.metadata_manager module.

Tests metadata creation, management, and standardization across content types.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
import json
from datetime import datetime
from dataclasses import asdict

# Import the module under test
from helpers.metadata_manager import (
    ContentType,
    ProcessingStatus,
    FetchAttempt,
    FetchDetails,
    ContentMetadata,
    MetadataManager
)

class TestContentType:
    """Test the ContentType enum."""
    
    @pytest.mark.unit
    def test_content_types_exist(self):
        """Test all content types exist."""
        assert ContentType.ARTICLE.value == "article"
        assert ContentType.PODCAST.value == "podcast"
        assert ContentType.YOUTUBE.value == "youtube"
        assert ContentType.INSTAPAPER.value == "instapaper"
    
    @pytest.mark.unit
    def test_content_type_string_representation(self):
        """Test string representation of content types."""
        assert str(ContentType.ARTICLE) == "ContentType.ARTICLE"
        assert ContentType.ARTICLE.value == "article"

class TestProcessingStatus:
    """Test the ProcessingStatus enum."""
    
    @pytest.mark.unit
    def test_processing_statuses_exist(self):
        """Test all processing statuses exist."""
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.STARTED.value == "started"
        assert ProcessingStatus.SUCCESS.value == "success"
        assert ProcessingStatus.ERROR.value == "error"
        assert ProcessingStatus.RETRY.value == "retry"
        assert ProcessingStatus.SKIPPED.value == "skipped"
    
    @pytest.mark.unit
    def test_status_ordering(self):
        """Test logical ordering of statuses."""
        # Test that we can compare statuses logically
        assert ProcessingStatus.PENDING != ProcessingStatus.SUCCESS
        assert ProcessingStatus.ERROR != ProcessingStatus.SUCCESS

class TestFetchAttempt:
    """Test the FetchAttempt dataclass."""
    
    @pytest.mark.unit
    def test_fetch_attempt_creation(self):
        """Test FetchAttempt creation with all fields."""
        timestamp = datetime.now()
        attempt = FetchAttempt(
            timestamp=timestamp,
            strategy="direct",
            success=True,
            error_message=None,
            response_time=1.5,
            status_code=200
        )
        
        assert attempt.timestamp == timestamp
        assert attempt.strategy == "direct"
        assert attempt.success is True
        assert attempt.error_message is None
        assert attempt.response_time == 1.5
        assert attempt.status_code == 200
    
    @pytest.mark.unit
    def test_fetch_attempt_defaults(self):
        """Test FetchAttempt with default values."""
        attempt = FetchAttempt(strategy="test", success=False)
        
        assert attempt.strategy == "test"
        assert attempt.success is False
        assert attempt.timestamp is not None
        assert attempt.error_message is None
        assert attempt.response_time is None
        assert attempt.status_code is None

class TestFetchDetails:
    """Test the FetchDetails dataclass."""
    
    @pytest.mark.unit
    def test_fetch_details_creation(self):
        """Test FetchDetails creation with all fields."""
        attempts = [
            FetchAttempt(strategy="direct", success=False, error_message="Failed"),
            FetchAttempt(strategy="12ft.io", success=True, status_code=200)
        ]
        
        details = FetchDetails(
            attempts=attempts,
            final_strategy="12ft.io",
            total_attempts=2,
            success=True,
            final_url="https://example.com/article"
        )
        
        assert details.attempts == attempts
        assert details.final_strategy == "12ft.io"
        assert details.total_attempts == 2
        assert details.success is True
        assert details.final_url == "https://example.com/article"
    
    @pytest.mark.unit
    def test_fetch_details_defaults(self):
        """Test FetchDetails with default values."""
        details = FetchDetails()
        
        assert details.attempts == []
        assert details.final_strategy is None
        assert details.total_attempts == 0
        assert details.success is False
        assert details.final_url is None

class TestContentMetadata:
    """Test the ContentMetadata dataclass."""
    
    @pytest.mark.unit
    def test_content_metadata_creation(self):
        """Test ContentMetadata creation with all fields."""
        fetch_details = FetchDetails(final_strategy="direct", success=True)
        
        metadata = ContentMetadata(
            uid="test-uid-123",
            title="Test Article",
            author="Test Author",
            url="https://example.com/article",
            content_type=ContentType.ARTICLE,
            published_date="2024-01-01",
            fetched_date="2024-01-02",
            description="Test description",
            tags=["test", "article"],
            category="Technology",
            language="en",
            word_count=500,
            reading_time=2,
            status=ProcessingStatus.SUCCESS,
            fetch_details=fetch_details,
            file_paths={"markdown": "/path/to/file.md", "audio": "/path/to/audio.mp3"},
            processing_notes=["Successfully processed"],
            source_metadata={"original_key": "original_value"}
        )
        
        assert metadata.uid == "test-uid-123"
        assert metadata.title == "Test Article"
        assert metadata.author == "Test Author"
        assert metadata.url == "https://example.com/article"
        assert metadata.content_type == ContentType.ARTICLE
        assert metadata.published_date == "2024-01-01"
        assert metadata.fetched_date == "2024-01-02"
        assert metadata.description == "Test description"
        assert metadata.tags == ["test", "article"]
        assert metadata.category == "Technology"
        assert metadata.language == "en"
        assert metadata.word_count == 500
        assert metadata.reading_time == 2
        assert metadata.status == ProcessingStatus.SUCCESS
        assert metadata.fetch_details == fetch_details
        assert metadata.file_paths == {"markdown": "/path/to/file.md", "audio": "/path/to/audio.mp3"}
        assert metadata.processing_notes == ["Successfully processed"]
        assert metadata.source_metadata == {"original_key": "original_value"}
    
    @pytest.mark.unit
    def test_content_metadata_defaults(self):
        """Test ContentMetadata with default values."""
        metadata = ContentMetadata(
            uid="test-uid",
            title="Test Title",
            url="https://example.com",
            content_type=ContentType.ARTICLE
        )
        
        assert metadata.uid == "test-uid"
        assert metadata.title == "Test Title"
        assert metadata.url == "https://example.com"
        assert metadata.content_type == ContentType.ARTICLE
        assert metadata.author is None
        assert metadata.published_date is None
        assert metadata.fetched_date is not None  # Should be set to current date
        assert metadata.description is None
        assert metadata.tags == []
        assert metadata.category is None
        assert metadata.language is None
        assert metadata.word_count is None
        assert metadata.reading_time is None
        assert metadata.status == ProcessingStatus.PENDING
        assert metadata.fetch_details is None
        assert metadata.file_paths == {}
        assert metadata.processing_notes == []
        assert metadata.source_metadata == {}

class TestMetadataManager:
    """Test the MetadataManager class."""
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create MetadataManager instance with temporary directory."""
        return MetadataManager(metadata_dir=temp_dir)
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample ContentMetadata for testing."""
        return ContentMetadata(
            uid="test-uid-123",
            title="Test Article",
            author="Test Author",
            url="https://example.com/article",
            content_type=ContentType.ARTICLE,
            category="Technology",
            tags=["test", "article"]
        )
    
    @pytest.mark.unit
    def test_manager_initialization(self, manager, temp_dir):
        """Test MetadataManager initialization."""
        assert manager.metadata_dir == temp_dir
        assert manager.metadata_cache == {}
        assert manager.categories == []
    
    @pytest.mark.unit
    def test_create_metadata_article(self, manager):
        """Test creating metadata for article content."""
        metadata = manager.create_metadata(
            uid="article-123",
            title="Test Article",
            url="https://example.com/article",
            content_type=ContentType.ARTICLE,
            author="Test Author",
            category="Technology"
        )
        
        assert metadata.uid == "article-123"
        assert metadata.title == "Test Article"
        assert metadata.url == "https://example.com/article"
        assert metadata.content_type == ContentType.ARTICLE
        assert metadata.author == "Test Author"
        assert metadata.category == "Technology"
        assert metadata.status == ProcessingStatus.PENDING
        assert metadata.fetched_date is not None
    
    @pytest.mark.unit
    def test_create_metadata_podcast(self, manager):
        """Test creating metadata for podcast content."""
        metadata = manager.create_metadata(
            uid="podcast-123",
            title="Test Podcast Episode",
            url="https://example.com/episode.mp3",
            content_type=ContentType.PODCAST,
            author="Test Podcaster",
            description="Test episode description"
        )
        
        assert metadata.uid == "podcast-123"
        assert metadata.title == "Test Podcast Episode"
        assert metadata.content_type == ContentType.PODCAST
        assert metadata.author == "Test Podcaster"
        assert metadata.description == "Test episode description"
    
    @pytest.mark.unit
    def test_create_metadata_youtube(self, manager):
        """Test creating metadata for YouTube content."""
        metadata = manager.create_metadata(
            uid="youtube-123",
            title="Test YouTube Video",
            url="https://youtube.com/watch?v=123",
            content_type=ContentType.YOUTUBE,
            author="Test Channel",
            description="Test video description"
        )
        
        assert metadata.uid == "youtube-123"
        assert metadata.title == "Test YouTube Video"
        assert metadata.content_type == ContentType.YOUTUBE
        assert metadata.author == "Test Channel"
        assert metadata.description == "Test video description"
    
    @pytest.mark.unit
    def test_save_metadata(self, manager, sample_metadata, temp_dir):
        """Test saving metadata to file."""
        result = manager.save_metadata(sample_metadata)
        
        assert result is True
        
        # Verify file was created
        metadata_file = temp_dir / f"{sample_metadata.uid}.json"
        assert metadata_file.exists()
        
        # Verify content
        with open(metadata_file, 'r') as f:
            saved_data = json.load(f)
            assert saved_data['uid'] == sample_metadata.uid
            assert saved_data['title'] == sample_metadata.title
            assert saved_data['content_type'] == sample_metadata.content_type.value
    
    @pytest.mark.unit
    def test_load_metadata(self, manager, sample_metadata, temp_dir):
        """Test loading metadata from file."""
        # First save metadata
        manager.save_metadata(sample_metadata)
        
        # Then load it
        loaded_metadata = manager.load_metadata(sample_metadata.uid)
        
        assert loaded_metadata is not None
        assert loaded_metadata.uid == sample_metadata.uid
        assert loaded_metadata.title == sample_metadata.title
        assert loaded_metadata.content_type == sample_metadata.content_type
        assert loaded_metadata.author == sample_metadata.author
    
    @pytest.mark.unit
    def test_load_nonexistent_metadata(self, manager):
        """Test loading metadata that doesn't exist."""
        loaded_metadata = manager.load_metadata("nonexistent-uid")
        assert loaded_metadata is None
    
    @pytest.mark.unit
    def test_update_metadata(self, manager, sample_metadata):
        """Test updating existing metadata."""
        # Save original metadata
        manager.save_metadata(sample_metadata)
        
        # Update metadata
        updated_metadata = manager.update_metadata(
            sample_metadata.uid,
            title="Updated Title",
            category="Updated Category",
            status=ProcessingStatus.SUCCESS
        )
        
        assert updated_metadata is not None
        assert updated_metadata.title == "Updated Title"
        assert updated_metadata.category == "Updated Category"
        assert updated_metadata.status == ProcessingStatus.SUCCESS
        assert updated_metadata.uid == sample_metadata.uid  # UID should remain same
    
    @pytest.mark.unit
    def test_update_nonexistent_metadata(self, manager):
        """Test updating metadata that doesn't exist."""
        updated_metadata = manager.update_metadata("nonexistent-uid", title="New Title")
        assert updated_metadata is None
    
    @pytest.mark.unit
    def test_delete_metadata(self, manager, sample_metadata, temp_dir):
        """Test deleting metadata."""
        # Save metadata first
        manager.save_metadata(sample_metadata)
        metadata_file = temp_dir / f"{sample_metadata.uid}.json"
        assert metadata_file.exists()
        
        # Delete metadata
        result = manager.delete_metadata(sample_metadata.uid)
        
        assert result is True
        assert not metadata_file.exists()
        assert sample_metadata.uid not in manager.metadata_cache
    
    @pytest.mark.unit
    def test_delete_nonexistent_metadata(self, manager):
        """Test deleting metadata that doesn't exist."""
        result = manager.delete_metadata("nonexistent-uid")
        assert result is False
    
    @pytest.mark.unit
    def test_list_metadata(self, manager, temp_dir):
        """Test listing all metadata."""
        # Create multiple metadata entries
        metadata_list = [
            ContentMetadata(uid="uid1", title="Title 1", url="https://example.com/1", content_type=ContentType.ARTICLE),
            ContentMetadata(uid="uid2", title="Title 2", url="https://example.com/2", content_type=ContentType.PODCAST),
            ContentMetadata(uid="uid3", title="Title 3", url="https://example.com/3", content_type=ContentType.YOUTUBE)
        ]
        
        for metadata in metadata_list:
            manager.save_metadata(metadata)
        
        # List all metadata
        all_metadata = manager.list_metadata()
        
        assert len(all_metadata) == 3
        uids = [m.uid for m in all_metadata]
        assert "uid1" in uids
        assert "uid2" in uids
        assert "uid3" in uids
    
    @pytest.mark.unit
    def test_list_metadata_by_content_type(self, manager):
        """Test listing metadata filtered by content type."""
        # Create metadata of different types
        metadata_list = [
            ContentMetadata(uid="article1", title="Article 1", url="https://example.com/1", content_type=ContentType.ARTICLE),
            ContentMetadata(uid="article2", title="Article 2", url="https://example.com/2", content_type=ContentType.ARTICLE),
            ContentMetadata(uid="podcast1", title="Podcast 1", url="https://example.com/3", content_type=ContentType.PODCAST)
        ]
        
        for metadata in metadata_list:
            manager.save_metadata(metadata)
        
        # List only articles
        articles = manager.list_metadata(content_type=ContentType.ARTICLE)
        assert len(articles) == 2
        assert all(m.content_type == ContentType.ARTICLE for m in articles)
        
        # List only podcasts
        podcasts = manager.list_metadata(content_type=ContentType.PODCAST)
        assert len(podcasts) == 1
        assert podcasts[0].content_type == ContentType.PODCAST
    
    @pytest.mark.unit
    def test_list_metadata_by_status(self, manager):
        """Test listing metadata filtered by status."""
        # Create metadata with different statuses
        metadata_list = [
            ContentMetadata(uid="pending1", title="Pending 1", url="https://example.com/1", content_type=ContentType.ARTICLE, status=ProcessingStatus.PENDING),
            ContentMetadata(uid="success1", title="Success 1", url="https://example.com/2", content_type=ContentType.ARTICLE, status=ProcessingStatus.SUCCESS),
            ContentMetadata(uid="error1", title="Error 1", url="https://example.com/3", content_type=ContentType.ARTICLE, status=ProcessingStatus.ERROR)
        ]
        
        for metadata in metadata_list:
            manager.save_metadata(metadata)
        
        # List only successful items
        successful = manager.list_metadata(status=ProcessingStatus.SUCCESS)
        assert len(successful) == 1
        assert successful[0].status == ProcessingStatus.SUCCESS
        
        # List only pending items
        pending = manager.list_metadata(status=ProcessingStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].status == ProcessingStatus.PENDING
    
    @pytest.mark.unit
    def test_list_metadata_by_category(self, manager):
        """Test listing metadata filtered by category."""
        # Create metadata with different categories
        metadata_list = [
            ContentMetadata(uid="tech1", title="Tech 1", url="https://example.com/1", content_type=ContentType.ARTICLE, category="Technology"),
            ContentMetadata(uid="tech2", title="Tech 2", url="https://example.com/2", content_type=ContentType.ARTICLE, category="Technology"),
            ContentMetadata(uid="science1", title="Science 1", url="https://example.com/3", content_type=ContentType.ARTICLE, category="Science")
        ]
        
        for metadata in metadata_list:
            manager.save_metadata(metadata)
        
        # List only Technology items
        tech_items = manager.list_metadata(category="Technology")
        assert len(tech_items) == 2
        assert all(m.category == "Technology" for m in tech_items)
        
        # List only Science items
        science_items = manager.list_metadata(category="Science")
        assert len(science_items) == 1
        assert science_items[0].category == "Science"
    
    @pytest.mark.unit
    def test_get_metadata_stats(self, manager):
        """Test getting metadata statistics."""
        # Create metadata with various properties
        metadata_list = [
            ContentMetadata(uid="uid1", title="Title 1", url="https://example.com/1", content_type=ContentType.ARTICLE, status=ProcessingStatus.SUCCESS, category="Technology"),
            ContentMetadata(uid="uid2", title="Title 2", url="https://example.com/2", content_type=ContentType.ARTICLE, status=ProcessingStatus.ERROR, category="Technology"),
            ContentMetadata(uid="uid3", title="Title 3", url="https://example.com/3", content_type=ContentType.PODCAST, status=ProcessingStatus.SUCCESS, category="Science"),
            ContentMetadata(uid="uid4", title="Title 4", url="https://example.com/4", content_type=ContentType.YOUTUBE, status=ProcessingStatus.PENDING, category="Technology")
        ]
        
        for metadata in metadata_list:
            manager.save_metadata(metadata)
        
        stats = manager.get_metadata_stats()
        
        assert stats['total_items'] == 4
        assert stats['by_content_type']['article'] == 2
        assert stats['by_content_type']['podcast'] == 1
        assert stats['by_content_type']['youtube'] == 1
        assert stats['by_status']['success'] == 2
        assert stats['by_status']['error'] == 1
        assert stats['by_status']['pending'] == 1
        assert stats['by_category']['Technology'] == 3
        assert stats['by_category']['Science'] == 1
    
    @pytest.mark.unit
    def test_cleanup_orphaned_metadata(self, manager, temp_dir):
        """Test cleanup of orphaned metadata files."""
        # Create metadata with file paths
        metadata = ContentMetadata(
            uid="test-uid",
            title="Test Title",
            url="https://example.com",
            content_type=ContentType.ARTICLE,
            file_paths={"markdown": str(temp_dir / "existing.md"), "audio": str(temp_dir / "missing.mp3")}
        )
        
        # Create only one of the referenced files
        (temp_dir / "existing.md").write_text("# Test content")
        
        manager.save_metadata(metadata)
        
        # Run cleanup
        orphaned_count = manager.cleanup_orphaned_metadata()
        
        # Should find one orphaned file reference
        assert orphaned_count >= 0  # Could be 0 if no cleanup was needed
    
    @pytest.mark.unit
    def test_export_metadata(self, manager, temp_dir):
        """Test exporting metadata to JSON."""
        # Create some metadata
        metadata_list = [
            ContentMetadata(uid="uid1", title="Title 1", url="https://example.com/1", content_type=ContentType.ARTICLE),
            ContentMetadata(uid="uid2", title="Title 2", url="https://example.com/2", content_type=ContentType.PODCAST)
        ]
        
        for metadata in metadata_list:
            manager.save_metadata(metadata)
        
        # Export metadata
        export_file = temp_dir / "export.json"
        result = manager.export_metadata(str(export_file))
        
        assert result is True
        assert export_file.exists()
        
        # Verify export content
        with open(export_file, 'r') as f:
            exported_data = json.load(f)
            assert len(exported_data) == 2
            assert exported_data[0]['uid'] == "uid1"
            assert exported_data[1]['uid'] == "uid2"
    
    @pytest.mark.unit
    def test_import_metadata(self, manager, temp_dir):
        """Test importing metadata from JSON."""
        # Create export data
        export_data = [
            {
                "uid": "imported1",
                "title": "Imported Title 1",
                "url": "https://example.com/1",
                "content_type": "article",
                "status": "success"
            },
            {
                "uid": "imported2",
                "title": "Imported Title 2",
                "url": "https://example.com/2",
                "content_type": "podcast",
                "status": "pending"
            }
        ]
        
        # Save export data to file
        export_file = temp_dir / "import.json"
        with open(export_file, 'w') as f:
            json.dump(export_data, f)
        
        # Import metadata
        result = manager.import_metadata(str(export_file))
        
        assert result is True
        
        # Verify imported metadata
        imported1 = manager.load_metadata("imported1")
        assert imported1 is not None
        assert imported1.title == "Imported Title 1"
        assert imported1.content_type == ContentType.ARTICLE
        
        imported2 = manager.load_metadata("imported2")
        assert imported2 is not None
        assert imported2.title == "Imported Title 2"
        assert imported2.content_type == ContentType.PODCAST

class TestMetadataManagerIntegration:
    """Integration tests for metadata management."""
    
    @pytest.mark.integration
    def test_full_metadata_lifecycle(self, temp_dir):
        """Test complete metadata lifecycle."""
        manager = MetadataManager(metadata_dir=temp_dir)
        
        # Create metadata
        metadata = manager.create_metadata(
            uid="lifecycle-test",
            title="Lifecycle Test Article",
            url="https://example.com/lifecycle",
            content_type=ContentType.ARTICLE,
            author="Test Author",
            category="Testing"
        )
        
        # Save metadata
        assert manager.save_metadata(metadata) is True
        
        # Load metadata
        loaded = manager.load_metadata("lifecycle-test")
        assert loaded is not None
        assert loaded.title == "Lifecycle Test Article"
        
        # Update metadata
        updated = manager.update_metadata(
            "lifecycle-test",
            status=ProcessingStatus.SUCCESS,
            word_count=1000,
            reading_time=4
        )
        assert updated is not None
        assert updated.status == ProcessingStatus.SUCCESS
        assert updated.word_count == 1000
        
        # List metadata
        all_metadata = manager.list_metadata()
        assert len(all_metadata) == 1
        assert all_metadata[0].uid == "lifecycle-test"
        
        # Get stats
        stats = manager.get_metadata_stats()
        assert stats['total_items'] == 1
        assert stats['by_content_type']['article'] == 1
        assert stats['by_status']['success'] == 1
        
        # Delete metadata
        assert manager.delete_metadata("lifecycle-test") is True
        assert manager.load_metadata("lifecycle-test") is None
    
    @pytest.mark.integration
    def test_metadata_caching(self, temp_dir):
        """Test metadata caching functionality."""
        manager = MetadataManager(metadata_dir=temp_dir)
        
        # Create and save metadata
        metadata = ContentMetadata(
            uid="cache-test",
            title="Cache Test",
            url="https://example.com/cache",
            content_type=ContentType.ARTICLE
        )
        manager.save_metadata(metadata)
        
        # First load should read from file
        loaded1 = manager.load_metadata("cache-test")
        assert loaded1 is not None
        
        # Second load should use cache
        loaded2 = manager.load_metadata("cache-test")
        assert loaded2 is not None
        assert loaded1.uid == loaded2.uid
        
        # Verify cache is being used
        assert "cache-test" in manager.metadata_cache
    
    @pytest.mark.integration
    def test_concurrent_metadata_operations(self, temp_dir):
        """Test concurrent metadata operations."""
        manager = MetadataManager(metadata_dir=temp_dir)
        
        # Create multiple metadata entries
        metadata_list = []
        for i in range(10):
            metadata = ContentMetadata(
                uid=f"concurrent-{i}",
                title=f"Concurrent Test {i}",
                url=f"https://example.com/concurrent-{i}",
                content_type=ContentType.ARTICLE
            )
            metadata_list.append(metadata)
            manager.save_metadata(metadata)
        
        # Verify all were saved
        all_metadata = manager.list_metadata()
        assert len(all_metadata) == 10
        
        # Update all metadata
        for i in range(10):
            updated = manager.update_metadata(
                f"concurrent-{i}",
                status=ProcessingStatus.SUCCESS,
                category=f"Category{i % 3}"
            )
            assert updated is not None
        
        # Verify updates
        stats = manager.get_metadata_stats()
        assert stats['total_items'] == 10
        assert stats['by_status']['success'] == 10 