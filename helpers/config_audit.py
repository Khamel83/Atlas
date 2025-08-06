"""
Configuration Change Logging and Auditing

This module provides comprehensive configuration change tracking, audit logging,
and compliance monitoring for security and operational purposes.
"""

import hashlib
import json
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from helpers.security import sanitize_for_logging


@dataclass
class ConfigChangeEvent:
    """Represents a configuration change event."""
    
    timestamp: str
    environment: str
    change_type: str  # 'initial_load', 'file_change', 'hot_reload', 'validation'
    source_file: Optional[str] = None
    changed_keys: List[str] = None
    change_summary: Dict[str, Any] = None
    user: Optional[str] = None
    process_id: Optional[int] = None
    config_hash: Optional[str] = None
    validation_errors: int = 0
    validation_warnings: int = 0


@dataclass
class AuditPolicy:
    """Configuration for audit logging behavior."""
    
    enabled: bool = True
    log_file: Optional[str] = None
    max_log_size_mb: int = 100
    retain_days: int = 30
    log_sensitive_changes: bool = False
    log_unchanged_reloads: bool = False
    alert_on_critical_changes: bool = True
    monitored_keys: Set[str] = None


class ConfigAuditor:
    """Manages configuration change auditing and logging."""

    # Keys that should trigger security alerts when changed
    SECURITY_CRITICAL_KEYS = {
        "llm_provider", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", 
        "YOUTUBE_API_KEY", "environment", "data_directory",
        "USE_12FT_IO_FALLBACK", "USE_PLAYWRIGHT_FOR_NYT"
    }

    # Keys that are performance-critical and should be monitored
    PERFORMANCE_KEYS = {
        "llm_model", "llm_model_premium", "llm_model_budget",
        "max_retries", "processing_timeout", "PODCAST_EPISODE_LIMIT"
    }

    def __init__(self, policy: Optional[AuditPolicy] = None):
        """
        Initialize the configuration auditor.
        
        Args:
            policy: Audit policy configuration
        """
        self.policy = policy or AuditPolicy()
        self._lock = threading.Lock()
        self._last_config_hash: Optional[str] = None
        self._setup_logging()

    def _setup_logging(self):
        """Set up audit logging configuration."""
        if not self.policy.enabled:
            return
            
        # Default log file location
        if not self.policy.log_file:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            self.policy.log_file = str(log_dir / "config_audit.jsonl")
        
        # Ensure log directory exists
        log_path = Path(self.policy.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def _calculate_config_hash(self, config: Dict) -> str:
        """
        Calculate a hash of the configuration for change detection.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Hash string representing the configuration state
        """
        # Create a sanitized copy for hashing (remove sensitive values)
        sanitized = sanitize_for_logging(config)
        
        # Sort keys for consistent hashing
        sorted_config = json.dumps(sanitized, sort_keys=True)
        return hashlib.sha256(sorted_config.encode()).hexdigest()[:16]

    def _detect_changes(self, old_config: Optional[Dict], new_config: Dict) -> Dict[str, Any]:
        """
        Detect changes between configuration states.
        
        Args:
            old_config: Previous configuration (can be None)
            new_config: New configuration
            
        Returns:
            Summary of changes detected
        """
        if not old_config:
            return {"type": "initial_load", "changed_keys": list(new_config.keys())}
        
        changes = {}
        changed_keys = []
        
        # Check for added or modified keys
        for key, new_value in new_config.items():
            old_value = old_config.get(key)
            if old_value != new_value:
                changed_keys.append(key)
                if key not in old_config:
                    changes[key] = {"action": "added", "new_value": new_value}
                else:
                    changes[key] = {
                        "action": "modified",
                        "old_value": old_value,
                        "new_value": new_value
                    }
        
        # Check for removed keys
        for key in old_config:
            if key not in new_config:
                changed_keys.append(key)
                changes[key] = {"action": "removed", "old_value": old_config[key]}
        
        return {
            "type": "modification" if changes else "no_change",
            "changed_keys": changed_keys,
            "changes": changes
        }

    def _categorize_change_importance(self, changed_keys: List[str]) -> str:
        """
        Categorize the importance of configuration changes.
        
        Args:
            changed_keys: List of configuration keys that changed
            
        Returns:
            Importance level: 'critical', 'important', 'minor', or 'none'
        """
        if not changed_keys:
            return "none"
        
        critical_changes = set(changed_keys) & self.SECURITY_CRITICAL_KEYS
        performance_changes = set(changed_keys) & self.PERFORMANCE_KEYS
        
        if critical_changes:
            return "critical"
        elif performance_changes:
            return "important"
        elif len(changed_keys) > 10:
            return "important"  # Many changes might be significant
        else:
            return "minor"

    def _write_audit_log(self, event: ConfigChangeEvent):
        """
        Write an audit event to the log file.
        
        Args:
            event: Configuration change event to log
        """
        if not self.policy.enabled or not self.policy.log_file:
            return
        
        try:
            # Convert event to dictionary for JSON serialization
            event_dict = asdict(event)
            
            # Write to JSONL format (one JSON object per line)
            with open(self.policy.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_dict) + '\n')
            
            # Rotate log if it's too large
            self._rotate_log_if_needed()
            
        except Exception as e:
            print(f"⚠️  Failed to write audit log: {e}")

    def _rotate_log_if_needed(self):
        """Rotate audit log if it exceeds size limits."""
        if not os.path.exists(self.policy.log_file):
            return
        
        file_size_mb = os.path.getsize(self.policy.log_file) / (1024 * 1024)
        if file_size_mb > self.policy.max_log_size_mb:
            # Rotate the log file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archived_name = f"{self.policy.log_file}.{timestamp}"
            os.rename(self.policy.log_file, archived_name)
            print(f"📁 Rotated audit log to {archived_name}")

    def _should_log_event(self, event: ConfigChangeEvent) -> bool:
        """
        Determine if an event should be logged based on policy.
        
        Args:
            event: Configuration change event
            
        Returns:
            True if event should be logged
        """
        if not self.policy.enabled:
            return False
        
        # Always log initial loads and validation issues
        if event.change_type in ['initial_load', 'validation']:
            return True
        
        # Skip unchanged reloads if policy says so
        if (event.change_type == 'hot_reload' and 
            not event.changed_keys and 
            not self.policy.log_unchanged_reloads):
            return False
        
        # Check if any monitored keys changed
        if self.policy.monitored_keys:
            changed_monitored = set(event.changed_keys or []) & self.policy.monitored_keys
            return len(changed_monitored) > 0
        
        return True

    def log_config_load(self, config: Dict, source: str = "unknown"):
        """
        Log initial configuration loading.
        
        Args:
            config: Loaded configuration
            source: Source of the configuration load
        """
        with self._lock:
            config_hash = self._calculate_config_hash(config)
            
            event = ConfigChangeEvent(
                timestamp=datetime.now().isoformat(),
                environment=config.get("environment", "unknown"),
                change_type="initial_load",
                source_file=source,
                changed_keys=list(config.keys()),
                user=os.environ.get("USER"),
                process_id=os.getpid(),
                config_hash=config_hash
            )
            
            if self._should_log_event(event):
                self._write_audit_log(event)
            
            self._last_config_hash = config_hash

    def log_config_change(self, old_config: Optional[Dict], new_config: Dict, 
                         source_file: str = None, change_type: str = "file_change"):
        """
        Log configuration changes.
        
        Args:
            old_config: Previous configuration state
            new_config: New configuration state
            source_file: File that triggered the change
            change_type: Type of change ('file_change', 'hot_reload', etc.)
        """
        with self._lock:
            new_hash = self._calculate_config_hash(new_config)
            
            # Skip if configuration hasn't actually changed
            if new_hash == self._last_config_hash and change_type == "hot_reload":
                if self.policy.log_unchanged_reloads:
                    event = ConfigChangeEvent(
                        timestamp=datetime.now().isoformat(),
                        environment=new_config.get("environment", "unknown"),
                        change_type=change_type,
                        source_file=source_file,
                        changed_keys=[],
                        user=os.environ.get("USER"),
                        process_id=os.getpid(),
                        config_hash=new_hash
                    )
                    self._write_audit_log(event)
                return
            
            # Detect changes
            change_summary = self._detect_changes(old_config, new_config)
            importance = self._categorize_change_importance(change_summary["changed_keys"])
            
            event = ConfigChangeEvent(
                timestamp=datetime.now().isoformat(),
                environment=new_config.get("environment", "unknown"),
                change_type=change_type,
                source_file=source_file,
                changed_keys=change_summary["changed_keys"],
                change_summary=change_summary,
                user=os.environ.get("USER"),
                process_id=os.getpid(),
                config_hash=new_hash
            )
            
            if self._should_log_event(event):
                self._write_audit_log(event)
                
                # Alert on critical changes
                if importance == "critical" and self.policy.alert_on_critical_changes:
                    self._alert_critical_change(event)
            
            self._last_config_hash = new_hash

    def log_validation_results(self, config: Dict, errors: List, warnings: List):
        """
        Log configuration validation results.
        
        Args:
            config: Configuration that was validated
            errors: List of validation errors
            warnings: List of validation warnings
        """
        with self._lock:
            event = ConfigChangeEvent(
                timestamp=datetime.now().isoformat(),
                environment=config.get("environment", "unknown"),
                change_type="validation",
                validation_errors=len(errors),
                validation_warnings=len(warnings),
                user=os.environ.get("USER"),
                process_id=os.getpid(),
                config_hash=self._calculate_config_hash(config)
            )
            
            if self._should_log_event(event):
                self._write_audit_log(event)

    def _alert_critical_change(self, event: ConfigChangeEvent):
        """
        Alert on critical configuration changes.
        
        Args:
            event: Configuration change event that triggered the alert
        """
        critical_keys = set(event.changed_keys or []) & self.SECURITY_CRITICAL_KEYS
        
        if critical_keys:
            print(f"🚨 SECURITY ALERT: Critical configuration keys changed: {', '.join(critical_keys)}")
            print(f"   Environment: {event.environment}")
            print(f"   Source: {event.source_file or 'Unknown'}")
            print(f"   Timestamp: {event.timestamp}")
            
            # In production, this could send alerts via email, Slack, etc.

    def get_recent_changes(self, hours: int = 24) -> List[ConfigChangeEvent]:
        """
        Get recent configuration changes from the audit log.
        
        Args:
            hours: Number of hours back to look for changes
            
        Returns:
            List of recent configuration change events
        """
        if not self.policy.enabled or not os.path.exists(self.policy.log_file):
            return []
        
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = []
        
        try:
            with open(self.policy.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())
                        event_time = datetime.fromisoformat(event_data['timestamp'])
                        
                        if event_time >= cutoff_time:
                            event = ConfigChangeEvent(**event_data)
                            recent_events.append(event)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue  # Skip malformed lines
        
        except Exception as e:
            print(f"⚠️  Error reading audit log: {e}")
        
        return sorted(recent_events, key=lambda x: x.timestamp, reverse=True)

    def generate_audit_report(self, days: int = 7) -> str:
        """
        Generate a summary audit report.
        
        Args:
            days: Number of days to include in the report
            
        Returns:
            Formatted audit report string
        """
        recent_changes = self.get_recent_changes(hours=days * 24)
        
        if not recent_changes:
            return f"📊 Configuration Audit Report (Last {days} days)\n" + \
                   "=" * 50 + "\n\nNo configuration changes recorded.\n"
        
        # Analyze changes
        change_types = {}
        critical_changes = 0
        environments = set()
        
        for event in recent_changes:
            change_types[event.change_type] = change_types.get(event.change_type, 0) + 1
            environments.add(event.environment)
            
            if event.changed_keys:
                critical_keys = set(event.changed_keys) & self.SECURITY_CRITICAL_KEYS
                if critical_keys:
                    critical_changes += 1
        
        report = f"📊 Configuration Audit Report (Last {days} days)\n"
        report += "=" * 50 + "\n\n"
        report += f"Total Changes: {len(recent_changes)}\n"
        report += f"Critical Changes: {critical_changes}\n"
        report += f"Environments: {', '.join(sorted(environments))}\n\n"
        
        report += "Change Types:\n"
        for change_type, count in sorted(change_types.items()):
            report += f"  • {change_type}: {count}\n"
        
        if critical_changes > 0:
            report += f"\n🚨 Recent Critical Changes:\n"
            for event in recent_changes:
                if event.changed_keys:
                    critical_keys = set(event.changed_keys) & self.SECURITY_CRITICAL_KEYS
                    if critical_keys:
                        report += f"  • {event.timestamp}: {', '.join(critical_keys)} in {event.environment}\n"
        
        return report


# Global auditor instance
_global_auditor: Optional[ConfigAuditor] = None


def get_config_auditor(policy: Optional[AuditPolicy] = None) -> ConfigAuditor:
    """
    Get or create the global configuration auditor.
    
    Args:
        policy: Audit policy configuration
        
    Returns:
        Global ConfigAuditor instance
    """
    global _global_auditor
    
    if _global_auditor is None:
        _global_auditor = ConfigAuditor(policy)
    
    return _global_auditor


def log_config_change(old_config: Optional[Dict], new_config: Dict, 
                     source_file: str = None, change_type: str = "file_change"):
    """
    Convenience function to log configuration changes using global auditor.
    
    Args:
        old_config: Previous configuration state
        new_config: New configuration state
        source_file: File that triggered the change
        change_type: Type of change
    """
    auditor = get_config_auditor()
    auditor.log_config_change(old_config, new_config, source_file, change_type)


def log_config_validation(config: Dict, errors: List, warnings: List):
    """
    Convenience function to log validation results using global auditor.
    
    Args:
        config: Configuration that was validated
        errors: List of validation errors
        warnings: List of validation warnings
    """
    auditor = get_config_auditor()
    auditor.log_validation_results(config, errors, warnings)


# Example usage
if __name__ == "__main__":
    # Example of setting up auditing
    policy = AuditPolicy(
        enabled=True,
        log_file="logs/config_audit.jsonl",
        alert_on_critical_changes=True,
        monitored_keys={"llm_provider", "environment", "data_directory"}
    )
    
    auditor = ConfigAuditor(policy)
    
    # Example configuration changes
    old_config = {"llm_provider": "openrouter", "environment": "development"}
    new_config = {"llm_provider": "deepseek", "environment": "development"}
    
    auditor.log_config_change(old_config, new_config, "config/.env", "file_change")
    
    # Generate report
    print(auditor.generate_audit_report(days=1))