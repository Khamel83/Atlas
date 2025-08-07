#!/usr/bin/env python3
"""
Atlas Audio Processing Integration

Enhanced audio processing helper that integrates Podemos advanced capabilities
with Atlas unified database and workflows. Provides seamless audio processing
including ad detection, removal, and high-quality transcription.

This module bridges the gap between Podemos's advanced audio processing
capabilities and Atlas's cognitive analysis pipeline, creating a unified
audio-to-insights workflow.

Usage:
    from helpers.audio_processor import AudioProcessor, PodcastProcessingResult
    
    # Initialize processor with database integration
    processor = AudioProcessor()
    
    # Process audio with ad removal and transcription
    result = processor.process_audio_url(
        audio_url="https://example.com/podcast.mp3",
        title="Podcast Episode",
        show_name="Tech Talk"
    )
    
    # Get processing status
    status = processor.get_processing_status(episode_id)
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Atlas imports
from helpers.atlas_database_helper import get_atlas_database_manager
from helpers.utils import log_info, log_error
from helpers.metadata_manager import ContentType, ProcessingStatus

logger = logging.getLogger(__name__)

# Database integration
try:
    from database_integration import ContentItem, PodcastEpisode
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.error("Database integration not available for audio processing")

# Podemos imports (with fallbacks)
PODEMOS_AVAILABLE = False
try:
    # Try to import Podemos components with proper path handling
    import sys
    import types
    
    # Setup paths
    atlas_root = os.path.dirname(os.path.dirname(__file__))  # Atlas root directory
    podcast_processing_path = os.path.join(atlas_root, "podcast_processing")
    
    if podcast_processing_path not in sys.path:
        sys.path.insert(0, podcast_processing_path)
    
    # Create a 'src' module that points to podcast_processing
    # This allows the internal imports like 'from src.detect.chapters' to work
    src_module = types.ModuleType('src')
    src_module.__path__ = [podcast_processing_path]
    sys.modules['src'] = src_module
    
    # Also add the Atlas root so src can be found
    if atlas_root not in sys.path:
        sys.path.insert(0, atlas_root)
    
    # Now import the modules - they should be able to find their src. imports
    from detect.fusion import detect_ads_fast
    from cut.plan import build_keep_segments  
    from cut.ffmpeg_exec import cut_with_ffmpeg
    from transcribe.full_whisper import full_transcribe
    from transcribe.md_formatter import format_transcript_to_md
    from dl.fetcher import download_file
    from dl.integrity import get_audio_duration
    
    PODEMOS_AVAILABLE = True
    logger.info("Podemos audio processing modules loaded successfully")
    
except ImportError as e:
    logger.warning(f"Podemos modules not available: {e}")
    logger.info("Audio processing will use basic Atlas capabilities")

@dataclass
class AudioProcessingConfig:
    """Configuration for audio processing operations"""
    
    # Ad detection settings
    enable_ad_detection: bool = True
    min_confidence: float = 0.7
    padding_seconds: float = 2.0
    
    # Transcription settings  
    transcription_model: str = "base"
    enable_word_timestamps: bool = True
    enable_vad: bool = True
    beam_size: int = 5
    
    # Processing settings
    max_retries: int = 3
    timeout_seconds: int = 3600  # 1 hour
    
    # Quality settings
    audio_quality: str = "high"  # low, medium, high
    preserve_original: bool = True

@dataclass
class PodcastProcessingResult:
    """Result of podcast processing operation"""
    
    success: bool
    content_uid: str
    episode_id: Optional[int] = None
    
    # File paths
    original_file_path: Optional[str] = None
    cleaned_file_path: Optional[str] = None
    transcript_file_path: Optional[str] = None
    
    # Processing data
    original_duration: Optional[float] = None
    cleaned_duration: Optional[float] = None
    ad_segments: List[Dict] = None
    transcript_data: Dict = None
    
    # Status and error info
    processing_status: str = "completed"
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    
    def __post_init__(self):
        if self.ad_segments is None:
            self.ad_segments = []
        if self.transcript_data is None:
            self.transcript_data = {}

class AudioProcessor:
    """
    Enhanced audio processor with Podemos integration
    
    Provides advanced audio processing capabilities including ad detection,
    removal, and high-quality transcription integrated with Atlas database
    and cognitive analysis pipeline.
    """
    
    def __init__(self, config: AudioProcessingConfig = None, db_path: str = None):
        """
        Initialize audio processor
        
        Args:
            config: Audio processing configuration
            db_path: Path to unified database
        """
        self.config = config or AudioProcessingConfig()
        
        # Initialize database integration
        if DATABASE_AVAILABLE:
            self.atlas_db = get_atlas_database_manager(db_path)
            self.database_enabled = self.atlas_db.database_enabled
        else:
            self.atlas_db = None
            self.database_enabled = False
            
        # Setup processing directories
        self.setup_processing_directories()
        
        logger.info(f"AudioProcessor initialized - Podemos: {PODEMOS_AVAILABLE}, Database: {self.database_enabled}")
    
    def setup_processing_directories(self):
        """Setup directories for audio processing"""
        base_dir = Path("output/audio")
        
        self.directories = {
            "originals": base_dir / "originals",
            "cleaned": base_dir / "cleaned", 
            "transcripts": base_dir / "transcripts"
        }
        
        # Create directories
        for directory in self.directories.values():
            directory.mkdir(parents=True, exist_ok=True)
    
    def process_audio_url(
        self,
        audio_url: str,
        title: str,
        show_name: str = None,
        description: str = None,
        pub_date: datetime = None
    ) -> PodcastProcessingResult:
        """
        Process audio from URL with full pipeline
        
        Args:
            audio_url: URL to audio file
            title: Episode title
            show_name: Podcast show name
            description: Episode description
            pub_date: Publication date
            
        Returns:
            PodcastProcessingResult with processing details
        """
        start_time = datetime.now()
        
        # Generate content UID
        content_uid = hashlib.md5(f"podcast_{audio_url}".encode()).hexdigest()
        
        try:
            logger.info(f"Starting audio processing for: {title}")
            
            # Create initial database entry if available
            if self.database_enabled:
                self._create_database_entry(
                    content_uid, title, show_name, audio_url, 
                    description, pub_date
                )
            
            # Step 1: Download original audio
            original_path = self._download_audio(audio_url, content_uid)
            if not original_path:
                return self._create_error_result(
                    content_uid, "Failed to download audio file"
                )
            
            # Step 2: Get audio duration
            original_duration = self._get_audio_duration(original_path)
            
            # Step 3: Process with advanced capabilities if available
            if PODEMOS_AVAILABLE:
                result = self._process_with_podemos(
                    content_uid, original_path, original_duration,
                    title, show_name
                )
            else:
                result = self._process_basic(
                    content_uid, original_path, original_duration,
                    title, show_name
                )
            
            # Step 4: Update database with results
            if self.database_enabled and result.success:
                self._update_database_with_results(content_uid, result)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time = processing_time
            
            logger.info(f"Audio processing completed in {processing_time:.1f}s: {title}")
            return result
            
        except Exception as e:
            logger.error(f"Audio processing failed for {title}: {e}")
            return self._create_error_result(
                content_uid, f"Processing error: {e}"
            )
    
    def _download_audio(self, audio_url: str, content_uid: str) -> Optional[str]:
        """Download audio file to local storage"""
        try:
            # Determine file extension from URL
            file_ext = "mp3"  # Default
            if audio_url.lower().endswith(('.mp4', '.m4a', '.wav', '.ogg')):
                file_ext = audio_url.split('.')[-1].lower()
            
            output_path = self.directories["originals"] / f"{content_uid}.{file_ext}"
            
            if PODEMOS_AVAILABLE:
                # Use Podemos download capabilities
                return download_file(audio_url, str(output_path))
            else:
                # Basic download fallback
                import requests
                response = requests.get(audio_url, stream=True)
                response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                return str(output_path)
                
        except Exception as e:
            logger.error(f"Failed to download audio from {audio_url}: {e}")
            return None
    
    def _get_audio_duration(self, audio_path: str) -> Optional[float]:
        """Get audio file duration"""
        try:
            if PODEMOS_AVAILABLE:
                return get_audio_duration(audio_path)
            else:
                # Fallback duration detection
                try:
                    import subprocess
                    result = subprocess.run([
                        'ffprobe', '-v', 'quiet', '-print_format', 'json',
                        '-show_format', audio_path
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        return float(data['format']['duration'])
                except:
                    pass
                return None
                
        except Exception as e:
            logger.error(f"Failed to get audio duration for {audio_path}: {e}")
            return None
    
    def _process_with_podemos(
        self, 
        content_uid: str,
        original_path: str,
        original_duration: float,
        title: str,
        show_name: str
    ) -> PodcastProcessingResult:
        """Process audio using advanced Podemos capabilities"""
        
        try:
            logger.info(f"Processing with Podemos advanced pipeline: {title}")
            
            # Step 1: Ad detection
            ad_segments = []
            if self.config.enable_ad_detection:
                ad_segments = self._detect_ads(original_path, original_duration)
                logger.info(f"Detected {len(ad_segments)} ad segments")
            
            # Step 2: Audio cleaning (ad removal)
            cleaned_path = None
            cleaned_duration = original_duration
            
            if ad_segments and self.config.enable_ad_detection:
                cleaned_path = self._remove_ads(
                    original_path, ad_segments, content_uid
                )
                if cleaned_path:
                    cleaned_duration = self._get_audio_duration(cleaned_path)
                    logger.info(f"Audio cleaned: {original_duration:.1f}s -> {cleaned_duration:.1f}s")
            
            # Step 3: High-quality transcription
            audio_for_transcription = cleaned_path or original_path
            transcript_data, transcript_path = self._transcribe_audio(
                audio_for_transcription, content_uid
            )
            
            return PodcastProcessingResult(
                success=True,
                content_uid=content_uid,
                original_file_path=original_path,
                cleaned_file_path=cleaned_path,
                transcript_file_path=transcript_path,
                original_duration=original_duration,
                cleaned_duration=cleaned_duration,
                ad_segments=ad_segments,
                transcript_data=transcript_data,
                processing_status="completed"
            )
            
        except Exception as e:
            logger.error(f"Podemos processing failed: {e}")
            return self._create_error_result(
                content_uid, f"Advanced processing failed: {e}"
            )
    
    def _process_basic(
        self,
        content_uid: str,
        original_path: str,
        original_duration: float,
        title: str,
        show_name: str
    ) -> PodcastProcessingResult:
        """Process audio using basic Atlas capabilities"""
        
        try:
            logger.info(f"Processing with basic Atlas pipeline: {title}")
            
            # Basic transcription only (no ad detection/removal)
            transcript_data, transcript_path = self._transcribe_basic(
                original_path, content_uid
            )
            
            return PodcastProcessingResult(
                success=True,
                content_uid=content_uid,
                original_file_path=original_path,
                cleaned_file_path=None,
                transcript_file_path=transcript_path,
                original_duration=original_duration,
                cleaned_duration=original_duration,
                ad_segments=[],
                transcript_data=transcript_data,
                processing_status="completed"
            )
            
        except Exception as e:
            logger.error(f"Basic processing failed: {e}")
            return self._create_error_result(
                content_uid, f"Basic processing failed: {e}"
            )
    
    def _detect_ads(self, audio_path: str, duration: float) -> List[Dict]:
        """Detect ad segments using Podemos fusion detection"""
        try:
            # Use Podemos ad detection
            cuts = detect_ads_fast(audio_path, duration)
            
            # Convert to standard format
            ad_segments = []
            for cut in cuts:
                ad_segments.append({
                    'start': cut.get('start', 0),
                    'end': cut.get('end', 0),
                    'confidence': cut.get('confidence', 0),
                    'type': cut.get('type', 'unknown')
                })
            
            return ad_segments
            
        except Exception as e:
            logger.error(f"Ad detection failed: {e}")
            return []
    
    def _remove_ads(
        self, 
        original_path: str, 
        ad_segments: List[Dict], 
        content_uid: str
    ) -> Optional[str]:
        """Remove ads from audio using Podemos cutting"""
        try:
            # Build keep segments (inverse of ad segments)
            keep_segments = build_keep_segments(ad_segments, self._get_audio_duration(original_path))
            
            # Output path for cleaned audio
            cleaned_path = self.directories["cleaned"] / f"{content_uid}_cleaned.mp3"
            
            # Use Podemos FFmpeg integration
            success = cut_with_ffmpeg(
                str(original_path), 
                str(cleaned_path),
                keep_segments
            )
            
            if success:
                return str(cleaned_path)
            else:
                logger.error("FFmpeg cutting failed")
                return None
                
        except Exception as e:
            logger.error(f"Ad removal failed: {e}")
            return None
    
    def _transcribe_audio(self, audio_path: str, content_uid: str) -> tuple:
        """High-quality transcription using Podemos whisper integration"""
        try:
            # Use Podemos full transcription
            transcript_result = full_transcribe(
                audio_path,
                model_size=self.config.transcription_model,
                enable_vad=self.config.enable_vad,
                beam_size=self.config.beam_size,
                word_timestamps=self.config.enable_word_timestamps
            )
            
            # Format to markdown
            transcript_path = self.directories["transcripts"] / f"{content_uid}_transcript.md"
            markdown_content = format_transcript_to_md(transcript_result)
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return transcript_result, str(transcript_path)
            
        except Exception as e:
            logger.error(f"High-quality transcription failed: {e}")
            return {}, None
    
    def _transcribe_basic(self, audio_path: str, content_uid: str) -> tuple:
        """Basic transcription fallback"""
        try:
            # Use existing Atlas transcription capabilities
            from helpers.transcription import transcribe_audio_openrouter
            
            transcript_text = transcribe_audio_openrouter(audio_path)
            
            transcript_data = {
                'text': transcript_text,
                'segments': [],
                'language': 'en',
                'method': 'basic_atlas'
            }
            
            # Save as markdown
            transcript_path = self.directories["transcripts"] / f"{content_uid}_transcript.md"
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"# Transcript\n\n{transcript_text}")
            
            return transcript_data, str(transcript_path)
            
        except Exception as e:
            logger.error(f"Basic transcription failed: {e}")
            return {}, None
    
    def _create_database_entry(
        self,
        content_uid: str,
        title: str, 
        show_name: str,
        audio_url: str,
        description: str,
        pub_date: datetime
    ):
        """Create initial database entry for podcast"""
        try:
            if not self.database_enabled:
                return
            
            # Create content item entry
            success = self.atlas_db.store_content(
                metadata=None,  # We'll create this manually
                content_data={
                    'description': description,
                    'show_name': show_name,
                    'pub_date': pub_date or datetime.now(),
                    'tags': ['podcast', show_name] if show_name else ['podcast']
                }
            )
            
            # Create manual content entry using database directly
            with self.atlas_db.db.session() as session:
                # Create content item
                content_item = ContentItem(
                    uid=content_uid,
                    content_type='podcast',
                    source_url=audio_url,
                    title=title,
                    status='processing',
                    show_name=show_name,
                    pub_date=pub_date,
                    description=description,
                    tags=['podcast', show_name] if show_name else ['podcast']
                )
                session.add(content_item)
                session.flush()
                
                # Create podcast episode entry
                podcast_episode = PodcastEpisode(
                    content_item_id=content_item.id,
                    original_audio_url=audio_url,
                    show_author=show_name
                )
                session.add(podcast_episode)
                session.commit()
                
                logger.info(f"Database entry created for podcast: {title}")
            
        except Exception as e:
            logger.error(f"Failed to create database entry: {e}")
    
    def _update_database_with_results(
        self, 
        content_uid: str, 
        result: PodcastProcessingResult
    ):
        """Update database with processing results"""
        try:
            if not self.database_enabled:
                return
                
            with self.atlas_db.db.session() as session:
                # Find content item
                content_item = session.query(ContentItem).filter_by(uid=content_uid).first()
                if not content_item:
                    logger.error(f"Content item not found for UID: {content_uid}")
                    return
                
                # Update content item
                content_item.status = 'completed' if result.success else 'error'
                content_item.processing_completed_at = datetime.utcnow()
                if not result.success:
                    content_item.last_error = result.error_message
                
                # Update podcast episode
                podcast_episode = session.query(PodcastEpisode).filter_by(
                    content_item_id=content_item.id
                ).first()
                
                if podcast_episode:
                    podcast_episode.original_file_path = result.original_file_path
                    podcast_episode.original_duration = result.original_duration
                    podcast_episode.cleaned_file_path = result.cleaned_file_path
                    podcast_episode.cleaned_duration = result.cleaned_duration
                    podcast_episode.md_transcript_file_path = result.transcript_file_path
                    
                    if result.ad_segments:
                        podcast_episode.ad_segments = result.ad_segments
                    
                    if result.transcript_data:
                        podcast_episode.transcript = result.transcript_data
                
                session.commit()
                logger.info(f"Database updated with processing results: {content_uid}")
                
        except Exception as e:
            logger.error(f"Failed to update database with results: {e}")
    
    def _create_error_result(self, content_uid: str, error_message: str) -> PodcastProcessingResult:
        """Create error result"""
        if self.database_enabled:
            self.atlas_db.mark_content_error(content_uid, error_message)
        
        return PodcastProcessingResult(
            success=False,
            content_uid=content_uid,
            processing_status="error",
            error_message=error_message
        )
    
    def get_processing_status(self, content_uid: str) -> Dict[str, Any]:
        """Get processing status for content"""
        try:
            if self.database_enabled:
                content = self.atlas_db.get_content(content_uid)
                if content:
                    return {
                        'uid': content_uid,
                        'status': content.get('status', 'unknown'),
                        'error': content.get('error'),
                        'created_at': content.get('created_at'),
                        'updated_at': content.get('updated_at')
                    }
            
            return {'uid': content_uid, 'status': 'not_found'}
            
        except Exception as e:
            logger.error(f"Failed to get processing status: {e}")
            return {'uid': content_uid, 'status': 'error', 'error': str(e)}
    
    def list_processed_podcasts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List processed podcasts with details"""
        try:
            if self.database_enabled:
                return self.atlas_db.get_podcasts(limit=limit)
            else:
                return []
        except Exception as e:
            logger.error(f"Failed to list processed podcasts: {e}")
            return []
    
    def close(self):
        """Close database connections"""
        if self.atlas_db:
            self.atlas_db.close()

# Global instance for easy access
_global_audio_processor: Optional[AudioProcessor] = None

def get_audio_processor(config: AudioProcessingConfig = None) -> AudioProcessor:
    """
    Get global audio processor instance
    
    Args:
        config: Audio processing configuration (only used on first call)
        
    Returns:
        AudioProcessor instance
    """
    global _global_audio_processor
    
    if _global_audio_processor is None:
        _global_audio_processor = AudioProcessor(config)
    
    return _global_audio_processor

def close_global_audio_processor():
    """Close global audio processor"""
    global _global_audio_processor
    
    if _global_audio_processor:
        _global_audio_processor.close()
        _global_audio_processor = None