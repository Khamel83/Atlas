"""
Atlas Test Suite

This module provides shared test utilities, fixtures, and configurations
for the Atlas testing framework.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

# Project constants
PROJECT_ROOT = Path(__file__).parent.parent
TEST_DATA_DIR = PROJECT_ROOT / "tests" / "data"

# Sample test data
SAMPLE_URLS = [
    "https://example.com/article1",
    "https://example.com/article2",
    "https://www.youtube.com/watch?v=test123",
    "https://feeds.example.com/podcast.rss",
]

SAMPLE_METADATA = {
    "title": "Test Article",
    "author": "Test Author",
    "published_date": "2024-01-01",
    "url": "https://example.com/test",
    "category": "Technology",
    "tags": ["test", "article"],
    "word_count": 500,
    "read_time": 2,
}


class TestEnvironment:
    """Manages isolated test environment with temporary directories."""

    def __init__(self):
        self.temp_dir = None
        self.original_cwd = None

    def setup(self) -> Path:
        """Set up temporary test environment."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="atlas_test_"))
        self.original_cwd = os.getcwd()

        # Create essential directories
        (self.temp_dir / "output").mkdir()
        (self.temp_dir / "config").mkdir()
        (self.temp_dir / "logs").mkdir()

        return self.temp_dir

    def teardown(self):
        """Clean up test environment."""
        if self.original_cwd:
            os.chdir(self.original_cwd)

        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


def create_mock_response(content: str = "", status_code: int = 200) -> MagicMock:
    """Create a mock HTTP response."""
    mock_response = MagicMock()
    mock_response.text = content
    mock_response.content = content.encode()
    mock_response.status_code = status_code
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.ok = status_code < 400
    return mock_response


def create_sample_article_html() -> str:
    """Create sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Article Title</title>
        <meta name="author" content="Test Author">
        <meta name="description" content="Test article description">
    </head>
    <body>
        <article>
            <h1>Test Article Title</h1>
            <p>This is a test article with sample content.</p>
            <p>It has multiple paragraphs for testing.</p>
        </article>
    </body>
    </html>
    """


def create_sample_opml() -> str:
    """Create sample OPML content for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <opml version="1.0">
        <head>
            <title>Test Podcasts</title>
        </head>
        <body>
            <outline text="Technology" title="Technology">
                <outline text="Test Podcast 1"
                         title="Test Podcast 1"
                         type="rss"
                         xmlUrl="https://example.com/feed1.rss" />
                <outline text="Test Podcast 2"
                         title="Test Podcast 2"
                         type="rss"
                         xmlUrl="https://example.com/feed2.rss" />
            </outline>
        </body>
    </opml>
    """


def create_sample_rss_feed() -> str:
    """Create sample RSS feed for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test Podcast</title>
            <description>A test podcast feed</description>
            <link>https://example.com</link>
            <item>
                <title>Test Episode 1</title>
                <description>Test episode description</description>
                <link>https://example.com/episode1</link>
                <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                <enclosure url="https://example.com/episode1.mp3"
                          type="audio/mpeg"
                          length="1000000" />
            </item>
        </channel>
    </rss>
    """
