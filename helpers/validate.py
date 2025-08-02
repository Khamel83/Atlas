"""
Configuration Validation Module

This module provides functions to validate the application's configuration
with detailed error messages and specific guidance for resolution.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ValidationError:
    """Structured validation error with specific guidance."""

    field: str
    message: str
    severity: str  # 'error', 'warning', 'info'
    guidance: str
    fix_command: Optional[str] = None
    documentation_url: Optional[str] = None


class ConfigValidator:
    """Enhanced configuration validator with detailed error guidance."""

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate_config(
        self, config: Dict
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Validates the configuration dictionary with detailed error guidance.

        Args:
            config: The configuration dictionary loaded from config.py.

        Returns:
            Tuple of (errors, warnings). Errors prevent operation, warnings suggest improvements.
        """
        self.errors = []
        self.warnings = []

        # Core validation checks
        self._validate_llm_configuration(config)
        self._validate_api_keys(config)
        self._validate_ingestor_configuration(config)
        self._validate_paths_and_directories(config)
        self._validate_model_configuration(config)
        self._validate_security_settings(config)
        self._validate_performance_settings(config)

        # Advanced validation checks
        self._validate_environment_consistency(config)
        self._validate_feature_dependencies(config)
        self._validate_resource_availability(config)
        self._validate_configuration_completeness(config)

        return self.errors, self.warnings

    def _validate_llm_configuration(self, config: Dict):
        """Validate LLM provider and model configuration."""
        provider = config.get("llm_provider")

        if not provider:
            self.errors.append(
                ValidationError(
                    field="llm_provider",
                    message="LLM provider is not configured",
                    severity="error",
                    guidance="Set LLM_PROVIDER in your .env file to one of: 'openrouter', 'deepseek', 'ollama'",
                    fix_command="echo 'LLM_PROVIDER=openrouter' >> config/.env",
                    documentation_url="https://docs.atlas.com/configuration#llm-providers",
                )
            )
            return

        valid_providers = ["openrouter", "deepseek", "ollama"]
        if provider not in valid_providers:
            self.errors.append(
                ValidationError(
                    field="llm_provider",
                    message=f"Invalid LLM provider '{provider}'",
                    severity="error",
                    guidance=f"Valid providers are: {', '.join(valid_providers)}. Choose based on your needs:\n"
                    + "- 'openrouter': Best model variety, requires API key and costs money\n"
                    + "- 'deepseek': Cost-effective, good performance, requires API key\n"
                    + "- 'ollama': Free local models, no API key needed but requires local setup",
                    fix_command=f"sed -i 's/LLM_PROVIDER={provider}/LLM_PROVIDER=openrouter/' config/.env",
                )
            )

        # Validate model configuration
        model = config.get("llm_model")
        if not model:
            self.errors.append(
                ValidationError(
                    field="llm_model",
                    message="No LLM model specified",
                    severity="error",
                    guidance="Set LLM_MODEL in your .env file. Recommended models:\n"
                    + "- For OpenRouter: 'mistralai/mistral-7b-instruct' (free), 'anthropic/claude-3-sonnet' (premium)\n"
                    + "- For DeepSeek: 'deepseek-ai/deepseek-chat' (default), 'deepseek-ai/deepseek-reasoner' (reasoning)\n"
                    + "- For Ollama: 'llama2', 'mistral', 'codellama'",
                    fix_command="echo 'LLM_MODEL=mistralai/mistral-7b-instruct' >> config/.env",
                )
            )

    def _validate_api_keys(self, config: Dict):
        """Validate API keys with provider-specific guidance."""
        provider = config.get("llm_provider")

        # OpenRouter validation
        if provider == "openrouter":
            api_key = config.get("OPENROUTER_API_KEY")
            if not api_key:
                self.errors.append(
                    ValidationError(
                        field="OPENROUTER_API_KEY",
                        message="OpenRouter API key is required but not configured",
                        severity="error",
                        guidance="Get your API key from https://openrouter.ai/keys and add it to your .env file. "
                        + "OpenRouter provides access to multiple AI models with pay-per-use pricing.",
                        fix_command="echo 'OPENROUTER_API_KEY=your_key_here' >> config/.env",
                        documentation_url="https://openrouter.ai/docs/quick-start",
                    )
                )
            elif not self._is_valid_openrouter_key(api_key):
                self.errors.append(
                    ValidationError(
                        field="OPENROUTER_API_KEY",
                        message="OpenRouter API key format appears invalid",
                        severity="error",
                        guidance="OpenRouter API keys should start with 'sk-or-v1-'. Please verify your key at https://openrouter.ai/keys",
                        fix_command="# Copy the correct key from https://openrouter.ai/keys and update config/.env",
                    )
                )

        # DeepSeek validation
        elif provider == "deepseek":
            api_key = config.get("DEEPSEEK_API_KEY")
            if not api_key:
                self.errors.append(
                    ValidationError(
                        field="DEEPSEEK_API_KEY",
                        message="DeepSeek API key is required but not configured",
                        severity="error",
                        guidance="Get your API key from https://platform.deepseek.com/api_keys and add it to your .env file. "
                        + "DeepSeek offers competitive pricing for reasoning and chat models.",
                        fix_command="echo 'DEEPSEEK_API_KEY=your_key_here' >> config/.env",
                        documentation_url="https://platform.deepseek.com/docs",
                    )
                )

        # YouTube API validation
        if config.get("youtube_ingestor", {}).get("enabled"):
            youtube_key = config.get("YOUTUBE_API_KEY")
            if not youtube_key:
                self.errors.append(
                    ValidationError(
                        field="YOUTUBE_API_KEY",
                        message="YouTube API key is required when YouTube ingestor is enabled",
                        severity="error",
                        guidance="Get a YouTube Data API v3 key from Google Cloud Console:\n"
                        + "1. Go to https://console.cloud.google.com/apis/library/youtube.googleapis.com\n"
                        + "2. Enable the YouTube Data API v3\n"
                        + "3. Create credentials (API key)\n"
                        + "4. Add the key to your .env file\n"
                        + "Alternatively, disable YouTube ingestor by setting YOUTUBE_INGESTOR_ENABLED=false",
                        fix_command="echo 'YOUTUBE_API_KEY=your_youtube_api_key' >> config/.env",
                        documentation_url="https://developers.google.com/youtube/v3/getting-started",
                    )
                )

    def _validate_ingestor_configuration(self, config: Dict):
        """Validate ingestor-specific configurations."""
        # Instapaper validation
        if config.get("instapaper_ingestor", {}).get("enabled"):
            login = config.get("INSTAPAPER_LOGIN")
            password = config.get("INSTAPAPER_PASSWORD")

            if not login or not password:
                self.errors.append(
                    ValidationError(
                        field="INSTAPAPER_CREDENTIALS",
                        message="Instapaper credentials are incomplete",
                        severity="error",
                        guidance="Both INSTAPAPER_LOGIN and INSTAPAPER_PASSWORD are required when Instapaper ingestor is enabled. "
                        + "Use your Instapaper account email and password, or disable the ingestor by setting INSTAPAPER_INGESTOR_ENABLED=false",
                        fix_command="echo -e 'INSTAPAPER_LOGIN=your_email\nINSTAPAPER_PASSWORD=your_password' >> config/.env",
                    )
                )

        # NYT validation
        if config.get("USE_PLAYWRIGHT_FOR_NYT"):
            username = config.get("NYT_USERNAME")
            password = config.get("NYT_PASSWORD")

            if not username or not password:
                self.errors.append(
                    ValidationError(
                        field="NYT_CREDENTIALS",
                        message="NYT credentials are required when Playwright NYT scraping is enabled",
                        severity="error",
                        guidance="Both NYT_USERNAME and NYT_PASSWORD are required when USE_PLAYWRIGHT_FOR_NYT=true. "
                        + "Use your New York Times subscription credentials, or disable Playwright NYT scraping by setting USE_PLAYWRIGHT_FOR_NYT=false",
                        fix_command="echo -e 'NYT_USERNAME=your_email\nNYT_PASSWORD=your_password' >> config/.env",
                    )
                )

        # Podcast episode limit validation
        episode_limit = config.get("PODCAST_EPISODE_LIMIT", 0)
        if episode_limit > 100:
            self.warnings.append(
                ValidationError(
                    field="PODCAST_EPISODE_LIMIT",
                    message=f"High podcast episode limit ({episode_limit}) may impact performance",
                    severity="warning",
                    guidance="Processing many episodes at once can be slow and expensive. Consider a lower limit (10-50) for better performance. "
                    + "Set to 0 for no limit if you specifically need all episodes.",
                    fix_command=f"sed -i 's/PODCAST_EPISODE_LIMIT={episode_limit}/PODCAST_EPISODE_LIMIT=20/' config/.env",
                )
            )

    def _validate_paths_and_directories(self, config: Dict):
        """Validate path configurations and directory accessibility."""
        data_dir = config.get("data_directory", "output")

        # Check if data directory is writable
        data_path = Path(data_dir)
        try:
            data_path.mkdir(parents=True, exist_ok=True)
            test_file = data_path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
        except (PermissionError, OSError) as e:
            self.errors.append(
                ValidationError(
                    field="data_directory",
                    message=f"Data directory '{data_dir}' is not writable",
                    severity="error",
                    guidance=f"The application needs write access to store processed content. Error: {e}\n"
                    + "Solutions:\n"
                    + "1. Create the directory with proper permissions: mkdir -p {data_dir} && chmod 755 {data_dir}\n"
                    + "2. Choose a different directory by setting DATA_DIRECTORY in your .env file\n"
                    + "3. Run with appropriate permissions if needed",
                    fix_command=f"mkdir -p {data_dir} && chmod 755 {data_dir}",
                )
            )

        # Validate output subdirectories can be created
        subdirs = ["articles", "podcasts", "youtube", "logs"]
        for subdir in subdirs:
            subdir_path = data_path / subdir
            try:
                subdir_path.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError):
                self.warnings.append(
                    ValidationError(
                        field=f"output_{subdir}_directory",
                        message=f"Unable to create {subdir} subdirectory",
                        severity="warning",
                        guidance=f"The {subdir} subdirectory in {data_dir} cannot be created. "
                        + f"This may cause issues when processing {subdir} content.",
                        fix_command=f"mkdir -p {data_dir}/{subdir} && chmod 755 {data_dir}/{subdir}",
                    )
                )

    def _validate_model_configuration(self, config: Dict):
        """Validate model tier configuration."""
        provider = config.get("llm_provider")

        if provider == "deepseek":
            # Validate DeepSeek model configuration
            reasoner_model = config.get("llm_model_reasoner")
            if reasoner_model and "reasoner" not in reasoner_model:
                self.warnings.append(
                    ValidationError(
                        field="llm_model_reasoner",
                        message="Reasoner model may not be a reasoning model",
                        severity="warning",
                        guidance="For best reasoning performance, use 'deepseek-ai/deepseek-reasoner' for the reasoner model. "
                        + "Regular chat models may not provide optimal reasoning capabilities.",
                        fix_command="echo 'MODEL_REASONER=deepseek-ai/deepseek-reasoner' >> config/.env",
                    )
                )

        # Check if premium/budget models are configured for cost optimization
        if not config.get("llm_model_budget") and provider in [
            "openrouter",
            "deepseek",
        ]:
            self.warnings.append(
                ValidationError(
                    field="llm_model_budget",
                    message="No budget model configured for cost optimization",
                    severity="warning",
                    guidance="Configure a budget model to reduce costs for simple tasks. Recommended budget models:\n"
                    + "- OpenRouter: 'mistralai/mistral-7b-instruct:free' or 'google/gemma-2-9b-it:free'\n"
                    + "- DeepSeek: Use the same model as default for simplicity",
                    fix_command="echo 'MODEL_BUDGET=mistralai/mistral-7b-instruct:free' >> config/.env",
                )
            )

    def _validate_security_settings(self, config: Dict):
        """Validate security-related configuration."""
        # Check for insecure configurations
        if config.get("USE_12FT_IO_FALLBACK"):
            self.warnings.append(
                ValidationError(
                    field="USE_12FT_IO_FALLBACK",
                    message="12ft.io fallback is enabled - potential privacy concern",
                    severity="warning",
                    guidance="The 12ft.io service sends URLs to a third-party service to bypass paywalls. "
                    + "This may expose your reading habits. Consider disabling if privacy is a concern.",
                    fix_command="sed -i 's/USE_12FT_IO_FALLBACK=true/USE_12FT_IO_FALLBACK=false/' config/.env",
                )
            )

        # Check for credentials in environment that might be logged
        sensitive_fields = [
            "OPENROUTER_API_KEY",
            "DEEPSEEK_API_KEY",
            "YOUTUBE_API_KEY",
            "INSTAPAPER_PASSWORD",
            "NYT_PASSWORD",
        ]

        for field in sensitive_fields:
            value = config.get(field)
            if value and (
                "test" in value.lower()
                or "example" in value.lower()
                or "your_" in value.lower()
            ):
                self.warnings.append(
                    ValidationError(
                        field=field,
                        message=f"Potentially placeholder value detected in {field}",
                        severity="warning",
                        guidance=f"The value for {field} appears to be a placeholder. Make sure to replace it with your actual API key or credential.",
                        fix_command=f"# Update {field} in config/.env with your real credential",
                    )
                )

    def _validate_performance_settings(self, config: Dict):
        """Validate performance-related settings."""
        # Check for potentially expensive configurations
        if (
            not config.get("llm_model_budget")
            and config.get("llm_provider") == "openrouter"
        ):
            premium_model = config.get("llm_model_premium", config.get("llm_model", ""))
            if "claude-3" in premium_model or "gpt-4" in premium_model:
                self.warnings.append(
                    ValidationError(
                        field="llm_model_configuration",
                        message="Using expensive model without budget tier configured",
                        severity="warning",
                        guidance="You're using an expensive model as default. Consider:\n"
                        + "1. Set a budget model for simple tasks to reduce costs\n"
                        + "2. Reserve premium models for complex analysis only\n"
                        + "3. Monitor your OpenRouter usage and costs regularly",
                        fix_command="echo 'MODEL_BUDGET=mistralai/mistral-7b-instruct:free' >> config/.env",
                    )
                )

        # Validate memory and processing limits
        episode_limit = config.get("PODCAST_EPISODE_LIMIT", 0)
        if episode_limit > 500:
            self.warnings.append(
                ValidationError(
                    field="PODCAST_EPISODE_LIMIT",
                    message=f"Very high podcast episode limit ({episode_limit}) may cause memory issues",
                    severity="warning",
                    guidance="Processing hundreds of episodes simultaneously can consume significant memory and processing time. "
                    + "Consider processing in smaller batches or implementing streaming processing.",
                    fix_command=f"sed -i 's/PODCAST_EPISODE_LIMIT={episode_limit}/PODCAST_EPISODE_LIMIT=100/' config/.env",
                )
            )

        # Check for inefficient model configuration
        models = [
            config.get("llm_model"),
            config.get("llm_model_premium"),
            config.get("llm_model_budget"),
            config.get("llm_model_fallback"),
        ]
        unique_models = set(filter(None, models))
        if len(unique_models) == 1 and len([m for m in models if m]) > 1:
            self.warnings.append(
                ValidationError(
                    field="model_tier_configuration",
                    message="All model tiers use the same model - no cost optimization",
                    severity="warning",
                    guidance="Using the same model for all tiers (premium/budget/fallback) doesn't provide cost optimization. "
                    + "Consider using a cheaper model for budget tasks and a more capable model for premium tasks.",
                    fix_command="echo 'MODEL_BUDGET=mistralai/mistral-7b-instruct:free' >> config/.env",
                )
            )

    def _validate_environment_consistency(self, config: Dict):
        """Validate consistency between different configuration values."""
        # Check provider-model consistency
        provider = config.get("llm_provider")
        model = config.get("llm_model", "")

        if provider == "deepseek" and not model.startswith("deepseek"):
            self.warnings.append(
                ValidationError(
                    field="provider_model_mismatch",
                    message=f"Provider '{provider}' doesn't match model '{model}'",
                    severity="warning",
                    guidance="Using a non-DeepSeek model with DeepSeek provider may cause issues. "
                    + "Either change the provider to match your model or use a DeepSeek model.",
                    fix_command="echo 'LLM_MODEL=deepseek-ai/deepseek-chat' >> config/.env",
                )
            )

        # Check data directory consistency
        data_dir = config.get("data_directory", "output")

        expected_paths = {
            "article_output_path": os.path.join(data_dir, "articles"),
            "podcast_output_path": os.path.join(data_dir, "podcasts"),
            "youtube_output_path": os.path.join(data_dir, "youtube"),
        }

        for path_key, expected_path in expected_paths.items():
            if config.get(path_key) != expected_path:
                self.warnings.append(
                    ValidationError(
                        field=path_key,
                        message="Output path inconsistent with data directory",
                        severity="warning",
                        guidance=f"The {path_key} should be under {data_dir} for consistency. "
                        + f"Expected: {expected_path}, got: {config.get(path_key)}",
                        fix_command="# Update configuration to use consistent paths",
                    )
                )

    def _validate_feature_dependencies(self, config: Dict):
        """Validate dependencies between enabled features."""
        # YouTube ingestor requires API key
        if config.get("youtube_ingestor", {}).get("enabled", True) and not config.get(
            "YOUTUBE_API_KEY"
        ):
            self.warnings.append(
                ValidationError(
                    field="youtube_feature_dependency",
                    message="YouTube ingestor enabled but no API key provided",
                    severity="warning",
                    guidance="YouTube ingestor requires YOUTUBE_API_KEY to function. Either provide the key or disable the ingestor.",
                    fix_command="echo 'YOUTUBE_INGESTOR_ENABLED=false' >> config/.env",
                )
            )

        # Transcription requires either API key or local setup
        if config.get("TRANSCRIBE_ENABLED", "false").lower() == "true":
            backend = config.get("TRANSCRIBE_BACKEND", "local")
            if backend == "api" and not config.get("OPENROUTER_API_KEY"):
                self.errors.append(
                    ValidationError(
                        field="transcription_dependency",
                        message="API transcription enabled but no API key provided",
                        severity="error",
                        guidance="When using 'api' transcription backend, OPENROUTER_API_KEY is required. "
                        + "Either provide the key or switch to local transcription.",
                        fix_command="echo 'TRANSCRIBE_BACKEND=local' >> config/.env",
                    )
                )
            elif backend == "local" and not os.path.exists(
                config.get("WHISPER_PATH", "/usr/local/bin/whisper")
            ):
                self.warnings.append(
                    ValidationError(
                        field="local_transcription_dependency",
                        message="Local transcription enabled but Whisper not found",
                        severity="warning",
                        guidance="Local transcription requires Whisper to be installed. "
                        + "Install with: pip install openai-whisper",
                        fix_command="pip install openai-whisper",
                    )
                )

    def _validate_resource_availability(self, config: Dict):
        """Validate system resources and external dependencies."""
        import shutil

        # Check for required system commands
        required_commands = ["ffmpeg", "yt-dlp"]
        for cmd in required_commands:
            if not shutil.which(cmd):
                self.warnings.append(
                    ValidationError(
                        field=f"{cmd}_availability",
                        message=f"Required command '{cmd}' not found in PATH",
                        severity="warning",
                        guidance=f"The {cmd} command is required for audio/video processing. "
                        + f"Install it using your system package manager.",
                        fix_command=f"# Install {cmd} using your package manager (brew/apt install {cmd})",
                    )
                )

        # Check disk space
        data_dir = config.get("data_directory", "output")
        try:
            statvfs = os.statvfs(data_dir if os.path.exists(data_dir) else ".")
            free_space_gb = (statvfs.f_bavail * statvfs.f_frsize) / (1024**3)
            if free_space_gb < 1:
                self.warnings.append(
                    ValidationError(
                        field="disk_space",
                        message=f"Low disk space: {free_space_gb:.1f}GB available",
                        severity="warning",
                        guidance="Atlas may consume significant disk space for downloaded content. "
                        + "Ensure adequate free space for operation.",
                        fix_command="# Free up disk space or choose a different data directory",
                    )
                )
        except (OSError, AttributeError):
            # Skip disk space check on systems where it's not available
            pass

    def _validate_configuration_completeness(self, config: Dict):
        """Validate configuration completeness and provide suggestions."""
        # Check for commonly missed configurations
        if not config.get("LOG_LEVEL"):
            self.warnings.append(
                ValidationError(
                    field="LOG_LEVEL",
                    message="No log level specified",
                    severity="warning",
                    guidance="Setting a log level helps with debugging. Recommended values: INFO for normal use, DEBUG for troubleshooting.",
                    fix_command="echo 'LOG_LEVEL=INFO' >> config/.env",
                )
            )

        # Check for processing timeout configuration
        timeout = config.get("PROCESSING_TIMEOUT")
        if not timeout:
            self.warnings.append(
                ValidationError(
                    field="PROCESSING_TIMEOUT",
                    message="No processing timeout configured",
                    severity="warning",
                    guidance="Setting a processing timeout prevents stuck operations. Recommended: 30-60 minutes for most use cases.",
                    fix_command="echo 'PROCESSING_TIMEOUT=30' >> config/.env",
                )
            )
        elif timeout and int(timeout) < 5:
            self.warnings.append(
                ValidationError(
                    field="PROCESSING_TIMEOUT",
                    message=f"Very short processing timeout ({timeout} minutes)",
                    severity="warning",
                    guidance="Short timeouts may cause legitimate operations to fail. Consider 15-30 minutes minimum.",
                    fix_command="echo 'PROCESSING_TIMEOUT=30' >> config/.env",
                )
            )

        # Check for max retries configuration
        max_retries = config.get("MAX_RETRIES")
        if not max_retries:
            self.warnings.append(
                ValidationError(
                    field="MAX_RETRIES",
                    message="No retry limit configured",
                    severity="warning",
                    guidance="Setting retry limits prevents infinite retry loops. Recommended: 3-5 retries.",
                    fix_command="echo 'MAX_RETRIES=3' >> config/.env",
                )
            )
        elif max_retries and int(max_retries) > 10:
            self.warnings.append(
                ValidationError(
                    field="MAX_RETRIES",
                    message=f"Very high retry limit ({max_retries})",
                    severity="warning",
                    guidance="Too many retries can cause long delays. Consider 3-5 retries for most use cases.",
                    fix_command="echo 'MAX_RETRIES=3' >> config/.env",
                )
            )

    def _is_valid_openrouter_key(self, key: str) -> bool:
        """Validate OpenRouter API key format."""
        return key.startswith("sk-or-v1-") and len(key) > 20

    def format_validation_report(
        self, errors: List[ValidationError], warnings: List[ValidationError]
    ) -> str:
        """Format validation results into a readable report."""
        if not errors and not warnings:
            return "✅ Configuration validation passed - no issues found."

        report = "\n🔧 Configuration Validation Report\n" + "=" * 40 + "\n"

        if errors:
            report += f"\n❌ ERRORS ({len(errors)} found) - These must be fixed:\n"
            for i, error in enumerate(errors, 1):
                report += f"\n{i}. {error.field}: {error.message}\n"
                report += f"   💡 How to fix: {error.guidance}\n"
                if error.fix_command:
                    report += f"   🔨 Quick fix: {error.fix_command}\n"
                if error.documentation_url:
                    report += f"   📖 Docs: {error.documentation_url}\n"

        if warnings:
            report += f"\n⚠️  WARNINGS ({len(warnings)} found) - Consider addressing:\n"
            for i, warning in enumerate(warnings, 1):
                report += f"\n{i}. {warning.field}: {warning.message}\n"
                report += f"   💡 Suggestion: {warning.guidance}\n"
                if warning.fix_command:
                    report += f"   🔨 Optional fix: {warning.fix_command}\n"

        report += "\n" + "=" * 40 + "\n"

        if errors:
            report += (
                "\n❗ Application may not work correctly until errors are resolved.\n"
            )

        return report


# Legacy function for backward compatibility
def validate_config(config: Dict) -> List[str]:
    """
    Legacy validation function for backward compatibility.

    Args:
        config: The configuration dictionary loaded from config.py.

    Returns:
        A list of error messages. An empty list indicates a valid configuration.
    """
    validator = ConfigValidator()
    errors, warnings = validator.validate_config(config)

    # Convert ValidationError objects to strings for backward compatibility
    error_messages = [f"{error.field}: {error.message}" for error in errors]
    warning_messages = [f"{warning.field}: {warning.message}" for warning in warnings]

    return error_messages + warning_messages


# New enhanced validation function
def validate_config_enhanced(
    config: Dict,
) -> Tuple[List[ValidationError], List[ValidationError]]:
    """
    Enhanced validation function with detailed error guidance.

    Args:
        config: The configuration dictionary loaded from config.py.

    Returns:
        Tuple of (errors, warnings) as ValidationError objects.
    """
    validator = ConfigValidator()
    return validator.validate_config(config)


def print_validation_report(config: Dict) -> bool:
    """
    Validate configuration and print a detailed report.

    Args:
        config: The configuration dictionary loaded from config.py.

    Returns:
        True if configuration is valid (no errors), False otherwise.
    """
    validator = ConfigValidator()
    errors, warnings = validator.validate_config(config)

    report = validator.format_validation_report(errors, warnings)
    print(report)

    return len(errors) == 0
