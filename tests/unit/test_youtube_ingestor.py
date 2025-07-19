import os
import pytest
from unittest.mock import patch, MagicMock
from helpers.youtube_ingestor import YouTubeIngestor

@pytest.fixture
def dummy_config(tmp_path):
    return {
        "data_directory": str(tmp_path),
        "youtube_output_path": os.path.join(str(tmp_path), "youtube"),
    }

@pytest.fixture
def ingestor(dummy_config):
    return YouTubeIngestor(dummy_config)

def test_initialization(ingestor):
    assert ingestor.config is not None
    assert hasattr(ingestor, "error_handler")
    assert hasattr(ingestor, "video_dir")
    assert hasattr(ingestor, "meta_dir")
    assert hasattr(ingestor, "md_dir")
    assert hasattr(ingestor, "transcript_dir")
    assert hasattr(ingestor, "log_path")

def test_ingest_single_video_success(ingestor):
    with patch("helpers.youtube_ingestor.extract_video_id", return_value="vidid"), \
         patch("helpers.youtube_ingestor.link_uid", return_value="testuid"), \
         patch("helpers.youtube_ingestor.YouTube") as mock_yt, \
         patch("helpers.youtube_ingestor.YouTubeTranscriptApi.get_transcript", return_value=[{"text": "transcript"}]), \
         patch("helpers.youtube_ingestor.generate_markdown_summary", return_value="# Markdown"), \
         patch("helpers.youtube_ingestor.EvaluationFile"), \
         patch("helpers.youtube_ingestor.log_info"), \
         patch("helpers.youtube_ingestor.log_error"):
        mock_yt.return_value.title = "Test Video"
        mock_yt.return_value.streams.filter.return_value.order_by.return_value.desc.return_value.first.return_value.download = lambda output_path, filename: None
        result = ingestor.ingest_single_video("https://youtube.com/watch?v=vidid")
        assert result is True
        meta_path = os.path.join(ingestor.meta_dir, "testuid.json")
        assert os.path.exists(meta_path)

def test_ingest_single_video_missing_video_id(ingestor):
    with patch("helpers.youtube_ingestor.extract_video_id", return_value=None), \
         patch("helpers.youtube_ingestor.log_error") as mock_log_error:
        result = ingestor.ingest_single_video("badurl")
        assert result is False
        assert mock_log_error.called

def test_error_handling_on_download_failure(ingestor):
    with patch("helpers.youtube_ingestor.extract_video_id", return_value="vidid"), \
         patch("helpers.youtube_ingestor.link_uid", return_value="testuid"), \
         patch("helpers.youtube_ingestor.YouTube", side_effect=Exception("fail")), \
         patch("helpers.youtube_ingestor.log_error") as mock_log_error:
        result = ingestor.ingest_single_video("https://youtube.com/watch?v=vidid")
        assert result is False
        assert mock_log_error.called 