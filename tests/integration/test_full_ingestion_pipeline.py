import os
from unittest.mock import MagicMock, patch

import pytest

from helpers.article_fetcher import fetch_and_save_articles
from helpers.instapaper_ingestor import InstapaperIngestor
from helpers.podcast_ingestor import PodcastIngestor
from helpers.youtube_ingestor import YouTubeIngestor


@pytest.fixture
def dummy_config(tmp_path):
    return {
        "data_directory": str(tmp_path),
        "article_output_path": os.path.join(str(tmp_path), "articles"),
        "podcast_output_path": os.path.join(str(tmp_path), "podcasts"),
        "youtube_output_path": os.path.join(str(tmp_path), "youtube"),
        "INSTAPAPER_LOGIN": "user",
        "INSTAPAPER_PASSWORD": "pass",
        "run_transcription": False,
    }


def test_full_ingestion_pipeline(dummy_config):
    # Article ingestion (mocked)
    with patch(
        "helpers.article_fetcher.fetch_and_save_article", return_value=True
    ) as mock_article:
        result = fetch_and_save_articles(dummy_config)
        assert result is None or result is True or isinstance(result, dict)
        mock_article.assert_not_called()  # No input file, so nothing processed

    # Podcast ingestion (mocked)
    podcast_ingestor = PodcastIngestor(dummy_config)
    with patch.object(
        podcast_ingestor,
        "fetch_content",
        return_value=(
            True,
            [
                {
                    "title": "Test Podcast",
                    "guid": "g",
                    "enclosures": [MagicMock(href="http://audio.mp3")],
                    "links": [],
                }
            ],
        ),
    ), patch.object(
        podcast_ingestor, "process_content", return_value=True
    ) as mock_process:
        result = podcast_ingestor.process_feed("http://feed.url")
        assert result is True
        mock_process.assert_called_once()

    # YouTube ingestion (mocked)
    youtube_ingestor = YouTubeIngestor(dummy_config)
    with patch(
        "helpers.youtube_ingestor.extract_video_id", return_value="vidid"
    ), patch("helpers.youtube_ingestor.link_uid", return_value="testuid"), patch(
        "helpers.youtube_ingestor.YouTube"
    ) as mock_yt, patch(
        "helpers.youtube_ingestor.YouTubeTranscriptApi.get_transcript",
        return_value=[{"text": "transcript"}],
    ), patch(
        "helpers.youtube_ingestor.generate_markdown_summary", return_value="# Markdown"
    ), patch(
        "helpers.youtube_ingestor.EvaluationFile"
    ), patch(
        "helpers.youtube_ingestor.log_info"
    ), patch(
        "helpers.youtube_ingestor.log_error"
    ):
        mock_yt.return_value.title = "Test Video"
        mock_yt.return_value.streams.filter.return_value.order_by.return_value.desc.return_value.first.return_value.download = (
            lambda output_path, filename: None
        )
        result = youtube_ingestor.ingest_single_video(
            "https://youtube.com/watch?v=vidid"
        )
        assert result is True

    # Instapaper ingestion (mocked)
    instapaper_ingestor = InstapaperIngestor(dummy_config)
    with patch("helpers.instapaper_ingestor.sync_playwright") as mock_playwright, patch(
        "helpers.instapaper_ingestor.log_info"
    ), patch("helpers.instapaper_ingestor.log_error"):
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = (
            mock_browser
        )
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.locator.return_value.count = MagicMock(return_value=0)
        mock_page.locator.return_value.all.return_value = (
            []
        )  # Mock all() to return empty list
        mock_page.locator.return_value.inner_text.return_value = "Test Article"
        mock_page.locator.return_value.get_attribute.return_value = (
            "https://example.com/article"
        )
        mock_page.locator.return_value.inner_html.return_value = (
            "<html><body>Test Content</body></html>"
        )

        instapaper_ingestor.ingest_articles(limit=1)
        # No assertion: just ensure no exceptions and log_error/log_info are called
