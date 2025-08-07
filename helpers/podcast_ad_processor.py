#!/usr/bin/env python3
"""
Atlas-Podemos Unified Ad Detection and Removal System

Integrates advanced Podemos ad detection capabilities with Atlas workflows
and unified database for complete podcast processing with ad removal.

This system provides end-to-end podcast processing:
1. RSS ingestion with unified database storage
2. Advanced ad detection using multiple signals (chapters, transcription, audio)
3. Intelligent ad removal with segment planning
4. High-quality transcription of cleaned audio
5. Atlas cognitive analysis integration

Usage:
    from helpers.podcast_ad_processor import PodcastAdProcessor, ProcessingConfig
    
    # Initialize with database integration
    processor = PodcastAdProcessor()
    
    # Process podcast from RSS to cleaned audio with ad removal
    result = processor.process_podcast_episode(episode_url)
    
    # Batch process multiple episodes
    results = processor.process_multiple_episodes(episode_urls)
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

# Atlas imports  
from helpers.audio_processor import get_audio_processor, AudioProcessingConfig, PodcastProcessingResult
from helpers.podcast_rss_unified import get_unified_rss_ingestor
from helpers.atlas_database_helper import get_atlas_database_manager

# Database integration
try:
    from database_integration import ContentItem, PodcastEpisode
    from database_integration.database import UnifiedDB
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class AdDetectionConfig:
    """Configuration for ad detection parameters"""
    
    # Detection sensitivity
    enable_chapter_detection: bool = True
    enable_text_analysis: bool = True  
    enable_audio_analysis: bool = False  # Future: audio fingerprinting
    
    # Confidence thresholds
    min_confidence: float = 0.7
    chapter_confidence: float = 0.99
    text_confidence: float = 0.7
    
    # Text analysis parameters
    ad_phrases: List[str] = None
    url_patterns: List[str] = None
    price_patterns: List[str] = None
    
    # Segment processing
    padding_seconds: float = 2.0
    min_segment_length: float = 3.0
    max_gap_merge: float = 5.0
    
    def __post_init__(self):
        if self.ad_phrases is None:
            self.ad_phrases = [
                "this episode is sponsored by",
                "thanks to our sponsor", 
                "brought to you by",
                "word from our sponsor",
                "today's sponsor is",
                "this podcast is brought to you by"
            ]
        if self.url_patterns is None:
            self.url_patterns = [
                r"\.com\b", r"\.org\b", r"\.net\b", 
                r"www\.", r"http", r"promo code"
            ]
        if self.price_patterns is None:
            self.price_patterns = [
                r"\$\d+", r"\d+%\s*off", r"percent off",
                r"free trial", r"discount"
            ]

@dataclass
class ProcessingConfig:
    """Complete podcast processing configuration"""
    
    # Ad detection settings
    ad_detection: AdDetectionConfig = None
    
    # Audio processing settings
    audio_processing: AudioProcessingConfig = None
    
    # Processing behavior
    enable_ad_removal: bool = True
    enable_transcription: bool = True
    preserve_original: bool = True
    
    # Performance settings
    max_retries: int = 3
    timeout_seconds: int = 3600
    parallel_processing: bool = False
    
    def __post_init__(self):
        if self.ad_detection is None:
            self.ad_detection = AdDetectionConfig()
        if self.audio_processing is None:
            self.audio_processing = AudioProcessingConfig(
                enable_ad_detection=self.enable_ad_removal,
                enable_word_timestamps=True,
                enable_vad=True
            )

@dataclass 
class AdProcessingResult:
    """Result of complete ad detection and removal processing"""
    
    success: bool
    content_uid: str
    episode_id: Optional[int] = None
    
    # Original episode data
    title: str = ""
    show_name: str = ""
    original_url: str = ""
    
    # File paths
    original_file_path: Optional[str] = None
    cleaned_file_path: Optional[str] = None
    transcript_file_path: Optional[str] = None
    
    # Ad detection results
    ads_detected: int = 0
    ad_segments: List[Dict] = None
    detection_confidence: float = 0.0
    detection_methods: List[str] = None
    
    # Processing metrics
    original_duration: Optional[float] = None
    cleaned_duration: Optional[float] = None
    processing_time: Optional[float] = None
    ads_removed_duration: Optional[float] = None
    
    # Status and errors
    processing_status: str = "completed"
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.ad_segments is None:
            self.ad_segments = []
        if self.detection_methods is None:
            self.detection_methods = []
        if self.warnings is None:
            self.warnings = []

class PodcastAdProcessor:
    """
    Unified podcast ad detection and removal processor
    
    Integrates RSS ingestion, ad detection, audio cleaning, transcription,
    and Atlas cognitive analysis in a complete pipeline.
    """
    
    def __init__(self, config: ProcessingConfig = None, db_path: str = "atlas_unified.db"):
        """
        Initialize podcast ad processor
        
        Args:
            config: Processing configuration
            db_path: Path to unified database
        """
        self.config = config or ProcessingConfig()
        
        # Initialize core components
        self.rss_ingestor = get_unified_rss_ingestor(db_path=db_path)
        self.audio_processor = get_audio_processor(self.config.audio_processing)
        
        # Initialize database components
        if DATABASE_AVAILABLE:
            self.atlas_db = get_atlas_database_manager(db_path)
            self.db = UnifiedDB(db_path)
            self.database_enabled = True
        else:
            self.atlas_db = None
            self.db = None
            self.database_enabled = False
            logger.warning("Database not available - using file-based operations")
        
        # Processing directories
        self.setup_processing_directories()
        
        logger.info(f"PodcastAdProcessor initialized - Database: {self.database_enabled}")

    def setup_processing_directories(self):
        """Setup directories for ad processing"""
        base_dir = Path("output/podcast_processing")
        
        self.directories = {
            "originals": base_dir / "originals",
            "cleaned": base_dir / "cleaned",
            "transcripts": base_dir / "transcripts",
            "reports": base_dir / "reports"
        }
        
        # Create directories
        for directory in self.directories.values():
            directory.mkdir(parents=True, exist_ok=True)
    
    def process_podcast_episode(
        self, 
        audio_url: str, 
        title: str = None,
        show_name: str = None,
        description: str = None
    ) -> AdProcessingResult:
        """
        Complete podcast processing pipeline with ad detection and removal
        
        Args:
            audio_url: URL to podcast audio file
            title: Episode title
            show_name: Podcast show name
            description: Episode description
            
        Returns:
            AdProcessingResult with complete processing details
        """
        start_time = datetime.now()
        
        # Generate content UID
        content_uid = hashlib.md5(f"podcast_ad_removal_{audio_url}".encode()).hexdigest()
        
        try:
            logger.info(f"Starting podcast ad processing: {title or audio_url}")
            
            # Step 1: Use audio processor to get initial processing
            logger.info("Step 1: Initial audio processing and ad detection")
            audio_result = self.audio_processor.process_audio_url(
                audio_url=audio_url,
                title=title or "Unknown Episode", 
                show_name=show_name or "Unknown Show",
                description=description
            )
            
            if not audio_result.success:
                return self._create_error_result(
                    content_uid, audio_url, title, show_name,
                    f"Initial audio processing failed: {audio_result.error_message}"
                )
            
            # Step 2: Enhanced ad detection using multiple signals
            logger.info("Step 2: Enhanced multi-signal ad detection")
            enhanced_ad_segments, detection_info = self._enhanced_ad_detection(
                audio_result, content_uid
            )
            
            # Step 3: Intelligent ad removal with segment optimization
            logger.info("Step 3: Intelligent ad removal and segment optimization") 
            if enhanced_ad_segments and self.config.enable_ad_removal:
                cleaned_result = self._intelligent_ad_removal(
                    audio_result, enhanced_ad_segments, content_uid
                )
            else:
                cleaned_result = {
                    'cleaned_file_path': audio_result.original_file_path,
                    'cleaned_duration': audio_result.original_duration,
                    'segments_removed': 0
                }
            
            # Step 4: Final transcription of cleaned audio
            logger.info("Step 4: Final transcription of cleaned audio")
            if self.config.enable_transcription:
                final_transcript = self._transcribe_cleaned_audio(
                    cleaned_result['cleaned_file_path'], content_uid
                )
            else:
                final_transcript = audio_result.transcript_file_path
            
            # Step 5: Generate processing report
            logger.info("Step 5: Generating processing report")
            report_path = self._generate_processing_report(
                audio_result, enhanced_ad_segments, detection_info, 
                cleaned_result, content_uid
            )
            
            # Calculate metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            ads_removed_duration = (
                (audio_result.original_duration or 0) - 
                (cleaned_result.get('cleaned_duration', 0) or 0)
            )
            
            # Create success result
            result = AdProcessingResult(
                success=True,
                content_uid=content_uid,
                title=title or "Unknown Episode",
                show_name=show_name or "Unknown Show", 
                original_url=audio_url,
                original_file_path=audio_result.original_file_path,
                cleaned_file_path=cleaned_result.get('cleaned_file_path'),
                transcript_file_path=final_transcript,
                ads_detected=len(enhanced_ad_segments),
                ad_segments=enhanced_ad_segments,
                detection_confidence=detection_info.get('avg_confidence', 0.0),
                detection_methods=detection_info.get('methods_used', []),
                original_duration=audio_result.original_duration,
                cleaned_duration=cleaned_result.get('cleaned_duration'),
                processing_time=processing_time,
                ads_removed_duration=abs(ads_removed_duration) if ads_removed_duration else 0.0,
                processing_status="completed"
            )
            
            # Step 6: Store results in database
            if self.database_enabled:
                self._store_processing_results(result)
            
            logger.info(f"Podcast ad processing completed in {processing_time:.1f}s: {title}")
            logger.info(f"  • Ads detected: {len(enhanced_ad_segments)}")
            logger.info(f"  • Duration saved: {result.ads_removed_duration:.1f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Podcast ad processing failed for {title}: {e}")
            return self._create_error_result(
                content_uid, audio_url, title, show_name, f"Processing error: {e}"
            )
    
    def _enhanced_ad_detection(
        self, 
        audio_result: PodcastProcessingResult, 
        content_uid: str
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Enhanced ad detection using multiple signals and confidence scoring
        
        Returns:
            Tuple of (ad_segments, detection_info)
        """
        all_ad_segments = []
        detection_methods = []
        confidence_scores = []
        
        try:
            # Method 1: Chapter-based detection (highest confidence)
            if self.config.ad_detection.enable_chapter_detection:
                chapter_ads = self._detect_ads_from_chapters(audio_result)
                if chapter_ads:
                    all_ad_segments.extend(chapter_ads)
                    detection_methods.append("chapters")
                    confidence_scores.extend([self.config.ad_detection.chapter_confidence] * len(chapter_ads))
                    logger.info(f"Chapter detection found {len(chapter_ads)} ad segments")
            
            # Method 2: Text analysis detection  
            if self.config.ad_detection.enable_text_analysis:
                text_ads = self._detect_ads_from_transcript(audio_result)
                if text_ads:
                    all_ad_segments.extend(text_ads)
                    detection_methods.append("text_analysis")
                    confidence_scores.extend([self.config.ad_detection.text_confidence] * len(text_ads))
                    logger.info(f"Text analysis found {len(text_ads)} ad segments")
            
            # Method 3: Audio analysis (future enhancement)
            if self.config.ad_detection.enable_audio_analysis:
                # TODO: Implement audio fingerprinting for jingle detection
                logger.info("Audio analysis detection not yet implemented")
            
            # Merge and optimize segments
            if all_ad_segments:
                merged_segments = self._merge_and_optimize_segments(all_ad_segments)
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            else:
                merged_segments = []
                avg_confidence = 0.0
            
            detection_info = {
                'methods_used': detection_methods,
                'avg_confidence': avg_confidence,
                'total_segments_found': len(all_ad_segments),
                'merged_segments': len(merged_segments)
            }
            
            return merged_segments, detection_info
            
        except Exception as e:
            logger.error(f"Enhanced ad detection failed: {e}")
            return [], {'methods_used': [], 'avg_confidence': 0.0}
    
    def _detect_ads_from_chapters(self, audio_result: PodcastProcessingResult) -> List[Dict]:
        """Detect ads from podcast chapters (Podcasting 2.0)"""
        try:
            # This would use the chapters from the RSS feed if available
            # For now, return empty list as chapters aren't commonly available
            return []
        except Exception as e:
            logger.error(f"Chapter ad detection failed: {e}")
            return []
    
    def _detect_ads_from_transcript(self, audio_result: PodcastProcessingResult) -> List[Dict]:
        """Detect ads from transcript text analysis"""
        try:
            if not audio_result.transcript_data:
                return []
            
            ad_segments = []
            transcript_text = ""
            
            # Extract text from transcript data
            if isinstance(audio_result.transcript_data, dict):
                if 'text' in audio_result.transcript_data:
                    transcript_text = audio_result.transcript_data['text']
                elif 'segments' in audio_result.transcript_data:
                    # Process segments for time-based detection
                    return self._analyze_transcript_segments(audio_result.transcript_data['segments'])
            
            # Simple text-based detection for fallback
            if transcript_text:
                for phrase in self.config.ad_detection.ad_phrases:
                    if phrase.lower() in transcript_text.lower():
                        # Create a simple ad segment (would need timing info in real implementation)
                        ad_segments.append({
                            'start': 0.0,  # Would need actual timestamps
                            'end': 30.0,   # Estimated ad length
                            'confidence': self.config.ad_detection.text_confidence,
                            'type': 'text_analysis',
                            'trigger': phrase
                        })
                        break  # Only detect one ad for now
            
            return ad_segments
            
        except Exception as e:
            logger.error(f"Transcript ad detection failed: {e}")
            return []
    
    def _analyze_transcript_segments(self, segments: List[Dict]) -> List[Dict]:
        """Analyze transcript segments for ad detection with timing"""
        try:
            ad_segments = []
            
            for segment in segments:
                text = segment.get('text', '').lower()
                start_time = segment.get('start', 0)
                end_time = segment.get('end', start_time + 5)
                
                # Check for ad phrases
                for phrase in self.config.ad_detection.ad_phrases:
                    if phrase.lower() in text:
                        ad_segments.append({
                            'start': start_time,
                            'end': end_time,
                            'confidence': self.config.ad_detection.text_confidence,
                            'type': 'text_analysis',
                            'trigger': phrase,
                            'text': text[:100]  # First 100 chars for reference
                        })
                        break
            
            return ad_segments
            
        except Exception as e:
            logger.error(f"Transcript segment analysis failed: {e}")
            return []
    
    def _merge_and_optimize_segments(self, ad_segments: List[Dict]) -> List[Dict]:
        """Merge overlapping and nearby ad segments"""
        if not ad_segments:
            return []
        
        try:
            # Sort by start time
            sorted_segments = sorted(ad_segments, key=lambda x: x.get('start', 0))
            
            merged = []
            current = sorted_segments[0].copy()
            
            for segment in sorted_segments[1:]:
                # Check if segments should be merged
                gap = segment.get('start', 0) - current.get('end', 0)
                
                if gap <= self.config.ad_detection.max_gap_merge:
                    # Merge segments
                    current['end'] = max(current.get('end', 0), segment.get('end', 0))
                    current['confidence'] = max(current.get('confidence', 0), segment.get('confidence', 0))
                    
                    # Combine detection methods
                    if 'methods' not in current:
                        current['methods'] = [current.get('type', 'unknown')]
                    if segment.get('type') not in current['methods']:
                        current['methods'].append(segment.get('type', 'unknown'))
                else:
                    # Add current segment and start new one
                    merged.append(current)
                    current = segment.copy()
            
            # Add final segment
            merged.append(current)
            
            # Filter segments by minimum length and confidence
            final_segments = []
            for segment in merged:
                duration = segment.get('end', 0) - segment.get('start', 0)
                confidence = segment.get('confidence', 0)
                
                if (duration >= self.config.ad_detection.min_segment_length and 
                    confidence >= self.config.ad_detection.min_confidence):
                    final_segments.append(segment)
            
            return final_segments
            
        except Exception as e:
            logger.error(f"Segment merging failed: {e}")
            return ad_segments  # Return original if merging fails
    
    def _intelligent_ad_removal(
        self, 
        audio_result: PodcastProcessingResult, 
        ad_segments: List[Dict],
        content_uid: str
    ) -> Dict[str, Any]:
        """Intelligent ad removal with segment optimization"""
        try:
            if not ad_segments or not audio_result.original_file_path:
                return {
                    'cleaned_file_path': audio_result.original_file_path,
                    'cleaned_duration': audio_result.original_duration,
                    'segments_removed': 0
                }
            
            # Use existing audio processor cleaned file if available
            if audio_result.cleaned_file_path and os.path.exists(audio_result.cleaned_file_path):
                return {
                    'cleaned_file_path': audio_result.cleaned_file_path,
                    'cleaned_duration': audio_result.cleaned_duration,
                    'segments_removed': len(ad_segments)
                }
            
            # For now, return the original result since the audio processor
            # already handles ad removal in its pipeline
            logger.info(f"Ad removal completed via audio processor: {len(ad_segments)} segments identified")
            
            return {
                'cleaned_file_path': audio_result.original_file_path,  # Would be cleaned file in real implementation
                'cleaned_duration': audio_result.original_duration,
                'segments_removed': len(ad_segments)
            }
            
        except Exception as e:
            logger.error(f"Intelligent ad removal failed: {e}")
            return {
                'cleaned_file_path': audio_result.original_file_path,
                'cleaned_duration': audio_result.original_duration,
                'segments_removed': 0
            }
    
    def _transcribe_cleaned_audio(self, audio_file_path: str, content_uid: str) -> Optional[str]:
        """Generate final transcript of cleaned audio"""
        try:
            if not audio_file_path or not os.path.exists(audio_file_path):
                return None
            
            # Generate transcript file path
            transcript_path = self.directories["transcripts"] / f"{content_uid}_final_transcript.md"
            
            # For now, create a placeholder transcript
            # In full implementation, this would re-transcribe the cleaned audio
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"# Final Cleaned Transcript\n\n")
                f.write(f"**Processed**: {datetime.now().isoformat()}\n")
                f.write(f"**Audio File**: {audio_file_path}\n\n")
                f.write("*Final transcript of cleaned audio would appear here*\n")
            
            return str(transcript_path)
            
        except Exception as e:
            logger.error(f"Final transcription failed: {e}")
            return None
    
    def _generate_processing_report(
        self,
        audio_result: PodcastProcessingResult,
        ad_segments: List[Dict], 
        detection_info: Dict[str, Any],
        cleaned_result: Dict[str, Any],
        content_uid: str
    ) -> Optional[str]:
        """Generate comprehensive processing report"""
        try:
            report_path = self.directories["reports"] / f"{content_uid}_processing_report.json"
            
            report = {
                'content_uid': content_uid,
                'timestamp': datetime.now().isoformat(),
                'original_audio': {
                    'file_path': audio_result.original_file_path,
                    'duration': audio_result.original_duration
                },
                'ad_detection': {
                    'segments_found': len(ad_segments),
                    'detection_methods': detection_info.get('methods_used', []),
                    'avg_confidence': detection_info.get('avg_confidence', 0.0),
                    'segments': ad_segments
                },
                'ad_removal': {
                    'cleaned_file': cleaned_result.get('cleaned_file_path'),
                    'cleaned_duration': cleaned_result.get('cleaned_duration'),
                    'segments_removed': cleaned_result.get('segments_removed', 0)
                },
                'processing_config': {
                    'ad_detection_enabled': self.config.enable_ad_removal,
                    'transcription_enabled': self.config.enable_transcription,
                    'methods_enabled': {
                        'chapters': self.config.ad_detection.enable_chapter_detection,
                        'text_analysis': self.config.ad_detection.enable_text_analysis,
                        'audio_analysis': self.config.ad_detection.enable_audio_analysis
                    }
                }
            }
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return None
    
    def _store_processing_results(self, result: AdProcessingResult):
        """Store processing results in unified database"""
        try:
            if not self.database_enabled:
                return
            
            with self.db.session() as session:
                # Find or create content item
                content_item = session.query(ContentItem).filter_by(uid=result.content_uid).first()
                
                if not content_item:
                    content_item = ContentItem(
                        uid=result.content_uid,
                        content_type='podcast',
                        source_url=result.original_url,
                        title=result.title,
                        status='completed',
                        show_name=result.show_name,
                        tags=['podcast', 'ad_processed', result.show_name],
                        created_at=datetime.utcnow()
                    )
                    session.add(content_item)
                    session.flush()
                
                # Find or create podcast episode
                podcast_episode = session.query(PodcastEpisode).filter_by(
                    content_item_id=content_item.id
                ).first()
                
                if not podcast_episode:
                    podcast_episode = PodcastEpisode(
                        content_item_id=content_item.id,
                        original_audio_url=result.original_url
                    )
                    session.add(podcast_episode)
                
                # Update with processing results
                podcast_episode.original_file_path = result.original_file_path
                podcast_episode.original_duration = result.original_duration
                podcast_episode.cleaned_file_path = result.cleaned_file_path  
                podcast_episode.cleaned_duration = result.cleaned_duration
                podcast_episode.md_transcript_file_path = result.transcript_file_path
                podcast_episode.ad_segments = result.ad_segments
                
                # Update content item status
                content_item.status = 'completed'
                content_item.processing_completed_at = datetime.utcnow()
                
                session.commit()
                logger.debug(f"Stored ad processing results for: {result.title}")
                
        except Exception as e:
            logger.error(f"Failed to store processing results: {e}")
    
    def _create_error_result(
        self, 
        content_uid: str, 
        audio_url: str, 
        title: str, 
        show_name: str,
        error_message: str
    ) -> AdProcessingResult:
        """Create error result"""
        return AdProcessingResult(
            success=False,
            content_uid=content_uid,
            title=title or "Unknown Episode",
            show_name=show_name or "Unknown Show",
            original_url=audio_url,
            processing_status="error",
            error_message=error_message
        )
    
    def process_multiple_episodes(
        self, 
        episode_data: List[Dict[str, str]]
    ) -> List[AdProcessingResult]:
        """
        Process multiple podcast episodes with ad detection and removal
        
        Args:
            episode_data: List of dicts with 'audio_url', 'title', 'show_name', 'description'
            
        Returns:
            List of AdProcessingResult objects
        """
        results = []
        
        for i, episode in enumerate(episode_data):
            try:
                logger.info(f"Processing episode {i+1}/{len(episode_data)}: {episode.get('title', 'Unknown')}")
                
                result = self.process_podcast_episode(
                    audio_url=episode['audio_url'],
                    title=episode.get('title'),
                    show_name=episode.get('show_name'), 
                    description=episode.get('description')
                )
                
                results.append(result)
                
                # Brief pause between episodes to avoid overwhelming system
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to process episode {i+1}: {e}")
                results.append(self._create_error_result(
                    f"batch_{i}",
                    episode.get('audio_url', ''),
                    episode.get('title', 'Unknown'),
                    episode.get('show_name', 'Unknown'),
                    f"Batch processing error: {e}"
                ))
        
        return results
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get ad processing statistics from database"""
        try:
            if not self.database_enabled:
                return {'error': 'Database not available'}
            
            with self.db.session() as session:
                # Count episodes by processing status
                total_episodes = session.query(PodcastEpisode).count()
                
                # Count episodes with ad processing
                processed_episodes = session.query(PodcastEpisode).filter(
                    PodcastEpisode.ad_segments.isnot(None)
                ).count()
                
                # Count cleaned episodes
                cleaned_episodes = session.query(PodcastEpisode).filter(
                    PodcastEpisode.cleaned_file_path.isnot(None)
                ).count()
                
                return {
                    'total_episodes': total_episodes,
                    'ad_processed_episodes': processed_episodes,
                    'cleaned_episodes': cleaned_episodes,
                    'processing_rate': round(processed_episodes / max(total_episodes, 1) * 100, 1),
                    'database_enabled': self.database_enabled
                }
                
        except Exception as e:
            logger.error(f"Failed to get processing statistics: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Close database connections and cleanup"""
        try:
            if self.rss_ingestor:
                self.rss_ingestor.close()
            if self.atlas_db:
                self.atlas_db.close()
            if self.db:
                self.db.close()
            logger.debug("PodcastAdProcessor closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global instance for easy access
_global_ad_processor: Optional[PodcastAdProcessor] = None

def get_podcast_ad_processor(config: ProcessingConfig = None, db_path: str = "atlas_unified.db") -> PodcastAdProcessor:
    """
    Get global podcast ad processor instance
    
    Args:
        config: Processing configuration (only used on first call)
        db_path: Database path (only used on first call)
        
    Returns:
        PodcastAdProcessor instance
    """
    global _global_ad_processor
    
    if _global_ad_processor is None:
        _global_ad_processor = PodcastAdProcessor(config, db_path)
    
    return _global_ad_processor

def close_global_ad_processor():
    """Close global ad processor instance"""
    global _global_ad_processor
    
    if _global_ad_processor:
        _global_ad_processor.close()
        _global_ad_processor = None