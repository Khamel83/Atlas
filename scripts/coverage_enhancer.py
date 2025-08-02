#!/usr/bin/env python3
"""
Coverage Enhancement Script for Atlas Production-Ready System

This script analyzes current test coverage and provides actionable
recommendations for improving coverage to production-ready levels.

Usage:
    python3 scripts/coverage_enhancer.py
"""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CoverageAnalyzer:
    """Analyze test coverage and generate enhancement recommendations."""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.coverage_xml = self.project_root / "coverage.xml"
        self.htmlcov_dir = self.project_root / "htmlcov"

    def run_coverage_analysis(self) -> Dict:
        """Run pytest with coverage and analyze results."""
        print("🔍 Running coverage analysis...")

        # Run pytest with coverage (focus on unit tests first)
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/",
            "--cov=helpers",
            "--cov=ask",
            "--cov=web",
            "--cov=scripts",
            "--cov-report=xml:coverage-unit.xml",
            "--cov-report=html:htmlcov-unit",
            "--cov-report=term-missing",
            "--tb=short",
            "-q",
        ]

        try:
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True
            )

            # Parse XML coverage report
            coverage_xml = self.project_root / "coverage-unit.xml"
            if coverage_xml.exists():
                return self._parse_coverage_xml(coverage_xml)
            else:
                print("❌ Coverage XML not generated")
                return {}

        except Exception as e:
            print(f"❌ Error running coverage: {e}")
            return {}

    def _parse_coverage_xml(self, xml_file: Path) -> Dict:
        """Parse coverage XML and extract statistics."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Get overall coverage
            overall = {
                "line_rate": float(root.get("line-rate", 0)),
                "lines_covered": int(root.get("lines-covered", 0)),
                "lines_valid": int(root.get("lines-valid", 0)),
            }

            # Get per-package coverage
            packages = {}
            for package in root.findall(".//package"):
                package_name = package.get("name", "unknown")
                packages[package_name] = {
                    "line_rate": float(package.get("line-rate", 0)),
                    "classes": [],
                }

                for class_elem in package.findall(".//class"):
                    filename = class_elem.get("filename", "")
                    line_rate = float(class_elem.get("line-rate", 0))
                    packages[package_name]["classes"].append(
                        {"filename": filename, "line_rate": line_rate}
                    )

            return {"overall": overall, "packages": packages}

        except Exception as e:
            print(f"❌ Error parsing coverage XML: {e}")
            return {}

    def find_untested_modules(self) -> List[str]:
        """Find modules with no or low test coverage."""
        untested = []

        # Check helpers directory
        helpers_dir = self.project_root / "helpers"
        if helpers_dir.exists():
            for py_file in helpers_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    test_file = (
                        self.project_root / "tests" / "unit" / f"test_{py_file.name}"
                    )
                    if not test_file.exists():
                        untested.append(f"helpers/{py_file.name}")

        # Check ask directory
        ask_dir = self.project_root / "ask"
        if ask_dir.exists():
            for subdir in ask_dir.iterdir():
                if subdir.is_dir():
                    for py_file in subdir.glob("*.py"):
                        if py_file.name != "__init__.py":
                            test_file = (
                                self.project_root
                                / "tests"
                                / "unit"
                                / f"test_{py_file.name}"
                            )
                            if not test_file.exists():
                                untested.append(f"ask/{subdir.name}/{py_file.name}")

        return untested

    def generate_recommendations(self, coverage_data: Dict) -> List[str]:
        """Generate actionable recommendations for improving coverage."""
        recommendations = []

        if not coverage_data:
            recommendations.append(
                "❌ No coverage data available - fix test execution first"
            )
            return recommendations

        overall_rate = coverage_data.get("overall", {}).get("line_rate", 0)

        if overall_rate < 0.3:
            recommendations.append(
                "🔴 CRITICAL: Coverage below 30% - focus on basic unit tests"
            )
        elif overall_rate < 0.5:
            recommendations.append(
                "🟡 LOW: Coverage below 50% - expand unit test suite"
            )
        elif overall_rate < 0.7:
            recommendations.append(
                "🟠 MODERATE: Coverage below 70% - add integration tests"
            )
        elif overall_rate < 0.9:
            recommendations.append(
                "🟢 GOOD: Coverage above 70% - optimize and add edge cases"
            )
        else:
            recommendations.append(
                "✅ EXCELLENT: Coverage above 90% - maintain and refine"
            )

        # Find modules with no tests
        untested = self.find_untested_modules()
        if untested:
            recommendations.append(f"📝 Missing tests for {len(untested)} modules:")
            for module in untested[:10]:  # Show first 10
                recommendations.append(f"   - {module}")
            if len(untested) > 10:
                recommendations.append(f"   ... and {len(untested) - 10} more")

        # Package-specific recommendations
        packages = coverage_data.get("packages", {})
        for package_name, package_data in packages.items():
            package_rate = package_data.get("line_rate", 0)
            if package_rate < 0.5:
                recommendations.append(
                    f"🎯 FOCUS: '{package_name}' package has {package_rate:.1%} coverage"
                )

        return recommendations

    def create_test_template(self, module_path: str) -> str:
        """Create a basic test template for a module."""
        module_name = Path(module_path).stem

        template = f'''"""
Unit tests for {module_path}
Generated by coverage_enhancer.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import module under test
# TODO: Update import based on actual module structure
# from {module_path.replace('/', '.').replace('.py', '')} import ...


class Test{module_name.title().replace('_', '')}:
    """Test class for {module_name} module."""

    def test_module_imports(self):
        """Test that the module can be imported without errors."""
        # TODO: Add actual import test
        assert True  # Placeholder

    def test_basic_functionality(self):
        """Test basic functionality of the module."""
        # TODO: Add actual functionality tests
        assert True  # Placeholder

    @pytest.mark.parametrize("input_value,expected", [
        # TODO: Add test cases
        ("test", "expected"),
    ])
    def test_edge_cases(self, input_value, expected):
        """Test edge cases and error conditions."""
        # TODO: Add edge case tests
        assert True  # Placeholder


# TODO: Add more specific test classes and methods based on module content
'''
        return template

    def generate_missing_tests(self) -> None:
        """Generate template test files for untested modules."""
        untested = self.find_untested_modules()

        if not untested:
            print("✅ All modules have test files")
            return

        print(f"🏗️  Generating test templates for {len(untested)} modules...")

        tests_unit_dir = self.project_root / "tests" / "unit"
        tests_unit_dir.mkdir(parents=True, exist_ok=True)

        for module_path in untested[:5]:  # Limit to 5 at a time
            module_name = Path(module_path).stem
            test_filename = f"test_{module_name}.py"
            test_file_path = tests_unit_dir / test_filename

            if not test_file_path.exists():
                template = self.create_test_template(module_path)
                test_file_path.write_text(template)
                print(f"   📄 Created {test_file_path}")
            else:
                print(f"   ⚠️  {test_file_path} already exists")

    def run_analysis(self) -> None:
        """Run complete coverage analysis and generate recommendations."""
        print("🚀 Atlas Coverage Enhancement Analysis")
        print("=" * 50)

        # Run coverage analysis
        coverage_data = self.run_coverage_analysis()

        # Generate recommendations
        recommendations = self.generate_recommendations(coverage_data)

        # Display results
        print("\n📊 COVERAGE ANALYSIS RESULTS")
        print("-" * 30)

        if coverage_data and "overall" in coverage_data:
            overall = coverage_data["overall"]
            rate = overall["line_rate"] * 100
            print(
                f"Overall Coverage: {rate:.1f}% ({overall['lines_covered']}/{overall['lines_valid']} lines)"
            )

        print("\n🎯 RECOMMENDATIONS")
        print("-" * 20)
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")

        # Generate missing test templates
        print("\n🏗️  TEST GENERATION")
        print("-" * 18)
        self.generate_missing_tests()

        print(f"\n✅ Analysis complete! Coverage reports available in htmlcov-unit/")


def main():
    """Main entry point."""
    analyzer = CoverageAnalyzer()
    analyzer.run_analysis()


if __name__ == "__main__":
    main()
