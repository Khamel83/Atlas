"""
Integration tests for the complete configuration system.

This module tests the integration between configuration loading, validation,
hot-reloading, auditing, and security features.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

from helpers.config import load_config
from helpers.config_audit import AuditPolicy, ConfigAuditor
from helpers.config_hotreload import ConfigHotReloader
from helpers.security import validate_security
from helpers.validate import ConfigValidator


class TestConfigurationIntegration(unittest.TestCase):
    """Test integration between all configuration components."""

    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Clean up integration test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Restore environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_basic_config_loading_works(self):
        """Test that configuration loading works without errors."""
        try:
            config = load_config()
            
            # Basic checks that config loaded
            self.assertIsInstance(config, dict)
            self.assertIn("environment", config)
            self.assertIn("llm_provider", config)
            
        except Exception as e:
            self.fail(f"Configuration loading failed: {e}")

    def test_config_validation_integration(self):
        """Test that configuration validation integrates properly."""
        try:
            config = load_config()
            
            # Validate configuration
            validator = ConfigValidator()
            errors, warnings = validator.validate_config(config)
            
            # Should return lists (may be empty)
            self.assertIsInstance(errors, list)
            self.assertIsInstance(warnings, list)
            
            # Generate validation report
            report = validator.format_validation_report(errors, warnings)
            self.assertIsInstance(report, str)
            
        except Exception as e:
            self.fail(f"Configuration validation integration failed: {e}")

    def test_security_validation_integration(self):
        """Test that security validation integrates properly."""
        try:
            config = load_config()
            
            # Security validation
            security_results, security_report = validate_security(config)
            
            # Should return results and report
            self.assertIsInstance(security_results, list)
            self.assertIsInstance(security_report, str)
            
        except Exception as e:
            self.fail(f"Security validation integration failed: {e}")

    def test_audit_system_integration(self):
        """Test that audit system integrates properly."""
        try:
            # Create temporary audit policy
            log_file = os.path.join(self.temp_dir, "audit.jsonl")
            policy = AuditPolicy(enabled=True, log_file=log_file)
            
            # Create auditor
            auditor = ConfigAuditor(policy)
            
            # Load and audit configuration
            config = load_config()
            auditor.log_config_load(config, "integration_test")
            
            # Verify audit log was created
            self.assertTrue(os.path.exists(log_file))
            
            # Generate audit report
            report = auditor.generate_audit_report(days=1)
            self.assertIsInstance(report, str)
            self.assertIn("Configuration Audit Report", report)
            
        except Exception as e:
            self.fail(f"Audit system integration failed: {e}")

    @patch.dict(os.environ, {"ATLAS_ENVIRONMENT": "test"})
    def test_environment_specific_loading(self):
        """Test environment-specific configuration loading."""
        try:
            config = load_config()
            
            # Should load with environment context
            self.assertIn("environment", config)
            
            # Environment-specific config should be applied
            self.assertIn("environment_config", config)
            
        except Exception as e:
            self.fail(f"Environment-specific loading failed: {e}")

    def test_hot_reload_system_integration(self):
        """Test hot-reload system integration."""
        try:
            # Create temporary config files for testing
            config_dir = os.path.join(self.temp_dir, "config")
            os.makedirs(config_dir, exist_ok=True)
            
            env_file = os.path.join(config_dir, ".env")
            with open(env_file, 'w') as f:
                f.write("LLM_PROVIDER=openrouter\n")
            
            # Mock hot-reloader with temp files
            with patch.object(ConfigHotReloader, '_get_config_files') as mock_get_files:
                mock_get_files.return_value = {env_file}
                
                reloader = ConfigHotReloader()
                
                # Should initialize without errors
                self.assertFalse(reloader.is_running)
                self.assertIsNotNone(reloader.config_files)
                
        except Exception as e:
            self.fail(f"Hot-reload system integration failed: {e}")

    def test_complete_config_workflow(self):
        """Test complete configuration workflow integration."""
        try:
            # 1. Load configuration
            config = load_config()
            self.assertIsInstance(config, dict)
            
            # 2. Validate configuration
            validator = ConfigValidator()
            errors, warnings = validator.validate_config(config)
            
            # 3. Security validation
            security_results, security_report = validate_security(config)
            
            # 4. Audit logging
            log_file = os.path.join(self.temp_dir, "workflow_audit.jsonl")
            policy = AuditPolicy(enabled=True, log_file=log_file)
            auditor = ConfigAuditor(policy)
            
            auditor.log_config_load(config, "workflow_test")
            auditor.log_validation_results(config, errors, warnings)
            
            # Verify all components worked
            self.assertTrue(os.path.exists(log_file))
            
            # Generate comprehensive report
            audit_report = auditor.generate_audit_report(days=1)
            validation_report = validator.format_validation_report(errors, warnings)
            
            self.assertIsInstance(audit_report, str)
            self.assertIsInstance(validation_report, str)
            self.assertIsInstance(security_report, str)
            
        except Exception as e:
            self.fail(f"Complete workflow integration failed: {e}")

    def test_error_handling_robustness(self):
        """Test that the system handles errors gracefully."""
        # Test with invalid environment variable
        with patch.dict(os.environ, {"ATLAS_ENVIRONMENT": "invalid_env"}):
            try:
                config = load_config()
                # Should still load with fallback
                self.assertIsInstance(config, dict)
            except Exception as e:
                self.fail(f"System should handle invalid environment gracefully: {e}")

    def test_concurrent_access_safety(self):
        """Test concurrent access to configuration systems."""
        import threading
        import time
        
        results = []
        errors = []
        
        def load_and_validate():
            try:
                config = load_config()
                validator = ConfigValidator()
                validator_errors, validator_warnings = validator.validate_config(config)
                results.append(len(validator_errors) + len(validator_warnings))
            except Exception as e:
                errors.append(str(e))
        
        # Run multiple threads simultaneously
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=load_and_validate)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Check results
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")
        self.assertEqual(len(results), 5, "Not all threads completed successfully")


class TestConfigurationEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_missing_config_files(self):
        """Test behavior when configuration files are missing."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            try:
                config = load_config()
                # Should still return a config with defaults
                self.assertIsInstance(config, dict)
            except Exception as e:
                self.fail(f"Should handle missing config files gracefully: {e}")

    def test_corrupted_config_files(self):
        """Test behavior with corrupted configuration files."""
        temp_dir = tempfile.mkdtemp()
        try:
            config_dir = os.path.join(temp_dir, "config")
            os.makedirs(config_dir, exist_ok=True)
            
            # Create corrupted YAML file
            yaml_file = os.path.join(config_dir, "environments.yaml")
            with open(yaml_file, 'w') as f:
                f.write("invalid: yaml: content: [[[")
            
            # Should handle corrupted files gracefully
            try:
                config = load_config()
                self.assertIsInstance(config, dict)
            except Exception as e:
                self.fail(f"Should handle corrupted YAML gracefully: {e}")
                
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()