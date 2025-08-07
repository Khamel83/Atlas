#!/usr/bin/env python3
"""
Podcast Transcript Discovery System

Intelligent discovery and extraction of podcast transcripts from multiple sources,
eliminating the need for expensive transcription APIs by finding existing transcripts online.

This system integrates with Atlas unified database and podcast processing pipeline
to provide cost-effective, high-quality transcripts for cognitive analysis.

Usage:
    from helpers.transcript_discovery import TranscriptDiscoveryEngine, DiscoveryConfig
    
    # Initialize discovery engine
    engine = TranscriptDiscoveryEngine()
    
    # Discover transcripts for all podcasts
    results = engine.discover_all_transcripts()
    
    # Extract specific transcript
    transcript = engine.extract_transcript(source_url)
"""

import os
import re
import json
import csv
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET

# Atlas imports
from helpers.atlas_database_helper import get_atlas_database_manager
from helpers.podcast_rss_unified import get_unified_rss_ingestor

# Database integration
try:
    from database_integration import ContentItem, PodcastEpisode
    from database_integration.database import UnifiedDB
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Web scraping
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class TranscriptSource:
    """Information about a discovered transcript source"""
    
    podcast_name: str
    rss_url: str = ""
    source_type: str = "unknown"  # podscribe, website, rev, native
    source_url: str = ""
    example_transcript_url: str = ""
    has_transcripts: bool = False
    confidence_score: float = 0.0
    last_checked: datetime = None
    extraction_pattern: str = ""
    notes: str = ""
    
    def __post_init__(self):
        if self.last_checked is None:
            self.last_checked = datetime.now()

@dataclass  
class TranscriptResult:
    """Result of transcript extraction"""
    
    success: bool
    source_url: str
    podcast_name: str = ""
    episode_title: str = ""
    transcript_text: str = ""
    transcript_file_path: str = ""
    extraction_method: str = ""
    confidence_score: float = 0.0
    error_message: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class DiscoveryConfig:
    """Configuration for transcript discovery"""
    
    # Search settings
    enable_google_search: bool = False  # Requires API key
    enable_website_crawling: bool = True
    enable_podscribe_search: bool = True
    enable_rev_search: bool = True
    
    # Known transcript domains
    transcript_domains: List[str] = None
    
    # Search patterns
    search_patterns: List[str] = None
    
    # Request settings
    request_timeout: int = 30
    max_retries: int = 3
    delay_between_requests: float = 1.0
    
    # Quality thresholds
    min_confidence_score: float = 0.7
    min_transcript_length: int = 100
    
    def __post_init__(self):
        if self.transcript_domains is None:
            self.transcript_domains = [
                'podscribe.com',
                'rev.com', 
                'otter.ai',
                'descript.com',
                'conversationswithtyler.com',
                'theringer.com',
                'gimletmedia.com',
                'thisamericanlife.org',
                'npr.org'
            ]
        
        if self.search_patterns is None:
            self.search_patterns = [
                '{podcast_name} transcript',
                '{podcast_name} transcription', 
                'site:podscribe.com {podcast_name}',
                'site:rev.com {podcast_name}',
                '{podcast_name} "full transcript"'
            ]

class TranscriptDiscoveryEngine:
    """
    Main engine for discovering and extracting podcast transcripts
    
    Integrates with Atlas database and provides multiple discovery methods
    including direct website parsing, search engines, and known transcript sources.
    """
    
    def __init__(self, config: DiscoveryConfig = None, db_path: str = "atlas_unified.db"):
        """
        Initialize transcript discovery engine
        
        Args:
            config: Discovery configuration
            db_path: Path to unified database
        """
        self.config = config or DiscoveryConfig()
        
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
        
        # Setup directories
        self.setup_directories()
        
        # Initialize session for web requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Atlas-Transcript-Discovery/1.0 (+https://github.com/Khamel83/Atlas)'
        })
        
        logger.info(f"TranscriptDiscoveryEngine initialized - Database: {self.database_enabled}")
    
    def setup_directories(self):
        """Setup directories for transcript discovery"""
        base_dir = Path("podcast_transcripts")
        
        self.directories = {
            "discovery": base_dir / "discovery",
            "extractors": base_dir / "extractors", 
            "database": base_dir / "database",
            "output": base_dir / "output" / "transcripts",
            "atlas_ready": base_dir / "output" / "atlas_ready"
        }
        
        # Create directories
        for directory in self.directories.values():
            directory.mkdir(parents=True, exist_ok=True)
    
    def discover_all_transcripts(self) -> List[TranscriptSource]:
        """
        Discover transcript sources for all podcasts in the system
        
        Returns:
            List of discovered transcript sources
        """
        try:
            logger.info("Starting comprehensive transcript discovery")
            
            # Get podcast list from database or RSS feeds
            podcasts = self._get_podcast_list()
            
            if not podcasts:
                logger.warning("No podcasts found for transcript discovery")
                return []
            
            discovered_sources = []
            
            for i, podcast in enumerate(podcasts):
                try:
                    logger.info(f"Discovering transcripts for {podcast['name']} ({i+1}/{len(podcasts)})")
                    
                    sources = self._discover_podcast_transcripts(podcast)
                    discovered_sources.extend(sources)
                    
                    # Brief delay to be respectful
                    import time
                    time.sleep(self.config.delay_between_requests)
                    
                except Exception as e:
                    logger.error(f"Failed to discover transcripts for {podcast['name']}: {e}")
            
            # Save discovered sources
            self._save_discovered_sources(discovered_sources)
            
            logger.info(f"Transcript discovery completed: {len(discovered_sources)} sources found")
            return discovered_sources
            
        except Exception as e:
            logger.error(f"Transcript discovery failed: {e}")
            return []
    
    def _get_podcast_list(self) -> List[Dict[str, str]]:
        """Get list of podcasts from database or RSS feeds"""
        try:
            podcasts = []
            
            if self.database_enabled:
                # Get from database
                with self.db.session() as session:
                    podcast_episodes = session.query(PodcastEpisode).distinct(PodcastEpisode.show_author).all()
                    
                    for episode in podcast_episodes:
                        if episode.show_author:
                            podcasts.append({
                                'name': episode.show_author,
                                'rss_url': episode.original_audio_url or ''
                            })
            
            # Fallback: try to get from OPML file if it exists
            opml_path = Path("inputs/podcasts.opml")
            if opml_path.exists():
                opml_podcasts = self._parse_opml_file(str(opml_path))
                podcasts.extend(opml_podcasts)
            
            # Remove duplicates
            seen = set()
            unique_podcasts = []
            for podcast in podcasts:
                key = podcast['name'].lower()
                if key not in seen:
                    seen.add(key)
                    unique_podcasts.append(podcast)
            
            return unique_podcasts
            
        except Exception as e:
            logger.error(f"Failed to get podcast list: {e}")
            return []
    
    def _parse_opml_file(self, opml_path: str) -> List[Dict[str, str]]:
        """Parse OPML file to extract podcast information"""
        try:
            podcasts = []
            tree = ET.parse(opml_path)
            root = tree.getroot()
            
            for outline in root.findall('.//outline[@type="rss"]'):
                title = outline.get('title') or outline.get('text', '')
                rss_url = outline.get('xmlUrl', '')
                
                if title and rss_url:
                    podcasts.append({
                        'name': title,
                        'rss_url': rss_url
                    })
            
            return podcasts
            
        except Exception as e:
            logger.error(f"Failed to parse OPML file: {e}")
            return []
    
    def _discover_podcast_transcripts(self, podcast: Dict[str, str]) -> List[TranscriptSource]:
        """Discover transcript sources for a specific podcast"""
        sources = []
        podcast_name = podcast['name']
        rss_url = podcast.get('rss_url', '')
        
        try:
            # Method 1: Check Podscribe
            if self.config.enable_podscribe_search:
                podscribe_source = self._check_podscribe(podcast_name, rss_url)
                if podscribe_source:
                    sources.append(podscribe_source)
            
            # Method 2: Check Rev.com
            if self.config.enable_rev_search:
                rev_source = self._check_rev_com(podcast_name, rss_url)
                if rev_source:
                    sources.append(rev_source)
            
            # Method 3: Check podcast website for native transcripts
            if self.config.enable_website_crawling:
                website_source = self._check_podcast_website(podcast_name, rss_url)
                if website_source:
                    sources.append(website_source)
            
            # Method 4: Google Search (if API key available)
            if self.config.enable_google_search:
                search_sources = self._search_transcripts(podcast_name, rss_url)
                sources.extend(search_sources)
            
        except Exception as e:
            logger.error(f"Error discovering transcripts for {podcast_name}: {e}")
        
        return sources
    
    def _check_podscribe(self, podcast_name: str, rss_url: str) -> Optional[TranscriptSource]:
        """Check if podcast has transcripts on Podscribe"""
        try:
            # Search Podscribe for the podcast
            search_url = f"https://app.podscribe.com/search?q={requests.utils.quote(podcast_name)}"
            
            response = self.session.get(search_url, timeout=self.config.request_timeout)
            if response.status_code != 200:
                return None
            
            # Simple check for podcast presence (would need real parsing in production)
            if podcast_name.lower() in response.text.lower():
                return TranscriptSource(
                    podcast_name=podcast_name,
                    rss_url=rss_url,
                    source_type="podscribe",
                    source_url="https://app.podscribe.com",
                    example_transcript_url=search_url,
                    has_transcripts=True,
                    confidence_score=0.8,
                    extraction_pattern="podscribe_api",
                    notes="Found via Podscribe search"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking Podscribe for {podcast_name}: {e}")
            return None
    
    def _check_rev_com(self, podcast_name: str, rss_url: str) -> Optional[TranscriptSource]:
        """Check if podcast has transcripts on Rev.com"""
        try:
            # Rev.com search (simplified - would need proper API integration)
            search_terms = [
                podcast_name,
                podcast_name.replace(" ", "+"),
                f'"{podcast_name}"'
            ]
            
            for term in search_terms:
                search_url = f"https://www.rev.com/search?q={requests.utils.quote(term)}"
                
                try:
                    response = self.session.get(search_url, timeout=self.config.request_timeout)
                    if response.status_code == 200 and podcast_name.lower() in response.text.lower():
                        return TranscriptSource(
                            podcast_name=podcast_name,
                            rss_url=rss_url,
                            source_type="rev",
                            source_url="https://www.rev.com",
                            example_transcript_url=search_url,
                            has_transcripts=True,
                            confidence_score=0.7,
                            extraction_pattern="rev_scraper",
                            notes="Found via Rev.com search"
                        )
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking Rev.com for {podcast_name}: {e}")
            return None
    
    def _check_podcast_website(self, podcast_name: str, rss_url: str) -> Optional[TranscriptSource]:
        """Check if podcast has transcripts on its own website"""
        try:
            if not rss_url:
                return None
            
            # Try to find the main website from RSS URL
            domain = urlparse(rss_url).netloc
            website_url = f"https://{domain}"
            
            # Check main website
            response = self.session.get(website_url, timeout=self.config.request_timeout)
            if response.status_code != 200:
                return None
            
            # Look for transcript indicators
            transcript_indicators = [
                'transcript', 'transcription', 'full text', 
                'episode text', 'show notes', 'complete text'
            ]
            
            content_lower = response.text.lower()
            found_indicators = [ind for ind in transcript_indicators if ind in content_lower]
            
            if found_indicators:
                confidence = min(0.9, len(found_indicators) * 0.3)
                
                return TranscriptSource(
                    podcast_name=podcast_name,
                    rss_url=rss_url,
                    source_type="website",
                    source_url=website_url,
                    example_transcript_url=website_url,
                    has_transcripts=True,
                    confidence_score=confidence,
                    extraction_pattern="website_scraper",
                    notes=f"Found indicators: {', '.join(found_indicators)}"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking website for {podcast_name}: {e}")
            return None
    
    def _search_transcripts(self, podcast_name: str, rss_url: str) -> List[TranscriptSource]:
        """Search for transcripts using search engines (placeholder for Google CSE)"""
        try:
            # This would integrate with Google Custom Search Engine
            # For now, return placeholder indicating search capability
            
            return [TranscriptSource(
                podcast_name=podcast_name,
                rss_url=rss_url,
                source_type="search",
                source_url="google_cse",
                example_transcript_url="",
                has_transcripts=False,
                confidence_score=0.5,
                extraction_pattern="search_based",
                notes="Google CSE integration needed"
            )]
            
        except Exception as e:
            logger.error(f"Error searching for {podcast_name}: {e}")
            return []
    
    def _save_discovered_sources(self, sources: List[TranscriptSource]):
        """Save discovered sources to CSV database"""
        try:
            csv_path = self.directories["database"] / "transcript_sources.csv"
            
            # Write CSV header and data
            fieldnames = [
                'podcast_name', 'rss_url', 'source_type', 'source_url',
                'example_transcript_url', 'has_transcripts', 'confidence_score',
                'last_checked', 'extraction_pattern', 'notes'
            ]
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for source in sources:
                    writer.writerow(asdict(source))
            
            logger.info(f"Saved {len(sources)} discovered sources to {csv_path}")
            
        except Exception as e:
            logger.error(f"Failed to save discovered sources: {e}")
    
    def extract_transcript(
        self, 
        source_url: str, 
        extraction_method: str = "auto"
    ) -> TranscriptResult:
        """
        Extract transcript from a discovered source
        
        Args:
            source_url: URL of the transcript source
            extraction_method: Method to use (auto, podscribe, website, rev)
            
        Returns:
            TranscriptResult with extracted transcript
        """
        try:
            logger.info(f"Extracting transcript from: {source_url}")
            
            # Determine extraction method
            if extraction_method == "auto":
                extraction_method = self._determine_extraction_method(source_url)
            
            # Extract based on method
            if extraction_method == "podscribe":
                return self._extract_podscribe_transcript(source_url)
            elif extraction_method == "website":
                return self._extract_website_transcript(source_url)
            elif extraction_method == "rev":
                return self._extract_rev_transcript(source_url)
            else:
                return self._extract_generic_transcript(source_url)
            
        except Exception as e:
            logger.error(f"Transcript extraction failed for {source_url}: {e}")
            return TranscriptResult(
                success=False,
                source_url=source_url,
                error_message=f"Extraction error: {e}"
            )
    
    def _determine_extraction_method(self, source_url: str) -> str:
        """Determine the best extraction method based on URL"""
        domain = urlparse(source_url).netloc.lower()
        
        if 'podscribe.com' in domain:
            return 'podscribe'
        elif 'rev.com' in domain:
            return 'rev'
        else:
            return 'website'
    
    def _extract_podscribe_transcript(self, source_url: str) -> TranscriptResult:
        """Extract transcript from Podscribe"""
        try:
            # This would implement Podscribe API/scraping
            # For now, return a placeholder result
            
            return TranscriptResult(
                success=False,
                source_url=source_url,
                extraction_method="podscribe",
                error_message="Podscribe extraction not yet implemented"
            )
            
        except Exception as e:
            return TranscriptResult(
                success=False,
                source_url=source_url,
                extraction_method="podscribe",
                error_message=f"Podscribe extraction error: {e}"
            )
    
    def _extract_website_transcript(self, source_url: str) -> TranscriptResult:
        """Extract transcript from website"""
        try:
            if not BEAUTIFULSOUP_AVAILABLE:
                return TranscriptResult(
                    success=False,
                    source_url=source_url,
                    extraction_method="website",
                    error_message="BeautifulSoup not available for web scraping"
                )
            
            response = self.session.get(source_url, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for transcript content
            transcript_text = self._extract_text_from_soup(soup)
            
            if len(transcript_text) >= self.config.min_transcript_length:
                # Save transcript
                transcript_file = self._save_transcript(transcript_text, source_url, "website")
                
                return TranscriptResult(
                    success=True,
                    source_url=source_url,
                    transcript_text=transcript_text,
                    transcript_file_path=transcript_file,
                    extraction_method="website",
                    confidence_score=0.8
                )
            else:
                return TranscriptResult(
                    success=False,
                    source_url=source_url,
                    extraction_method="website",
                    error_message="Transcript text too short or not found"
                )
            
        except Exception as e:
            return TranscriptResult(
                success=False,
                source_url=source_url,
                extraction_method="website",
                error_message=f"Website extraction error: {e}"
            )
    
    def _extract_rev_transcript(self, source_url: str) -> TranscriptResult:
        """Extract transcript from Rev.com"""
        try:
            # This would implement Rev.com specific extraction
            # For now, return a placeholder
            
            return TranscriptResult(
                success=False,
                source_url=source_url,
                extraction_method="rev",
                error_message="Rev.com extraction not yet implemented"
            )
            
        except Exception as e:
            return TranscriptResult(
                success=False,
                source_url=source_url,
                extraction_method="rev",
                error_message=f"Rev extraction error: {e}"
            )
    
    def _extract_generic_transcript(self, source_url: str) -> TranscriptResult:
        """Generic transcript extraction"""
        try:
            # Fallback to website extraction
            return self._extract_website_transcript(source_url)
            
        except Exception as e:
            return TranscriptResult(
                success=False,
                source_url=source_url,
                extraction_method="generic",
                error_message=f"Generic extraction error: {e}"
            )
    
    def _extract_text_from_soup(self, soup) -> str:
        """Extract transcript text from BeautifulSoup object"""
        # Look for common transcript containers
        transcript_selectors = [
            '.transcript',
            '#transcript', 
            '.episode-transcript',
            '.show-transcript',
            '.post-content',
            'article',
            '.content'
        ]
        
        for selector in transcript_selectors:
            elements = soup.select(selector)
            if elements:
                return ' '.join(elem.get_text(strip=True) for elem in elements)
        
        # Fallback: extract all text and clean it
        text = soup.get_text()
        
        # Clean up text
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line and len(line) > 10]
        
        return '\n'.join(lines)
    
    def _save_transcript(self, transcript_text: str, source_url: str, method: str) -> str:
        """Save transcript to file"""
        try:
            # Generate filename
            url_hash = hashlib.md5(source_url.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transcript_{method}_{url_hash}_{timestamp}.md"
            
            file_path = self.directories["output"] / filename
            
            # Write transcript
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Transcript\n\n")
                f.write(f"**Source:** {source_url}\n")
                f.write(f"**Method:** {method}\n")
                f.write(f"**Extracted:** {datetime.now().isoformat()}\n\n")
                f.write("---\n\n")
                f.write(transcript_text)
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")
            return ""
    
    def get_discovery_statistics(self) -> Dict[str, Any]:
        """Get transcript discovery statistics"""
        try:
            csv_path = self.directories["database"] / "transcript_sources.csv"
            
            if not csv_path.exists():
                return {
                    'total_podcasts_checked': 0,
                    'sources_with_transcripts': 0,
                    'sources_by_type': {},
                    'average_confidence': 0.0
                }
            
            # Read CSV and analyze
            sources = []
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                sources = list(reader)
            
            total_podcasts = len(sources)
            with_transcripts = len([s for s in sources if s.get('has_transcripts') == 'True'])
            
            # Group by source type
            sources_by_type = {}
            confidences = []
            
            for source in sources:
                source_type = source.get('source_type', 'unknown')
                sources_by_type[source_type] = sources_by_type.get(source_type, 0) + 1
                
                try:
                    confidence = float(source.get('confidence_score', 0))
                    if confidence > 0:
                        confidences.append(confidence)
                except:
                    pass
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                'total_podcasts_checked': total_podcasts,
                'sources_with_transcripts': with_transcripts,
                'transcript_availability_rate': round(with_transcripts / max(total_podcasts, 1) * 100, 1),
                'sources_by_type': sources_by_type,
                'average_confidence': round(avg_confidence, 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get discovery statistics: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Close database connections and cleanup"""
        try:
            if self.atlas_db:
                self.atlas_db.close()
            if self.db:
                self.db.close()
            if self.session:
                self.session.close()
            logger.debug("TranscriptDiscoveryEngine closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global instance for easy access
_global_discovery_engine: Optional[TranscriptDiscoveryEngine] = None

def get_transcript_discovery_engine(config: DiscoveryConfig = None, db_path: str = "atlas_unified.db") -> TranscriptDiscoveryEngine:
    """
    Get global transcript discovery engine instance
    
    Args:
        config: Discovery configuration (only used on first call)
        db_path: Database path (only used on first call)
        
    Returns:
        TranscriptDiscoveryEngine instance
    """
    global _global_discovery_engine
    
    if _global_discovery_engine is None:
        _global_discovery_engine = TranscriptDiscoveryEngine(config, db_path)
    
    return _global_discovery_engine

def close_global_discovery_engine():
    """Close global discovery engine instance"""
    global _global_discovery_engine
    
    if _global_discovery_engine:
        _global_discovery_engine.close()
        _global_discovery_engine = None