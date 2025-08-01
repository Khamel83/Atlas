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
