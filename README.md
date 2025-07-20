# Atlas: Cognitive Amplification Platform

**Documentation up-to-date as of July 2025**

## 🚀 System Overview

- **Unified Job Scheduling:** All automated jobs (ingestion, maintenance, model discovery) are managed by APScheduler and a web UI (FastAPI + Jinja2). Jobs are persistent, visible, and fully manageable in the web interface, with real log viewing and last run status.
- **Enhanced Model Selection:** The model selector always tries free models first, with tiered fallback to paid options. Usage is tracked for cost optimization. Model discovery is automated and configuration is via `.env`. See `docs/ENHANCED_MODEL_SELECTOR_GUIDE.md`.
- **Bulletproof Capture & Processing:** All content is captured in a never-fail stage, then processed in a robust queue with retries and comprehensive logging. See `docs/CAPTURE_ARCHITECTURE.md` and `docs/IMPLEMENTATION_GUIDE.md`.

For full details, see the authoritative documentation in `docs/PROJECT_ROADMAP.md`, `docs/ENHANCED_MODEL_SELECTOR_GUIDE.md`, and `docs/IMPLEMENTATION_GUIDE.md`.

---

## ⚖️ Legal Notice

**IMPORTANT**: Atlas is provided for personal research and educational use only. By using this software, you agree to:

- **Use at your own risk** - No warranty or support provided
- **Follow all applicable laws** - You are responsible for legal compliance
- **Respect third-party terms** - Follow website and API terms of service
- **Secure your data** - Atlas stores data locally without encryption

**See the [LEGAL](LEGAL/) directory for complete terms, privacy policy, and compliance notes.**

## 🚀 Quick Start

**Want to try Atlas right now?** See [QUICK_START.md](QUICK_START.md) for 5-minute setup instructions.

**Need detailed status?** See [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md) for what actually works vs. what doesn't.

## 🧭 Core Philosophy

- **Local-First**: All data stored locally on your machine. No cloud dependencies.
- **Automated Ingestion**: Point Atlas at your sources and let it run.
- **Resilient**: Handles failures gracefully with comprehensive retry mechanisms.
- **Structured Output**: Clean, portable Markdown ready for any knowledge management app.

## 🧠 Cognitive Amplification Features

Atlas now includes a full suite of cognitive amplification tools, accessible via both API and a web dashboard:

- **Proactive Surfacer**: Surfaces forgotten/stale content for review or re-engagement.
- **Temporal Engine**: Finds time-aware relationships between content items.
- **Socratic Question Generator**: Generates Socratic questions from your content.
- **Active Recall Engine**: Schedules spaced repetition for knowledge retention.
- **Pattern Detector**: Detects common tags and sources, surfacing patterns and insights.

### API Endpoints
- `/ask/proactive` (GET): Surfaces forgotten content (JSON)
- `/ask/temporal` (GET): Time-aware relationships (JSON)
- `/ask/socratic` (POST): Socratic questions (JSON)
- `/ask/recall` (GET): Spaced repetition review (JSON)
- `/ask/patterns` (GET): Top tags and sources (JSON)

### Dashboard UI
- `/ask/html`: Interactive dashboard for all cognitive features

### Quickstart
1. **Start the web server:**
```bash
   uvicorn web.app:app --reload --port 8000
   ```
2. **Visit the dashboard:**
   [http://localhost:8000/ask/html](http://localhost:8000/ask/html)
3. **Explore features:**
   - Use the navigation bar to access each cognitive tool
   - For Socratic questions, paste content and submit the form

See [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) for full details, architecture, and extension instructions.

## 🧱 What Actually Works Right Now

### ✅ **Article Ingestion** 
- Multi-layer fallback system with 6 different methods
- Handles paywalls, JavaScript sites, and dead links
- Extracts clean text using readability algorithms
- Comprehensive metadata tracking

### ✅ **YouTube Processing**
- Extracts video transcripts using youtube-transcript-api
- Handles multiple languages and auto-generated captions
- Falls back to yt-dlp for difficult videos
- Saves video metadata and descriptions

### ✅ **Podcast Processing**
- Parses OPML feeds from podcast apps
- Downloads recent episodes automatically
- Transcription support (local Whisper or OpenRouter API)
- Episode metadata extraction

### ✅ **Robust Infrastructure**
- Comprehensive error handling and retry system
- Safety monitoring and pre-run checks
- Detailed logging for troubleshooting
- Deduplication to avoid processing duplicates

## 🔧 System Architecture

```
Atlas/
├── run.py                    # Main entry point
├── helpers/                  # Core ingestion modules
│   ├── article_fetcher.py   # Article processing (929 lines)
│   ├── youtube_ingestor.py  # YouTube processing (545 lines)
│   ├── podcast_ingestor.py  # Podcast processing (267 lines)
│   └── ...                  # Supporting modules
├── ingest/                   # Advanced ingestion pipeline
│   ├── link_dispatcher.py   # URL routing and dispatch
│   ├── capture/             # Never-fail capture system
│   └── queue/               # Processing queue management
├── process/                  # Content processing
├── inputs/                   # Input files (articles.txt, etc.)
└── output/                   # Processed content
```

## 🏃‍♂️ Usage

### Basic Commands
```bash
# Process articles from inputs/articles.txt
python3 run.py --articles

# Process YouTube videos from inputs/youtube.txt
python3 run.py --youtube

# Process podcasts from inputs/podcasts.opml
python3 run.py --podcasts

# Process everything
python3 run.py --all

# Process specific URL file
python3 run.py --urls path/to/urls.txt
```

### Input Files
- **`inputs/articles.txt`** - One URL per line
- **`inputs/youtube.txt`** - One YouTube URL per line
- **`inputs/podcasts.opml`** - OPML export from your podcast app

### Output Structure
```
output/
├── articles/
│   ├── html/         # Raw HTML files
│   ├── markdown/     # Processed markdown
│   └── metadata/     # Article metadata
├── youtube/
├── podcasts/
└── logs/
```

## ⚠️ Current Limitations

- **Configuration required** - Need to set up .env file (see QUICK_START.md)
- **AI features optional** - Requires OpenRouter API key for summarization/categorization
- **Command-line only** - No web interface
- **Manual input** - No automatic feed discovery
- **Basic search** - No full-text search implemented

## 🔮 Future Enhancements

Atlas is being enhanced with features inspired by leading knowledge management projects:

### **Enhanced Content Intelligence**
- Multi-method article extraction (Wallabag-inspired)
- Intelligent deduplication (Miniflux-style)
- Automatic categorization (FreshRSS-inspired)
- Document processing expansion (Unstructured integration)

### **Advanced Search & Discovery**
- Full-text search (Meilisearch integration)
- Semantic search (FAISS vector search)
- Entity graph building (spaCy-powered)
- Feed discovery system

### **Enhanced Processing**
- Local transcription (Whisper integration)
- Personal data integration (HPI-inspired)
- Automated workflows (APScheduler)
- Plugin system (Logseq-inspired)

**See [docs/SIMILAR_PROJECTS_RESEARCH.md](docs/SIMILAR_PROJECTS_RESEARCH.md) for detailed research and [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) for implementation plans.**

## 📋 Setup Requirements

### Dependencies
    ```bash
pip install -r requirements.txt
```

### Configuration
```bash
# Copy template and customize
cp env.template .env
```

### Minimum .env Configuration
```bash
DATA_DIRECTORY=output
TRANSCRIBE_ENABLED=false
```

## 🧪 Testing

Atlas includes a comprehensive testing infrastructure:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=helpers --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
```

## 🆘 Troubleshooting

### Common Issues

**"Security Issues Detected"**
- Type `y` to continue past .env file permissions warning

**"OPENROUTER_API_KEY is not set"**
- Normal warning - AI features disabled but basic ingestion works

**URLs returning 404**
- Check that URLs in input files are valid and accessible

**"No such file or directory"**
- Ensure you're in the Atlas directory and have created .env file

### Getting Help

1. Check [QUICK_START.md](QUICK_START.md) for setup issues
2. Review [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md) for known limitations
3. Check logs in `output/logs/` for detailed error information
4. Review the retry queue in `retries/` for failed items

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)** - 5-minute setup guide
- **[docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md)** - Accurate current state
- **[docs/PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md)** - Development roadmap
- **[docs/SIMILAR_PROJECTS_RESEARCH.md](docs/SIMILAR_PROJECTS_RESEARCH.md)** - Research findings
- **[docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)** - Future integration plans

## 🎯 Project Status

**Current State**: Atlas is a functional content ingestion system with sophisticated article fetching, YouTube transcript extraction, and podcast processing. The core pipeline works well but requires manual configuration and has some rough edges.

**What Works**: Multi-source content ingestion, robust error handling, comprehensive logging, retry mechanisms, and structured output.

**What Doesn't**: AI features require API keys, no web interface, manual input file management, and some advanced features are still in development.

**Bottom Line**: Atlas is a working system that needs better onboarding and documentation, not major architectural changes.

---

**Note**: This README reflects the actual current state of Atlas as of January 2025. For the most up-to-date status, see [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md). 

## 🤝 Getting Help & Contributing

- See [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md#contributor-onboarding--first-steps) for a detailed onboarding guide, codebase overview, and first contribution checklist.
- For technical details, see [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md).
- For philosophy and roadmap, see [docs/COGNITIVE_AMPLIFICATION_PHILOSOPHY.md](docs/COGNITIVE_AMPLIFICATION_PHILOSOPHY.md) and [docs/PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md).
- To submit issues or pull requests, use the GitHub repository (branch protection is enabled; all changes via PR).
- All contributors are welcome—Atlas is open source and community-driven! 
# Atlas is synced!

---

## 🔁 GitHub Sync Hook Setup

Atlas enforces GitHub consistency with a `post-commit` Git hook:

After every commit:
- 🔄 It **automatically pushes** your changes to GitHub
- 🔍 It **verifies the commit is live** on GitHub by commit hash
- ❌ It **fails loudly** if not successfully pushed

### ✅ How to enable it

In your local repo, run:

```bash
cp scripts/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
