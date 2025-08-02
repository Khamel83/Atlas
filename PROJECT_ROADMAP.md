# Atlas Project Roadmap
*The Single Source of Truth for Atlas Development*

**Last Updated**: January 2025  
**Document Status**: Authoritative - All project planning references this document  
**Project Phase**: Critical Implementation Phase

## Executive Summary

Atlas is a sophisticated local-first content ingestion and cognitive amplification platform that is **95% architecturally complete** but requires critical implementation work to bridge documentation and actual functionality. The system has excellent foundational architecture but needs focused development to deliver on its cognitive amplification promises.

**Current Status**: 4 critical implementation gaps block core cognitive features  
**Estimated Resolution**: 57-89 hours of focused development (6-9 weeks)  
**Next Milestone**: Fully functional cognitive amplification platform

## Project Vision and Goals

### Core Mission
Transform how users interact with and derive insights from their personal knowledge base through:
- **Local-first processing** that preserves privacy and data ownership
- **Cognitive amplification** that helps users think better, not just store more
- **Intelligent content curation** that surfaces relevant information proactively
- **Seamless multi-format ingestion** from web, audio, video, and document sources

### Strategic Objectives
1. **Privacy-First Architecture**: All processing happens locally, no cloud dependency for core features
2. **Cognitive Enhancement**: Provide tools that amplify human thinking and insight generation
3. **Seamless Integration**: Work with existing workflows and content sources
4. **Extensible Platform**: Support plugins and custom integrations
5. **User Empowerment**: Users maintain full control over their data and AI interactions

## Current Status Summary

### ✅ What Works Today

#### **Core Ingestion Pipeline**
- **Article Fetching** (`helpers/article_fetcher.py`) - 929 lines, multi-layered fallback system
  - Direct HTTP requests → 12ft.io bypass → Archive.today → Googlebot spoofing → Playwright → Wayback Machine
  - Content extraction using readability and BeautifulSoup
  - Comprehensive metadata generation and retry queue integration

- **YouTube Integration** (`helpers/youtube_ingestor.py`) - 545 lines, robust implementation
  - Transcript extraction using youtube-transcript-api
  - Video metadata extraction with fallback to yt-dlp
  - Retry mechanisms for failed downloads

- **Podcast Processing** (`helpers/podcast_ingestor.py`) - 267 lines, complete implementation
  - OPML parsing for podcast feeds
  - Audio download and storage with transcription integration
  - Episode metadata extraction and management

#### **Supporting Infrastructure**
- **Configuration Management** (`helpers/config.py`) - Environment and settings handling
- **Safety Monitoring** (`helpers/safety_monitor.py`) - Pre-run safety checks
- **Error Handling** (`helpers/error_handler.py`) - Centralized error management
- **Path Management** (`helpers/path_manager.py`) - File organization and backup
- **Retry System** (`helpers/retry_queue.py`) - Failed item recovery

#### **Advanced Architecture**
- **Base Ingestor** (`helpers/base_ingestor.py`) - Template method pattern for extensibility
- **Metadata Manager** (`helpers/metadata_manager.py`) - Standardized metadata handling
- **Article Strategies** (`helpers/article_strategies.py`) - Strategy pattern for content extraction
- **Transcription System** - Multiple backends (OpenRouter, local Whisper, helpers)

#### **Processing Pipeline**
- **Content Categorization** (`helpers/categorize.py`) - Automatic content classification
- **Evaluation System** (`process/evaluate.py`) - Content quality assessment
- **Recategorization** (`process/recategorize.py`) - Dynamic content reorganization

#### **Cognitive Amplification Foundation**
- **Ask Subsystems** - All 5 core cognitive modules implemented:
  - ProactiveSurfacer - Surfaces forgotten/stale content for review
  - TemporalEngine - Finds time-aware relationships between content
  - QuestionEngine - Generates Socratic questions for deeper thinking
  - RecallEngine - Schedules spaced repetition for knowledge retention
  - PatternDetector - Identifies patterns in tags and sources

- **Web Dashboard** (`web/app.py`) - FastAPI-based interface with `/ask/html` endpoint
- **API Endpoints** - RESTful access to all cognitive features

### ✅ Resolved Implementation Gaps

#### **1. MetadataManager Methods**
**Status**: All previously identified "missing" methods (`get_forgotten_content()`, `get_all_metadata()`, `get_temporal_patterns()`, `get_recall_items()`, `get_tag_patterns()`) are now implemented in `helpers/metadata_manager.py`.
**Impact**: This foundational component is now fully functional, providing the necessary data access for cognitive amplification features.

#### **2. Ask Subsystem Integration**
**Status**: The `ask` modules (`ProactiveSurfacer`, `TemporalEngine`, `QuestionEngine`, `RecallEngine`, `PatternDetector`) are correctly integrated with the `MetadataManager` and are utilizing its methods.
**Impact**: The core cognitive features are now able to retrieve and process data as intended.

#### **3. Web Dashboard Integration**
**Status**: The web dashboard (`web/app.py`) is correctly importing and utilizing the `ask` modules. The routes are calling the appropriate methods.
**Impact**: The web UI for cognitive features should now be functional, displaying data from the `ask` modules.

### 🚨 Remaining Critical Implementation Gap

#### **1. Configuration Documentation (2-4 hours)**
**Status**: Setup instructions reference wrong paths/files  
**Impact**: New users cannot run the system

## Implementation Phases

### **Phase 1: Documentation and Refinement (Weeks 1-2)**
*Priority: Address remaining documentation gaps and refine existing features*

#### Week 1: Configuration Documentation
**Objective**: Ensure all setup instructions are accurate and user-friendly.

**Deliverables**:
1. **Update QUICK_START.md** (2-4 hours)
   - Fix configuration paths and file references.
   - Ensure clear and concise setup instructions for new users.
2. **Update README.md** (1-2 hours)
   - Align all documentation with current implementation status.
   - Update references to configuration and setup.

#### Week 2: System Refinement and Minor Enhancements
**Objective**: Improve overall system reliability and user experience through minor code refinements.

**Deliverables**:
1. **Review and Refine Existing Code** (5-10 hours)
   - Address any minor bugs or inconsistencies identified during analysis.
   - Optimize performance where immediate gains are apparent.
2. **Enhance Error Handling and Logging** (3-5 hours)
   - Improve clarity of error messages.
   - Ensure comprehensive logging for easier debugging.

### **Phase 2: Advanced Features (Weeks 3-6)**
*Priority: Feature enhancement and reliability*

#### Weeks 4-5: Content Intelligence
**Objective**: Enhance content processing capabilities

**Deliverables**:
1. **Document Processing Expansion** (25-35 hours)
   - Unstructured integration for multi-format document support
   - PDF, Word, and 20+ document format processing
   - Enhanced metadata extraction

2. **Enhanced Deduplication** (15-20 hours)
   - Jaccard similarity scoring implementation
   - Multi-level duplicate detection
   - Content hash optimization

3. **Full-Text Search Integration** (20-30 hours)
   - Meilisearch integration for fast, typo-tolerant search
   - Index optimization and management
   - Search result ranking and filtering

#### Weeks 6-7: Intelligence and Automation
**Objective**: Add proactive intelligence and automation

**Deliverables**:
1. **Local Audio Transcription** (25-35 hours)
   - Whisper integration for privacy-preserving transcription
   - Model size optimization and device selection
   - Batch processing and quality assessment

2. **Instapaper API Integration** (25-35 hours)
   - Replace web scraping with OAuth API calls
   - Implement proper authentication flow
   - Add rate limiting and error handling

3. **Enhanced Retry Logic** (10-15 hours)
   - Exponential backoff implementation
   - Circuit breaker patterns
   - Comprehensive failure tracking

#### Offshoot Project: Podclean - Advanced Podcast Processing (Separate Timeline)
**Objective**: Develop a specialized, two-pass podcast processing system for ad-cutting and high-quality transcription. This is a related but independent project.

**Deliverables**:
1. **Fast Ad Cut (Pass A)**: Implement rapid ad detection and removal for playable cleaned audio files (target latency 5-30 min).
   - Chapters-based ad detection (Podcasting 2.0 spec)
   - Fast transcription model (e.g., small Whisper) with text rules for ad phrase detection
   - `ffmpeg` integration for non-destructive (skip chapters) and destructive cuts
   - Generated RSS feed for cleaned media.
2. **Full Transcription (Pass B)**: Implement slower, higher-quality transcription and cleanup for detailed analysis.
   - Larger Whisper model with better settings for accuracy
   - Optional LLM-based cleanup for transcripts
   - Storage of full transcripts and cleaned text for external consumption (e.g., by Atlas).
3. **Correction Mechanisms**: Implement API endpoints for manual ad segment marking and re-processing.
4. **Robust Failure Handling**: Define policies for confidence thresholds, excessive cuts, and original file retention.

### **Phase 3: Advanced Intelligence (Weeks 8-11)**
*Priority: Cognitive amplification and insights*

#### Weeks 8-9: Vector Search and Recommendations
**Objective**: Implement semantic search and content recommendations

**Deliverables**:
1. **FAISS Vector Search** (30-40 hours)
   - Vector embedding generation
   - Semantic similarity search
   - Content recommendation engine

2. **Entity Graph Building** (25-35 hours)
   - Named entity recognition and extraction
   - Knowledge graph construction
   - Relationship mapping and visualization

3. **Temporal Analysis Enhancement** (15-25 hours)
   - Advanced time-series analysis
   - Content lifecycle tracking
   - Seasonal pattern detection

#### Weeks 10-11: Plugin Architecture and Automation
**Objective**: Create extensible platform for custom integrations

**Deliverables**:
1. **Plugin System** (35-45 hours)
   - Plugin API and interface definition
   - Dynamic plugin loading and management
   - Plugin marketplace foundation

2. **APScheduler Integration** (15-25 hours)
   - Automated periodic ingestion
   - Scheduled cognitive analysis
   - Background processing optimization

3. **ActivityWatch Integration** (20-30 hours)
   - Personal activity data import
   - Usage pattern analysis
   - Productivity insights generation

## Success Criteria and Metrics

### **Phase 1 Success Criteria (Documentation and Refinement)**
- [ ] All setup instructions in `QUICK_START.md` and `README.md` are accurate and up-to-date.
- [ ] Minor bugs and inconsistencies identified during analysis are resolved.
- [ ] Error messages are clear and logging is comprehensive.

### **Phase 2 Success Criteria**
- [ ] Document processing supports 20+ file formats
- [ ] Search performance under 500ms for 10,000+ documents
- [ ] Deduplication accuracy >95% with <1% false positives
- [ ] Instapaper OAuth integration fully functional
- [ ] Audio transcription accuracy >90% for English content

### **Phase 3 Success Criteria**
- [ ] Vector search returns relevant results for semantic queries
- [ ] Plugin system supports 3rd party extensions
- [ ] Automated processing handles 1000+ items without intervention
- [ ] Entity graph provides actionable relationship insights
- [ ] System performance scales linearly with content volume

### **Key Performance Indicators**
- **Processing Throughput**: 100+ articles per hour
- **Memory Usage**: <1GB for 10,000 articles
- **Response Time**: <2 seconds for cognitive feature queries
- **Search Performance**: <500ms for full-text search
- **Uptime**: >99.9% availability for local processing
- **User Satisfaction**: >4.5/5 in user experience surveys

## Next Steps and Immediate Priorities

### **Week 1 Immediate Actions**
1.  **Day 1-2**: Update `QUICK_START.md` with correct configuration paths and setup instructions.
2.  **Day 3-4**: Update `README.md` to align with current implementation status and documentation.
3.  **Day 5**: Begin review and refinement of existing code, focusing on minor bugs and inconsistencies.

### **Week 2 Refinement Work**
1.  **Day 1-2**: Continue code refinement and optimization.
2.  **Day 3-4**: Enhance error handling and logging mechanisms.
3.  **Day 5**: Prepare for Phase 2 by reviewing advanced feature requirements.

### **Development Environment Setup**
```bash
# 1. Clone and setup environment
git clone <repository-url>
cd atlas
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Install development dependencies
pip install pytest pytest-cov black isort mypy

# 3. Configure environment
cp env.template .env
# Edit .env with your configuration

# 4. Test basic functionality
python run.py --help
uvicorn web.app:app --reload --port 8000
```

### **Contributing Guidelines**
1.  **Development Process**:
    -   Create feature branches for all work
    -   Write tests before implementing features (TDD)
    -   Maintain >90% code coverage
    -   Use black and isort for code formatting

2.  **Commit Strategy**:
    -   Commit after each module/file creation
    -   Use descriptive commit messages with task IDs
    -   Include testing status in commit descriptions

3.  **Review Process**:
    -   All changes require pull request review
    -   Ensure CI checks pass before merging
    -   Update documentation with code changes

## Technical Architecture Notes

### **Design Principles**
- **Modularity**: Clear separation of concerns with well-defined interfaces
- **Extensibility**: Plugin architecture for custom integrations
- **Performance**: Efficient processing with intelligent caching
- **Privacy**: Local-first processing with optional cloud integration
- **Reliability**: Comprehensive error handling and graceful degradation

### **Key Architectural Patterns**
- **Strategy Pattern**: Content extraction methods (ArticleStrategies)
- **Template Method**: Ingestor base classes (BaseIngestor)
- **Observer Pattern**: Event notifications and processing pipeline
- **Factory Pattern**: Creating different content types and processors
- **Dependency Injection**: Testability and configuration management

### **Performance Considerations**
- **Lazy Loading**: Load data only when needed to minimize memory usage
- **Caching Strategy**: Multi-level caching for metadata, search, and AI results
- **Batch Processing**: Group operations for efficiency
- **Async Operations**: Non-blocking I/O for web requests and file operations
- **Memory Management**: Proper resource cleanup and garbage collection

## Risk Assessment and Mitigation

### **High Risk Items**
1. **MetadataManager Complexity** - May require database schema changes
   - *Mitigation*: Implement incrementally with backward compatibility
2. **Performance with Large Datasets** - Memory and processing constraints
   - *Mitigation*: Implement pagination and caching early
3. **Integration Dependencies** - External API changes and rate limits
   - *Mitigation*: Robust error handling and fallback strategies

### **Medium Risk Items**
1. **Model Selection Optimization** - Complex logic may have edge cases
   - *Mitigation*: Comprehensive testing with various scenarios
2. **Plugin Architecture Security** - Third-party code execution risks
   - *Mitigation*: Sandboxing and security review process
3. **Search Index Performance** - Large index size and query optimization
   - *Mitigation*: Index optimization and monitoring

### **Mitigation Strategies**
- Implement features incrementally with frequent testing
- Maintain comprehensive test coverage (>90%)
- Regular performance profiling and optimization
- Create detailed documentation for all APIs and interfaces
- Establish clear rollback procedures for failed deployments

## Resource Requirements

### **Development Team**
- **1 Senior Python Developer** - MetadataManager and cognitive features (40-60 hours)
- **1 Web Developer** - Dashboard integration and UI improvements (15-25 hours)
- **1 DevOps Engineer** - Testing infrastructure and deployment (10-15 hours)
- **1 Technical Writer** - Documentation updates and user guides (5-10 hours)

### **Infrastructure Requirements**
- **Development Environment**: Python 3.9+, FastAPI, SQLAlchemy
- **Testing Infrastructure**: pytest, coverage tools, integration test framework
- **Performance Tools**: Profiling tools, memory monitoring, performance benchmarks
- **Documentation Tools**: Markdown processors, API documentation generators

### **Timeline Summary**
- **Phase 1 (Critical Fixes)**: 3 weeks, 47-74 hours
- **Phase 2 (Advanced Features)**: 4 weeks, 100-150 hours  
- **Phase 3 (Intelligence Platform)**: 4 weeks, 125-175 hours
- **Total Project**: 11 weeks, 272-399 hours

## Conclusion

Atlas represents a sophisticated and well-architected platform for local-first cognitive amplification. The current critical implementation gaps are primarily integration issues rather than fundamental architecture problems. With focused development effort over the next 11 weeks, Atlas can become a fully functional, production-ready cognitive amplification platform that delivers on its ambitious vision.

The immediate priority is completing Phase 1 to restore core functionality and provide a solid foundation for advanced feature development. This roadmap provides a clear path from the current state to a comprehensive cognitive amplification platform that empowers users to think better and derive more insights from their personal knowledge base.

---

*This roadmap serves as the single source of truth for Atlas project planning and development. All feature development, resource allocation, and milestone planning should reference this document.*