"""
Article Fetching Strategies Module

This module contains different strategies for fetching articles, organized into separate classes
for better maintainability and testing. Each strategy implements a common interface.
"""

import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from time import sleep
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth
from readability import Document

from helpers.utils import log_error, log_info

# --- Constants ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
GOOGLEBOT_USER_AGENT = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
)
PAYWALL_PHRASES = [
    "subscribe to continue",
    "create a free account",
    "sign in to read",
    "unlock this story",
    "your free articles",
    "to continue reading",
    "subscribe now",
    "subscription required",
    "premium content",
    "members only",
    "register to continue",
    "paid subscribers only",
    "subscribe for full access",
    "subscribe for unlimited access",
    "login to read more",
    "create an account to continue",
    "please enable js",
    "please enable javascript",
    "disable any ad blocker",
    "javascript is disabled",
    "javascript required",
    "enable javascript",
    "this site requires javascript",
    "javascript must be enabled",
]
PAYWALL_ELEMENTS = [
    ".paywall",
    ".subscription-required",
    ".premium-content",
    ".register-wall",
    ".subscription-wall",
    ".paid-content",
    "#paywall",
    "#subscribe-overlay",
    "#subscription-overlay",
    "div[data-paywall]",
    "[data-require-auth]",
]
MIN_WORD_COUNT = 150
TITLE_CONTENT_RATIO_THRESHOLD = 0.1


class FetchResult:
    """Container for fetch results with metadata."""

    def __init__(
        self,
        success: bool,
        content: str = None,
        method: str = None,
        error: str = None,
        is_truncated: bool = False,
        metadata: Dict[str, Any] = None,
        title: str = None,
        strategy: str = None,
    ):
        self.success = success
        self.content = content
        # Accept both 'method' and 'strategy' for compatibility
        self.method = method or strategy
        self.strategy = strategy or method
        self.error = error
        self.is_truncated = is_truncated
        self.metadata = metadata or {}
        self.title = title


class ArticleFetchStrategy(ABC):
    """Abstract base class for article fetching strategies."""

    @abstractmethod
    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        """Fetch content from the given URL."""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of this strategy."""
        pass


class ContentAnalyzer:
    """Utility class for analyzing content quality and detecting paywalls."""

    @staticmethod
    def is_truncated(html_content: str, log_path: str) -> bool:
        """
        Checks if the content is likely truncated or behind a paywall using multiple heuristics.
        """
        if not html_content:
            return False

        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text().lower()

        # 1. Check for paywall phrases
        for phrase in PAYWALL_PHRASES:
            if phrase in text:
                log_info(log_path, f"Paywall phrase '{phrase}' detected.")
                return True

        # 2. Check for paywall HTML elements
        for selector in PAYWALL_ELEMENTS:
            if soup.select(selector):
                log_info(log_path, f"Paywall element '{selector}' detected.")
                return True

        # 3. Extract title and check title-to-content ratio
        title_tag = soup.find("title")
        if title_tag and title_tag.text:
            title_length = len(title_tag.text.strip())
            content_length = len(text)

            if content_length > 0:
                ratio = title_length / content_length
                if ratio > TITLE_CONTENT_RATIO_THRESHOLD:
                    log_info(
                        log_path,
                        f"Suspicious title-to-content ratio: {ratio:.2f}. Likely truncated.",
                    )
                    return True

        # 4. Check for login forms near the top of the page
        form_tags = soup.find_all("form")
        for form in form_tags[:3]:  # Check only the first few forms
            form_text = form.get_text().lower()
            if any(
                word in form_text
                for word in ["login", "sign in", "subscribe", "register"]
            ):
                log_info(
                    log_path,
                    "Login/subscription form detected near the top of the page.",
                )
                return True

        # 5. Check word count from readability's summary
        try:
            summary_html = Document(html_content).summary()
            summary_text = BeautifulSoup(summary_html, "html.parser").get_text()
            word_count = len(summary_text.split())
            if word_count < MIN_WORD_COUNT:
                log_info(
                    log_path,
                    f"Content is very short ({word_count} words). Likely a teaser.",
                )
                return True
        except Exception:
            # If readability fails, fall back to raw text word count
            word_count = len(text.split())
            if word_count < MIN_WORD_COUNT:
                log_info(
                    log_path,
                    f"Content is very short ({word_count} words). Likely a teaser.",
                )
                return True

        return False

    @staticmethod
    def is_likely_paywall(html_content: str, log_path: str = "") -> bool:
        # Minimal check for test compatibility: keyword or very short content
        if not html_content:
            return False
        text = html_content.lower()
        if any(phrase in text for phrase in PAYWALL_PHRASES):
            return True
        if len(text) < 10 or len(text.split()) < 5:
            return True
        return False

    @staticmethod
    def extract_title_from_html(html: str) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        if title_tag and title_tag.text.strip():
            return title_tag.text.strip()
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.text.strip():
            return h1_tag.text.strip()
        return "Untitled"


class DirectFetchStrategy(ArticleFetchStrategy):
    """Standard HTTP request strategy."""

    def __init__(self):
        self.headers = {"User-Agent": USER_AGENT}

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting direct fetch for {url}")
            response = requests.get(
                url, headers=self.headers, timeout=30, allow_redirects=True
            )
            response.raise_for_status()

            content = response.text
            is_truncated = ContentAnalyzer.is_truncated(content, log_path)
            title = ContentAnalyzer.extract_title_from_html(content)

            return FetchResult(
                success=True,
                content=content,
                method="direct",
                is_truncated=is_truncated,
                metadata={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                },
                title=title,
            )
        except requests.exceptions.RequestException as e:
            log_error(log_path, f"Direct fetch failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="direct")

    def get_strategy_name(self) -> str:
        return "direct"


class TwelveFtStrategy(ArticleFetchStrategy):
    """12ft.io paywall bypass strategy."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting 12ft.io bypass for {url}")
            bypass_url = f"https://12ft.io/{url}"
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(bypass_url, headers=headers, timeout=20)
            response.raise_for_status()

            return FetchResult(
                success=True,
                content=response.text,
                method="12ft_bypass",
                metadata={
                    "bypass_url": bypass_url,
                    "status_code": response.status_code,
                },
            )
        except requests.exceptions.RequestException as e:
            log_error(log_path, f"12ft.io bypass failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="12ft_bypass")

    def get_strategy_name(self) -> str:
        return "12ft_bypass"


class ArchiveTodayStrategy(ArticleFetchStrategy):
    """Archive.today strategy for accessing archived content."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting archive.today for {url}")

            # First check if archive already exists
            search_url = f"https://archive.today/newest/{url}"
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(search_url, headers=headers, timeout=15)

            if response.status_code == 200 and "archive.today" in response.url:
                log_info(log_path, f"Found existing archive for {url}")
                return FetchResult(
                    success=True,
                    content=response.text,
                    method="archive_today_existing",
                    metadata={"archive_url": response.url},
                )

            # If no existing archive, try to create one
            log_info(
                log_path, f"No existing archive found, creating new archive for {url}"
            )
            submit_url = "https://archive.today/submit/"
            submit_data = {"url": url}

            response = requests.post(
                submit_url, data=submit_data, headers=headers, timeout=30
            )

            if response.status_code in [200, 302]:
                # Archive creation initiated, wait and try to access
                sleep(5)  # Give archive time to process

                # Try to access the newly created archive
                response = requests.get(search_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    return FetchResult(
                        success=True,
                        content=response.text,
                        method="archive_today_new",
                        metadata={"archive_url": response.url},
                    )

            raise Exception(
                f"Archive creation failed with status {response.status_code}"
            )

        except Exception as e:
            log_error(log_path, f"Archive.today failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="archive_today")

    def get_strategy_name(self) -> str:
        return "archive_today"


class GooglebotStrategy(ArticleFetchStrategy):
    """Googlebot user agent spoofing strategy."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Googlebot spoof for {url}")
            headers = {"User-Agent": GOOGLEBOT_USER_AGENT}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            return FetchResult(
                success=True,
                content=response.text,
                method="googlebot_spoof",
                metadata={"status_code": response.status_code},
            )
        except requests.exceptions.RequestException as e:
            log_error(log_path, f"Googlebot spoof failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="googlebot_spoof")

    def get_strategy_name(self) -> str:
        return "googlebot_spoof"


class PlaywrightStrategy(ArticleFetchStrategy):
    """Playwright headless browser strategy."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Playwright fetch for {url}")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context()
                stealth(context)
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                sleep(3)
                content = page.content()
                browser.close()
                return FetchResult(
                    success=True,
                    content=content,
                    method="playwright",
                    metadata={"url": url},
                )
        except Exception as e:
            log_error(log_path, f"Playwright fetch failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="playwright")

    def get_strategy_name(self) -> str:
        return "playwright"


class WaybackMachineStrategy(ArticleFetchStrategy):
    """Internet Archive Wayback Machine strategy."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Wayback Machine for {url}")

            # Get the latest snapshot
            api_url = f"https://archive.org/wayback/available?url={url}"
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            if not data.get("archived_snapshots", {}).get("closest"):
                raise Exception("No archived snapshots found")

            snapshot_url = data["archived_snapshots"]["closest"]["url"]
            log_info(log_path, f"Found Wayback snapshot: {snapshot_url}")

            # Fetch the archived content
            response = requests.get(snapshot_url, headers=headers, timeout=20)
            response.raise_for_status()

            return FetchResult(
                success=True,
                content=response.text,
                method="wayback_machine",
                metadata={
                    "snapshot_url": snapshot_url,
                    "timestamp": data["archived_snapshots"]["closest"]["timestamp"],
                },
            )
        except Exception as e:
            log_error(log_path, f"Wayback Machine failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="wayback_machine")

    def get_strategy_name(self) -> str:
        return "wayback_machine"


class ArticleFetcher:
    """Main article fetcher that orchestrates different strategies."""

    def __init__(self):
        self.strategies = [
            DirectFetchStrategy(),
            TwelveFtStrategy(),
            ArchiveTodayStrategy(),
            GooglebotStrategy(),
            PlaywrightStrategy(),
            WaybackMachineStrategy(),
        ]

    def fetch_article(self, url: str, strategy: str = None, log_path: str = "") -> FetchResult:
        """
        Public method to fetch an article using the orchestrated strategies.
        If a specific strategy is provided, it will attempt to use only that strategy.
        """
        if strategy:
            for s in self.strategies:
                if s.get_strategy_name() == strategy:
                    return s.fetch(url, log_path=log_path)
            raise ValueError(f"Unknown strategy: {strategy}")
        
        return self.fetch_with_fallbacks(url, log_path=log_path)

    def fetch_with_fallbacks(self, url: str, log_path: str) -> FetchResult:
        """
        Attempt to fetch content using multiple strategies in order.
        Returns the first successful result with good content quality.
        """
        last_result = None

        for strategy in self.strategies:
            result = strategy.fetch(url, log_path)

            if result.success:
                # Check if content is truncated or low quality for ALL strategies
                is_truncated = ContentAnalyzer.is_truncated(result.content, log_path)

                if is_truncated:
                    log_info(
                        log_path,
                        f"{strategy.get_strategy_name()} succeeded but content appears truncated/low quality, trying next strategy...",
                    )
                    result.is_truncated = True
                    last_result = result
                    continue

                log_info(
                    log_path,
                    f"Successfully fetched {url} using {strategy.get_strategy_name()}",
                )
                return result

            last_result = result

        # All strategies failed or returned low-quality content
        log_error(
            log_path,
            f"All fetch strategies failed or returned low-quality content for {url}",
        )
        return last_result or FetchResult(
            success=False, error="All strategies failed or returned low-quality content"
        )
