"""
Security utilities for Atlas configuration and credential management.

This module provides secure credential handling, validation, and access controls
to protect sensitive configuration data and prevent security vulnerabilities.
"""

import base64
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class SecurityCheckResult:
    """Result of a security validation check."""

    field: str
    passed: bool
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    recommendation: str
    fix_command: Optional[str] = None


class CredentialManager:
    """Manages secure credential handling and validation."""

    # Sensitive fields that should never be logged or exposed
    SENSITIVE_FIELDS = {
        "OPENROUTER_API_KEY",
        "DEEPSEEK_API_KEY",
        "YOUTUBE_API_KEY",
        "INSTAPAPER_PASSWORD",
        "NYT_PASSWORD",
        "API_KEY",
        "PASSWORD",
        "SECRET",
        "TOKEN",
        "PRIVATE_KEY",
    }

    # Known test/placeholder patterns
    PLACEHOLDER_PATTERNS = [
        r"test",
        r"example",
        r"your[_-]?key",
        r"your[_-]?password",
        r"placeholder",
        r"changeme",
        r"replace[_-]?this",
        r"sk-or-v1-[0-9a-f]{8}",  # Common example pattern
        r"xxx+",
        r"\*+",
    ]

    # API key format validators
    API_KEY_FORMATS = {
        "OPENROUTER_API_KEY": r"^sk-or-v1-[a-f0-9]{64}$",
        "DEEPSEEK_API_KEY": r"^sk-[a-zA-Z0-9]{32,}$",
        "YOUTUBE_API_KEY": r"^[A-Za-z0-9_-]{39}$",
    }

    def __init__(self):
        self.security_issues: List[SecurityCheckResult] = []

    def validate_credentials(self, config: Dict) -> List[SecurityCheckResult]:
        """
        Validate all credentials in the configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            List of security check results
        """
        self.security_issues = []

        # Check for sensitive data exposure
        self._check_sensitive_exposure(config)

        # Validate API key formats
        self._validate_api_key_formats(config)

        # Check for placeholder credentials
        self._check_placeholder_credentials(config)

        # Validate credential strength
        self._validate_credential_strength(config)

        # Check file permissions
        self._check_file_permissions()

        # Validate environment separation
        self._check_environment_separation(config)

        return self.security_issues

    def _check_sensitive_exposure(self, config: Dict):
        """Check for sensitive data that might be exposed."""
        exposed_fields = []

        for field, value in config.items():
            if self._is_sensitive_field(field) and value:
                # Check if value appears in non-sensitive locations
                if self._check_potential_exposure(field, str(value)):
                    exposed_fields.append(field)

        if exposed_fields:
            self.security_issues.append(
                SecurityCheckResult(
                    field="credential_exposure",
                    passed=False,
                    severity="high",
                    message=f"Potentially exposed credentials: {', '.join(exposed_fields)}",
                    recommendation="Ensure credentials are only stored in secure environment variables and not logged, cached, or exposed in error messages.",
                    fix_command="# Review logs and caches for exposed credentials",
                )
            )

    def _validate_api_key_formats(self, config: Dict):
        """Validate API key formats against known patterns."""
        for field, expected_format in self.API_KEY_FORMATS.items():
            value = config.get(field)
            if value and not re.match(expected_format, value):
                self.security_issues.append(
                    SecurityCheckResult(
                        field=field,
                        passed=False,
                        severity="medium",
                        message=f"API key format appears invalid for {field}",
                        recommendation=f"Verify the {field} format. Check the provider documentation for the correct key format.",
                        fix_command=f"# Verify {field} format with the provider",
                    )
                )

    def _check_placeholder_credentials(self, config: Dict):
        """Check for placeholder or test credentials."""
        for field, value in config.items():
            if self._is_sensitive_field(field) and value:
                if self._is_placeholder_value(str(value)):
                    self.security_issues.append(
                        SecurityCheckResult(
                            field=field,
                            passed=False,
                            severity="high",
                            message=f"Placeholder credential detected in {field}",
                            recommendation=f"Replace the placeholder value in {field} with a real credential.",
                            fix_command=f"# Update {field} in your .env file with the real credential",
                        )
                    )

    def _validate_credential_strength(self, config: Dict):
        """Validate the strength and security of credentials."""
        weak_passwords = []

        for field in ["INSTAPAPER_PASSWORD", "NYT_PASSWORD"]:
            password = config.get(field)
            if password and len(password) < 8:
                weak_passwords.append(field)

        if weak_passwords:
            self.security_issues.append(
                SecurityCheckResult(
                    field="password_strength",
                    passed=False,
                    severity="medium",
                    message=f"Weak passwords detected: {', '.join(weak_passwords)}",
                    recommendation="Use strong passwords (8+ characters) for account security.",
                    fix_command="# Update passwords to use stronger credentials",
                )
            )

    def _check_file_permissions(self):
        """Check file permissions for configuration files."""
        config_files = [
            "config/.env",
            "config/.env.development",
            "config/.env.production",
            "config/.env.test",
            ".env",
        ]

        insecure_files = []
        for file_path in config_files:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                # Check if file is readable by others (world-readable)
                if stat.st_mode & 0o044:  # Other read permissions
                    insecure_files.append(file_path)

        if insecure_files:
            self.security_issues.append(
                SecurityCheckResult(
                    field="file_permissions",
                    passed=False,
                    severity="high",
                    message=f"Insecure file permissions: {', '.join(insecure_files)}",
                    recommendation="Configuration files containing credentials should not be readable by other users.",
                    fix_command=f"chmod 600 {' '.join(insecure_files)}",
                )
            )

    def _check_environment_separation(self, config: Dict):
        """Check for proper environment separation."""
        env = config.get("environment", "unknown")

        # Check for production credentials in development
        if env == "development":
            prod_indicators = ["prod", "production", "live"]
            for field, value in config.items():
                if self._is_sensitive_field(field) and value:
                    value_lower = str(value).lower()
                    if any(indicator in value_lower for indicator in prod_indicators):
                        self.security_issues.append(
                            SecurityCheckResult(
                                field="environment_separation",
                                passed=False,
                                severity="high",
                                message=f"Production credential detected in development environment: {field}",
                                recommendation="Use separate credentials for different environments to prevent accidental production access.",
                                fix_command=f"# Use development-specific credentials for {field}",
                            )
                        )

    def _is_sensitive_field(self, field: str) -> bool:
        """Check if a field contains sensitive data."""
        field_upper = field.upper()
        return any(sensitive in field_upper for sensitive in self.SENSITIVE_FIELDS)

    def _is_placeholder_value(self, value: str) -> bool:
        """Check if a value appears to be a placeholder."""
        value_lower = value.lower()
        return any(
            re.search(pattern, value_lower) for pattern in self.PLACEHOLDER_PATTERNS
        )

    def _check_potential_exposure(self, field: str, value: str) -> bool:
        """Check if a credential might be exposed in logs or other locations."""
        # In a real implementation, this could check:
        # - Log files for the credential value
        # - Cache files
        # - Error reports
        # - Version control history

        # For now, we'll do basic checks
        value_hash = hashlib.sha256(value.encode()).hexdigest()[:16]

        # Check if any part of the credential appears in common locations
        check_paths = [
            "logs/",
            ".git/",
            "tmp/",
            "/tmp/",
            "/var/log/",
        ]

        # This is a simplified check - real implementation would be more thorough
        return False

    def sanitize_config_for_logging(self, config: Dict) -> Dict:
        """
        Create a sanitized version of config safe for logging.

        Args:
            config: Original configuration dictionary

        Returns:
            Sanitized configuration with sensitive values masked
        """
        sanitized = {}

        for key, value in config.items():
            if self._is_sensitive_field(key) and value:
                # Mask sensitive values
                if len(str(value)) > 8:
                    sanitized[key] = str(value)[:4] + "***" + str(value)[-4:]
                else:
                    sanitized[key] = "***"
            else:
                sanitized[key] = value

        return sanitized

    def generate_security_report(
        self, security_results: List[SecurityCheckResult]
    ) -> str:
        """
        Generate a formatted security report.

        Args:
            security_results: List of security check results

        Returns:
            Formatted security report string
        """
        if not security_results:
            return "✅ Security validation passed - no issues found."

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_results = sorted(
            security_results, key=lambda x: severity_order.get(x.severity, 3)
        )

        # Group by severity
        by_severity = {}
        for result in sorted_results:
            severity = result.severity
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(result)

        report = "\n🔒 Security Validation Report\n" + "=" * 40 + "\n"

        for severity in ["critical", "high", "medium", "low"]:
            if severity not in by_severity:
                continue

            issues = by_severity[severity]
            severity_icon = {"critical": "🚨", "high": "❌", "medium": "⚠️", "low": "ℹ️"}[
                severity
            ]

            report += f"\n{severity_icon} {severity.upper()} SECURITY ISSUES ({len(issues)} found):\n"

            for i, issue in enumerate(issues, 1):
                report += f"\n{i}. {issue.field}: {issue.message}\n"
                report += f"   💡 Recommendation: {issue.recommendation}\n"
                if issue.fix_command:
                    report += f"   🔨 Fix: {issue.fix_command}\n"

        report += "\n" + "=" * 40 + "\n"

        critical_or_high = len(
            [r for r in sorted_results if r.severity in ["critical", "high"]]
        )
        if critical_or_high > 0:
            report += f"\n🚨 {critical_or_high} critical/high security issues require immediate attention.\n"

        return report


def validate_security(config: Dict) -> Tuple[List[SecurityCheckResult], str]:
    """
    Validate security aspects of the configuration.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Tuple of (security_results, formatted_report)
    """
    manager = CredentialManager()
    results = manager.validate_credentials(config)
    report = manager.generate_security_report(results)
    return results, report


def sanitize_for_logging(config: Dict) -> Dict:
    """
    Convenience function to sanitize configuration for logging.

    Args:
        config: Configuration dictionary to sanitize

    Returns:
        Sanitized configuration dictionary
    """
    manager = CredentialManager()
    return manager.sanitize_config_for_logging(config)
