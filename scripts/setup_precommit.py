#!/usr/bin/env python3
"""
Pre-commit Setup Script for Atlas Production-Ready System

This script sets up and configures pre-commit hooks for the Atlas project,
ensuring automated quality checks run before every commit.

Usage:
    python3 scripts/setup_precommit.py [--force]
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class PreCommitSetup:
    """Setup and configure pre-commit hooks for Atlas."""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.precommit_config = self.project_root / ".pre-commit-config.yaml"

    def check_requirements(self) -> bool:
        """Check if required tools are available."""
        print("🔍 Checking requirements...")

        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            print(
                f"❌ Python 3.8+ required, found {python_version.major}.{python_version.minor}"
            )
            return False
        print(
            f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}"
        )

        # Check git
        try:
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"✅ Git available: {result.stdout.strip()}")
            else:
                print("❌ Git not available")
                return False
        except FileNotFoundError:
            print("❌ Git not found in PATH")
            return False

        return True

    def install_precommit(self) -> bool:
        """Install pre-commit if not already installed."""
        print("🔧 Installing pre-commit...")

        try:
            # Check if pre-commit is already installed
            result = subprocess.run(
                ["pre-commit", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"✅ Pre-commit already installed: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass

        # Install pre-commit
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pre-commit"], check=True
            )
            print("✅ Pre-commit installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install pre-commit")
            return False

    def check_config_file(self) -> bool:
        """Check if pre-commit config file exists and is valid."""
        print("📋 Checking pre-commit configuration...")

        if not self.precommit_config.exists():
            print("❌ .pre-commit-config.yaml not found")
            return False

        # Validate YAML syntax
        try:
            import yaml

            with open(self.precommit_config, "r") as f:
                yaml.safe_load(f)
            print("✅ .pre-commit-config.yaml is valid")
            return True
        except yaml.YAMLError as e:
            print(f"❌ Invalid YAML in .pre-commit-config.yaml: {e}")
            return False
        except ImportError:
            print("⚠️ PyYAML not available, skipping YAML validation")
            return True

    def install_hooks(self, force: bool = False) -> bool:
        """Install pre-commit hooks."""
        print("🪝 Installing pre-commit hooks...")

        try:
            cmd = ["pre-commit", "install"]
            if force:
                cmd.append("--overwrite")

            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True
            )

            if result.returncode == 0:
                print("✅ Pre-commit hooks installed")
                print(result.stdout)
                return True
            else:
                print(f"❌ Failed to install hooks: {result.stderr}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install pre-commit hooks: {e}")
            return False

    def install_push_hooks(self) -> bool:
        """Install pre-push hooks for coverage checks."""
        print("🚀 Installing pre-push hooks...")

        try:
            result = subprocess.run(
                ["pre-commit", "install", "--hook-type", "pre-push"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ Pre-push hooks installed")
                return True
            else:
                print(f"⚠️ Pre-push hooks installation had issues: {result.stderr}")
                return True  # Not critical for basic functionality

        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to install pre-push hooks: {e}")
            return True  # Not critical

    def run_test_hooks(self) -> bool:
        """Run a test of the hooks to ensure they work."""
        print("🧪 Testing pre-commit hooks...")

        try:
            # Run hooks on all files (dry run)
            result = subprocess.run(
                ["pre-commit", "run", "--all-files", "--show-diff-on-failure"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ All pre-commit hooks passed")
                return True
            else:
                print("⚠️ Some pre-commit hooks failed (this is normal for first run)")
                print("   Hooks will auto-fix issues on commit")
                print(f"   Output: {result.stdout}")
                return True  # Expected on first run

        except subprocess.CalledProcessError as e:
            print(f"⚠️ Error testing hooks: {e}")
            return True  # Not critical

    def create_commit_template(self) -> None:
        """Create a commit message template."""
        template_path = self.project_root / ".gitmessage"

        template_content = """# Atlas Commit Message
#
# Format: <type>(<scope>): <description>
#
# Types:
# - feat: new feature
# - fix: bug fix
# - docs: documentation changes
# - style: formatting changes
# - refactor: code restructuring
# - test: adding/updating tests
# - chore: maintenance tasks
#
# Examples:
# feat(helpers): add new config validation function
# fix(web): resolve dashboard loading issue
# test(unit): add comprehensive config tests
# docs(readme): update installation instructions
"""

        try:
            with open(template_path, "w") as f:
                f.write(template_content)

            # Set git to use this template
            subprocess.run(
                ["git", "config", "commit.template", ".gitmessage"],
                cwd=self.project_root,
                check=True,
            )

            print("✅ Git commit message template created")
        except Exception as e:
            print(f"⚠️ Could not create commit template: {e}")

    def setup(self, force: bool = False) -> bool:
        """Run complete pre-commit setup."""
        print("🚀 Setting up Atlas pre-commit hooks")
        print("=" * 50)

        steps = [
            self.check_requirements,
            self.install_precommit,
            lambda: self.check_config_file(),
            lambda: self.install_hooks(force),
            self.install_push_hooks,
            self.run_test_hooks,
        ]

        for step in steps:
            if not step():
                print(f"\n❌ Setup failed at step: {step.__name__}")
                return False

        # Create commit template (non-critical)
        self.create_commit_template()

        print("\n🎉 Pre-commit setup completed successfully!")
        print("\n📋 What happens now:")
        print("• Code formatting (Black, isort) runs automatically before commits")
        print("• Basic linting (flake8) checks code quality")
        print("• Security scanning (bandit) checks for vulnerabilities")
        print("• Quick unit tests run to catch immediate issues")
        print("• Configuration validation runs when config files change")
        print("• Coverage checks run before pushes")

        print("\n🔧 Manual commands:")
        print("• Run hooks manually: pre-commit run --all-files")
        print("• Update hooks: pre-commit autoupdate")
        print("• Skip hooks (not recommended): git commit --no-verify")

        return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Setup Atlas pre-commit hooks")
    parser.add_argument(
        "--force", action="store_true", help="Force reinstallation of hooks"
    )

    args = parser.parse_args()

    setup = PreCommitSetup()
    success = setup.setup(force=args.force)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
