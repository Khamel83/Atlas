"""
Pytest configuration and fixtures for Atlas tests.

This module provides comprehensive fixtures for testing the Atlas system,
including test environment setup, mock services, sample data, and utilities.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, Optional, Generator
import json
import os
import sys

# Import test utilities
from tests import (
    TestEnvironment,
    create_mock_response,
    create_sample_article_html,
    create_sample_opml,
    create_sample_rss_feed,
    SAMPLE_URLS,
    SAMPLE_METADATA,
    PROJECT_ROOT
)

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Test Environment Fixtures

@pytest.fixture(scope="function")
def test_env() -> Generator[TestEnvironment, None, None]:
    """Provide isolated test environment with temporary directories."""
    env = TestEnvironment()
    temp_dir = env.setup()
    
    yield env
    
    env.teardown()

@pytest.fixture(scope="function")
def temp_dir(test_env: TestEnvironment) -> Path:
    """Provide temporary directory for test files."""
    return test_env.temp_dir

@pytest.fixture(scope="function")
def output_dir(temp_dir: Path) -> Path:
    """Provide temporary output directory."""
    output_path = temp_dir / "output"
    output_path.mkdir(exist_ok=True)
    return output_path

@pytest.fixture(scope="function")
def data_dir(temp_dir: Path) -> Path:
    """Provide temporary data directory."""
    data_path = temp_dir / "data"
    data_path.mkdir(exist_ok=True)
    return data_path

@pytest.fixture(scope="function")
def logs_dir(temp_dir: Path) -> Path:
    """Provide temporary logs directory."""
    logs_path = temp_dir / "logs"
    logs_path.mkdir(exist_ok=True)
    return logs_path

# Mock Service Fixtures

@pytest.fixture
def mock_requests():
    """Mock requests library for HTTP operations."""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post, \
         patch('requests.put') as mock_put, \
         patch('requests.delete') as mock_delete:
        
        # Default successful response
        mock_response = create_mock_response(create_sample_article_html())
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        mock_put.return_value = mock_response
        mock_delete.return_value = mock_response
        
        yield {
            'get': mock_get,
            'post': mock_post,
            'put': mock_put,
            'delete': mock_delete,
            'response': mock_response
        }

@pytest.fixture
def mock_playwright():
    """Mock Playwright for browser automation."""
    with patch('playwright.sync_api.sync_playwright') as mock_playwright:
        # Create mock browser context
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_browser = MagicMock()
        
        # Set up mock chain
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock page methods
        mock_page.goto.return_value = None
        mock_page.content.return_value = create_sample_article_html()
        mock_page.title.return_value = "Test Article Title"
        
        yield {
            'playwright': mock_playwright,
            'browser': mock_browser,
            'context': mock_context,
            'page': mock_page
        }

@pytest.fixture
def mock_openai():
    """Mock OpenAI API for categorization and processing."""
    with patch('openai.OpenAI') as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "Technology",
            "confidence": 0.95,
            "reasoning": "Article discusses technical topics"
        })
        
        mock_client.chat.completions.create.return_value = mock_response
        
        yield {
            'client': mock_client,
            'response': mock_response
        }

@pytest.fixture
def mock_youtube_api():
    """Mock YouTube API for video metadata."""
    with patch('pytube.YouTube') as mock_youtube:
        mock_video = MagicMock()
        mock_video.title = "Test Video Title"
        mock_video.description = "Test video description"
        mock_video.author = "Test Channel"
        mock_video.length = 600  # 10 minutes
        mock_video.views = 1000
        mock_video.publish_date = "2024-01-01"
        
        mock_youtube.return_value = mock_video
        
        yield mock_video

@pytest.fixture
def mock_feedparser():
    """Mock feedparser for RSS/OPML parsing."""
    with patch('feedparser.parse') as mock_parse:
        mock_feed = {
            'feed': {
                'title': 'Test Podcast',
                'description': 'Test podcast description',
                'link': 'https://example.com'
            },
            'entries': [
                {
                    'title': 'Test Episode 1',
                    'description': 'Test episode description',
                    'link': 'https://example.com/episode1',
                    'published': 'Mon, 01 Jan 2024 12:00:00 GMT',
                    'enclosures': [
                        {
                            'url': 'https://example.com/episode1.mp3',
                            'type': 'audio/mpeg',
                            'length': '1000000'
                        }
                    ]
                }
            ]
        }
        
        mock_parse.return_value = mock_feed
        
        yield mock_feed

# Sample Data Fixtures

@pytest.fixture
def sample_article_html() -> str:
    """Provide sample article HTML."""
    return create_sample_article_html()

@pytest.fixture
def sample_opml() -> str:
    """Provide sample OPML content."""
    return create_sample_opml()

@pytest.fixture
def sample_rss_feed() -> str:
    """Provide sample RSS feed."""
    return create_sample_rss_feed()

@pytest.fixture
def sample_urls() -> list:
    """Provide sample URLs for testing."""
    return SAMPLE_URLS.copy()

@pytest.fixture
def sample_metadata() -> dict:
    """Provide sample metadata."""
    return SAMPLE_METADATA.copy()

@pytest.fixture
def sample_article_file(temp_dir: Path) -> Path:
    """Create sample article markdown file."""
    article_path = temp_dir / "sample_article.md"
    content = """---
title: Test Article
author: Test Author
published_date: 2024-01-01
url: https://example.com/article
category: Technology
tags: [test, article]
---

# Test Article

This is a test article with some content.

## Section 1

Some content here.

## Section 2

More content here.
"""
    article_path.write_text(content)
    return article_path

@pytest.fixture
def sample_opml_file(temp_dir: Path) -> Path:
    """Create sample OPML file."""
    opml_path = temp_dir / "sample_podcasts.opml"
    opml_path.write_text(create_sample_opml())
    return opml_path

@pytest.fixture
def sample_config_file(temp_dir: Path) -> Path:
    """Create sample configuration file."""
    config_path = temp_dir / "config" / "test_config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    
    config_content = """
# Test configuration
openai:
  api_key: "test_key"
  model: "gpt-3.5-turbo"

transcription:
  service: "openai"
  model: "whisper-1"

categories:
  - Technology
  - Science
  - Business
  - Entertainment

output:
  format: "markdown"
  include_metadata: true
"""
    config_path.write_text(config_content)
    return config_path

# Helper Function Fixtures

@pytest.fixture
def create_test_file():
    """Factory function to create test files."""
    def _create_file(path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path
    
    return _create_file

@pytest.fixture
def create_test_metadata():
    """Factory function to create test metadata."""
    def _create_metadata(**kwargs) -> dict:
        metadata = SAMPLE_METADATA.copy()
        metadata.update(kwargs)
        return metadata
    
    return _create_metadata

@pytest.fixture
def mock_error_handler():
    """Mock error handler for testing error conditions."""
    with patch('helpers.error_handler.AtlasErrorHandler') as mock_handler:
        mock_instance = MagicMock()
        mock_handler.return_value = mock_instance
        
        # Mock methods
        mock_instance.handle_error.return_value = True
        mock_instance.should_retry.return_value = True
        mock_instance.get_retry_delay.return_value = 1.0
        
        yield mock_instance

@pytest.fixture
def mock_path_manager():
    """Mock path manager for testing file operations."""
    with patch('helpers.path_manager.PathManager') as mock_manager:
        mock_instance = MagicMock()
        mock_manager.return_value = mock_instance
        
        # Mock methods
        mock_instance.get_content_paths.return_value = MagicMock()
        mock_instance.ensure_directories.return_value = True
        mock_instance.generate_filename.return_value = "test_file.md"
        
        yield mock_instance

@pytest.fixture
def mock_metadata_manager():
    """Mock metadata manager for testing metadata operations."""
    with patch('helpers.metadata_manager.MetadataManager') as mock_manager:
        mock_instance = MagicMock()
        mock_manager.return_value = mock_instance
        
        # Mock methods
        mock_instance.create_metadata.return_value = SAMPLE_METADATA.copy()
        mock_instance.save_metadata.return_value = True
        mock_instance.load_metadata.return_value = SAMPLE_METADATA.copy()
        
        yield mock_instance

# Performance Testing Fixtures

@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()

@pytest.fixture
def large_dataset(temp_dir: Path):
    """Create large dataset for performance testing."""
    dataset_dir = temp_dir / "large_dataset"
    dataset_dir.mkdir()
    
    # Create multiple test files
    for i in range(100):
        file_path = dataset_dir / f"article_{i:03d}.md"
        content = f"""---
title: Test Article {i}
author: Test Author {i % 10}
published_date: 2024-01-{(i % 30) + 1:02d}
url: https://example.com/article{i}
category: Technology
tags: [test, article, batch{i // 10}]
---

# Test Article {i}

This is test article number {i} with some content.

{'Lorem ipsum dolor sit amet, consectetur adipiscing elit. ' * 10}

## Section 1

{'Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. ' * 5}

## Section 2

{'Ut enim ad minim veniam, quis nostrud exercitation ullamco. ' * 5}
"""
        file_path.write_text(content)
    
    return dataset_dir

# Test Markers

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, may use external resources)"
    )
    config.addinivalue_line(
        "markers", "performance: Performance tests (benchmark and scaling)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (longer than 1 second)"
    )
    config.addinivalue_line(
        "markers", "network: Tests requiring network access"
    )
    config.addinivalue_line(
        "markers", "filesystem: Tests requiring file system operations"
    )
    config.addinivalue_line(
        "markers", "external: Tests requiring external services"
    )
    config.addinivalue_line(
        "markers", "smoke: Smoke tests (basic functionality)"
    )
    config.addinivalue_line(
        "markers", "regression: Regression tests for bug fixes"
    )

# Test Collection Hooks

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names and paths."""
    for item in items:
        # Add unit marker to unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker to performance tests
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        
        # Add slow marker to tests with "slow" in name
        if "slow" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Add network marker to tests with "network" in name
        if "network" in item.name:
            item.add_marker(pytest.mark.network)
        
        # Add filesystem marker to tests with "file" in name
        if "file" in item.name:
            item.add_marker(pytest.mark.filesystem) 