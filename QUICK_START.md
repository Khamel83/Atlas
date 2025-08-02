# Atlas Quick Start Guide

**Get Atlas configured and running in under 5 minutes with the new environment-aware configuration system.**

## 1. Installation

First, clone the repository and install the required Python packages:

```bash
# Clone the repository
git clone https://github.com/your-username/Atlas.git
cd Atlas

# Install dependencies
pip install -r requirements.txt
```

## 2. Environment Setup

Atlas uses environment-specific configuration. Choose your environment:

```bash
# For local development (default)
export ATLAS_ENVIRONMENT=development

# For production deployment
export ATLAS_ENVIRONMENT=production

# For testing
export ATLAS_ENVIRONMENT=test
```

## 3. Configuration

Create your configuration from the template:

```bash
# Create the config directory and copy template
mkdir -p config
cp env.template config/.env
```

**Essential Configuration**: Edit `config/.env` and set your LLM provider:

### Option A: OpenRouter (Recommended - Best model variety)
```bash
# Get your key from https://openrouter.ai/keys
echo 'OPENROUTER_API_KEY=sk-or-v1-your-key-here' >> config/.env
echo 'LLM_PROVIDER=openrouter' >> config/.env
```

### Option B: DeepSeek (Cost-effective reasoning)
```bash
# Get your key from https://platform.deepseek.com/api_keys
echo 'DEEPSEEK_API_KEY=your-key-here' >> config/.env
echo 'LLM_PROVIDER=deepseek' >> config/.env
```

### Option C: Local Ollama (Free, no API needed)
```bash
# Install Ollama first: https://ollama.ai
echo 'LLM_PROVIDER=ollama' >> config/.env
echo 'LLM_MODEL=llama2' >> config/.env
```

## 4. Validate Your Configuration

Atlas includes comprehensive configuration validation:

```bash
# Validate your setup
python scripts/validate_config.py

# Get quick fix commands for any issues
python scripts/validate_config.py --fix
```

## 5. Optional: YouTube Integration

For YouTube content processing, add a YouTube API key:

```bash
# Get API key from Google Cloud Console
# https://console.cloud.google.com/apis/library/youtube.googleapis.com
echo 'YOUTUBE_API_KEY=your-youtube-key' >> config/.env
```

## 6. Running Atlas

With configuration validated, run Atlas:

```bash
# Process all content types
python run.py --all

# Process specific content types
python run.py --articles    # Web articles
python run.py --youtube     # YouTube videos
python run.py --podcasts    # Podcast feeds

# Get help with all options
python run.py --help
```

## 7. Web Dashboard

Explore Atlas's cognitive amplification features via the web interface:

```bash
# Start the web server
uvicorn web.app:app --reload --port 8000
```

Visit http://localhost:8000/ask/html to access:
- **Proactive Surfacing**: Rediscover forgotten content
- **Temporal Analysis**: Find time-based patterns
- **Question Generation**: Socratic questioning for deeper thinking
- **Recall Scheduler**: Spaced repetition for knowledge retention
- **Pattern Detection**: Identify patterns in your content

## 🔧 Quick Troubleshooting

### Configuration Issues
```bash
# Fix common setup problems
python scripts/validate_config.py --fix

# Check what migrations are needed
python scripts/migrate_config.py --check
```

### Common Fixes
- **"API key format invalid"**: Ensure OpenRouter keys start with `sk-or-v1-`
- **"Data directory not writable"**: Run `mkdir -p dev_output && chmod 755 dev_output`
- **"YouTube API required"**: Either add the key or set `YOUTUBE_INGESTOR_ENABLED=false`

## 📚 Next Steps

- **Full Configuration Guide**: See [`docs/CONFIGURATION_REFERENCE.md`](docs/CONFIGURATION_REFERENCE.md)
- **Environment-Specific Setup**: Use [`docs/CONFIGURATION_QUICK_START.md`](docs/CONFIGURATION_QUICK_START.md)
- **Production Deployment**: Switch to `ATLAS_ENVIRONMENT=production`

## 🆘 Need Help?

1. Run validation: `python scripts/validate_config.py`
2. Check the troubleshooting guide: `docs/environment-troubleshooting.md`
3. Review the full configuration reference: `docs/CONFIGURATION_REFERENCE.md`

---

**Your Atlas instance is now ready for cognitive amplification and content processing!**
