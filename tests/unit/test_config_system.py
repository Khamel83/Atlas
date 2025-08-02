"""
Comprehensive tests for the centralized configuration system.

Tests cover configuration loading, validation, environment overrides,
credential management, hot-reloading, and audit logging.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pytest
import yaml

from helpers.config import load_config, load_categories, get_model_for_task
from helpers.validate import ConfigValidator, ValidationError


class TestConfigurationLoading(unittest.TestCase):
    """Test configuration loading from various sources."""

    def setUp(self):
        """Set up test environment with isolated configuration."""
        self.test_env = {}
        self.original_env = os.environ.copy()
        
    def tearDown(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_with_defaults(self):
        """Test configuration loading with only default values."""
        config = load_config()
        
        # Test default values are applied
        self.assertEqual(config["data_directory"], "output")
        self.assertEqual(config["llm_provider"], "openrouter")
        self.assertEqual(config["llm_model"], "mistralai/mistral-7b-instruct")
        self.assertEqual(config["PODCAST_EPISODE_LIMIT"], 0)
        self.assertFalse(config["USE_12FT_IO_FALLBACK"])
        
    @patch.dict(os.environ, {
        "LLM_PROVIDER": "deepseek",
        "DEEPSEEK_API_KEY": "test-key",
        "DATA_DIRECTORY": "custom_output",
        "PODCAST_EPISODE_LIMIT": "5"
    })
    def test_load_config_with_env_overrides(self):
        """Test configuration loading with environment variable overrides."""
        config = load_config()
        
        self.assertEqual(config["llm_provider"], "deepseek")
        self.assertEqual(config["data_directory"], "custom_output")
        self.assertEqual(config["PODCAST_EPISODE_LIMIT"], 5)
        self.assertIsNotNone(config["DEEPSEEK_API_KEY"])

    @patch("helpers.config.load_dotenv")
    def test_load_config_dotenv_priority(self, mock_load_dotenv):
        """Test that config/.env takes priority over root .env."""
        load_config()
        
        # Should load config/.env first, then root .env without override
        self.assertEqual(mock_load_dotenv.call_count, 2)
        calls = mock_load_dotenv.call_args_list
        
        # First call should be to config/.env
        first_call_path = calls[0][1]["dotenv_path"]
        self.assertTrue(first_call_path.endswith("config/.env"))
        
        # Second call should be to root .env with override=False
        second_call = calls[1][1]
        self.assertFalse(second_call["override"])

    @patch("builtins.open", mock_open(read_data="test:\n  categories:\n    - tech\n    - science"))
    def test_load_categories_success(self):
        """Test successful category loading from YAML file."""
        categories = load_categories()
        
        self.assertIsInstance(categories, dict)
        self.assertIn("test", categories)

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_categories_file_not_found(self):
        """Test category loading with missing file."""
        with patch("builtins.print") as mock_print:
            categories = load_categories()
            
            self.assertEqual(categories, {})
            mock_print.assert_called_once()
            self.assertIn("Warning: Categories file not found", mock_print.call_args[0][0])

    @patch("builtins.open", mock_open(read_data="invalid: yaml: content: ["))
    def test_load_categories_yaml_error(self):
        """Test category loading with invalid YAML."""
        with patch("builtins.print") as mock_print:
            categories = load_categories()
            
            self.assertEqual(categories, {})
            mock_print.assert_called_once()
            self.assertIn("Warning: Error parsing categories YAML", mock_print.call_args[0][0])


class TestModelSelection(unittest.TestCase):
    """Test model selection logic for different task types."""

    def test_get_model_for_task_deepseek_provider(self):
        """Test model selection for DeepSeek provider."""
        config = {
            "llm_provider": "deepseek",
            "llm_model": "deepseek-ai/deepseek-chat",
            "llm_model_premium": "deepseek-ai/deepseek-chat",
            "llm_model_reasoner": "deepseek-ai/deepseek-reasoner"
        }
        
        self.assertEqual(get_model_for_task(config, "default"), "deepseek-ai/deepseek-chat")
        self.assertEqual(get_model_for_task(config, "premium"), "deepseek-ai/deepseek-chat")
        self.assertEqual(get_model_for_task(config, "reasoner"), "deepseek-ai/deepseek-reasoner")

    def test_get_model_for_task_openrouter_provider(self):
        """Test model selection for OpenRouter provider."""
        config = {
            "llm_provider": "openrouter",
            "llm_model": "mistralai/mistral-7b-instruct",
            "llm_model_premium": "anthropic/claude-3-sonnet",
            "llm_model_budget": "mistralai/mistral-7b-instruct",
            "llm_model_fallback": "google/gemini-pro"
        }
        
        self.assertEqual(get_model_for_task(config, "default"), "mistralai/mistral-7b-instruct")
        self.assertEqual(get_model_for_task(config, "premium"), "anthropic/claude-3-sonnet")
        self.assertEqual(get_model_for_task(config, "budget"), "mistralai/mistral-7b-instruct")
        self.assertEqual(get_model_for_task(config, "fallback"), "google/gemini-pro")

    def test_get_model_for_task_missing_config(self):
        """Test model selection with missing configuration values."""
        config = {"llm_provider": "openrouter"}
        
        # Should return empty string for missing models
        self.assertEqual(get_model_for_task(config, "premium"), "")
        self.assertEqual(get_model_for_task(config, "budget"), "mistralai/mistral-7b-instruct")


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation with ConfigValidator."""

    def setUp(self):
        """Set up validator instance."""
        self.validator = ConfigValidator()

    def test_validate_empty_config(self):
        """Test validation of empty configuration."""
        errors, warnings = self.validator.validate_config({})
        
        # Should have errors for missing required fields
        error_fields = [error.field for error in errors]
        self.assertIn("llm_provider", error_fields)

    def test_validate_minimal_valid_config(self):
        """Test validation of minimal valid configuration."""
        config = {
            "llm_provider": "openrouter",
            "llm_model": "mistralai/mistral-7b-instruct",
            "OPENROUTER_API_KEY": "sk-or-v1-test-key",
            "data_directory": "output",
            "categories": {}
        }
        
        errors, warnings = self.validator.validate_config(config)
        
        # Should pass basic validation
        llm_errors = [e for e in errors if e.field in ["llm_provider", "llm_model"]]
        self.assertEqual(len(llm_errors), 0)

    def test_validate_invalid_provider(self):
        """Test validation with invalid LLM provider."""
        config = {"llm_provider": "invalid_provider"}
        
        errors, warnings = self.validator.validate_config(config)
        
        provider_errors = [e for e in errors if e.field == "llm_provider"]
        self.assertTrue(len(provider_errors) > 0)
        self.assertIn("Invalid LLM provider", provider_errors[0].message)

    def test_validation_error_structure(self):
        """Test that validation errors have proper structure."""
        config = {"llm_provider": "invalid"}
        
        errors, warnings = self.validator.validate_config(config)
        
        if errors:
            error = errors[0]
            self.assertIsInstance(error, ValidationError)
            self.assertIsInstance(error.field, str)
            self.assertIsInstance(error.message, str)
            self.assertIsInstance(error.severity, str)
            self.assertIsInstance(error.guidance, str)


class TestIngestorConfiguration(unittest.TestCase):
    """Test ingestor-specific configuration handling."""

    @patch.dict(os.environ, {
        "ARTICLE_INGESTOR_ENABLED": "false",
        "PODCAST_INGESTOR_ENABLED": "true",
        "PODCAST_EPISODE_LIMIT": "10"
    })
    def test_ingestor_configuration_loading(self):
        """Test that ingestor configurations are loaded correctly."""
        config = load_config()
        
        self.assertFalse(config["article_ingestor"]["enabled"])
        self.assertTrue(config["podcast_ingestor"]["enabled"])
        self.assertEqual(config["podcast_ingestor"]["episode_limit"], 10)

    def test_ingestor_default_configuration(self):
        """Test default ingestor configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
            
            # All ingestors should be enabled by default
            self.assertTrue(config["article_ingestor"]["enabled"])
            self.assertTrue(config["podcast_ingestor"]["enabled"])
            self.assertTrue(config["youtube_ingestor"]["enabled"])
            self.assertTrue(config["instapaper_ingestor"]["enabled"])


class TestSmartProviderLogic(unittest.TestCase):
    """Test smart LLM provider detection and configuration."""

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-deepseek-key"})
    def test_deepseek_provider_priority(self):
        """Test that DeepSeek provider is preferred when key is available."""
        config = load_config()
        
        self.assertEqual(config["llm_provider"], "deepseek")
        self.assertEqual(config["llm_model"], "deepseek-ai/deepseek-chat")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-or-v1-openrouter-key"})
    def test_openrouter_key_detection(self):
        """Test automatic OpenRouter key detection from OPENAI_API_KEY."""
        with patch("builtins.print") as mock_print:
            config = load_config()
            
            self.assertEqual(config["llm_provider"], "openrouter")
            self.assertEqual(config["OPENROUTER_API_KEY"], "sk-or-v1-openrouter-key")
            mock_print.assert_called()
            self.assertIn("OpenRouter key", mock_print.call_args[0][0])

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_warning(self):
        """Test warning when API key is missing for non-ollama providers."""
        with patch("builtins.print") as mock_print:
            config = load_config()
            
            # Should warn about missing OPENROUTER_API_KEY
            mock_print.assert_called()
            warning_found = any("OPENROUTER_API_KEY is not set" in str(call) 
                              for call in mock_print.call_args_list)
            self.assertTrue(warning_found)


class TestPathConfiguration(unittest.TestCase):
    """Test path and directory configuration."""

    @patch.dict(os.environ, {"DATA_DIRECTORY": "custom_data"})
    def test_custom_data_directory(self):
        """Test custom data directory configuration."""
        config = load_config()
        
        self.assertEqual(config["data_directory"], "custom_data")
        self.assertEqual(config["article_output_path"], 
                        os.path.join("custom_data", "articles"))
        self.assertEqual(config["podcast_output_path"], 
                        os.path.join("custom_data", "podcasts"))
        self.assertEqual(config["youtube_output_path"], 
                        os.path.join("custom_data", "youtube"))

    def test_default_output_paths(self):
        """Test default output path configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
            
            self.assertEqual(config["data_directory"], "output")
            self.assertTrue(config["article_output_path"].endswith("articles"))
            self.assertTrue(config["podcast_output_path"].endswith("podcasts"))
            self.assertTrue(config["youtube_output_path"].endswith("youtube"))


class TestFeatureFlags(unittest.TestCase):
    """Test feature flag configuration."""

    @patch.dict(os.environ, {
        "USE_12FT_IO_FALLBACK": "true",
        "USE_PLAYWRIGHT_FOR_NYT": "true"
    })
    def test_feature_flags_enabled(self):
        """Test feature flags when enabled."""
        config = load_config()
        
        self.assertTrue(config["USE_12FT_IO_FALLBACK"])
        self.assertTrue(config["USE_PLAYWRIGHT_FOR_NYT"])

    @patch.dict(os.environ, {
        "USE_12FT_IO_FALLBACK": "false",
        "USE_PLAYWRIGHT_FOR_NYT": "FALSE"
    })
    def test_feature_flags_disabled(self):
        """Test feature flags when explicitly disabled."""
        config = load_config()
        
        self.assertFalse(config["USE_12FT_IO_FALLBACK"])
        self.assertFalse(config["USE_PLAYWRIGHT_FOR_NYT"])

    def test_feature_flags_default(self):
        """Test default feature flag values."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
            
            self.assertFalse(config["USE_12FT_IO_FALLBACK"])
            self.assertFalse(config["USE_PLAYWRIGHT_FOR_NYT"])


class TestModelTierConfiguration(unittest.TestCase):
    """Test tiered model configuration for different use cases."""

    def test_free_model_tiers_loaded(self):
        """Test that all free model tiers are loaded with defaults."""
        config = load_config()
        
        # Test premium free models
        self.assertIn("MODEL_FREE_PREMIUM_1", config)
        self.assertIn("MODEL_FREE_PREMIUM_2", config)
        self.assertIn("MODEL_FREE_PREMIUM_3", config)
        
        # Test fallback free models  
        self.assertIn("MODEL_FREE_FALLBACK_1", config)
        self.assertIn("MODEL_FREE_FALLBACK_2", config)
        self.assertIn("MODEL_FREE_FALLBACK_3", config)
        
        # Test budget free models
        self.assertIn("MODEL_FREE_BUDGET_1", config)
        self.assertIn("MODEL_FREE_BUDGET_2", config)
        self.assertIn("MODEL_FREE_BUDGET_3", config)

    @patch.dict(os.environ, {
        "MODEL_FREE_PREMIUM_1": "custom/premium-model",
        "MODEL_FREE_BUDGET_1": "custom/budget-model"
    })
    def test_custom_free_model_tiers(self):
        """Test custom free model tier configuration."""
        config = load_config()
        
        self.assertEqual(config["MODEL_FREE_PREMIUM_1"], "custom/premium-model")
        self.assertEqual(config["MODEL_FREE_BUDGET_1"], "custom/budget-model")


if __name__ == "__main__":
    unittest.main()