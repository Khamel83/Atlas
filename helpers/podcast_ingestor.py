# helpers/podcast_ingestor.py
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import feedparser
import requests

from helpers.base_ingestor import BaseIngestor, IngestorResult
from helpers.dedupe import link_uid
from helpers.error_handler import AtlasErrorHandler
from helpers.evaluation_utils import EvaluationFile
from helpers.metadata_manager import ContentType
from helpers.retry_queue import enqueue
from helpers.transcription import transcribe_audio
from helpers.utils import (
    calculate_hash,
    generate_markdown_summary,
    log_error,
    log_info,
    sanitize_filename,
)
from process.evaluate import (
    classify_content,
    diarize_speakers,
    extract_entities,
    summarize_text,
)

USER_AGENT = "AtlasIngestor/1.0 (+https://github.com/yourrepo/atlas)"


class PodcastIngestor(BaseIngestor):
    def get_content_type(self):
        return ContentType.PODCAST

    def get_module_name(self):
        return "podcast_ingestor"

    def __init__(self, config):
        super().__init__(config)

        self.user_agent = USER_AGENT
        self._post_init()

    def fetch_content(self, feed_url, metadata):
        # Parse the feed and return entries
        feed = feedparser.parse(
            feed_url, request_headers={"User-Agent": self.user_agent}
        )
        if not feed.entries:
            self.error_handler.handle_error(
                Exception(f"No entries found in feed: {feed_url}"), self.log_path
            )
            return False, None
        return True, feed.entries

    def process_feed(self, feed_url):
        """
        Fetches and processes all entries from a podcast feed URL.
        Handles errors and logs progress for each entry.
        """
        metadata = {"source": feed_url}
        success, entries = self.fetch_content(feed_url, metadata)
        if not success or not entries:
            log_error(self.log_path, f"Failed to fetch entries for feed: {feed_url}")
            return False
        for entry in entries:
            try:
                self.process_content(entry, metadata)
            except Exception as e:
                self.error_handler.handle_error(
                    Exception(f"Error processing entry in feed {feed_url}: {e}"),
                    self.log_path,
                )
        return True

    def process_content(self, entry, metadata):
        # Assign title early for reliable logging
        title = entry.get("title", "Untitled Episode")

        # Robust audio URL extraction
        audio_url = None
        if hasattr(entry, "enclosures") and entry.enclosures:
            audio_url = entry.enclosures[0].href
        elif hasattr(entry, "links") and entry.links:
            for link in entry.links:
                if link.get("type", "").startswith("audio"):
                    audio_url = link.get("href")
                    break
        if not audio_url:
            self.error_handler.handle_error(
                Exception(f"No audio URL found for entry: {title}"), self.log_path
            )
            return False

        # --- UID Generation ---
        # Use the podcast's official guid if available, otherwise use the audio URL.
        # This is the key to deduplication.
        try:
            unique_identifier = entry.get("guid", audio_url)
            if not unique_identifier:
                self.error_handler.handle_error(
                    Exception(
                        f"Could not determine a unique identifier for entry: {title}"
                    ),
                    self.log_path,
                )
                return False

            # Use the standardized link_uid function
            file_id = link_uid(unique_identifier)
        except Exception as e:
            self.error_handler.handle_error(
                Exception(f"Error generating file ID for entry {title}: {e}"),
                self.log_path,
            )
            return False

        # Use the path_manager to get all required paths
        paths = self.path_manager.get_path_set(self.content_type, file_id)
        audio_path = paths.get_path("audio")
        meta_path = paths.get_path("metadata")
        transcript_path = paths.get_path("transcript")
        md_path = paths.get_path("markdown")

        meta = self.create_metadata(
            source=metadata["source"],
            title=entry.title,
            uid=file_id,
            audio_url=audio_url,
        )
        try:
            if not os.path.exists(audio_path):
                log_info(self.log_path, f"Downloading: {title}")
                with requests.get(audio_url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(audio_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                meta.status = "success"
            else:
                meta.status = "already_downloaded"

            transcript_text = None
            run_transcription = self.config.get("run_transcription", False)
            if run_transcription:
                transcript_text = transcribe_audio(audio_path, self.log_path)
                meta.transcript_path = transcript_path if transcript_text else None
            else:
                log_info(
                    self.log_path, "Transcription is disabled via config. Skipping."
                )
                meta.transcript_path = None
                # If transcription is off, check if an old transcript exists
                if os.path.exists(transcript_path):
                    with open(transcript_path, "r", encoding="utf-8") as tf:
                        transcript_text = tf.read()

            # Generate Markdown summary file first
            md = generate_markdown_summary(
                title=entry.title,
                source=metadata["source"],
                date=meta.date,
                tags=[],
                notes=[],
                content=transcript_text,
            )
            with open(md_path, "w", encoding="utf-8") as mdf:
                mdf.write(md)
            meta.content_path = md_path

            # --- Run Evaluations ---
            if transcript_text:
                self.run_evaluations(transcript_text, meta)

        except Exception as e:
            self.handle_error(
                f"Failed to download or process podcast: {e}",
                source=audio_url,
                should_retry=True,
            )
            meta.set_error(str(e))

        # Save metadata regardless of success/failure
        self.save_metadata(meta)

        return meta.status == "success"

        return True  # Indicate success for the ingestor


def ingest_podcasts(config: dict, opml_path: str = "inputs/podcasts.opml"):
    ingestor = PodcastIngestor(config)

    if not os.path.exists(opml_path):
        log_error(ingestor.log_path, f"OPML file not found: {opml_path}")
        return

    with open(opml_path, "r") as f:
        lines = f.read().splitlines()

    feed_urls = [
        line.split("xmlUrl=")[-1].split('"')[1] for line in lines if "xmlUrl=" in line
    ]

    for feed_url in feed_urls:
        log_info(ingestor.log_path, f"Processing feed: {feed_url}")
        # The fetch_content method handles its own error logging and retry queue
        ingestor.process_feed(feed_url)

    log_info(ingestor.log_path, "Podcast ingestion complete.")
