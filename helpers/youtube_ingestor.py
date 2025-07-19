import os
import json
import hashlib
from datetime import datetime
from pytube import YouTube
from helpers.utils import sanitize_filename, extract_video_id, generate_markdown_summary, log_error, log_info, calculate_hash
from process.evaluate import summarize_text, extract_entities, classify_content, diarize_speakers
from helpers.evaluation_utils import EvaluationFile
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import subprocess
import shutil
from helpers.retry_queue import enqueue
from helpers.dedupe import link_uid
from typing import Dict
from helpers.base_ingestor import BaseIngestor
from helpers.error_handler import AtlasErrorHandler


def is_ytdlp_installed():
    """Check if yt-dlp is installed and available in the system's PATH."""
    return shutil.which("yt-dlp") is not None

class YouTubeIngestor(BaseIngestor):
    def __init__(self, config):
        super().__init__(config)
        self.content_type = "youtube"
        self.ytdlp_available = is_ytdlp_installed()
        self._post_init()

    def ingest_history(self, input_file: str = 'inputs/youtube.txt'):
        if not self.ytdlp_available:
            log_info(self.log_path, "yt-dlp not found in PATH. Pytube fallback downloads will not be available.")
        if not os.path.exists(input_file):
            log_error(self.log_path, f"YouTube input file not found: {input_file}")
            return
        with open(input_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        for url in urls:
            self.ingest_single_video(url)
        log_info(self.log_path, "YouTube ingestion complete.")

    def ingest_single_video(self, url: str) -> bool:
        try:
            # Accept both raw video IDs and URLs
            if url.startswith("http"):
                video_id = extract_video_id(url)
                full_url = url
            else:
                video_id = url
                full_url = f"https://www.youtube.com/watch?v={video_id}"
            file_id = link_uid(full_url)
            meta = self.create_metadata(source=full_url, title=None, uid=file_id, video_id=video_id)
            
            paths = self.path_manager.get_path_set(self.content_type, file_id)
            transcript_path = paths.get_path("transcript")
            meta_path = paths.get_path("metadata")
            if not video_id:
                meta["status"] = "error"
                meta["error"] = "Could not extract video ID"
                log_error(self.log_path, f"Could not extract video ID from {url}")
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf, indent=2)
                return False
            yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
            title = yt.title
            meta.title = title
            video_filename = f"{file_id}.mp4"
            video_path = self.path_manager.get_single_path(self.content_type, file_id, "video")
            if not os.path.exists(video_path):
                log_info(self.log_path, f"Downloading: {title}")
                yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first().download(output_path=os.path.dirname(video_path), filename=video_filename)
                meta.status = "success"
            else:
                meta.status = "already_downloaded"
                    # Fetch transcript if available
            try:
                log_info(self.log_path, f"Fetching transcript for: {title}")
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                transcript_text = "\n".join([x["text"] for x in transcript])
                with open(transcript_path, "w", encoding="utf-8") as tf:
                    tf.write(transcript_text)
                meta.transcript_path = transcript_path
                # Generate Markdown file first
                md_path = self.path_manager.get_single_path(self.content_type, file_id, "markdown")
                md = generate_markdown_summary(
                    title=title,
                    source=full_url,
                    date=meta.date,
                    tags=[],
                    notes=[],
                    content=transcript_text
                )
                with open(md_path, "w", encoding="utf-8") as mdf:
                    mdf.write(md)
                meta.content_path = md_path
                # --- Run Evaluations ---
                if transcript_text:
                    self.run_evaluations(transcript_text, meta)
            except (TranscriptsDisabled, NoTranscriptFound):
                meta.transcript_path = None
                log_error(self.log_path, f"No transcript available for {title}")
            except Exception as e:
                self.handle_error(f"Transcript fetch failed for {title}: {e}", source=full_url)
                meta.transcript_error = str(e)

        except Exception as e:
            self.handle_error(f"Error downloading {url}: {e}", source=full_url, should_retry=True)
            meta.set_error(str(e))
            if self.ytdlp_available:
                log_info(self.log_path, f"Trying yt-dlp fallback for {full_url}...")
                video_path = self.path_manager.get_single_path(self.content_type, file_id, "video")
                ytdlp_cmd = [
                    "yt-dlp",
                    f"https://www.youtube.com/watch?v={video_id}",
                    "-f", "best[ext=mp4]",
                    "-o", video_path
                ]
                try:
                    result = subprocess.run(ytdlp_cmd, capture_output=True, text=True, check=True)
                    log_info(self.log_path, f"yt-dlp download succeeded for {video_id}")
                    meta.status = "success"
                    meta.type_specific["ytdlp_fallback"] = True
                    meta.type_specific["ytdlp_stdout"] = result.stdout
                    meta.type_specific["ytdlp_stderr"] = result.stderr
                except Exception as ytdlp_e:
                    self.handle_error(f"yt-dlp download failed for {video_id}: {ytdlp_e}", source=full_url, should_retry=True)
                    meta.set_error(f"yt-dlp failed: {ytdlp_e}")
            else:
                log_error(self.log_path, f"Skipping yt-dlp fallback for {full_url} because it is not installed.")
        finally:
            if meta_path:
                self.save_metadata(meta)
        return True

def ingest_youtube_history(config: dict, input_file: str = 'inputs/youtube.txt'):
    ingestor = YouTubeIngestor(config)
    ingestor.ingest_history(input_file)

def ingest_youtube_video(url: str, config: Dict) -> bool:
    ingestor = YouTubeIngestor(config)
    return ingestor.ingest_single_video(url)