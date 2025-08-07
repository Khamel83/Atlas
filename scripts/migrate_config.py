#!/usr/bin/env python3
"""
Atlas Configuration Migration Tool

This script handles configuration schema migrations, helping users upgrade
their configuration files when the Atlas configuration format changes.
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ConfigMigration:
    """Base class for configuration migrations."""

    def __init__(self, version_from: str, version_to: str):
        self.version_from = version_from
        self.version_to = version_to
        self.description = "Base migration"

    def check_applicable(self, config_path: Path) -> bool:
        """Check if this migration applies to the given configuration."""
        raise NotImplementedError

    def migrate(self, config_path: Path, backup_dir: Path) -> bool:
        """Perform the migration. Returns True if successful."""
        raise NotImplementedError

    def rollback(self, config_path: Path, backup_dir: Path) -> bool:
        """Rollback the migration if possible."""
        raise NotImplementedError


class LegacyEnvMigration(ConfigMigration):
    """Migration from legacy .env in project root to config/.env structure."""

    def __init__(self):
        super().__init__("legacy", "1.0.0")
        self.description = "Migrate from legacy .env to config/ directory structure"

    def check_applicable(self, config_path: Path) -> bool:
        """Check if legacy .env file exists and needs migration."""
        legacy_env = config_path.parent / ".env"
        config_env = config_path / ".env"

        return legacy_env.exists() and not config_env.exists()

    def migrate(self, config_path: Path, backup_dir: Path) -> bool:
        """Move .env to config/.env and update paths."""
        legacy_env = config_path.parent / ".env"
        config_env = config_path / ".env"

        try:
            # Create backup
            if backup_dir:
                shutil.copy2(legacy_env, backup_dir / ".env.legacy")

            # Read legacy configuration
            with open(legacy_env, "r") as f:
                content = f.read()

            # Update any relative paths that might be affected
            updated_content = self._update_legacy_paths(content)

            # Write to new location
            config_env.parent.mkdir(parents=True, exist_ok=True)
            with open(config_env, "w") as f:
                f.write(updated_content)

            print(f"✅ Migrated {legacy_env} → {config_env}")

            # Optionally remove legacy file (ask user)
            response = input(f"Remove legacy file {legacy_env}? [y/N]: ")
            if response.lower() == "y":
                legacy_env.unlink()
                print(f"🗑️  Removed legacy file {legacy_env}")

            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

    def _update_legacy_paths(self, content: str) -> str:
        """Update any paths that might be affected by the migration."""
        # Update relative paths to account for new config directory location
        # This is a simple example - real migrations might be more complex

        # Add environment identifier if not present
        if "ATLAS_ENVIRONMENT" not in content:
            content = "# Atlas Environment\nATLAS_ENVIRONMENT=development\n\n" + content

        return content

    def rollback(self, config_path: Path, backup_dir: Path) -> bool:
        """Rollback by restoring legacy .env file."""
        if not backup_dir or not (backup_dir / ".env.legacy").exists():
            print("❌ No backup found for rollback")
            return False

        try:
            legacy_env = config_path.parent / ".env"
            shutil.copy2(backup_dir / ".env.legacy", legacy_env)
            print(f"✅ Restored legacy configuration to {legacy_env}")
            return True
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False


class EnvironmentProfileMigration(ConfigMigration):
    """Migration to add environment-specific profiles."""

    def __init__(self):
        super().__init__("1.0.0", "1.1.0")
        self.description = "Add environment-specific configuration profiles"

    def check_applicable(self, config_path: Path) -> bool:
        """Check if environment profiles need to be created."""
        env_file = config_path / ".env"
        env_dev = config_path / ".env.development"

        return env_file.exists() and not env_dev.exists()

    def migrate(self, config_path: Path, backup_dir: Path) -> bool:
        """Create environment-specific .env files."""
        try:
            env_file = config_path / ".env"

            # Create backup
            if backup_dir:
                shutil.copy2(env_file, backup_dir / ".env.before_profiles")

            # Read existing configuration
            with open(env_file, "r") as f:
                content = f.read()

            # Create environment-specific files
            environments = ["development", "test", "production"]

            for env in environments:
                env_specific_file = config_path / f".env.{env}"
                env_content = self._create_env_specific_content(content, env)

                with open(env_specific_file, "w") as f:
                    f.write(env_content)

                print(f"✅ Created {env_specific_file}")

            # Add environment indicator to main .env if missing
            if "ATLAS_ENVIRONMENT" not in content:
                with open(env_file, "a") as f:
                    f.write("\n# Default environment\nATLAS_ENVIRONMENT=development\n")
                print(f"✅ Updated {env_file} with environment setting")

            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

    def _create_env_specific_content(self, base_content: str, env: str) -> str:
        """Create environment-specific configuration content."""
        lines = [f"# Atlas {env.title()} Environment Configuration"]
        lines.append(
            f"# Generated from base configuration on {datetime.now().isoformat()}"
        )
        lines.append("")
        lines.append(f"ATLAS_ENVIRONMENT={env}")
        lines.append("")

        # Environment-specific adjustments
        env_adjustments = {
            "development": {
                "DATA_DIRECTORY": "dev_output",
                "LOG_LEVEL": "DEBUG",
                "MAX_RETRIES": "1",
                "PROCESSING_TIMEOUT": "10",
                "PODCAST_EPISODE_LIMIT": "5",
            },
            "test": {
                "DATA_DIRECTORY": "test_output",
                "LOG_LEVEL": "WARNING",
                "MAX_RETRIES": "1",
                "PROCESSING_TIMEOUT": "5",
                "PODCAST_EPISODE_LIMIT": "1",
                "LLM_PROVIDER": "mock",
                "LLM_MODEL": "mock-model",
            },
            "production": {
                "DATA_DIRECTORY": "production_data",
                "LOG_LEVEL": "INFO",
                "MAX_RETRIES": "5",
                "PROCESSING_TIMEOUT": "60",
                "PODCAST_EPISODE_LIMIT": "50",
                "USE_12FT_IO_FALLBACK": "false",
            },
        }

        # Process base content and apply environment adjustments
        base_vars = {}
        for line in base_content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                base_vars[key.strip()] = value.strip()

        # Apply environment-specific overrides
        adjustments = env_adjustments.get(env, {})
        for key, value in adjustments.items():
            base_vars[key] = value

        # Convert back to .env format
        for key, value in base_vars.items():
            if key != "ATLAS_ENVIRONMENT":  # Already added above
                lines.append(f"{key}={value}")

        return "\n".join(lines)

    def rollback(self, config_path: Path, backup_dir: Path) -> bool:
        """Remove environment-specific files and restore original."""
        if not backup_dir or not (backup_dir / ".env.before_profiles").exists():
            print("❌ No backup found for rollback")
            return False

        try:
            # Remove environment-specific files
            environments = ["development", "test", "production"]
            for env in environments:
                env_file = config_path / f".env.{env}"
                if env_file.exists():
                    env_file.unlink()
                    print(f"🗑️  Removed {env_file}")

            # Restore original .env
            env_file = config_path / ".env"
            shutil.copy2(backup_dir / ".env.before_profiles", env_file)
            print(f"✅ Restored original {env_file}")

            return True
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False


class ModelTierMigration(ConfigMigration):
    """Migration to add model tier configuration."""

    def __init__(self):
        super().__init__("1.1.0", "1.2.0")
        self.description = "Add model tier configuration for cost optimization"

    def check_applicable(self, config_path: Path) -> bool:
        """Check if model tiers need to be added."""
        env_files = [config_path / ".env", config_path / ".env.development"]

        for env_file in env_files:
            if env_file.exists():
                with open(env_file, "r") as f:
                    content = f.read()
                if "MODEL_BUDGET" not in content and "LLM_MODEL" in content:
                    return True
        return False

    def migrate(self, config_path: Path, backup_dir: Path) -> bool:
        """Add model tier configuration."""
        try:
            env_files = list(config_path.glob(".env*"))

            for env_file in env_files:
                if not env_file.is_file():
                    continue

                # Create backup
                if backup_dir:
                    shutil.copy2(env_file, backup_dir / f"{env_file.name}.before_tiers")

                # Read and update content
                with open(env_file, "r") as f:
                    content = f.read()

                # Add model tiers if missing
                updated_content = self._add_model_tiers(content, env_file.name)

                with open(env_file, "w") as f:
                    f.write(updated_content)

                print(f"✅ Added model tiers to {env_file}")

            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

    def _add_model_tiers(self, content: str, filename: str) -> str:
        """Add model tier configuration to content."""
        lines = content.split("\n")
        new_lines = []
        added_tiers = False

        for line in lines:
            new_lines.append(line)

            # Add tiers after LLM_MODEL line
            if line.startswith("LLM_MODEL=") and not added_tiers:
                new_lines.extend(
                    [
                        "",
                        "# Model Tiers for Cost Optimization",
                        "MODEL_PREMIUM=google/gemini-2.0-flash-lite-001",
                        "MODEL_BUDGET=mistralai/mistral-7b-instruct:free",
                        "MODEL_FALLBACK=google/gemini-2.0-flash-lite-001",
                    ]
                )
                added_tiers = True

        # If no LLM_MODEL found, add at end
        if not added_tiers:
            new_lines.extend(
                [
                    "",
                    "# Model Configuration",
                    "LLM_MODEL=mistralai/mistral-7b-instruct",
                    "MODEL_PREMIUM=google/gemini-2.0-flash-lite-001",
                    "MODEL_BUDGET=mistralai/mistral-7b-instruct:free",
                    "MODEL_FALLBACK=google/gemini-2.0-flash-lite-001",
                ]
            )

        return "\n".join(new_lines)

    def rollback(self, config_path: Path, backup_dir: Path) -> bool:
        """Restore files before model tier addition."""
        if not backup_dir:
            print("❌ No backup directory specified")
            return False

        try:
            backup_files = list(backup_dir.glob("*.before_tiers"))
            for backup_file in backup_files:
                original_name = backup_file.name.replace(".before_tiers", "")
                original_file = config_path / original_name
                shutil.copy2(backup_file, original_file)
                print(f"✅ Restored {original_file}")

            return True
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False


class ConfigMigrationManager:
    """Manages configuration migrations."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.migrations = [
            LegacyEnvMigration(),
            EnvironmentProfileMigration(),
            ModelTierMigration(),
        ]

    def check_migrations_needed(self) -> List[ConfigMigration]:
        """Check which migrations are applicable."""
        applicable = []
        for migration in self.migrations:
            if migration.check_applicable(self.config_dir):
                applicable.append(migration)
        return applicable

    def apply_migrations(self, backup: bool = True) -> bool:
        """Apply all applicable migrations."""
        needed = self.check_migrations_needed()

        if not needed:
            print("✅ No migrations needed - configuration is up to date")
            return True

        print(f"Found {len(needed)} migrations to apply:")
        for migration in needed:
            print(f"  - {migration.description}")

        # Create backup directory if requested
        backup_dir = None
        if backup:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.config_dir / f"backup_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created backup directory: {backup_dir}")

        # Apply migrations
        success = True
        for migration in needed:
            print(f"\n🔄 Applying: {migration.description}")
            if not migration.migrate(self.config_dir, backup_dir):
                success = False
                break

        if success:
            print("\n✅ All migrations applied successfully!")
        else:
            print("\n❌ Migration failed. Check backups if rollback is needed.")

        return success

    def create_backup(self) -> Path:
        """Create a backup of the current configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.config_dir / f"backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Copy all configuration files
        config_files = list(self.config_dir.glob(".env*")) + list(
            self.config_dir.glob("*.yaml")
        )
        for config_file in config_files:
            if config_file.is_file():
                shutil.copy2(config_file, backup_dir)

        print(f"📁 Created backup: {backup_dir}")
        return backup_dir


def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(description="Atlas Configuration Migration Tool")
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Configuration directory (default: config)",
    )
    parser.add_argument(
        "--check", action="store_true", help="Check what migrations are needed"
    )
    parser.add_argument("--apply", action="store_true", help="Apply needed migrations")
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup before migration (default: true)",
    )
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")

    args = parser.parse_args()

    # Handle backup flags
    backup = args.backup and not args.no_backup

    if not args.config_dir.exists():
        print(f"❌ Configuration directory not found: {args.config_dir}")
        return 1

    manager = ConfigMigrationManager(args.config_dir)

    if args.check:
        needed = manager.check_migrations_needed()
        if needed:
            print(f"🔄 {len(needed)} migrations needed:")
            for migration in needed:
                print(f"  - {migration.description}")
            return 2  # Exit code 2 indicates migrations needed
        else:
            print("✅ No migrations needed - configuration is up to date")
            return 0

    elif args.apply:
        success = manager.apply_migrations(backup=backup)
        return 0 if success else 1

    else:
        # Default: check and prompt for apply
        needed = manager.check_migrations_needed()
        if needed:
            print(f"🔄 {len(needed)} migrations available:")
            for migration in needed:
                print(f"  - {migration.description}")

            response = input("\nApply migrations? [y/N]: ")
            if response.lower() == "y":
                success = manager.apply_migrations(backup=backup)
                return 0 if success else 1
        else:
            print("✅ No migrations needed - configuration is up to date")

        return 0


if __name__ == "__main__":
    sys.exit(main())
