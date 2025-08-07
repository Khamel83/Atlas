# 🎙️ Podcast Transcript Discovery System - Specification

*Version: 1.0*  
*Date: August 6, 2025*  
*Status: Ready for Implementation*

## 🎯 Overview

A comprehensive system to discover and extract podcast transcripts from multiple sources, eliminating the need for expensive transcription APIs. This system will leverage existing transcript sources like Podscribe, podcast websites, and search engines to build a complete transcript database for your podcast collection.

## 📋 Problem Statement

**Current Situation**:
- Atlas uses expensive transcription APIs (OpenRouter, Whisper) for podcast processing
- Many podcasts already have transcripts available online
- We're paying for transcription when free sources exist
- No systematic way to discover transcript availability

**Examples of Existing Transcript Sources**:
- **Podscribe**: https://app.podscribe.com/episode/136207434 (Bill Simmons)
- **Podcast Websites**: https://conversationswithtyler.com/episodes/
- **Rev.com**: Many shows upload transcripts here
- **Podcast Networks**: Ringer, Gimlet, NPR, etc. host transcripts

## 🎉 Solution Goals

1. **Discovery**: Find transcript sources for your podcast subscriptions
2. **Extraction**: Pull transcripts from discovered sources  
3. **Integration**: Feed transcripts into Atlas pipeline
4. **Cost Reduction**: Eliminate 70-90% of transcription API costs
5. **Quality**: Get human-quality transcripts vs AI transcription errors

## 🏗️ Architecture

### Phase 1: Transcript Discovery Engine
```
OPML Subscriptions → Google CSE Search → Transcript Source Database
```

### Phase 2: Multi-Source Extraction
```
Source Database → Targeted Scrapers → Raw Transcript Files → Atlas Integration
```

### Phase 3: Automation Pipeline
```
New Episodes → Auto-Discovery → Extract → Atlas Ingest → Processed Content
```

## 📁 Project Structure

```
Atlas/
├── podcast_transcripts/
│   ├── discovery/
│   │   ├── transcript_finder.py          # Main discovery engine
│   │   ├── google_cse_searcher.py        # Google Custom Search
│   │   ├── source_validators.py          # Validate transcript links
│   │   └── discovery_config.yaml         # Search patterns & domains
│   ├── extractors/
│   │   ├── podscribe_extractor.py        # Podscribe.com scraper
│   │   ├── generic_web_extractor.py      # General website transcripts
│   │   ├── rev_com_extractor.py          # Rev.com transcripts
│   │   └── podcast_site_extractor.py     # Native podcast site transcripts
│   ├── database/
│   │   ├── transcript_sources.csv        # Discovered sources
│   │   ├── extraction_status.csv         # Extraction tracking
│   │   └── failed_sources.csv           # Sources that failed
│   ├── output/
│   │   ├── transcripts/                  # Raw transcript files
│   │   └── atlas_ready/                  # Atlas-formatted files
│   └── config/
│       ├── search_patterns.yaml          # Discovery search terms
│       └── extraction_rules.yaml         # Site-specific extraction rules
```

## 🔧 Implementation Plan

### Stage 1: Discovery Engine (Week 1)
**Goal**: Find transcript sources for all podcasts in OPML

**Components**:
1. **OPML Parser**: Extract podcast names and RSS URLs
2. **Google CSE Integration**: Search for "[Podcast Name] transcript" 
3. **Source Validator**: Check if links actually contain transcripts
4. **Database Builder**: Store discovered sources with metadata

**Output**: `transcript_sources.csv` with columns:
- Podcast Name
- RSS URL  
- Has Transcripts (Boolean)
- Source Type (Podscribe, Website, Rev, etc.)
- Example Transcript URL
- Confidence Score
- Last Checked

### Stage 2: Multi-Source Extractors (Week 2)
**Goal**: Extract transcripts from discovered sources

**Site-Specific Extractors**:

1. **Podscribe Extractor**
   - Pattern: `app.podscribe.com/episode/*`
   - Method: Direct API or HTML scraping
   - Success Rate: Very High

2. **Podcast Website Extractor**  
   - Examples: conversationswithtyler.com, samharris.org
   - Method: Custom scraping per site
   - Success Rate: High

3. **Rev.com Extractor**
   - Pattern: `rev.com/transcript/*`  
   - Method: HTML parsing
   - Success Rate: High

4. **Generic Web Extractor**
   - Method: Intelligent text extraction
   - Fallback for unknown sites
   - Success Rate: Medium

### Stage 3: Atlas Integration (Week 3)
**Goal**: Feed discovered transcripts into Atlas pipeline

**Integration Points**:
1. **Format Converter**: Transform scraped transcripts to Atlas format
2. **Metadata Enricher**: Add source attribution and quality scores
3. **Deduplication**: Avoid processing same episodes multiple times
4. **Quality Assurance**: Validate transcript completeness

### Stage 4: Automation Pipeline (Week 4)
**Goal**: Automatically process new episodes

**Automation Features**:
1. **RSS Monitoring**: Watch for new episodes
2. **Auto-Discovery**: Search for transcripts of new episodes
3. **Batch Processing**: Process multiple episodes efficiently
4. **Error Handling**: Graceful failure and retry logic

## 📊 Expected Results

### Discovery Phase Results
Based on podcast transcript availability research:

**Expected Discovery Rates**:
- **Popular Podcasts** (Joe Rogan, Bill Simmons): 90-95% transcript availability
- **Interview Shows** (Tyler Cowen, Sam Harris): 80-90% availability  
- **News/Politics** (NYT Daily, Pod Save America): 70-85% availability
- **Niche/Technical**: 30-60% availability
- **Overall Average**: 60-75% of podcasts have some transcript source

### Cost Reduction Analysis
**Current Transcription Costs** (estimated):
- OpenRouter API: ~$0.02-0.05 per minute
- Average podcast: 60 minutes = $1.20-3.00 per episode
- Processing 100 episodes/month = $120-300/month

**Post-Implementation Costs**:
- 70% episodes use free transcripts = $36-90/month savings
- **Annual Savings**: $1,000-2,500+ 

### Quality Improvements
**Free Transcript Sources Often Superior**:
- Human-generated vs AI transcription
- Speaker identification included
- Proper punctuation and formatting
- Technical terms spelled correctly
- Time stamps often included

## 🔍 Technical Specifications

### Google Custom Search Engine Setup
```yaml
CSE Configuration:
  - Sites to search: "www.google.com" (universal)
  - Search terms: 
    - "[Podcast Name] transcript"
    - "[Podcast Name] full transcript"
    - "site:podscribe.com [Podcast Name]"
    - "site:rev.com [Podcast Name]"
    - "[Host Name] transcript"
```

### API Requirements
```bash
# Required APIs
GOOGLE_CSE_API_KEY=your_api_key
GOOGLE_CSE_ID=your_cse_id

# Optional APIs for enhanced extraction
PODSCRIBE_API_KEY=optional_key  # If they have API
REV_API_KEY=optional_key       # If available
```

### Rate Limiting
```python
# Google CSE: 100 queries/day free, 10,000 paid
SEARCH_DELAY = 1.5  # seconds between searches
DAILY_QUOTA = 100   # free tier limit

# Scraping rate limits per site
PODSCRIBE_DELAY = 2.0
GENERIC_SITE_DELAY = 3.0
```

## 📋 Database Schema

### transcript_sources.csv
```csv
podcast_name,rss_url,has_transcripts,source_type,example_url,confidence,last_checked,episodes_found,extraction_success_rate
"The Bill Simmons Podcast","http://feeds.megaphone.fm/BS",True,"Podscribe","https://app.podscribe.com/episode/136207434",0.95,"2025-08-06",150,0.92
"Conversations with Tyler","https://conversationswithtyler.libsyn.com/rss",True,"Website","https://conversationswithtyler.com/episodes/",0.98,"2025-08-06",200,0.96
```

### extraction_status.csv
```csv
podcast_name,episode_title,episode_url,transcript_url,extraction_status,transcript_file,character_count,extracted_at
"Joe Rogan Experience","#2156 - Jeremie Harris","spotify.com/episode/abc","podscribe.com/episode/123","success","output/jre_2156.md",45000,"2025-08-06 14:30:00"
```

## 🧪 Testing Strategy

### Discovery Testing
1. **Accuracy Test**: Manual verification of transcript links for 50 popular podcasts
2. **Coverage Test**: Discovery rate across different podcast categories
3. **False Positive Test**: Verification that "transcript" links actually contain transcripts

### Extraction Testing  
1. **Site Reliability**: Test extractors against 10-20 episodes per source
2. **Content Quality**: Compare extracted transcripts vs API transcription
3. **Error Handling**: Test behavior with broken links, rate limits, site changes

### Integration Testing
1. **Atlas Compatibility**: Ensure extracted transcripts work in Atlas pipeline
2. **Format Consistency**: Verify all extractors produce consistent output format
3. **Performance**: Test processing speed vs current transcription pipeline

## 🚨 Risk Mitigation

### Technical Risks
**Risk**: Websites change structure, breaking extractors  
**Mitigation**: Modular extractor design, easy to update individual scrapers

**Risk**: Rate limiting blocks discovery  
**Mitigation**: Respectful delays, distribute across multiple days

**Risk**: Legal concerns with scraping  
**Mitigation**: Respect robots.txt, focus on publicly available transcripts

### Operational Risks
**Risk**: Discovery finds low-quality transcripts  
**Mitigation**: Quality scoring system, fallback to AI transcription

**Risk**: Maintenance overhead  
**Mitigation**: Focus on high-success sources first, generic extractors

## 📈 Success Metrics

### Key Performance Indicators
1. **Discovery Success Rate**: % of podcasts with found transcript sources
2. **Extraction Success Rate**: % of transcript URLs successfully extracted
3. **Cost Reduction**: Monthly transcription API savings
4. **Quality Score**: User rating of transcript quality vs AI transcription
5. **Coverage**: % of new episodes processed via discovered transcripts

### Target Goals (6 months)
- **70%** of podcast episodes processed via discovered transcripts
- **$200+** monthly cost savings
- **95%** extraction success rate for discovered sources
- **<2 hours** average discovery time for new podcast additions

## 🚀 Getting Started

### Prerequisites
1. Google Cloud Console account (for CSE API)
2. Atlas environment set up
3. OPML file with podcast subscriptions
4. Basic Python development environment

### Quick Start Commands
```bash
# 1. Set up Google CSE
# Follow: https://programmablesearchengine.google.com/

# 2. Configure environment
cp .env.example .env
# Add GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID

# 3. Run discovery
python3 podcast_transcripts/discovery/transcript_finder.py

# 4. Review results
open podcast_transcripts/database/transcript_sources.csv

# 5. Run extraction for high-confidence sources  
python3 podcast_transcripts/run_extraction.py --confidence-min 0.8

# 6. Check Atlas integration
python3 podcast_transcripts/atlas_integration.py
```

## 🔄 Future Enhancements

### Phase 2 Features
1. **Smart Episode Matching**: Match RSS episodes to transcript URLs
2. **Transcript Quality Scoring**: Rate transcript accuracy and completeness  
3. **Community Database**: Share transcript source discoveries
4. **Real-time Monitoring**: Alert when new transcript sources become available

### Phase 3 Advanced Features
1. **Machine Learning**: Predict transcript availability for new podcasts
2. **OCR Integration**: Extract transcripts from PDF/image sources
3. **Multi-language Support**: Discover transcripts in different languages
4. **Sponsor Segment Detection**: Identify and skip/tag sponsor content

## 📝 Implementation Notes

This spec provides a complete roadmap for building a podcast transcript discovery system that could:

1. **Save significant costs** by using existing free transcript sources
2. **Improve quality** by using human-generated transcripts
3. **Scale efficiently** through automated discovery and extraction
4. **Integrate seamlessly** with existing Atlas infrastructure

The modular design allows for incremental implementation - start with discovery, add extractors one source at a time, then build automation.

---

**Next Steps**: Ready for implementation! This spec provides everything needed to build a comprehensive podcast transcript discovery system.

*Saved as: `PODCAST_TRANSCRIPT_DISCOVERY_SPEC.md`*