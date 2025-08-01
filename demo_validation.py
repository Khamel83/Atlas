#!/usr/bin/env python3
"""
Demo script to showcase the enhanced configuration validation system.
This demonstrates Task 1.5: Add configuration validation with specific error guidance.
"""

from helpers.validate import ConfigValidator


def demo_validation():
    """Demonstrate the enhanced validation system with various configurations."""

    print("=" * 60)
    print("Atlas Enhanced Configuration Validation Demo")
    print("=" * 60)

    validator = ConfigValidator()

    # Test Case 1: Empty configuration (many errors)
    print("\n🔥 Test Case 1: Empty Configuration")
    print("-" * 40)
    config_empty = {}
    errors, warnings = validator.validate_config(config_empty)
    report = validator.format_validation_report(errors, warnings)
    print(report)

    # Test Case 2: Invalid provider configuration
    print("\n🔥 Test Case 2: Invalid LLM Provider")
    print("-" * 40)
    config_invalid_provider = {
        "llm_provider": "invalid_provider",
        "llm_model": "some-model",
    }
    errors, warnings = validator.validate_config(config_invalid_provider)
    report = validator.format_validation_report(errors, warnings)
    print(report)

    # Test Case 3: Missing API key with detailed guidance
    print("\n🔥 Test Case 3: Missing OpenRouter API Key")
    print("-" * 40)
    config_missing_key = {
        "llm_provider": "openrouter",
        "llm_model": "mistralai/mistral-7b-instruct",
    }
    errors, warnings = validator.validate_config(config_missing_key)
    report = validator.format_validation_report(errors, warnings)
    print(report)

    # Test Case 4: Valid configuration with warnings
    print("\n✅ Test Case 4: Valid Configuration with Optimization Suggestions")
    print("-" * 40)
    config_valid_with_warnings = {
        "llm_provider": "openrouter",
        "llm_model": "anthropic/claude-3-sonnet",  # Expensive model
        "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
        "data_directory": "output",
        "PODCAST_EPISODE_LIMIT": 150,  # High limit
        "USE_12FT_IO_FALLBACK": True,  # Privacy concern
        "article_ingestor": {"enabled": True},
        "podcast_ingestor": {"enabled": True},
        "youtube_ingestor": {"enabled": False},
        "instapaper_ingestor": {"enabled": False},
    }
    errors, warnings = validator.validate_config(config_valid_with_warnings)
    report = validator.format_validation_report(errors, warnings)
    print(report)

    # Test Case 5: Placeholder credentials detection
    print("\n⚠️  Test Case 5: Placeholder Credentials Detection")
    print("-" * 40)
    config_placeholders = {
        "llm_provider": "openrouter",
        "llm_model": "mistralai/mistral-7b-instruct",
        "OPENROUTER_API_KEY": "your_key_here",  # Placeholder
        "youtube_ingestor": {"enabled": True},
        "YOUTUBE_API_KEY": "test_youtube_key",  # Another placeholder
    }
    errors, warnings = validator.validate_config(config_placeholders)
    report = validator.format_validation_report(errors, warnings)
    print(report)

    # Test Case 6: Perfect configuration
    print("\n🎉 Test Case 6: Optimal Configuration")
    print("-" * 40)
    config_perfect = {
        "llm_provider": "openrouter",
        "llm_model": "mistralai/mistral-7b-instruct",
        "llm_model_premium": "anthropic/claude-3-sonnet",
        "llm_model_budget": "mistralai/mistral-7b-instruct:free",
        "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
        "data_directory": "output",
        "PODCAST_EPISODE_LIMIT": 20,
        "USE_12FT_IO_FALLBACK": False,
        "article_ingestor": {"enabled": True},
        "podcast_ingestor": {"enabled": True, "episode_limit": 20},
        "youtube_ingestor": {"enabled": False},
        "instapaper_ingestor": {"enabled": False},
    }
    errors, warnings = validator.validate_config(config_perfect)
    report = validator.format_validation_report(errors, warnings)
    print(report)

    print("\n" + "=" * 60)
    print("Demo completed! The enhanced validation system provides:")
    print("✅ Detailed error messages with specific guidance")
    print("✅ Fix commands for common issues")
    print("✅ Documentation links for complex setup")
    print("✅ Security and performance warnings")
    print("✅ Cost optimization suggestions")
    print("=" * 60)


if __name__ == "__main__":
    demo_validation()
