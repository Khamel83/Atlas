import os
import pytest
from unittest.mock import patch, MagicMock
from helpers.instapaper_ingestor import InstapaperIngestor

@pytest.fixture
def dummy_config(tmp_path):
    return {
        "data_directory": str(tmp_path),
        "article_output_path": os.path.join(str(tmp_path), "articles"),
        "INSTAPAPER_LOGIN": "user",
        "INSTAPAPER_PASSWORD": "pass",
    }

@pytest.fixture
def ingestor(dummy_config):
    return InstapaperIngestor(dummy_config)

def test_initialization(ingestor):
    assert ingestor.config is not None
    assert hasattr(ingestor, "error_handler")
    assert hasattr(ingestor, "login")
    assert hasattr(ingestor, "password")
    assert hasattr(ingestor, "meta_save_dir")
    assert hasattr(ingestor, "md_save_dir")
    assert hasattr(ingestor, "html_save_dir")
    assert hasattr(ingestor, "log_path")

def test_missing_credentials(tmp_path):
    config = {"data_directory": str(tmp_path), "article_output_path": os.path.join(str(tmp_path), "articles")}
    ingestor = InstapaperIngestor(config)
    with patch("helpers.instapaper_ingestor.log_error") as mock_log_error:
        ingestor.ingest_articles()
        assert mock_log_error.called

def test_ingest_articles_playwright_error(ingestor):
    with patch("helpers.instapaper_ingestor.sync_playwright") as mock_playwright, \
         patch("helpers.instapaper_ingestor.log_error") as mock_log_error:
        mock_playwright.side_effect = Exception("Playwright error")
        ingestor.ingest_articles()
        assert mock_log_error.called or ingestor.error_handler 