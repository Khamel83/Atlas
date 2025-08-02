import os
from pathlib import Path

import pytest

from helpers.path_manager import ContentType, PathManager, PathType


@pytest.fixture
def config(tmp_path):
    return {
        "data_directory": str(tmp_path),
        "article_output_path": os.path.join(str(tmp_path), "articles"),
        "podcast_output_path": os.path.join(str(tmp_path), "podcasts"),
        "youtube_output_path": os.path.join(str(tmp_path), "youtube"),
    }


@pytest.fixture
def path_manager(config):
    return PathManager(config)


def test_get_base_directory(path_manager, tmp_path):
    assert path_manager.get_base_directory(ContentType.ARTICLE) == os.path.join(
        str(tmp_path), "articles"
    )
    assert path_manager.get_base_directory(ContentType.PODCAST) == os.path.join(
        str(tmp_path), "podcasts"
    )
    assert path_manager.get_base_directory(ContentType.YOUTUBE) == os.path.join(
        str(tmp_path), "youtube"
    )


def test_get_path_set(path_manager, tmp_path):
    path_set = path_manager.get_path_set(ContentType.ARTICLE, "test_uid")
    assert path_set.uid == "test_uid"
    assert path_set.content_type == ContentType.ARTICLE
    assert path_set.base_dir == os.path.join(str(tmp_path), "articles")
    assert path_set.get_path(PathType.METADATA) == os.path.join(
        str(tmp_path), "articles", "metadata", "test_uid.json"
    )
    assert path_set.get_path(PathType.MARKDOWN) == os.path.join(
        str(tmp_path), "articles", "markdown", "test_uid.md"
    )
    assert path_set.get_path(PathType.HTML) == os.path.join(
        str(tmp_path), "articles", "html", "test_uid.html"
    )
    assert path_set.get_path(PathType.LOG) == os.path.join(
        str(tmp_path), "articles", "ingest.log"
    )


def test_get_path_set_podcast(path_manager, tmp_path):
    path_set = path_manager.get_path_set(ContentType.PODCAST, "test_uid")
    assert path_set.uid == "test_uid"
    assert path_set.content_type == ContentType.PODCAST
    assert path_set.base_dir == os.path.join(str(tmp_path), "podcasts")
    assert path_set.get_path(PathType.METADATA) == os.path.join(
        str(tmp_path), "podcasts", "metadata", "test_uid.json"
    )
    assert path_set.get_path(PathType.MARKDOWN) == os.path.join(
        str(tmp_path), "podcasts", "markdown", "test_uid.md"
    )
    assert path_set.get_path(PathType.AUDIO) == os.path.join(
        str(tmp_path), "podcasts", "audio", "test_uid.mp3"
    )
    assert path_set.get_path(PathType.TRANSCRIPT) == os.path.join(
        str(tmp_path), "podcasts", "transcripts", "test_uid.txt"
    )


def test_get_path_set_youtube(path_manager, tmp_path):
    path_set = path_manager.get_path_set(ContentType.YOUTUBE, "test_uid")
    assert path_set.uid == "test_uid"
    assert path_set.content_type == ContentType.YOUTUBE
    assert path_set.base_dir == os.path.join(str(tmp_path), "youtube")
    assert path_set.get_path(PathType.METADATA) == os.path.join(
        str(tmp_path), "youtube", "metadata", "test_uid.json"
    )
    assert path_set.get_path(PathType.MARKDOWN) == os.path.join(
        str(tmp_path), "youtube", "markdown", "test_uid.md"
    )
    assert path_set.get_path(PathType.VIDEO) == os.path.join(
        str(tmp_path), "youtube", "videos", "test_uid.mp4"
    )
    assert path_set.get_path(PathType.TRANSCRIPT) == os.path.join(
        str(tmp_path), "youtube", "transcripts", "test_uid.txt"
    )


def test_get_single_path(path_manager, tmp_path):
    metadata_path = path_manager.get_single_path(
        ContentType.ARTICLE, "test_uid", PathType.METADATA
    )
    assert metadata_path == os.path.join(
        str(tmp_path), "articles", "metadata", "test_uid.json"
    )
    
    # Test non-existent path type
    assert path_manager.get_single_path(
        ContentType.ARTICLE, "test_uid", PathType.AUDIO
    ) is None


def test_ensure_directories(path_manager, tmp_path):
    # Test ensuring directories for a content type
    assert path_manager.ensure_directories(ContentType.ARTICLE)
    
    # Check that directories were created
    assert os.path.exists(os.path.join(str(tmp_path), "articles", "metadata"))
    assert os.path.exists(os.path.join(str(tmp_path), "articles", "markdown"))
    assert os.path.exists(os.path.join(str(tmp_path), "articles", "html"))
    
    # Test ensuring directories with specific UID
    assert path_manager.ensure_directories(ContentType.PODCAST, "test_uid")
    assert os.path.exists(os.path.join(str(tmp_path), "podcasts", "metadata"))
    assert os.path.exists(os.path.join(str(tmp_path), "podcasts", "audio"))
    assert os.path.exists(os.path.join(str(tmp_path), "podcasts", "transcripts"))


def test_get_log_path(path_manager, tmp_path):
    log_path = path_manager.get_log_path(ContentType.ARTICLE)
    assert log_path == os.path.join(str(tmp_path), "articles", "ingest.log")
    
    log_path = path_manager.get_log_path(ContentType.PODCAST)
    assert log_path == os.path.join(str(tmp_path), "podcasts", "ingest.log")


def test_get_evaluation_path(path_manager):
    eval_path = path_manager.get_evaluation_path(ContentType.ARTICLE, "test_uid")
    assert eval_path == os.path.join("evaluation", "article", "test_uid.eval.json")
    
    eval_path = path_manager.get_evaluation_path(ContentType.PODCAST, "test_uid")
    assert eval_path == os.path.join("evaluation", "podcast", "test_uid.eval.json")


def test_get_temp_path(path_manager, tmp_path):
    temp_path = path_manager.get_temp_path(ContentType.ARTICLE, "test_uid")
    expected_path = os.path.join(str(tmp_path), "articles", "temp", "test_uid")
    assert temp_path == expected_path
    assert os.path.exists(os.path.dirname(temp_path))  # temp dir should be created
    
    # Test with suffix
    temp_path_with_suffix = path_manager.get_temp_path(
        ContentType.ARTICLE, "test_uid", ".tmp"
    )
    expected_path_with_suffix = os.path.join(
        str(tmp_path), "articles", "temp", "test_uid.tmp"
    )
    assert temp_path_with_suffix == expected_path_with_suffix


def test_cleanup_temp_files(path_manager, tmp_path):
    # Create some temp files first
    articles_temp_dir = os.path.join(str(tmp_path), "articles", "temp")
    os.makedirs(articles_temp_dir, exist_ok=True)
    
    # Create test files
    test_file1 = os.path.join(articles_temp_dir, "test_uid_1.tmp")
    test_file2 = os.path.join(articles_temp_dir, "test_uid_2.tmp")
    other_file = os.path.join(articles_temp_dir, "other_file.tmp")
    
    for file_path in [test_file1, test_file2, other_file]:
        with open(file_path, "w") as f:
            f.write("test")
    
    # Test cleanup specific UID files
    assert path_manager.cleanup_temp_files(ContentType.ARTICLE, "test_uid")
    assert not os.path.exists(test_file1)
    assert not os.path.exists(test_file2)
    assert os.path.exists(other_file)  # Should still exist
    
    # Test cleanup all temp files
    assert path_manager.cleanup_temp_files(ContentType.ARTICLE)
    assert os.path.exists(articles_temp_dir)  # Directory recreated
    assert not os.path.exists(other_file)  # Should be gone


def test_get_relative_path(path_manager, tmp_path):
    absolute_path = os.path.join(str(tmp_path), "articles", "test.json")
    relative_path = path_manager.get_relative_path(absolute_path)
    assert relative_path == os.path.join("articles", "test.json")
    
    # Test with path outside data directory - method returns relative path even for outside paths
    outside_path = "/some/other/path/file.txt"
    result = path_manager.get_relative_path(outside_path)
    # The method will return a relative path, not the original absolute path
    assert result.endswith("some/other/path/file.txt")


def test_get_absolute_path(path_manager, tmp_path):
    relative_path = os.path.join("articles", "test.json")
    absolute_path = path_manager.get_absolute_path(relative_path)
    expected_path = os.path.join(str(tmp_path), "articles", "test.json")
    assert absolute_path == expected_path
    
    # Test with already absolute path
    already_absolute = "/absolute/path/file.txt"
    result = path_manager.get_absolute_path(already_absolute)
    assert result == already_absolute


def test_validate_path(path_manager, tmp_path):
    # Valid path within data directory
    valid_path = os.path.join(str(tmp_path), "articles", "test.json")
    assert path_manager.validate_path(valid_path) is True
    
    # Invalid path outside data directory
    invalid_path = "/some/other/path/file.txt"
    assert path_manager.validate_path(invalid_path) is False
    
    # Test relative path that resolves within data directory
    relative_valid = os.path.join(str(tmp_path), "articles", "..", "articles", "test.json")
    assert path_manager.validate_path(relative_valid) is True


def test_get_all_content_paths(path_manager, tmp_path):
    # Create some metadata files
    metadata_dir = os.path.join(str(tmp_path), "articles", "metadata")
    os.makedirs(metadata_dir, exist_ok=True)
    
    # Create test metadata files
    for uid in ["uid1", "uid2", "uid3"]:
        metadata_file = os.path.join(metadata_dir, f"{uid}.json")
        with open(metadata_file, "w") as f:
            f.write('{"title": "test"}')
    
    # Create a non-json file that should be ignored
    with open(os.path.join(metadata_dir, "readme.txt"), "w") as f:
        f.write("readme")
    
    path_sets = path_manager.get_all_content_paths(ContentType.ARTICLE)
    assert len(path_sets) == 3
    
    uids = [ps.uid for ps in path_sets]
    assert "uid1" in uids
    assert "uid2" in uids
    assert "uid3" in uids
    
    # Test with non-existent metadata directory
    path_sets_empty = path_manager.get_all_content_paths(ContentType.YOUTUBE)
    assert len(path_sets_empty) == 0


def test_migrate_paths(path_manager, tmp_path):
    # Create old directory structure
    old_dir = os.path.join(str(tmp_path), "old_articles")
    new_dir = os.path.join(str(tmp_path), "new_articles")
    
    os.makedirs(os.path.join(old_dir, "metadata"), exist_ok=True)
    os.makedirs(os.path.join(old_dir, "markdown"), exist_ok=True)
    
    # Create some test files
    with open(os.path.join(old_dir, "metadata", "test.json"), "w") as f:
        f.write('{"title": "test"}')
    with open(os.path.join(old_dir, "test_file.txt"), "w") as f:
        f.write("test content")
    
    # Test migration
    assert path_manager.migrate_paths(old_dir, new_dir, ContentType.ARTICLE)
    
    # Verify files were copied
    assert os.path.exists(os.path.join(new_dir, "metadata", "test.json"))
    assert os.path.exists(os.path.join(new_dir, "test_file.txt"))
    
    # Verify type directory was updated
    assert path_manager.type_directories[ContentType.ARTICLE] == new_dir
    
    # Test migration with non-existent old directory
    assert path_manager.migrate_paths("/non/existent", "/some/new", ContentType.PODCAST)


def test_get_backup_path(path_manager, tmp_path):
    # Test with provided timestamp
    backup_path = path_manager.get_backup_path(
        ContentType.ARTICLE, "test_uid", "20240101_120000"
    )
    expected_path = os.path.join(
        str(tmp_path), "articles", "backups", "20240101_120000"
    )
    assert backup_path == expected_path
    assert os.path.exists(backup_path)  # Directory should be created
    
    # Test without timestamp (should generate one)
    backup_path_auto = path_manager.get_backup_path(ContentType.ARTICLE, "test_uid")
    assert backup_path_auto.startswith(
        os.path.join(str(tmp_path), "articles", "backups")
    )
    assert os.path.exists(backup_path_auto)


def test_create_backup(path_manager, tmp_path):
    # Create some files to backup
    path_set = path_manager.get_path_set(ContentType.ARTICLE, "test_uid")
    path_set.ensure_directories()
    
    # Create test files
    metadata_path = path_set.get_path(PathType.METADATA)
    markdown_path = path_set.get_path(PathType.MARKDOWN)
    
    with open(metadata_path, "w") as f:
        f.write('{"title": "test"}')
    with open(markdown_path, "w") as f:
        f.write("# Test Article")
    
    # Create backup
    backup_dir = path_manager.create_backup(ContentType.ARTICLE, "test_uid")
    assert backup_dir is not None
    assert os.path.exists(backup_dir)
    
    # Verify backup files exist
    assert os.path.exists(os.path.join(backup_dir, "test_uid.json"))
    assert os.path.exists(os.path.join(backup_dir, "test_uid.md"))
    
    # Verify backup content
    with open(os.path.join(backup_dir, "test_uid.json"), "r") as f:
        assert f.read() == '{"title": "test"}'


# Test PathSet class methods
def test_path_set_ensure_directories(tmp_path):
    from helpers.path_manager import PathSet, PathType
    
    paths = {
        PathType.METADATA: os.path.join(str(tmp_path), "test", "metadata", "test.json"),
        PathType.MARKDOWN: os.path.join(str(tmp_path), "test", "markdown", "test.md"),
    }
    
    path_set = PathSet(
        uid="test_uid",
        content_type=ContentType.ARTICLE,
        base_dir=str(tmp_path),
        paths=paths
    )
    
    assert path_set.ensure_directories() is True
    assert os.path.exists(os.path.join(str(tmp_path), "test", "metadata"))
    assert os.path.exists(os.path.join(str(tmp_path), "test", "markdown"))


def test_path_set_get_path():
    from helpers.path_manager import PathSet, PathType
    
    paths = {
        PathType.METADATA: "/test/metadata.json",
        PathType.MARKDOWN: "/test/markdown.md",
    }
    
    path_set = PathSet(
        uid="test_uid",
        content_type=ContentType.ARTICLE,
        base_dir="/test",
        paths=paths
    )
    
    assert path_set.get_path(PathType.METADATA) == "/test/metadata.json"
    assert path_set.get_path(PathType.MARKDOWN) == "/test/markdown.md"
    assert path_set.get_path(PathType.AUDIO) is None  # Not in paths


# Test convenience functions
def test_create_path_manager(tmp_path):
    from helpers.path_manager import create_path_manager
    
    config = {"data_directory": str(tmp_path)}
    manager = create_path_manager(config)
    assert isinstance(manager, PathManager)
    assert manager.data_directory == str(tmp_path)


def test_get_content_paths(tmp_path):
    from helpers.path_manager import get_content_paths
    
    config = {"data_directory": str(tmp_path)}
    path_set = get_content_paths(ContentType.ARTICLE, "test_uid", config)
    assert path_set.uid == "test_uid"
    assert path_set.content_type == ContentType.ARTICLE


def test_ensure_content_directories(tmp_path):
    from helpers.path_manager import ensure_content_directories
    
    config = {"data_directory": str(tmp_path)}
    assert ensure_content_directories(ContentType.ARTICLE, config) is True
    assert os.path.exists(os.path.join(str(tmp_path), "articles", "metadata"))


def test_get_log_path_convenience(tmp_path):
    from helpers.path_manager import get_log_path
    
    config = {"data_directory": str(tmp_path)}
    log_path = get_log_path(ContentType.ARTICLE, config)
    assert log_path == os.path.join(str(tmp_path), "articles", "ingest.log")


# Test edge cases and error conditions
def test_path_manager_with_custom_config(tmp_path):
    custom_config = {
        "data_directory": str(tmp_path),
        "article_output_path": os.path.join(str(tmp_path), "custom_articles"),
        "podcast_output_path": os.path.join(str(tmp_path), "custom_podcasts"),
        "youtube_output_path": os.path.join(str(tmp_path), "custom_youtube"),
    }
    
    manager = PathManager(custom_config)
    assert manager.get_base_directory(ContentType.ARTICLE) == os.path.join(str(tmp_path), "custom_articles")
    assert manager.get_base_directory(ContentType.PODCAST) == os.path.join(str(tmp_path), "custom_podcasts")
    assert manager.get_base_directory(ContentType.YOUTUBE) == os.path.join(str(tmp_path), "custom_youtube")


def test_instapaper_content_type(path_manager, tmp_path):
    # INSTAPAPER should use article output path 
    base_dir = path_manager.get_base_directory(ContentType.INSTAPAPER)
    assert base_dir == os.path.join(str(tmp_path), "articles")


def test_path_normalization(path_manager, tmp_path):
    # Test that paths are properly normalized
    path_set = path_manager.get_path_set(ContentType.ARTICLE, "test_uid")
    for path in path_set.paths.values():
        assert ".." not in path  # No relative path components
        assert os.path.normpath(path) == path  # Already normalized


def test_path_set_ensure_directories_failure():
    from helpers.path_manager import PathSet, PathType
    from unittest.mock import patch
    
    paths = {
        PathType.METADATA: "/invalid/path/metadata.json",
    }
    
    path_set = PathSet(
        uid="test_uid",
        content_type=ContentType.ARTICLE,
        base_dir="/invalid",
        paths=paths
    )
    
    # Mock os.makedirs to raise OSError
    with patch('os.makedirs', side_effect=OSError("Permission denied")):
        assert path_set.ensure_directories() is False


def test_ensure_directories_failure(path_manager):
    from unittest.mock import patch
    
    # Mock os.makedirs to raise OSError
    with patch('os.makedirs', side_effect=OSError("Permission denied")):
        assert path_manager.ensure_directories(ContentType.ARTICLE) is False


def test_cleanup_temp_files_failure(path_manager, tmp_path):
    from unittest.mock import patch
    
    # Create temp directory first
    temp_dir = os.path.join(str(tmp_path), "articles", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Test cleanup failure - need to patch the actual failure point
    with patch('os.remove', side_effect=OSError("Permission denied")):
        # Create a file that matches the UID pattern
        test_file = os.path.join(temp_dir, "test_uid_1.tmp")
        with open(test_file, "w") as f:
            f.write("test")
        assert path_manager.cleanup_temp_files(ContentType.ARTICLE, "test_uid") is False


def test_migrate_paths_failure(path_manager, tmp_path):
    from unittest.mock import patch
    
    old_dir = os.path.join(str(tmp_path), "old")
    new_dir = os.path.join(str(tmp_path), "new")
    os.makedirs(old_dir, exist_ok=True)
    
    # Create a subdirectory to trigger copytree
    sub_dir = os.path.join(old_dir, "subdir")
    os.makedirs(sub_dir, exist_ok=True)
    
    # Mock shutil operations to fail - patch the global shutil module
    with patch('shutil.copytree', side_effect=OSError("Permission denied")):
        assert path_manager.migrate_paths(old_dir, new_dir, ContentType.ARTICLE) is False


def test_create_backup_failure(path_manager, tmp_path):
    from unittest.mock import patch
    
    # Create files to backup first
    path_set = path_manager.get_path_set(ContentType.ARTICLE, "test_uid")
    path_set.ensure_directories()
    
    # Create test file to backup
    metadata_path = path_set.get_path(PathType.METADATA)
    with open(metadata_path, "w") as f:
        f.write('{"title": "test"}')
    
    # Mock shutil operations to fail - patch the global shutil module
    with patch('shutil.copy2', side_effect=OSError("Permission denied")):
        result = path_manager.create_backup(ContentType.ARTICLE, "test_uid")
        assert result is None
