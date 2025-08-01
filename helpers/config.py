import os
import yaml
from dotenv import load_dotenv

# --- Constants ---
# The base path is the project root where run.py is executed.
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
DOTENV_PATH = os.path.join(CONFIG_DIR, '.env')
CATEGORIES_PATH = os.path.join(CONFIG_DIR, 'categories.yaml')

# --- Configuration Loading ---

def load_categories() -> dict:
    """Loads the categories from the YAML file."""
    try:
        with open(CATEGORIES_PATH, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Warning: Categories file not found at {CATEGORIES_PATH}. Categorization will be disabled.")
        return {}
    except yaml.YAMLError as e:
        print(f"Warning: Error parsing categories YAML file: {e}. Categorization will be disabled.")
        return {}

def load_config() -> dict:
    """
    Loads all configuration from .env and YAML files into a single dictionary.
    """
    # Load environment variables
    # 1) Load config/.env first (primary location)
    load_dotenv(dotenv_path=DOTENV_PATH)
    # 2) Load project root .env for backwards compatibility (without overriding existing)
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=False)

    # Default to 'output' if not set in .env
    data_directory = os.getenv("DATA_DIRECTORY", "output")

    config = {
        # Secrets and settings from .env
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY"),
        "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY"),
        "NYT_USERNAME": os.environ.get("NYT_USERNAME"),
        "NYT_PASSWORD": os.environ.get("NYT_PASSWORD"),
        "INSTAPAPER_LOGIN": os.environ.get("INSTAPAPER_LOGIN") or os.environ.get("INSTAPAPER_USERNAME"),
        "INSTAPAPER_PASSWORD": os.environ.get("INSTAPAPER_PASSWORD"),
        
        # AI Configuration
        "llm_provider": os.environ.get("LLM_PROVIDER", "openrouter"),
        "llm_model": os.environ.get("LLM_MODEL") or os.environ.get("MODEL", "mistralai/mistral-7b-instruct"),
        
        # Tiered Model Configuration
        "llm_model_premium": os.environ.get("MODEL_PREMIUM", "google/gemini-2.0-flash-lite-001"),
        "llm_model_budget": os.environ.get("MODEL_BUDGET", "mistralai/mistral-7b-instruct"),
        "llm_model_fallback": os.environ.get("MODEL_FALLBACK", "google/gemini-2.0-flash-lite-001"),
        
        # Free Model Tiers
        "MODEL_FREE_PREMIUM_1": os.environ.get("MODEL_FREE_PREMIUM_1", "deepseek/deepseek-r1:free"),
        "MODEL_FREE_PREMIUM_2": os.environ.get("MODEL_FREE_PREMIUM_2", "deepseek/deepseek-v3:free"),
        "MODEL_FREE_PREMIUM_3": os.environ.get("MODEL_FREE_PREMIUM_3", "meta-llama/llama-3.1-8b-instruct:free"),
        "MODEL_FREE_FALLBACK_1": os.environ.get("MODEL_FREE_FALLBACK_1", "google/gemma-2-9b-it:free"),
        "MODEL_FREE_FALLBACK_2": os.environ.get("MODEL_FREE_FALLBACK_2", "mistralai/mistral-7b-instruct:free"),
        "MODEL_FREE_FALLBACK_3": os.environ.get("MODEL_FREE_FALLBACK_3", "qwen/qwen-2.5-7b-instruct:free"),
        "MODEL_FREE_BUDGET_1": os.environ.get("MODEL_FREE_BUDGET_1", "mistralai/mistral-7b-instruct:free"),
        "MODEL_FREE_BUDGET_2": os.environ.get("MODEL_FREE_BUDGET_2", "qwen/qwen-2.5-7b-instruct:free"),
        "MODEL_FREE_BUDGET_3": os.environ.get("MODEL_FREE_BUDGET_3", "google/gemma-2-9b-it:free"),

        # Paths
        "data_directory": data_directory,
        "article_output_path": os.path.join(data_directory, "articles"),
        "podcast_output_path": os.path.join(data_directory, "podcasts"),
        "youtube_output_path": os.path.join(data_directory, "youtube"),
        
        # Feature Flags
        "PODCAST_EPISODE_LIMIT": int(os.environ.get("PODCAST_EPISODE_LIMIT", 0)),
        "USE_12FT_IO_FALLBACK": os.environ.get("USE_12FT_IO_FALLBACK", "false").lower() == "true",
        "USE_PLAYWRIGHT_FOR_NYT": os.environ.get("USE_PLAYWRIGHT_FOR_NYT", "false").lower() == "true",
        
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
        config["llm_model_premium"] = os.environ.get("MODEL_PREMIUM", "deepseek-ai/deepseek-chat")
        config["llm_model_reasoner"] = os.environ.get("MODEL_REASONER", "deepseek-ai/deepseek-reasoner")
        # Optionally, warn if funds are low (not implemented here)
    else:
        # For user convenience, if OPENAI_API_KEY contains an OpenRouter key,
        # we'll automatically set the provider and key correctly.
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key and openai_key.startswith("sk-or-v1-") and not config["OPENROUTER_API_KEY"]:
            print("Info: Found OpenRouter key in OPENAI_API_KEY. Setting provider to OpenRouter.")
            config["OPENROUTER_API_KEY"] = openai_key
            config["llm_provider"] = "openrouter"


    if not config["OPENROUTER_API_KEY"]:
        # Only show this warning if the user intends to use a provider that needs this key.
        # We assume 'ollama' is the only provider that doesn't need it.
        if config["llm_provider"].lower() != 'ollama':
            print("Warning: OPENROUTER_API_KEY is not set in your .env file. AI features will be disabled.")

    # Ingestor-specific configurations
    config["article_ingestor"] = {
        "enabled": os.getenv("ARTICLE_INGESTOR_ENABLED", "true").lower() == "true",
    }
    config["podcast_ingestor"] = {
        "enabled": os.getenv("PODCAST_INGESTOR_ENABLED", "true").lower() == "true",
        "episode_limit": int(os.getenv("PODCAST_EPISODE_LIMIT", 0)),
    }
    config["youtube_ingestor"] = {
        "enabled": os.getenv("YOUTUBE_INGESTOR_ENABLED", "true").lower() == "true",
    }
    config["instapaper_ingestor"] = {
        "enabled": os.getenv("INSTAPAPER_INGESTOR_ENABLED", "true").lower() == "true",
    }

    return config

def get_model_for_task(config: dict, task_type: str = "default") -> str:
    """
    Get the appropriate model for a specific task type.
    
    Args:
        config: Configuration dictionary from load_config()
        task_type: Type of task - "premium", "budget", "fallback", "reasoner", or "default"
        
    Returns:
        str: Model name to use for the task
    """
    if config.get("llm_provider") == "deepseek":
        if task_type == "reasoner":
            return config.get("llm_model_reasoner", "deepseek-ai/deepseek-reasoner")
        elif task_type == "premium":
            return config.get("llm_model_premium", "deepseek-ai/deepseek-chat")
        else:
            return config.get("llm_model", "deepseek-ai/deepseek-chat")
    # Fallback to existing logic
    if task_type == "premium":
        return config.get("llm_model_premium", config.get("llm_model"))
    elif task_type == "budget":
        return config.get("llm_model_budget", "mistralai/mistral-7b-instruct")
    elif task_type == "fallback":
        return config.get("llm_model_fallback", config.get("llm_model"))
    else:
        return config.get("llm_model", "mistralai/mistral-7b-instruct")

# --- Legacy Functions (to be deprecated) ---

from typing import Optional

def get_config(key: str, default: str = None) -> Optional[str]:
    """
    Retrieves a configuration value from the environment variables.
    DEPRECATED: Use load_config() instead.
    """
    return os.environ.get(key, default)

def is_feature_enabled(feature_key: str, default: str = "false") -> bool:
    """
    Checks if a feature toggle is enabled in the environment variables.
    Assumes 'true' means enabled.
    DEPRECATED: Use load_config() instead.
    """
    return get_config(feature_key, default).lower() == "true"

# Legacy code removed - API key checking now happens in load_config()
