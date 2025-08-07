# Atlas Configuration Reference

**Complete guide to Atlas configuration system with environment-specific profiles and advanced validation.**

## Table of Contents

1. [Overview](#overview)
2. [Environment Profiles](#environment-profiles)
3. [Configuration Files](#configuration-files)
4. [Environment Variables](#environment-variables)
5. [LLM Configuration](#llm-configuration)
6. [Ingestor Configuration](#ingestor-configuration)
7. [Processing Configuration](#processing-configuration)
8. [Security Configuration](#security-configuration)
9. [Validation and Troubleshooting](#validation-and-troubleshooting)
10. [Migration Guide](#migration-guide)

## Overview

Atlas uses a sophisticated configuration system that supports:

- **Environment-specific profiles** with inheritance (dev/test/prod/staging)
- **Multiple configuration sources** (.env files, YAML, environment variables)
- **Advanced validation** with detailed error reporting and fix suggestions
- **Security hardening** with credential validation and access controls
- **Migration tools** for configuration schema changes

### Configuration Hierarchy

Configuration is loaded in the following order (later values override earlier ones):

1. Environment-specific YAML defaults (`config/environments.yaml`)
2. Environment-specific .env file (`.env.development`, `.env.production`, etc.)
3. Main .env file (`config/.env`)
4. Legacy .env file (project root `.env`)
5. Environment variables

## Environment Profiles

Atlas supports multiple pre-configured environments with inheritance:

### Base Environment
Default settings shared by all environments.

### Development (`ATLAS_ENVIRONMENT=development`)
- **Purpose**: Local development with fast iteration
- **Features**: Debug logging, shorter timeouts, conservative limits
- **Data Directory**: `dev_output`
- **Models**: Free models only for cost savings
- **Settings**: Relaxed security, quick feedback

### Test (`ATLAS_ENVIRONMENT=test`)
- **Purpose**: Automated testing and CI/CD
- **Features**: Mock providers, minimal external dependencies
- **Data Directory**: `test_output`
- **Models**: Mock models for consistent testing
- **Settings**: Fail-fast, no external API calls

### Production (`ATLAS_ENVIRONMENT=production`)
- **Purpose**: Production deployment
- **Features**: Optimized performance, reliability-focused
- **Data Directory**: `production_data`
- **Models**: Tiered model selection for cost optimization
- **Settings**: Security-hardened, comprehensive logging

### Staging (`ATLAS_ENVIRONMENT=staging`)
- **Purpose**: Pre-production testing
- **Features**: Production-like with enhanced monitoring
- **Data Directory**: `staging_data`
- **Models**: Cost-optimized alternatives to production models
- **Settings**: Debug logging with production security

### Local-with-APIs (`ATLAS_ENVIRONMENT=local-with-apis`)
- **Purpose**: Local development with real external services
- **Features**: Full API integration for testing
- **Data Directory**: `dev_output`
- **Models**: Real LLM providers
- **Settings**: Development-friendly with real service testing

## Configuration Files

### `config/environments.yaml`
Defines environment-specific defaults with inheritance.

```yaml
base:
  data_directory: "output"
  llm_provider: "openrouter"
  max_retries: 3

development:
  inherits: base
  log_level: "DEBUG"
  max_retries: 1
  data_directory: "dev_output"
```

### Environment-specific .env files
- `.env.development` - Development environment variables
- `.env.test` - Test environment variables
- `.env.production` - Production environment variables

### `config/.env`
Main environment configuration file.

### Legacy `.env`
Project root .env file (maintained for backward compatibility).

## Environment Variables

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ATLAS_ENVIRONMENT` | `development` | Environment profile to use |
| `DATA_DIRECTORY` | `output` | Base directory for processed content |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openrouter` | LLM provider (openrouter, deepseek, ollama, mock) |
| `LLM_MODEL` | `mistralai/mistral-7b-instruct` | Default model |
| `MODEL_PREMIUM` | `google/gemini-2.0-flash-lite-001` | Premium model for complex tasks |
| `MODEL_BUDGET` | `mistralai/mistral-7b-instruct:free` | Budget model for simple tasks |
| `MODEL_FALLBACK` | `google/gemini-2.0-flash-lite-001` | Fallback model if primary fails |

### API Keys

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | For OpenRouter | OpenRouter API key for model access |
| `DEEPSEEK_API_KEY` | For DeepSeek | DeepSeek API key |
| `YOUTUBE_API_KEY` | For YouTube | YouTube Data API v3 key |
| `INSTAPAPER_LOGIN` | For Instapaper | Instapaper account email |
| `INSTAPAPER_PASSWORD` | For Instapaper | Instapaper account password |
| `NYT_USERNAME` | For NYT scraping | New York Times subscription email |
| `NYT_PASSWORD` | For NYT scraping | New York Times subscription password |

### Processing Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_RETRIES` | `3` | Maximum retries for failed operations |
| `PROCESSING_TIMEOUT` | `30` | Processing timeout in minutes |
| `PODCAST_EPISODE_LIMIT` | `20` | Maximum episodes to process per podcast |

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_12FT_IO_FALLBACK` | `false` | Enable 12ft.io paywall bypass |
| `USE_PLAYWRIGHT_FOR_NYT` | `false` | Use Playwright for NYT scraping |
| `ARTICLE_INGESTOR_ENABLED` | `true` | Enable article ingestion |
| `PODCAST_INGESTOR_ENABLED` | `true` | Enable podcast ingestion |
| `YOUTUBE_INGESTOR_ENABLED` | `true` | Enable YouTube ingestion |
| `INSTAPAPER_INGESTOR_ENABLED` | `true` | Enable Instapaper ingestion |

### Transcription Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSCRIBE_ENABLED` | `false` | Enable audio transcription |
| `TRANSCRIBE_BACKEND` | `local` | Transcription backend (api, local) |
| `WHISPER_PATH` | `/usr/local/bin/whisper` | Path to Whisper executable |

## LLM Configuration

### Provider Options

#### OpenRouter (`LLM_PROVIDER=openrouter`)
- **Best for**: Model variety, pay-per-use pricing
- **Requires**: `OPENROUTER_API_KEY`
- **Models**: Access to 100+ models from various providers
- **Billing**: Pay-per-token usage

#### DeepSeek (`LLM_PROVIDER=deepseek`)
- **Best for**: Cost-effective reasoning and chat
- **Requires**: `DEEPSEEK_API_KEY`
- **Models**: `deepseek-ai/deepseek-chat`, `deepseek-ai/deepseek-reasoner`
- **Billing**: Competitive per-token pricing

#### Ollama (`LLM_PROVIDER=ollama`)
- **Best for**: Local inference, no API costs
- **Requires**: Local Ollama installation
- **Models**: `llama2`, `mistral`, `codellama`, etc.
- **Billing**: Free (local compute only)

#### Mock (`LLM_PROVIDER=mock`)
- **Best for**: Testing and development
- **Requires**: No API keys
- **Models**: Simulated responses
- **Billing**: Free

### Model Tiers

Atlas supports tiered model selection for cost optimization:

- **Premium**: Complex analysis, reasoning tasks
- **Default**: General-purpose processing
- **Budget**: Simple tasks, categorization
- **Fallback**: Used when primary models fail

### Recommended Model Configurations

#### Development
```bash
LLM_PROVIDER=openrouter
LLM_MODEL=mistralai/mistral-7b-instruct:free
MODEL_PREMIUM=mistralai/mistral-7b-instruct:free
MODEL_BUDGET=mistralai/mistral-7b-instruct:free
```

#### Production
```bash
LLM_PROVIDER=openrouter
LLM_MODEL=google/gemini-2.0-flash-lite-001
MODEL_PREMIUM=anthropic/claude-3-sonnet
MODEL_BUDGET=mistralai/mistral-7b-instruct:free
MODEL_FALLBACK=google/gemini-2.0-flash-lite-001
```

## Ingestor Configuration

### Article Ingestor
- **Purpose**: Process web articles and blog posts
- **Requirements**: None (uses multiple fallback strategies)
- **Configuration**: `ARTICLE_INGESTOR_ENABLED`

### YouTube Ingestor
- **Purpose**: Download and transcribe YouTube videos
- **Requirements**: `YOUTUBE_API_KEY` (optional but recommended)
- **Configuration**: `YOUTUBE_INGESTOR_ENABLED`

### Podcast Ingestor
- **Purpose**: Process podcast feeds and episodes
- **Requirements**: None (uses public RSS feeds)
- **Configuration**: `PODCAST_INGESTOR_ENABLED`, `PODCAST_EPISODE_LIMIT`

### Instapaper Ingestor
- **Purpose**: Import saved articles from Instapaper
- **Requirements**: `INSTAPAPER_LOGIN`, `INSTAPAPER_PASSWORD`
- **Configuration**: `INSTAPAPER_INGESTOR_ENABLED`

## Processing Configuration

### Retry Logic
- **Purpose**: Handle transient failures gracefully
- **Configuration**: `MAX_RETRIES` (recommended: 3-5)
- **Behavior**: Exponential backoff with circuit breakers

### Timeouts
- **Purpose**: Prevent stuck operations
- **Configuration**: `PROCESSING_TIMEOUT` (recommended: 30-60 minutes)
- **Scope**: Per-item processing timeout

### Logging
- **Levels**: DEBUG, INFO, WARNING, ERROR
- **Configuration**: `LOG_LEVEL`
- **Output**: Console and file logging

## Security Configuration

### Credential Management
- **Storage**: Environment variables only
- **Validation**: Format and placeholder detection
- **Access**: Never logged or exposed in error messages

### Privacy Controls
- **12ft.io Fallback**: Can be disabled for privacy
- **Local Processing**: Prefer local models when possible
- **Data Retention**: Configurable storage policies

### API Key Security
- **Format Validation**: Ensures keys match expected patterns
- **Placeholder Detection**: Warns about example/test values
- **Access Control**: Keys only accessible to authorized components

## Validation and Troubleshooting

### Configuration Validation

Run comprehensive validation:
```bash
# Basic validation
python scripts/validate_config.py

# JSON output for automation
python scripts/validate_config.py --json

# Show only fix commands
python scripts/validate_config.py --fix

# Quiet mode (only output if issues)
python scripts/validate_config.py --quiet
```

### Common Issues

#### Invalid API Key Format
```
❌ OPENROUTER_API_KEY: OpenRouter API key format appears invalid
💡 OpenRouter API keys should start with 'sk-or-v1-'
🔨 Verify your key at https://openrouter.ai/keys
```

#### Missing Dependencies
```
⚠️ ffmpeg_availability: Required command 'ffmpeg' not found in PATH
💡 Install using your package manager
🔨 brew install ffmpeg
```

#### Configuration Mismatch
```
⚠️ provider_model_mismatch: Provider 'deepseek' doesn't match model 'gpt-4'
💡 Either change provider or use a DeepSeek model
🔨 echo 'LLM_MODEL=deepseek-ai/deepseek-chat' >> config/.env
```

### Environment Detection

Atlas automatically detects the environment:

1. `ATLAS_ENVIRONMENT` environment variable
2. CI/CD indicators (`CI`, `GITHUB_ACTIONS`)
3. Production indicators (`PRODUCTION`, `PROD`)
4. Development indicators (`.git` directory, `DEBUG`)
5. Default: `development`

## Migration Guide

### From Legacy Configuration

1. **Move .env file**:
   ```bash
   mv .env config/.env
   ```

2. **Set environment**:
   ```bash
   echo 'ATLAS_ENVIRONMENT=development' >> config/.env
   ```

3. **Update paths**:
   ```bash
   # Old format
   DATA_DIRECTORY=output

   # New format (automatic based on environment)
   # No change needed - handled automatically
   ```

4. **Validate configuration**:
   ```bash
   python scripts/validate_config.py
   ```

### Configuration Schema Changes

Atlas includes migration tools for schema updates:

```bash
# Check for migration needs
python scripts/migrate_config.py --check

# Apply migrations
python scripts/migrate_config.py --apply

# Backup before migration
python scripts/migrate_config.py --backup
```

## Best Practices

### Environment Management
1. Use environment-specific .env files
2. Set `ATLAS_ENVIRONMENT` explicitly in production
3. Keep sensitive credentials out of version control
4. Validate configuration before deployment

### Security
1. Use different API keys for different environments
2. Disable unnecessary features in production
3. Regular credential rotation
4. Monitor API usage and costs

### Performance
1. Configure appropriate timeouts for your use case
2. Use budget models for simple tasks
3. Set reasonable processing limits
4. Monitor resource usage

### Development
1. Use development environment for local work
2. Test with real APIs using `local-with-apis`
3. Run validation frequently
4. Use debug logging for troubleshooting

## Support

For configuration issues:

1. Run `python scripts/validate_config.py` for detailed diagnostics
2. Check the troubleshooting guide in `docs/environment-troubleshooting.md`
3. Review the configuration validation documentation
4. Consult the Atlas documentation for specific features

---

*This configuration reference is automatically updated with each Atlas release. For the latest information, always refer to the version included with your Atlas installation.*
