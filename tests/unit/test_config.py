"""
Unit tests for helpers/config.py
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import yaml

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from helpers.config import (
    get_config,
    get_model_for_task,
    is_feature_enabled,
    load_categories,
    load_config,
)


class TestLoadCategories:
    """Test load_categories function."""

    def test_load_categories_success(self):
        """Test successful loading of categories YAML."""
        mock_categories = {
            "technology": ["AI", "Machine Learning"],
            "business": ["Finance", "Marketing"],
        }

        with patch(
            "builtins.open", mock_open(read_data=yaml.dump(mock_categories))
        ), patch("os.path.join") as mock_join, patch(
            "yaml.safe_load", return_value=mock_categories
        ) as mock_yaml:

            result = load_categories()

            assert result == mock_categories
            mock_yaml.assert_called_once()

    def test_load_categories_file_not_found(self, capsys):
        """Test handling of missing categories file."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = load_categories()

            assert result == {}
            captured = capsys.readouterr()
            assert "Warning: Categories file not found" in captured.out

    def test_load_categories_yaml_error(self, capsys):
        """Test handling of YAML parsing errors."""
        with patch(
            "builtins.open", mock_open(read_data="invalid: yaml: content:")
        ), patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML")):

            result = load_categories()

            assert result == {}
            captured = capsys.readouterr()
            assert "Warning: Error parsing categories YAML file" in captured.out


class TestLoadConfig:
    """Test load_config function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_defaults(self):
        """Test load_config with default values."""
        with patch("dotenv.load_dotenv"), patch(
            "helpers.config.load_categories", return_value={}
        ), patch("helpers.validate.ConfigValidator") as mock_validator_class:

            # Mock the validator
            mock_validator = Mock()
            mock_validator.validate_config.return_value = ([], [])
            mock_validator.format_validation_report.return_value = ""
            mock_validator_class.return_value = mock_validator

            config = load_config()

            # Test default values
            assert config["data_directory"] == "output"
            assert config["llm_provider"] == "openrouter"
            assert config["llm_model"] == "mistralai/mistral-7b-instruct"
            assert config["PODCAST_EPISODE_LIMIT"] == 0
            assert config["USE_12FT_IO_FALLBACK"] is False

    @patch.dict(
        os.environ,
        {
            "DATA_DIRECTORY": "custom_output",
            "OPENROUTER_API_KEY": "sk-or-v1-test-key",
            "LLM_PROVIDER": "custom_provider",
            "LLM_MODEL": "custom-model",
            "PODCAST_EPISODE_LIMIT": "5",
            "USE_12FT_IO_FALLBACK": "true",
        },
    )
    def test_load_config_custom_values(self):
        """Test load_config with custom environment values."""
        with patch("dotenv.load_dotenv"), patch(
            "helpers.config.load_categories", return_value={}
        ), patch("helpers.validate.ConfigValidator") as mock_validator_class:

            # Mock the validator
            mock_validator = Mock()
            mock_validator.validate_config.return_value = ([], [])
            mock_validator.format_validation_report.return_value = ""
            mock_validator_class.return_value = mock_validator

            config = load_config()

            # Test custom values
            assert config["data_directory"] == "custom_output"
            assert config["OPENROUTER_API_KEY"] == "sk-or-v1-test-key"
            assert config["llm_provider"] == "custom_provider"
            assert config["llm_model"] == "custom-model"
            assert config["PODCAST_EPISODE_LIMIT"] == 5
            assert config["USE_12FT_IO_FALLBACK"] is True

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-deepseek-key"})
    def test_load_config_deepseek_provider(self):
        """Test load_config with DeepSeek API key present."""
        with patch("dotenv.load_dotenv"), patch(
            "helpers.config.load_categories", return_value={}
        ), patch("helpers.validate.ConfigValidator") as mock_validator_class:

            # Mock the validator
            mock_validator = Mock()
            mock_validator.validate_config.return_value = ([], [])
            mock_validator.format_validation_report.return_value = ""
            mock_validator_class.return_value = mock_validator

            config = load_config()

            # Test DeepSeek provider configuration
            assert config["DEEPSEEK_API_KEY"] == "test-deepseek-key"
            assert config["llm_provider"] == "deepseek"
            assert config["llm_model"] == "deepseek-ai/deepseek-chat"
            assert "llm_model_reasoner" in config

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-or-v1-openrouter-key"})
    def test_load_config_openrouter_from_openai_key(self, capsys):
        """Test auto-detection of OpenRouter key in OPENAI_API_KEY."""
        with patch("dotenv.load_dotenv"), patch(
            "helpers.config.load_categories", return_value={}
        ), patch("helpers.validate.ConfigValidator") as mock_validator_class:

            # Mock the validator
            mock_validator = Mock()
            mock_validator.validate_config.return_value = ([], [])
            mock_validator.format_validation_report.return_value = ""
            mock_validator_class.return_value = mock_validator

            config = load_config()

            # Test auto-configuration
            assert config["OPENROUTER_API_KEY"] == "sk-or-v1-openrouter-key"
            assert config["llm_provider"] == "openrouter"

            captured = capsys.readouterr()
            assert "Found OpenRouter key in OPENAI_API_KEY" in captured.out

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_validation_errors(self, capsys):
        """Test handling of validation errors."""
        mock_error = Mock()
        mock_error.field = "test_field"
        mock_error.message = "test error message"

        mock_warning = Mock()
        mock_warning.field = "test_warning_field"
        mock_warning.message = "test warning message"

        with patch("dotenv.load_dotenv"), patch(
            "helpers.config.load_categories", return_value={}
        ), patch("helpers.validate.ConfigValidator") as mock_validator_class:

            # Mock the validator with errors
            mock_validator = Mock()
            mock_validator.validate_config.return_value = ([mock_error], [mock_warning])
            mock_validator.format_validation_report.return_value = (
                "Test validation report"
            )
            mock_validator_class.return_value = mock_validator

            config = load_config()

            captured = capsys.readouterr()
            assert "Test validation report" in captured.out
            assert "Simple Error Summary:" in captured.out
            assert "test_field: test error message" in captured.out

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_validation_import_error(self):
        """Test fallback when ConfigValidator import fails."""
        with patch("dotenv.load_dotenv"), patch(
            "helpers.config.load_categories", return_value={}
        ), patch("helpers.validate.ConfigValidator", side_effect=ImportError), patch(
            "helpers.validate.validate_config", return_value=["legacy error"]
        ) as mock_legacy:

            config = load_config()

            mock_legacy.assert_called_once()


class TestGetModelForTask:
    """Test get_model_for_task function."""

    def test_get_model_deepseek_reasoner(self):
        """Test model selection for DeepSeek reasoner task."""
        config = {
            "llm_provider": "deepseek",
            "llm_model_reasoner": "deepseek-ai/deepseek-reasoner",
        }

        result = get_model_for_task(config, "reasoner")
        assert result == "deepseek-ai/deepseek-reasoner"

    def test_get_model_deepseek_premium(self):
        """Test model selection for DeepSeek premium task."""
        config = {
            "llm_provider": "deepseek",
            "llm_model_premium": "deepseek-ai/deepseek-chat",
        }

        result = get_model_for_task(config, "premium")
        assert result == "deepseek-ai/deepseek-chat"

    def test_get_model_deepseek_default(self):
        """Test model selection for DeepSeek default task."""
        config = {"llm_provider": "deepseek", "llm_model": "deepseek-ai/deepseek-chat"}

        result = get_model_for_task(config, "default")
        assert result == "deepseek-ai/deepseek-chat"

    def test_get_model_non_deepseek_premium(self):
        """Test model selection for non-DeepSeek premium task."""
        config = {
            "llm_provider": "openrouter",
            "llm_model_premium": "gpt-4",
            "llm_model": "gpt-3.5-turbo",
        }

        result = get_model_for_task(config, "premium")
        assert result == "gpt-4"

    def test_get_model_budget(self):
        """Test model selection for budget task."""
        config = {
            "llm_provider": "openrouter",
            "llm_model_budget": "mistralai/mistral-7b-instruct",
        }

        result = get_model_for_task(config, "budget")
        assert result == "mistralai/mistral-7b-instruct"

    def test_get_model_fallback(self):
        """Test model selection for fallback task."""
        config = {
            "llm_provider": "openrouter",
            "llm_model_fallback": "fallback-model",
            "llm_model": "primary-model",
        }

        result = get_model_for_task(config, "fallback")
        assert result == "fallback-model"

    def test_get_model_default(self):
        """Test model selection for default task."""
        config = {"llm_provider": "openrouter", "llm_model": "default-model"}

        result = get_model_for_task(config, "default")
        assert result == "default-model"


class TestLegacyFunctions:
    """Test legacy functions."""

    @patch.dict(os.environ, {"TEST_KEY": "test_value"})
    def test_get_config_existing_key(self):
        """Test get_config with existing environment variable."""
        result = get_config("TEST_KEY")
        assert result == "test_value"

    def test_get_config_missing_key_with_default(self):
        """Test get_config with missing key and default value."""
        result = get_config("MISSING_KEY", "default_value")
        assert result == "default_value"

    def test_get_config_missing_key_no_default(self):
        """Test get_config with missing key and no default."""
        result = get_config("MISSING_KEY")
        assert result is None

    @patch("helpers.config.get_config")
    def test_is_feature_enabled_true(self, mock_get_config):
        """Test is_feature_enabled with true value."""
        mock_get_config.return_value = "true"

        result = is_feature_enabled("FEATURE_KEY")
        assert result is True
        mock_get_config.assert_called_once_with("FEATURE_KEY", "false")

    @patch("helpers.config.get_config")
    def test_is_feature_enabled_false(self, mock_get_config):
        """Test is_feature_enabled with false value."""
        mock_get_config.return_value = "false"

        result = is_feature_enabled("FEATURE_KEY")
        assert result is False

    @patch("helpers.config.get_config")
    def test_is_feature_enabled_none(self, mock_get_config):
        """Test is_feature_enabled with None value."""
        mock_get_config.return_value = None

        result = is_feature_enabled("FEATURE_KEY")
        assert result is False


class TestConfigIntegration:
    """Integration tests for config module."""

    def test_ingestor_configurations(self):
        """Test that ingestor configurations are properly set."""
        with patch("dotenv.load_dotenv"), patch(
            "helpers.config.load_categories", return_value={}
        ), patch(
            "helpers.validate.ConfigValidator"
        ) as mock_validator_class, patch.dict(
            os.environ,
            {
                "ARTICLE_INGESTOR_ENABLED": "false",
                "PODCAST_EPISODE_LIMIT": "10",
                "YOUTUBE_INGESTOR_ENABLED": "true",
            },
        ):

            # Mock the validator
            mock_validator = Mock()
            mock_validator.validate_config.return_value = ([], [])
            mock_validator.format_validation_report.return_value = ""
            mock_validator_class.return_value = mock_validator

            config = load_config()

            assert config["article_ingestor"]["enabled"] is False
            assert config["podcast_ingestor"]["episode_limit"] == 10
            assert config["youtube_ingestor"]["enabled"] is True
            assert config["instapaper_ingestor"]["enabled"] is True  # default

    def test_model_fallback_chain(self):
        """Test that model fallback chain works correctly."""
        config = {
            "llm_provider": "openrouter",
            "llm_model": None,
            "llm_model_premium": None,
            "llm_model_budget": None,
            "llm_model_fallback": None,
        }

        # Test fallbacks
        result_default = get_model_for_task(config, "default")
        result_budget = get_model_for_task(config, "budget")

        assert result_default == "mistralai/mistral-7b-instruct"
        assert result_budget == "mistralai/mistral-7b-instruct"
