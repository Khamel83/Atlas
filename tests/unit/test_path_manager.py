
import os
import pytest
from pathlib import Path
from helpers.path_manager import PathManager, PathType, ContentType

@pytest.fixture
def config():
    return {
        "data_directory": "output",
        "article_output_path": "output/articles",
        "podcast_output_path": "output/podcasts",
        "youtube_output_path": "output/youtube",
    }

@pytest.fixture
def path_manager(config):
    return PathManager(config)

def test_get_base_directory(path_manager):
    assert path_manager.get_base_directory(ContentType.ARTICLE) == "output/articles"
    assert path_manager.get_base_directory(ContentType.PODCAST) == "output/podcasts"
    assert path_manager.get_base_directory(ContentType.YOUTUBE) == "output/youtube"

def test_get_path_set(path_manager):
    path_set = path_manager.get_path_set(ContentType.ARTICLE, "test_uid")
    assert path_set.uid == "test_uid"
    assert path_set.content_type == ContentType.ARTICLE
    assert path_set.base_dir == "output/articles"
    assert path_set.get_path(PathType.METADATA) == "output/articles/metadata/test_uid.json"
    assert path_set.get_path(PathType.MARKDOWN) == "output/articles/markdown/test_uid.md"
    assert path_set.get_path(PathType.HTML) == "output/articles/html/test_uid.html"
    assert path_set.get_path(PathType.LOG) == "output/articles/ingest.log"

def test_get_single_path(path_manager):
    path = path_manager.get_single_path(ContentType.ARTICLE, "test_uid", PathType.METADATA)
    assert path == "output/articles/metadata/test_uid.json"

def test_ensure_directories(path_manager, tmp_path):
    path_manager.data_directory = str(tmp_path)
    path_manager.type_directories[ContentType.ARTICLE] = str(tmp_path / "articles")
    assert path_manager.ensure_directories(ContentType.ARTICLE, "test_uid")
    assert (tmp_path / "articles" / "metadata").exists()
    assert (tmp_path / "articles" / "markdown").exists()
    assert (tmp_path / "articles" / "html").exists()

def test_get_log_path(path_manager):
    assert path_manager.get_log_path(ContentType.ARTICLE) == "output/articles/ingest.log"

def test_get_evaluation_path(path_manager):
    assert path_manager.get_evaluation_path(ContentType.ARTICLE, "test_uid") == "evaluation/article/test_uid.eval.json"

def test_get_temp_path(path_manager, tmp_path):
    path_manager.data_directory = str(tmp_path)
    path_manager.type_directories[ContentType.ARTICLE] = str(tmp_path / "articles")
    temp_path = path_manager.get_temp_path(ContentType.ARTICLE, "test_uid", ".tmp")
    assert temp_path == str(tmp_path / "articles" / "temp" / "test_uid.tmp")
    assert (tmp_path / "articles" / "temp").exists()

def test_cleanup_temp_files(path_manager, tmp_path):
    path_manager.data_directory = str(tmp_path)
    path_manager.type_directories[ContentType.ARTICLE] = str(tmp_path / "articles")
    temp_dir = tmp_path / "articles" / "temp"
    temp_dir.mkdir(parents=True)
    (temp_dir / "test_uid.tmp").touch()
    assert path_manager.cleanup_temp_files(ContentType.ARTICLE, "test_uid")
    assert not (temp_dir / "test_uid.tmp").exists()

def test_get_relative_path(path_manager):
    abs_path = os.path.abspath("output/articles/markdown/test_uid.md")
    rel_path = path_manager.get_relative_path(abs_path)
    assert rel_path == "articles/markdown/test_uid.md"

def test_get_absolute_path(path_manager):
    rel_path = "articles/markdown/test_uid.md"
    abs_path = path_manager.get_absolute_path(rel_path)
    assert abs_path == os.path.abspath("output/articles/markdown/test_uid.md")

def test_validate_path(path_manager):
    assert path_manager.validate_path("output/articles/markdown/test_uid.md")
    assert not path_manager.validate_path("../../../etc/passwd")
