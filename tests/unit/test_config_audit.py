"""
Tests for configuration change logging and auditing functionality.

This module tests the audit logging, change detection, and compliance
monitoring capabilities for configuration management.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from helpers.config_audit import (
    AuditPolicy,
    ConfigAuditor,
    ConfigChangeEvent,
    get_config_auditor,
    log_config_change,
    log_config_validation,
)


class TestConfigChangeEvent(unittest.TestCase):
    """Test configuration change event data structure."""

    def test_event_creation(self):
        """Test creating a configuration change event."""
        event = ConfigChangeEvent(
            timestamp="2024-01-01T10:00:00",
            environment="test",
            change_type="file_change",
            source_file="config/.env",
            changed_keys=["llm_provider"],
            user="testuser",
            process_id=1234,
        )

        self.assertEqual(event.timestamp, "2024-01-01T10:00:00")
        self.assertEqual(event.environment, "test")
        self.assertEqual(event.change_type, "file_change")
        self.assertEqual(event.source_file, "config/.env")
        self.assertEqual(event.changed_keys, ["llm_provider"])
        self.assertEqual(event.user, "testuser")
        self.assertEqual(event.process_id, 1234)


class TestAuditPolicy(unittest.TestCase):
    """Test audit policy configuration."""

    def test_default_policy(self):
        """Test default audit policy values."""
        policy = AuditPolicy()

        self.assertTrue(policy.enabled)
        self.assertIsNone(policy.log_file)
        self.assertEqual(policy.max_log_size_mb, 100)
        self.assertEqual(policy.retain_days, 30)
        self.assertFalse(policy.log_sensitive_changes)
        self.assertFalse(policy.log_unchanged_reloads)
        self.assertTrue(policy.alert_on_critical_changes)
        self.assertIsNone(policy.monitored_keys)

    def test_custom_policy(self):
        """Test custom audit policy configuration."""
        policy = AuditPolicy(
            enabled=False,
            log_file="/custom/audit.log",
            max_log_size_mb=50,
            retain_days=14,
            log_sensitive_changes=True,
            log_unchanged_reloads=True,
            alert_on_critical_changes=False,
            monitored_keys={"llm_provider", "environment"},
        )

        self.assertFalse(policy.enabled)
        self.assertEqual(policy.log_file, "/custom/audit.log")
        self.assertEqual(policy.max_log_size_mb, 50)
        self.assertEqual(policy.retain_days, 14)
        self.assertTrue(policy.log_sensitive_changes)
        self.assertTrue(policy.log_unchanged_reloads)
        self.assertFalse(policy.alert_on_critical_changes)
        self.assertEqual(policy.monitored_keys, {"llm_provider", "environment"})


class TestConfigAuditor(unittest.TestCase):
    """Test configuration auditor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test_audit.jsonl")
        self.policy = AuditPolicy(enabled=True, log_file=self.log_file)
        self.auditor = ConfigAuditor(self.policy)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_auditor_initialization(self):
        """Test auditor initializes correctly."""
        self.assertEqual(self.auditor.policy, self.policy)
        self.assertIsNone(self.auditor._last_config_hash)

    def test_calculate_config_hash(self):
        """Test configuration hash calculation."""
        config = {"llm_provider": "openrouter", "environment": "test"}
        hash1 = self.auditor._calculate_config_hash(config)

        # Same config should produce same hash
        hash2 = self.auditor._calculate_config_hash(config)
        self.assertEqual(hash1, hash2)

        # Different config should produce different hash
        config["llm_provider"] = "deepseek"
        hash3 = self.auditor._calculate_config_hash(config)
        self.assertNotEqual(hash1, hash3)

    def test_detect_changes_initial_load(self):
        """Test change detection for initial configuration load."""
        config = {"llm_provider": "openrouter", "environment": "test"}
        changes = self.auditor._detect_changes(None, config)

        self.assertEqual(changes["type"], "initial_load")
        self.assertEqual(set(changes["changed_keys"]), {"llm_provider", "environment"})

    def test_detect_changes_modification(self):
        """Test change detection for configuration modifications."""
        old_config = {"llm_provider": "openrouter", "environment": "test"}
        new_config = {"llm_provider": "deepseek", "environment": "test"}

        changes = self.auditor._detect_changes(old_config, new_config)

        self.assertEqual(changes["type"], "modification")
        self.assertEqual(changes["changed_keys"], ["llm_provider"])
        self.assertIn("llm_provider", changes["changes"])
        self.assertEqual(changes["changes"]["llm_provider"]["action"], "modified")

    def test_detect_changes_no_change(self):
        """Test change detection when no changes occurred."""
        config = {"llm_provider": "openrouter", "environment": "test"}
        changes = self.auditor._detect_changes(config, config)

        self.assertEqual(changes["type"], "no_change")
        self.assertEqual(changes["changed_keys"], [])

    def test_detect_changes_added_removed(self):
        """Test change detection for added and removed keys."""
        old_config = {"llm_provider": "openrouter", "old_key": "value"}
        new_config = {"llm_provider": "openrouter", "new_key": "value"}

        changes = self.auditor._detect_changes(old_config, new_config)

        self.assertEqual(changes["type"], "modification")
        self.assertEqual(set(changes["changed_keys"]), {"old_key", "new_key"})
        self.assertEqual(changes["changes"]["old_key"]["action"], "removed")
        self.assertEqual(changes["changes"]["new_key"]["action"], "added")

    def test_categorize_change_importance(self):
        """Test change importance categorization."""
        # No changes
        self.assertEqual(self.auditor._categorize_change_importance([]), "none")

        # Critical changes
        critical_keys = ["llm_provider", "OPENROUTER_API_KEY"]
        self.assertEqual(
            self.auditor._categorize_change_importance(critical_keys), "critical"
        )

        # Performance changes
        perf_keys = ["llm_model", "max_retries"]
        self.assertEqual(
            self.auditor._categorize_change_importance(perf_keys), "important"
        )

        # Many changes
        many_keys = [f"key_{i}" for i in range(15)]
        self.assertEqual(
            self.auditor._categorize_change_importance(many_keys), "important"
        )

        # Minor changes
        minor_keys = ["some_other_setting"]
        self.assertEqual(self.auditor._categorize_change_importance(minor_keys), "minor")

    def test_should_log_event(self):
        """Test event logging decision logic."""
        # Always log initial loads
        event = ConfigChangeEvent(
            timestamp="2024-01-01T10:00:00",
            environment="test",
            change_type="initial_load",
        )
        self.assertTrue(self.auditor._should_log_event(event))

        # Always log validation events
        event.change_type = "validation"
        self.assertTrue(self.auditor._should_log_event(event))

        # Skip unchanged reloads by default
        event.change_type = "hot_reload"
        event.changed_keys = []
        self.assertFalse(self.auditor._should_log_event(event))

        # Log unchanged reloads if policy allows
        self.policy.log_unchanged_reloads = True
        self.assertTrue(self.auditor._should_log_event(event))

    def test_should_log_event_with_monitored_keys(self):
        """Test event logging with monitored keys policy."""
        self.policy.monitored_keys = {"llm_provider", "environment"}

        # Event with monitored key change
        event = ConfigChangeEvent(
            timestamp="2024-01-01T10:00:00",
            environment="test",
            change_type="file_change",
            changed_keys=["llm_provider", "other_key"],
        )
        self.assertTrue(self.auditor._should_log_event(event))

        # Event with no monitored key changes
        event.changed_keys = ["other_key", "another_key"]
        self.assertFalse(self.auditor._should_log_event(event))

    def test_log_config_load(self):
        """Test logging configuration load events."""
        config = {
            "llm_provider": "openrouter",
            "environment": "test",
            "OPENROUTER_API_KEY": "test-key",
        }

        self.auditor.log_config_load(config, "config/.env")

        # Check that log file was created and contains event
        self.assertTrue(os.path.exists(self.log_file))

        with open(self.log_file, "r") as f:
            log_line = f.readline().strip()
            event_data = json.loads(log_line)

        self.assertEqual(event_data["change_type"], "initial_load")
        self.assertEqual(event_data["environment"], "test")
        self.assertIn("llm_provider", event_data["changed_keys"])
        self.assertIsNotNone(event_data["config_hash"])

    def test_log_config_change(self):
        """Test logging configuration change events."""
        old_config = {"llm_provider": "openrouter", "environment": "test"}
        new_config = {"llm_provider": "deepseek", "environment": "test"}

        self.auditor.log_config_change(
            old_config, new_config, "config/.env", "file_change"
        )

        # Check log file content
        with open(self.log_file, "r") as f:
            log_line = f.readline().strip()
            event_data = json.loads(log_line)

        self.assertEqual(event_data["change_type"], "file_change")
        self.assertEqual(event_data["changed_keys"], ["llm_provider"])
        self.assertIn("change_summary", event_data)

    def test_log_config_change_no_change(self):
        """Test logging when configuration hasn't changed."""
        config = {"llm_provider": "openrouter", "environment": "test"}

        # Set initial hash
        self.auditor._last_config_hash = self.auditor._calculate_config_hash(config)

        # Log change with same config
        self.auditor.log_config_change(config, config, "config/.env", "hot_reload")

        # Should not create log entry (unless policy says to log unchanged reloads)
        if os.path.exists(self.log_file):
            with open(self.log_file, "r") as f:
                content = f.read().strip()
                self.assertEqual(content, "")

    def test_log_validation_results(self):
        """Test logging validation results."""
        config = {"llm_provider": "openrouter", "environment": "test"}
        errors = [MagicMock()]  # Mock validation error
        warnings = [MagicMock(), MagicMock()]  # Mock validation warnings

        self.auditor.log_validation_results(config, errors, warnings)

        # Check log file content
        with open(self.log_file, "r") as f:
            log_line = f.readline().strip()
            event_data = json.loads(log_line)

        self.assertEqual(event_data["change_type"], "validation")
        self.assertEqual(event_data["validation_errors"], 1)
        self.assertEqual(event_data["validation_warnings"], 2)

    @patch("builtins.print")
    def test_alert_critical_change(self, mock_print):
        """Test critical change alerting."""
        event = ConfigChangeEvent(
            timestamp="2024-01-01T10:00:00",
            environment="production",
            change_type="file_change",
            changed_keys=["OPENROUTER_API_KEY", "environment"],
            source_file="config/.env",
        )

        self.auditor._alert_critical_change(event)

        # Should have printed security alert
        mock_print.assert_called()
        calls = [str(call) for call in mock_print.call_args_list]
        alert_found = any("SECURITY ALERT" in call for call in calls)
        self.assertTrue(alert_found)

    def test_get_recent_changes_empty(self):
        """Test getting recent changes from empty log."""
        changes = self.auditor.get_recent_changes(hours=24)
        self.assertEqual(changes, [])

    def test_get_recent_changes_with_data(self):
        """Test getting recent changes with log data."""
        # Create some test log entries
        now = datetime.now()
        events = [
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "environment": "test",
                "change_type": "file_change",
                "changed_keys": ["llm_provider"],
            },
            {
                "timestamp": (now - timedelta(hours=25)).isoformat(),  # Too old
                "environment": "test",
                "change_type": "file_change",
                "changed_keys": ["environment"],
            },
        ]

        with open(self.log_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        changes = self.auditor.get_recent_changes(hours=24)

        # Should only get the recent change
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].changed_keys, ["llm_provider"])

    def test_generate_audit_report_empty(self):
        """Test generating audit report with no data."""
        report = self.auditor.generate_audit_report(days=7)

        self.assertIn("Configuration Audit Report", report)
        self.assertIn("No configuration changes recorded", report)

    def test_generate_audit_report_with_data(self):
        """Test generating audit report with data."""
        # Create test log entries
        now = datetime.now()
        events = [
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "environment": "production",
                "change_type": "file_change",
                "changed_keys": ["OPENROUTER_API_KEY"],  # Critical change
            },
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "environment": "development",
                "change_type": "hot_reload",
                "changed_keys": ["llm_model"],
            },
        ]

        with open(self.log_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        report = self.auditor.generate_audit_report(days=1)

        self.assertIn("Total Changes: 2", report)
        self.assertIn("Critical Changes: 1", report)
        self.assertIn("development, production", report)
        self.assertIn("file_change: 1", report)
        self.assertIn("hot_reload: 1", report)
        self.assertIn("Recent Critical Changes", report)


class TestGlobalAuditorFunctions(unittest.TestCase):
    """Test global auditor convenience functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global auditor
        import helpers.config_audit
        helpers.config_audit._global_auditor = None

    def tearDown(self):
        """Clean up test fixtures."""
        # Reset global auditor
        import helpers.config_audit
        helpers.config_audit._global_auditor = None

    def test_get_config_auditor(self):
        """Test getting global config auditor."""
        auditor1 = get_config_auditor()
        auditor2 = get_config_auditor()

        # Should return the same instance
        self.assertIs(auditor1, auditor2)

    def test_get_config_auditor_with_policy(self):
        """Test getting global config auditor with custom policy."""
        policy = AuditPolicy(enabled=False)
        auditor = get_config_auditor(policy)

        self.assertEqual(auditor.policy, policy)

    @patch("helpers.config_audit.get_config_auditor")
    def test_log_config_change_convenience(self, mock_get_auditor):
        """Test convenience function for logging config changes."""
        mock_auditor = MagicMock()
        mock_get_auditor.return_value = mock_auditor

        old_config = {"llm_provider": "openrouter"}
        new_config = {"llm_provider": "deepseek"}

        log_config_change(old_config, new_config, "config/.env", "file_change")

        mock_auditor.log_config_change.assert_called_once_with(
            old_config, new_config, "config/.env", "file_change"
        )

    @patch("helpers.config_audit.get_config_auditor")
    def test_log_config_validation_convenience(self, mock_get_auditor):
        """Test convenience function for logging validation results."""
        mock_auditor = MagicMock()
        mock_get_auditor.return_value = mock_auditor

        config = {"llm_provider": "openrouter"}
        errors = [MagicMock()]
        warnings = [MagicMock()]

        log_config_validation(config, errors, warnings)

        mock_auditor.log_validation_results.assert_called_once_with(
            config, errors, warnings
        )


class TestAuditLogRotation(unittest.TestCase):
    """Test audit log rotation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test_audit.jsonl")
        self.policy = AuditPolicy(
            enabled=True, log_file=self.log_file, max_log_size_mb=1  # Small size for testing
        )
        self.auditor = ConfigAuditor(self.policy)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_rotation_large_file(self):
        """Test log rotation when file gets too large."""
        # Create a large log file (> 1MB)
        large_content = "x" * (2 * 1024 * 1024)  # 2MB of content
        with open(self.log_file, "w") as f:
            f.write(large_content)

        # Trigger rotation by writing a log entry
        config = {"llm_provider": "openrouter", "environment": "test"}
        self.auditor.log_config_load(config)

        # Original file should be rotated and new file created
        log_files = list(Path(self.temp_dir).glob("test_audit.jsonl*"))
        # Should have rotated file (original file gets recreated)
        self.assertTrue(any("test_audit.jsonl." in str(f) for f in log_files))


if __name__ == "__main__":
    unittest.main()