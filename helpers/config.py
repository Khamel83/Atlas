import os
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

# --- Constants ---
# The base path is the project root where run.py is executed.
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
DOTENV_PATH = os.path.join(CONFIG_DIR, ".env")
CATEGORIES_PATH = os.path.join(CONFIG_DIR, "categories.yaml")
ENVIRONMENTS_PATH = os.path.join(CONFIG_DIR, "environments.yaml")

# --- Configuration Loading ---


def load_environments() -> Dict[str, Any]:
    """Load environment configurations from environments.yaml."""
    try:
        with open(ENVIRONMENTS_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(
            f"Warning: Environments file not found at {ENVIRONMENTS_PATH}. "
            "Using defaults."
        )
        return {}
    except yaml.YAMLError as e:
        print(f"Warning: Error parsing environments YAML file: {e}. Using defaults.")
        return {}


def resolve_environment_config(
    env_name: str, environments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Resolve environment configuration with inheritance.

    Args:
        env_name: Name of the environment (e.g., 'development', 'production')
        environments: Dictionary of all environment configurations

    Returns:
        Resolved configuration dictionary with inheritance applied
    """
    if env_name not in environments:
        print(
            f"Warning: Environment '{env_name}' not found. " "Using base configuration."
        )
        env_name = "base"

    # Start with the requested environment
    config = environments.get(env_name, {}).copy()

    # Handle inheritance
    visited = set()
    while "inherits" in config and config["inherits"] not in visited:
        parent_name = config["inherits"]
        visited.add(env_name)

        if parent_name not in environments:
            print(f"Warning: Parent environment '{parent_name}' not found.")
            break

        parent_config = environments[parent_name].copy()

        # Remove inherits from current config and merge with parent
        del config["inherits"]
        merged_config = parent_config.copy()
        merged_config.update(config)
        config = merged_config

        # Continue with parent if it also inherits
        env_name = parent_name
        if "inherits" in parent_config:
            config["inherits"] = parent_config["inherits"]

    # Remove any remaining inherits key
    config.pop("inherits", None)
    return config


def get_current_environment() -> str:
    """
    Determine the current environment from environment variables.

    Returns:
        Environment name (e.g., 'development', 'production', 'test')
    """
    # Check for explicit environment setting
    env = os.environ.get("ATLAS_ENVIRONMENT")
    if env:
        return env.lower()

    # Detect based on common environment indicators
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return "test"
    elif os.environ.get("PRODUCTION") or os.environ.get("PROD"):
        return "production"
    elif os.environ.get("DEVELOPMENT") or os.environ.get("DEV"):
        return "development"

    # Default based on presence of development indicators
    if os.path.exists(".git") or os.environ.get("DEBUG"):
        return "development"

    # Safe default
    return "development"


def load_environment_dotenv(env_name: str):
    """
    Load environment-specific .env file if it exists.

    Args:
        env_name: Environment name to load .env file for
    """
    env_dotenv_path = os.path.join(CONFIG_DIR, f".env.{env_name}")
    if os.path.exists(env_dotenv_path):
        load_dotenv(dotenv_path=env_dotenv_path, override=True)
        print(f"Loaded environment-specific configuration: {env_dotenv_path}")


def load_categories() -> dict:
    """Loads the categories from the YAML file."""
    try:
        with open(CATEGORIES_PATH, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(
            f"Warning: Categories file not found at {CATEGORIES_PATH}. "
            "Categorization will be disabled."
        )
        return {}
    except yaml.YAMLError as e:
        print(
            f"Warning: Error parsing categories YAML file: {e}. "
            "Categorization will be disabled."
        )
        return {}


def load_config() -> dict:
    """
    Loads all configuration from .env and YAML files into a single dictionary.
    Supports environment-specific configuration with inheritance.
    """
    # Determine current environment
    current_env = get_current_environment()

    # Load environment-specific .env file first
    load_environment_dotenv(current_env)

    # Load environment variables
    # 1) Load config/.env first (primary location)
    load_dotenv(dotenv_path=DOTENV_PATH)
    # 2) Load project root .env for backwards compatibility
    # (without overriding existing)
    load_dotenv(
        dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"),
        override=False,
    )

    # Load environment configurations
    environments = load_environments()
    env_config = resolve_environment_config(current_env, environments)

    # Apply environment defaults before building config
    data_directory = os.getenv("DATA_DIRECTORY") or env_config.get(
        "data_directory", "output"
    )

    config = {
        # Environment information
        "environment": current_env,
        "environment_config": env_config,
        # Secrets and settings from .env
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY"),
        "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY"),
        "NYT_USERNAME": os.environ.get("NYT_USERNAME"),
        "NYT_PASSWORD": os.environ.get("NYT_PASSWORD"),
        "INSTAPAPER_LOGIN": os.environ.get("INSTAPAPER_LOGIN")
        or os.environ.get("INSTAPAPER_USERNAME"),
        "INSTAPAPER_PASSWORD": os.environ.get("INSTAPAPER_PASSWORD"),
        # AI Configuration (with environment defaults)
        "llm_provider": os.environ.get("LLM_PROVIDER")
        or env_config.get("llm_provider", "openrouter"),
        "llm_model": os.environ.get("LLM_MODEL")
        or os.environ.get("MODEL")
        or env_config.get("llm_model", "mistralai/mistral-7b-instruct"),
        # Tiered Model Configuration (with environment defaults)
        "llm_model_premium": os.environ.get("MODEL_PREMIUM")
        or env_config.get("llm_model_premium", "google/gemini-2.0-flash-lite-001"),
        "llm_model_budget": os.environ.get("MODEL_BUDGET")
        or env_config.get("llm_model_budget", "mistralai/mistral-7b-instruct"),
        "llm_model_fallback": os.environ.get("MODEL_FALLBACK")
        or env_config.get("llm_model_fallback", "google/gemini-2.0-flash-lite-001"),
        # Free Model Tiers
        "MODEL_FREE_PREMIUM_1": os.environ.get(
            "MODEL_FREE_PREMIUM_1", "deepseek/deepseek-r1:free"
        ),
        "MODEL_FREE_PREMIUM_2": os.environ.get(
            "MODEL_FREE_PREMIUM_2", "deepseek/deepseek-v3:free"
        ),
        "MODEL_FREE_PREMIUM_3": os.environ.get(
            "MODEL_FREE_PREMIUM_3", "meta-llama/llama-3.1-8b-instruct:free"
        ),
        "MODEL_FREE_FALLBACK_1": os.environ.get(
            "MODEL_FREE_FALLBACK_1", "google/gemma-2-9b-it:free"
        ),
        "MODEL_FREE_FALLBACK_2": os.environ.get(
            "MODEL_FREE_FALLBACK_2", "mistralai/mistral-7b-instruct:free"
        ),
        "MODEL_FREE_FALLBACK_3": os.environ.get(
            "MODEL_FREE_FALLBACK_3", "qwen/qwen-2.5-7b-instruct:free"
        ),
        "MODEL_FREE_BUDGET_1": os.environ.get(
            "MODEL_FREE_BUDGET_1", "mistralai/mistral-7b-instruct:free"
        ),
        "MODEL_FREE_BUDGET_2": os.environ.get(
            "MODEL_FREE_BUDGET_2", "qwen/qwen-2.5-7b-instruct:free"
        ),
        "MODEL_FREE_BUDGET_3": os.environ.get(
            "MODEL_FREE_BUDGET_3", "google/gemma-2-9b-it:free"
        ),
        # Paths
        "data_directory": data_directory,
        "article_output_path": os.path.join(data_directory, "articles"),
        "podcast_output_path": os.path.join(data_directory, "podcasts"),
        "youtube_output_path": os.path.join(data_directory, "youtube"),
        # Feature Flags (with environment defaults)
        "PODCAST_EPISODE_LIMIT": int(
            os.environ.get("PODCAST_EPISODE_LIMIT")
            or env_config.get("podcast_episode_limit", 0)
        ),
        "USE_12FT_IO_FALLBACK": (
            os.environ.get("USE_12FT_IO_FALLBACK")
            or str(env_config.get("use_12ft_io_fallback", "false"))
        ).lower()
        == "true",
        "USE_PLAYWRIGHT_FOR_NYT": (
            os.environ.get("USE_PLAYWRIGHT_FOR_NYT")
            or str(env_config.get("use_playwright_for_nyt", "false"))
        ).lower()
        == "true",
        # Categorization
        "categories": load_categories(),
        # --- DeepSeek API Key ---
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),
    }

    # --- Smart LLM Provider/Key Logic ---
    # Prefer DeepSeek if key is present and funds remain
    if config["DEEPSEEK_API_KEY"]:
        config["llm_provider"] = "deepseek"
        # Use deepseek-chat as default, deepseek-reasoner for premium/reasoning
        config["llm_model"] = os.environ.get("LLM_MODEL", "deepseek-ai/deepseek-chat")
        config["llm_model_premium"] = os.environ.get(
            "MODEL_PREMIUM", "deepseek-ai/deepseek-chat"
        )
        config["llm_model_reasoner"] = os.environ.get(
            "MODEL_REASONER", "deepseek-ai/deepseek-reasoner"
        )
        # Optionally, warn if funds are low (not implemented here)
    else:
        # For user convenience, if OPENAI_API_KEY contains an OpenRouter key,
        # we'll automatically set the provider and key correctly.
        openai_key = os.environ.get("OPENAI_API_KEY")
        if (
            openai_key
            and openai_key.startswith("sk-or-v1-")
            and not config["OPENROUTER_API_KEY"]
        ):
            print(
                "Info: Found OpenRouter key in OPENAI_API_KEY. "
                "Setting provider to OpenRouter."
            )
            config["OPENROUTER_API_KEY"] = openai_key
            config["llm_provider"] = "openrouter"

    if not config["OPENROUTER_API_KEY"]:
        # Only show this warning if the user intends to use a provider that
        # needs this key. We assume 'ollama' is the only provider that doesn't need it.
        if config["llm_provider"] and config["llm_provider"].lower() != "ollama":
            print(
                "Warning: OPENROUTER_API_KEY is not set in your .env file. "
                "AI features will be disabled."
            )

    # Ingestor-specific configurations (with environment defaults)
    config["article_ingestor"] = {
        "enabled": (
            os.getenv("ARTICLE_INGESTOR_ENABLED")
            or str(env_config.get("article_ingestor_enabled", "true"))
        ).lower()
        == "true",
    }
    config["podcast_ingestor"] = {
        "enabled": (
            os.getenv("PODCAST_INGESTOR_ENABLED")
            or str(env_config.get("podcast_ingestor_enabled", "true"))
        ).lower()
        == "true",
        "episode_limit": int(
            os.getenv("PODCAST_EPISODE_LIMIT")
            or env_config.get("podcast_episode_limit", 0)
        ),
    }
    config["youtube_ingestor"] = {
        "enabled": (
            os.getenv("YOUTUBE_INGESTOR_ENABLED")
            or str(env_config.get("youtube_ingestor_enabled", "true"))
        ).lower()
        == "true",
    }
    config["instapaper_ingestor"] = {
        "enabled": (
            os.getenv("INSTAPAPER_INGESTOR_ENABLED")
            or str(env_config.get("instapaper_ingestor_enabled", "true"))
        ).lower()
        == "true",
    }

    # Processing configuration (with environment defaults)
    config["max_retries"] = int(
        os.getenv("MAX_RETRIES") or env_config.get("max_retries", 3)
    )
    config["processing_timeout"] = int(
        os.getenv("PROCESSING_TIMEOUT") or env_config.get("processing_timeout", 30)
    )
    config["log_level"] = os.getenv("LOG_LEVEL") or env_config.get("log_level", "INFO")

    # Transcription configuration (with environment defaults)
    config["transcribe_enabled"] = (
        os.getenv("TRANSCRIBE_ENABLED")
        or str(env_config.get("transcribe_enabled", "false"))
    ).lower() == "true"
    config["transcribe_backend"] = os.getenv("TRANSCRIBE_BACKEND") or env_config.get(
        "transcribe_backend", "local"
    )
    config["whisper_path"] = os.getenv("WHISPER_PATH") or env_config.get(
        "whisper_path", "/usr/local/bin/whisper"
    )

    # Validate the configuration with enhanced validation
    from helpers.validate import ConfigValidator

    try:
        validator = ConfigValidator()
        errors, warnings = validator.validate_config(config)

        if errors or warnings:
            report = validator.format_validation_report(errors, warnings)
            print(report)

            # Log validation errors for monitoring and analysis
            try:
                from helpers.error_handler import create_error_handler

                error_handler = create_error_handler(config)
                error_handler.log_validation_errors(errors, warnings)
            except ImportError:
                pass  # Error handler is optional

            # For backward compatibility, also add simple error messages
            if errors:
                print("\nSimple Error Summary:")
                for error in errors:
                    print(f"- {error.field}: {error.message}")
    except ImportError:
        # Fallback to legacy validation if enhanced validation fails
        from helpers.validate import validate_config

        errors = validate_config(config)
        if errors:
            print("Configuration Errors:")
            for error in errors:
                print(f"- {error}")

    # Perform security validation
    try:
        from helpers.security import validate_security

        security_results, security_report = validate_security(config)

        # Only show security report if there are issues
        high_severity_issues = [
            r for r in security_results if r.severity in ["critical", "high"]
        ]
        if high_severity_issues:
            print(security_report)
        elif security_results:
            # Show brief summary for medium/low issues
            print(
                f"\n🔒 Security: {len(security_results)} minor security "
                "recommendations available. Run 'python scripts/validate_config.py "
                "--security' for details."
            )

    except ImportError:
        # Security validation is optional
        pass

    return config


def get_model_for_task(config: dict, task_type: str = "default") -> Optional[str]:
    """
    Get the appropriate model for a specific task type with optimized fallback chains.

    Args:
        config: Configuration dictionary from load_config()
        task_type: Type of task - "premium", "budget", "fallback",
                  "reasoner", or "default"

    Returns:
        str: Model name to use for the task
    """
    provider = config.get("llm_provider", "openrouter")

    # DeepSeek provider optimization
    if provider == "deepseek":
        if task_type == "reasoner":
            return _get_with_fallback(
                config,
                [
                    "llm_model_reasoner",
                    "MODEL_REASONER",
                    "llm_model_premium",
                    "llm_model",
                ],
                "deepseek-ai/deepseek-reasoner",
            )
        elif task_type == "premium":
            return _get_with_fallback(
                config,
                ["llm_model_premium", "MODEL_PREMIUM", "llm_model"],
                "deepseek-ai/deepseek-chat",
            )
        elif task_type == "budget":
            return _get_with_fallback(
                config,
                ["llm_model_budget", "MODEL_BUDGET", "llm_model"],
                "deepseek-ai/deepseek-chat",
            )
        else:
            return _get_with_fallback(
                config, ["llm_model", "LLM_MODEL"], "deepseek-ai/deepseek-chat"
            )

    # OpenRouter provider optimization with free models
    elif provider == "openrouter":
        free_models = _get_free_model_tiers(config)

        if task_type == "premium":
            return _get_with_fallback(
                config,
                ["llm_model_premium", "MODEL_PREMIUM", "llm_model"],
                free_models.get("premium", "google/gemini-2.0-flash-lite-001"),
            )
        elif task_type == "budget":
            return _get_with_fallback(
                config,
                [
                    "llm_model_budget",
                    "MODEL_BUDGET",
                    "MODEL_FREE_BUDGET_1",
                    "MODEL_FREE_FALLBACK_1",
                ],
                free_models.get("budget", "mistralai/mistral-7b-instruct:free"),
            )
        elif task_type == "fallback":
            return _get_with_fallback(
                config,
                [
                    "llm_model_fallback",
                    "MODEL_FALLBACK",
                    "MODEL_FREE_FALLBACK_1",
                    "MODEL_FREE_BUDGET_1",
                    "llm_model",
                ],
                free_models.get("fallback", "google/gemma-2-9b-it:free"),
            )
        else:
            return _get_with_fallback(
                config,
                ["llm_model", "LLM_MODEL", "MODEL"],
                "mistralai/mistral-7b-instruct:free",
            )

    # Ollama provider
    elif provider == "ollama":
        ollama_models = {
            "premium": "llama2",
            "budget": "mistral",
            "fallback": "codellama",
            "default": "llama2",
        }
        return ollama_models.get(task_type, "llama2")

    # Mock provider for testing
    elif provider == "mock":
        return "mock-model"

    # Generic fallback for unknown providers
    else:
        if task_type == "premium":
            return _get_with_fallback(
                config,
                ["llm_model_premium", "MODEL_PREMIUM", "llm_model"],
                "google/gemini-2.0-flash-lite-001",
            )
        elif task_type == "budget":
            return _get_with_fallback(
                config,
                ["llm_model_budget", "MODEL_BUDGET"],
                "mistralai/mistral-7b-instruct:free",
            )
        elif task_type == "fallback":
            return _get_with_fallback(
                config,
                ["llm_model_fallback", "MODEL_FALLBACK", "llm_model"],
                "google/gemma-2-9b-it:free",
            )
        else:
            return _get_with_fallback(
                config,
                ["llm_model", "LLM_MODEL", "MODEL"],
                "mistralai/mistral-7b-instruct:free",
            )


def _get_with_fallback(config: dict, keys: List[str], default: str) -> str:
    """
    Get configuration value with fallback chain.

    Args:
        config: Configuration dictionary
        keys: List of keys to try in order
        default: Default value if none found

    Returns:
        First non-empty value found or default
    """
    for key in keys:
        value = config.get(key)
        if value and str(value).strip():
            return str(value).strip()
    return default


def _get_free_model_tiers(config: dict) -> Dict[str, str]:
    """
    Get free model tier configuration for cost optimization.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary mapping tier types to free models
    """
    return {
        "premium": config.get("MODEL_FREE_PREMIUM_1", "deepseek/deepseek-r1:free"),
        "budget": config.get(
            "MODEL_FREE_BUDGET_1", "mistralai/mistral-7b-instruct:free"
        ),
        "fallback": config.get("MODEL_FREE_FALLBACK_1", "google/gemma-2-9b-it:free"),
    }


# --- Legacy Functions (to be deprecated) ---


def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Retrieves a configuration value from the environment variables.
    DEPRECATED: Use load_config() instead.
    """
    return os.environ.get(key, default)


def is_feature_enabled(feature_key: str, default: str = "false") -> bool:
    value = get_config(feature_key, default)
    return value is not None and value.lower() == "true"


# Legacy code removed - API key checking now happens in load_config()
