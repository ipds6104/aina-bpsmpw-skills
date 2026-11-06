#!/usr/bin/env python3
"""
Unit tests for osv_scanner_gate.py
Hermetic, isolated, zero-network tests.
"""

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent scripts directory to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import osv_scanner_gate


class TestOSVScannerGate(unittest.TestCase):

    def test_is_manifest_file(self):
        # Truthy manifest / lockfiles
        self.assertTrue(osv_scanner_gate.is_manifest_file("composer.lock"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("composer.json"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("package-lock.json"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("pnpm-lock.yaml"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("yarn.lock"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("bun.lock"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("requirements.txt"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("requirements-dev.txt"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("poetry.lock"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("uv.lock"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("Cargo.lock"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("go.mod"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("pom.xml"))
        self.assertTrue(osv_scanner_gate.is_manifest_file("path/to/nested/composer.lock"))

        # Falsy regular files
        self.assertFalse(osv_scanner_gate.is_manifest_file("main.py"))
        self.assertFalse(osv_scanner_gate.is_manifest_file("Controller.php"))
        self.assertFalse(osv_scanner_gate.is_manifest_file("README.md"))
        self.assertFalse(osv_scanner_gate.is_manifest_file(".gitignore"))

    def test_calculate_cvss3_score(self):
        # CVSS 3.1 vector calculation
        vector = "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:L"
        score = osv_scanner_gate.calculate_cvss3_score(vector)
        self.assertEqual(score, 5.4)

        # High severity vector
        high_vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        high_score = osv_scanner_gate.calculate_cvss3_score(high_vector)
        self.assertEqual(high_score, 9.8)

    def test_parse_vulnerabilities(self):
        sample_json = {
            "results": [
                {
                    "source": {"path": "composer.lock", "type": "lockfile"},
                    "packages": [
                        {
                            "package": {
                                "name": "laravel/framework",
                                "version": "10.0.0",
                                "ecosystem": "Packagist",
                            },
                            "vulnerabilities": [
                                {
                                    "id": "GHSA-5wcm-3v2w-8362",
                                    "summary": "Improper Input Validation in Laravel",
                                    "severity": [{"type": "CVSS_V3", "score": 6.5}],
                                },
                                {
                                    "id": "GHSA-f9x3-7vq9-cph6",
                                    "summary": "Remote Code Execution",
                                    "severity": [{"type": "CVSS_V3", "score": 9.2}],
                                },
                            ],
                        }
                    ],
                }
            ]
        }

        # Scan all (min_severity = 0.0)
        vulns = osv_scanner_gate.parse_vulnerabilities(sample_json, min_severity=0.0)
        self.assertEqual(len(vulns), 2)
        self.assertEqual(vulns[0]["id"], "GHSA-5wcm-3v2w-8362")
        self.assertEqual(vulns[0]["package"], "laravel/framework")
        self.assertEqual(vulns[0]["cvss"], 6.5)
        self.assertEqual(vulns[0]["url"], "https://osv.dev/GHSA-5wcm-3v2w-8362")

        # Scan with min_severity = 7.0 (should filter out 6.5)
        vulns_filtered = osv_scanner_gate.parse_vulnerabilities(sample_json, min_severity=7.0)
        self.assertEqual(len(vulns_filtered), 1)
        self.assertEqual(vulns_filtered[0]["id"], "GHSA-f9x3-7vq9-cph6")
        self.assertEqual(vulns_filtered[0]["cvss"], 9.2)

    def test_format_table(self):
        vulns = [
            {
                "id": "GHSA-1234",
                "package": "axios",
                "version": "0.21.1",
                "ecosystem": "npm",
                "cvss": 7.5,
                "url": "https://osv.dev/GHSA-1234",
            }
        ]
        table = osv_scanner_gate.format_table(vulns)
        self.assertIn("GHSA-1234", table)
        self.assertIn("axios", table)
        self.assertIn("7.5", table)
        self.assertIn("https://osv.dev/GHSA-1234", table)

    @patch("shutil.which", return_value=None)
    def test_main_missing_binary(self, mock_which):
        with patch("sys.argv", ["osv-scanner-gate"]):
            with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                code = osv_scanner_gate.main()
                self.assertEqual(code, 2)
                self.assertIn("'osv-scanner' binary not found", mock_stderr.getvalue())

    @patch("shutil.which", return_value="/usr/bin/osv-scanner")
    @patch("osv_scanner_gate.get_git_staged_files", return_value=["src/App.vue", "docs/README.md"])
    def test_main_staged_no_manifest_skipped(self, mock_git, mock_which):
        with patch("sys.argv", ["osv-scanner-gate", "--staged"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                code = osv_scanner_gate.main()
                self.assertEqual(code, 0)
                self.assertIn("No dependency manifests or lockfiles staged", mock_stdout.getvalue())

    @patch("shutil.which", return_value="/usr/bin/osv-scanner")
    @patch("osv_scanner_gate.get_git_staged_files", return_value=["composer.lock"])
    @patch("osv_scanner_gate.run_osv_scan")
    def test_main_staged_clean_scan(self, mock_scan, mock_git, mock_which):
        mock_scan.return_value = (0, {"results": []}, "")
        with patch("sys.argv", ["osv-scanner-gate", "--staged"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                code = osv_scanner_gate.main()
                self.assertEqual(code, 0)
                self.assertIn("Zero known vulnerabilities found", mock_stdout.getvalue())

    @patch("shutil.which", return_value="/usr/bin/osv-scanner")
    @patch("osv_scanner_gate.get_git_staged_files", return_value=["composer.lock"])
    @patch("osv_scanner_gate.run_osv_scan")
    def test_main_staged_vulnerabilities_found(self, mock_scan, mock_git, mock_which):
        mock_scan.return_value = (
            1,
            {
                "results": [
                    {
                        "source": {"path": "composer.lock"},
                        "packages": [
                            {
                                "package": {"name": "test-pkg", "version": "1.0.0", "ecosystem": "npm"},
                                "vulnerabilities": [
                                    {"id": "GHSA-test-123", "severity": [{"score": 8.0}], "summary": "Test Vuln"}
                                ],
                            }
                        ],
                    }
                ]
            },
            "",
        )
        with patch("sys.argv", ["osv-scanner-gate", "--staged"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                code = osv_scanner_gate.main()
                self.assertEqual(code, 1)
                self.assertIn("Found 1 vulnerability(ies)", mock_stdout.getvalue())
                self.assertIn("GHSA-test-123", mock_stdout.getvalue())

    @patch("shutil.which", return_value="/usr/bin/osv-scanner")
    @patch("osv_scanner_gate.run_osv_scan")
    def test_main_json_output(self, mock_scan, mock_which):
        mock_scan.return_value = (0, {"results": []}, "")
        with patch("sys.argv", ["osv-scanner-gate", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                code = osv_scanner_gate.main()
                self.assertEqual(code, 0)
                data = json.loads(mock_stdout.getvalue())
                self.assertEqual(data["status"], "passed")
                self.assertEqual(data["vulnerabilities_count"], 0)


if __name__ == "__main__":
    unittest.main()
