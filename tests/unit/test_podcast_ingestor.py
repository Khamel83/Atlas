import os
import pytest
from unittest.mock import patch, MagicMock
from helpers.podcast_ingestor import PodcastIngestor
from helpers.metadata_manager import ContentType

@pytest.fixture
def dummy_config(tmp_path):
    return {
        "data_directory": str(tmp_path),
        "podcast_output_path": os.path.join(str(tmp_path), "podcasts"),
        "run_transcription": False,
    }

@pytest.fixture
def ingestor(dummy_config):
    return PodcastIngestor(dummy_config)

def test_initialization(ingestor):
    assert ingestor.config is not None
    assert hasattr(ingestor, "error_handler")
    assert hasattr(ingestor, "audio_dir")
    assert hasattr(ingestor, "meta_dir")
    assert hasattr(ingestor, "md_dir")
    assert hasattr(ingestor, "transcript_dir")
    assert hasattr(ingestor, "log_path")

def test_metadata_creation_and_save(ingestor, tmp_path):
    entry = {"title": "Test Podcast", "guid": "test-guid", "enclosures": [MagicMock(href="http://audio.mp3")], "links": []}
    metadata = {"source": "http://feed.url"}
    with patch("helpers.podcast_ingestor.link_uid", return_value="testuid"), \
         patch("helpers.podcast_ingestor.requests.get") as mock_get, \
         patch("helpers.podcast_ingestor.log_info"), \
         patch("helpers.podcast_ingestor.generate_markdown_summary", return_value="# Markdown"), \
         patch("helpers.podcast_ingestor.EvaluationFile"):
        mock_get.return_value.__enter__.return_value.iter_content = lambda chunk_size: [b"audio"]
        mock_get.return_value.__enter__.return_value.raise_for_status = lambda: None
        mock_get.return_value.__enter__.return_value.status_code = 200
        result = ingestor.process_content(entry, metadata)
        assert result is True
        meta_path = os.path.join(ingestor.meta_dir, "testuid.json")
        assert os.path.exists(meta_path)

def test_error_handling_on_missing_audio_url(ingestor):
    entry = {"title": "No Audio", "guid": "test-guid", "enclosures": [], "links": []}
    metadata = {"source": "http://feed.url"}
    with patch.object(ingestor.error_handler, "handle_error") as mock_handle_error:
        result = ingestor.process_content(entry, metadata)
        assert result is False
        assert mock_handle_error.called

def test_batch_ingestion_with_mocked_feed(tmp_path, dummy_config):
    ingestor = PodcastIngestor(dummy_config)
    with patch.object(ingestor, "fetch_content", return_value=(True, [{"title": "Test", "guid": "g", "enclosures": [MagicMock(href="http://audio.mp3")], "links": []}])), \
         patch.object(ingestor, "process_content", return_value=True) as mock_process:
        result = ingestor.process_feed("http://feed.url")
        assert result is True
        mock_process.assert_called_once() 