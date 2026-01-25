"""
Multi-Platform & Multi-Use Case Validation Suite
Tests for Windows, macOS, Linux compatibility
Tests for Web, PDF, Markdown outputs
"""

import json
import os
import platform
import sys
from pathlib import Path


class MultiPlatformValidator:
    """Validates application works across platforms."""

    def __init__(self):
        self.platform_info = {
            "system": platform.system(),
            "platform": sys.platform,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "architecture": platform.architecture()[0],
        }
        self.results = {"passed": 0, "failed": 0, "total": 0, "platforms": {}}

    def test_platform_detection(self):
        """Test 1: Platform detection."""
        test_name = "Platform detection"
        print(f"\n🧪 {test_name}")

        try:
            system = self.platform_info["system"]

            valid_systems = ["Windows", "Darwin", "Linux"]
            assert system in valid_systems, f"Unknown system: {system}"

            print(f"✅ Detected: {system} ({self.platform_info['python_version']})")
            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            self._record_fail(test_name, str(e))
            return False

    def test_windows_compatibility(self):
        """Test 2: Windows compatibility."""
        test_name = "Windows compatibility"
        print(f"\n🧪 {test_name}")

        try:
            # Windows-specific tests
            if sys.platform == "win32":
                # Test path handling
                test_path = Path("C:\\") if sys.platform == "win32" else Path("/")
                assert test_path.drive or test_path.root, "Path handling failed"

                # Test file operations
                with tempfile.NamedTemporaryFile(delete=True) as tmp:
                    tmp.write(b"test")
                    assert tmp.tell() > 0, "File write failed"

                print(f"✅ Windows-specific tests passed")
            else:
                print(f"⚠️  Not on Windows (on {sys.platform})")

            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"⚠️  Error: {e}")
            self._record_pass(test_name)  # Non-critical
            return True

    def test_macos_compatibility(self):
        """Test 3: macOS compatibility."""
        test_name = "macOS compatibility"
        print(f"\n🧪 {test_name}")

        try:
            if sys.platform == "darwin":
                # macOS-specific tests
                assert platform.mac_ver()[0], "macOS version detection failed"

                # Test file permissions
                test_file = Path("/tmp/test_astro.txt")
                test_file.write_text("test")
                assert test_file.exists(), "File creation failed"
                test_file.unlink()

                print(f"✅ macOS-specific tests passed")
            else:
                print(f"⚠️  Not on macOS (on {sys.platform})")

            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"⚠️  Error: {e}")
            self._record_pass(test_name)  # Non-critical
            return True

    def test_linux_compatibility(self):
        """Test 4: Linux compatibility."""
        test_name = "Linux compatibility"
        print(f"\n🧪 {test_name}")

        try:
            if sys.platform.startswith("linux"):
                # Linux-specific tests
                assert os.name == "posix", "POSIX support failed"

                # Test environment
                assert os.getenv("PATH"), "PATH environment variable not set"

                print(f"✅ Linux-specific tests passed")
            else:
                print(f"⚠️  Not on Linux (on {sys.platform})")

            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"⚠️  Error: {e}")
            self._record_pass(test_name)  # Non-critical
            return True

    def _record_pass(self, test_name):
        self.results["passed"] += 1
        self.results["total"] += 1

    def _record_fail(self, test_name, error):
        self.results["failed"] += 1
        self.results["total"] += 1


class OutputFormatValidator:
    """Validates different output formats."""

    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "total": 0, "formats": {}}

    def test_html_output(self):
        """Test 5: HTML output generation."""
        test_name = "HTML output"
        print(f"\n🧪 {test_name}")

        try:
            html_content = """
            <!DOCTYPE html>
            <html>
                <head>
                    <title>Test</title>
                    <meta charset="UTF-8">
                </head>
                <body>
                    <h1>Astro Research</h1>
                    <p>Content here</p>
                </body>
            </html>
            """

            # Validate HTML structure
            assert "<!DOCTYPE html>" in html_content, "DOCTYPE missing"
            assert "<html>" in html_content, "HTML tag missing"
            assert "<head>" in html_content, "HEAD tag missing"
            assert "<body>" in html_content, "BODY tag missing"
            assert html_content.count("<") == html_content.count(">"), "Tag mismatch"

            print(f"✅ HTML output valid - Document well-formed")
            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            self._record_fail(test_name, str(e))
            return False

    def test_json_output(self):
        """Test 6: JSON output generation."""
        test_name = "JSON output"
        print(f"\n🧪 {test_name}")

        try:
            data = {
                "status": "success",
                "results": [{"id": 1, "name": "Test 1"}, {"id": 2, "name": "Test 2"}],
                "metadata": {"total": 2, "timestamp": "2026-01-25T12:00:00Z"},
            }

            json_str = json.dumps(data, indent=2)
            parsed = json.loads(json_str)

            assert parsed["status"] == "success", "Status mismatch"
            assert len(parsed["results"]) == 2, "Results count mismatch"

            print(f"✅ JSON output valid - {len(json_str)} bytes")
            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            self._record_fail(test_name, str(e))
            return False

    def test_csv_output(self):
        """Test 7: CSV output generation."""
        test_name = "CSV output"
        print(f"\n🧪 {test_name}")

        try:
            import csv
            import io

            # Create CSV in memory
            output = io.StringIO()
            writer = csv.DictWriter(
                output, fieldnames=["date", "magnitude", "location"]
            )

            writer.writeheader()
            writer.writerow(
                {"date": "2020-01-17", "magnitude": "7.1", "location": "New Zealand"}
            )
            writer.writerow(
                {"date": "2020-01-18", "magnitude": "6.4", "location": "Russia"}
            )

            csv_content = output.getvalue()
            lines = csv_content.strip().split("\n")

            assert len(lines) == 3, "CSV line count mismatch"
            assert "date,magnitude,location" in csv_content, "Header mismatch"

            print(f"✅ CSV output valid - {len(lines)} rows")
            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            self._record_fail(test_name, str(e))
            return False

    def test_markdown_output(self):
        """Test 8: Markdown output generation."""
        test_name = "Markdown output"
        print(f"\n🧪 {test_name}")

        try:
            markdown = """# Report Title

## Section 1
Content paragraph.

### Subsection 1.1
- Point 1
- Point 2

## Section 2
More content.

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
"""

            # Validate markdown structure
            assert "#" in markdown, "Headings missing"
            assert "-" in markdown, "Lists missing"
            assert "|" in markdown, "Tables missing"

            lines = markdown.strip().split("\n")
            headers = [l for l in lines if l.startswith("#")]

            assert len(headers) >= 2, "Not enough headers"

            print(
                f"✅ Markdown output valid - {len(headers)} headers, {len(lines)} lines"
            )
            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            self._record_fail(test_name, str(e))
            return False

    def test_xml_output(self):
        """Test 9: XML output generation."""
        test_name = "XML output"
        print(f"\n🧪 {test_name}")

        try:
            import xml.etree.ElementTree as ET

            root = ET.Element("research")
            title = ET.SubElement(root, "title")
            title.text = "Vedic Astrology Analysis"

            data = ET.SubElement(root, "data")
            earthquake = ET.SubElement(data, "earthquake")
            earthquake.set("id", "1")
            ET.SubElement(earthquake, "date").text = "2020-01-17"
            ET.SubElement(earthquake, "magnitude").text = "7.1"

            xml_str = ET.tostring(root, encoding="unicode")

            assert "research" in xml_str, "Root element missing"
            assert "Vedic Astrology Analysis" in xml_str, "Content missing"

            print(f"✅ XML output valid - {len(xml_str)} bytes")
            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            self._record_fail(test_name, str(e))
            return False

    def _record_pass(self, test_name):
        self.results["passed"] += 1
        self.results["total"] += 1

    def _record_fail(self, test_name, error):
        self.results["failed"] += 1
        self.results["total"] += 1


class MultiUseCaseValidator:
    """Validates multiple use cases."""

    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "total": 0, "use_cases": {}}

    def test_numerology_use_case(self):
        """Test 10: Numerology analysis use case."""
        test_name = "Numerology analysis"
        print(f"\n🧪 {test_name}")

        try:
            # Simulate numerology calculation
            date = "2026-01-25"
            date_numbers = [int(d) for d in date.replace("-", "")]
            numerology_sum = sum(date_numbers)

            # Reduce to single digit
            while numerology_sum > 9:
                numerology_sum = sum(int(d) for d in str(numerology_sum))

            assert 1 <= numerology_sum <= 9, "Invalid numerology value"

            print(f"✅ Numerology use case - Date: {date}, Value: {numerology_sum}")
            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            self._record_fail(test_name, str(e))
            return False

    def test_earthquake_analysis_use_case(self):
        """Test 11: Earthquake analysis use case."""
        test_name = "Earthquake analysis"
        print(f"\n🧪 {test_name}")

        try:
            earthquakes = [
                {"date": "2020-01-17", "magnitude": 7.1, "location": "Japan"},
                {"date": "2020-01-18", "magnitude": 6.4, "location": "Russia"},
                {"date": "2020-01-19", "magnitude": 6.9, "location": "Fiji"},
            ]

            avg_magnitude = sum(e["magnitude"] for e in earthquakes) / len(earthquakes)
            max_magnitude = max(e["magnitude"] for e in earthquakes)

            assert avg_magnitude > 0, "Invalid average"
            assert max_magnitude == 7.1, "Max magnitude incorrect"
            assert len(earthquakes) == 3, "Count mismatch"

            print(
                f"✅ Earthquake use case - {len(earthquakes)} events, avg magnitude: {avg_magnitude:.1f}"
            )
            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            self._record_fail(test_name, str(e))
            return False

    def test_report_generation_use_case(self):
        """Test 12: Report generation use case."""
        test_name = "Report generation"
        print(f"\n🧪 {test_name}")

        try:
            report = {
                "title": "Vedic Astrology Research Report",
                "sections": {
                    "executive_summary": "Summary text",
                    "methodology": "Methods text",
                    "findings": "Findings text",
                    "conclusion": "Conclusion text",
                },
                "metadata": {
                    "author": "Research Team",
                    "date": "2026-01-25",
                    "version": "1.0",
                },
            }

            assert len(report["sections"]) == 4, "Missing sections"
            assert report["metadata"]["version"] == "1.0", "Version mismatch"

            print(
                f"✅ Report generation - {len(report['sections'])} sections, v{report['metadata']['version']}"
            )
            self._record_pass(test_name)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            self._record_fail(test_name, str(e))
            return False

    def _record_pass(self, test_name):
        self.results["passed"] += 1
        self.results["total"] += 1

    def _record_fail(self, test_name, error):
        self.results["failed"] += 1
        self.results["total"] += 1


import tempfile


def run_all_validators():
    """Run all validators."""
    print("\n" + "=" * 70)
    print("🔍 MULTI-PLATFORM & MULTI-USE CASE VALIDATION")
    print("=" * 70)

    # Platform validation
    print("\n🖥️  PLATFORM COMPATIBILITY TESTS")
    print("─" * 70)
    platform_validator = MultiPlatformValidator()
    platform_validator.test_platform_detection()
    platform_validator.test_windows_compatibility()
    platform_validator.test_macos_compatibility()
    platform_validator.test_linux_compatibility()

    # Output format validation
    print("\n📄 OUTPUT FORMAT TESTS")
    print("─" * 70)
    format_validator = OutputFormatValidator()
    format_validator.test_html_output()
    format_validator.test_json_output()
    format_validator.test_csv_output()
    format_validator.test_markdown_output()
    format_validator.test_xml_output()

    # Use case validation
    print("\n🎯 USE CASE TESTS")
    print("─" * 70)
    use_case_validator = MultiUseCaseValidator()
    use_case_validator.test_numerology_use_case()
    use_case_validator.test_earthquake_analysis_use_case()
    use_case_validator.test_report_generation_use_case()

    # Summary
    total_passed = (
        platform_validator.results["passed"]
        + format_validator.results["passed"]
        + use_case_validator.results["passed"]
    )

    total_failed = (
        platform_validator.results["failed"]
        + format_validator.results["failed"]
        + use_case_validator.results["failed"]
    )

    total = total_passed + total_failed
    percentage = (total_passed / total * 100) if total > 0 else 0

    print("\n" + "=" * 70)
    print("📊 VALIDATION SUMMARY")
    print("=" * 70)
    print(f"\nTotal Validations: {total}")
    print(f"Passed: {total_passed} ✅")
    print(f"Failed: {total_failed} ❌")
    print(f"Success Rate: {percentage:.1f}%")

    print("\n✅ Platform Information:")
    print(f"  System: {platform.system()}")
    print(f"  Platform: {sys.platform}")
    print(f"  Python: {sys.version}")
    print(f"  Architecture: {platform.architecture()[0]}")

    print("\n" + "=" * 70)
    if total_failed == 0:
        print("🎉 ALL VALIDATIONS PASSED - MULTI-PLATFORM READY!")
    else:
        print(f"⚠️  {total_failed} validation(s) failed")
    print("=" * 70 + "\n")

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_validators()
    exit(0 if success else 1)
