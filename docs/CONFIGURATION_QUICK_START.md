# Atlas Configuration Quick Start

**Get Atlas configured and running in under 5 minutes.**

## 🚀 Quick Setup

### 1. Choose Your Environment

```bash
# For local development
export ATLAS_ENVIRONMENT=development

# For production deployment
export ATLAS_ENVIRONMENT=production

# For testing
export ATLAS_ENVIRONMENT=test
```

### 2. Configure API Keys

Choose one LLM provider:

#### Option A: OpenRouter (Recommended)
```bash
# Get your key from https://openrouter.ai/keys
echo 'OPENROUTER_API_KEY=sk-or-v1-your-key-here' >> config/.env.development
```

#### Option B: DeepSeek (Cost-effective)
```bash
# Get your key from https://platform.deepseek.com/api_keys
echo 'DEEPSEEK_API_KEY=your-key-here' >> config/.env.development
echo 'LLM_PROVIDER=deepseek' >> config/.env.development
```

#### Option C: Local Ollama (Free)
```bash
# Install Ollama first: https://ollama.ai
echo 'LLM_PROVIDER=ollama' >> config/.env.development
echo 'LLM_MODEL=llama2' >> config/.env.development
```

### 3. Optional: YouTube Integration
```bash
# Get API key from Google Cloud Console
# https://console.cloud.google.com/apis/library/youtube.googleapis.com
echo 'YOUTUBE_API_KEY=your-youtube-key' >> config/.env.development
```

### 4. Validate Configuration
```bash
python scripts/validate_config.py
```

## ✅ Verification

Test your setup:
```bash
# Run a quick test
python run.py --help

# Start the web interface
uvicorn web.app:app --reload --port 8000
```

Visit http://localhost:8000 to see the Atlas dashboard.

## 🔧 Common Quick Fixes

### "OpenRouter API key format appears invalid"
```bash
# Make sure your key starts with 'sk-or-v1-'
echo 'OPENROUTER_API_KEY=sk-or-v1-your-actual-key' >> config/.env.development
```

### "YouTube API key required but not provided"
```bash
# Either add the key or disable YouTube
echo 'YOUTUBE_INGESTOR_ENABLED=false' >> config/.env.development
```

### "Data directory not writable"
```bash
# Create the directory with proper permissions
mkdir -p dev_output && chmod 755 dev_output
```

### "High podcast episode limit"
```bash
# Reduce for faster processing
echo 'PODCAST_EPISODE_LIMIT=5' >> config/.env.development
```

## 📁 Configuration Files

After setup, you'll have:

```
config/
├── .env.development      # Your environment config
├── environments.yaml     # Environment profiles
├── categories.yaml       # Content categories
└── paywall_patterns.json # Paywall detection
```

## 🌟 Next Steps

1. **Read the full configuration reference**: [`CONFIGURATION_REFERENCE.md`](./CONFIGURATION_REFERENCE.md)
2. **Set up additional integrations**: Instapaper, NYT, etc.
3. **Customize your environment**: Adjust timeouts, limits, models
4. **Enable transcription**: Configure Whisper or API transcription
5. **Production deployment**: Switch to production environment

## 🆘 Need Help?

- **Validation errors**: Run `python scripts/validate_config.py --fix`
- **Environment issues**: Check [`environment-troubleshooting.md`](./environment-troubleshooting.md)
- **Full documentation**: See [`CONFIGURATION_REFERENCE.md`](./CONFIGURATION_REFERENCE.md)
- **Test your setup**: Use the test environment first

---

**Ready to go?** Your Atlas instance should now be configured and ready for content processing!
