
"""
Configuration Validation Module

This module provides functions to validate the application's configuration.
"""

from typing import Dict, List, Optional


def validate_config(config: Dict) -> List[str]:
    """
    Validates the configuration dictionary.

    Args:
        config: The configuration dictionary loaded from config.py.

    Returns:
        A list of error messages. An empty list indicates a valid configuration.
    """
    errors = []

    # Validate API Keys
    if config.get("llm_provider") == "openrouter" and not config.get("OPENROUTER_API_KEY"):
        errors.append("OPENROUTER_API_KEY is required when llm_provider is 'openrouter'.")

    if config.get("llm_provider") == "deepseek" and not config.get("DEEPSEEK_API_KEY"):
        errors.append("DEEPSEEK_API_KEY is required when llm_provider is 'deepseek'.")

    if config.get("youtube_ingestor", {}).get("enabled") and not config.get("YOUTUBE_API_KEY"):
        errors.append("YOUTUBE_API_KEY is required when the YouTube ingestor is enabled.")

    # Validate Instapaper Credentials
    if config.get("instapaper_ingestor", {}).get("enabled"):
        if not config.get("INSTAPAPER_LOGIN") or not config.get("INSTAPAPER_PASSWORD"):
            errors.append("INSTAPAPER_LOGIN and INSTAPAPER_PASSWORD are required when the Instapaper ingestor is enabled.")

    # Validate NYT Credentials
    if config.get("USE_PLAYWRIGHT_FOR_NYT"):
        if not config.get("NYT_USERNAME") or not config.get("NYT_PASSWORD"):
            errors.append("NYT_USERNAME and NYT_PASSWORD are required when USE_PLAYWRIGHT_FOR_NYT is true.")

    return errors
