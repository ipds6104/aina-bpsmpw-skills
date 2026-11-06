"""
Unit & Integration Tests for Zero-Mock Static Detector.
Verifies detection accuracy, repo-level debt ledger exemptions, and false-positive prevention.
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from detector import ZeroMockDetector
from rules import Severity

class TestZeroMockDetector(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mock_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def write_file(self, rel_path: str, content: str):
        full = Path(self.test_dir) / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)

    def test_clean_production_code_passes(self):
        self.write_file("src/service.py", """
import asyncpg

async def get_user(pool, user_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        self.assertEqual(len(findings), 0)

    def test_mock_framework_import_detected_in_production(self):
        self.write_file("src/client.py", """
from unittest.mock import MagicMock

def execute_call():
    return MagicMock()
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        self.assertTrue(any(f.rule_id == "MOCK_IMPORT_PY" and f.severity == Severity.CRITICAL for f in findings))

    def test_fake_latency_detected_in_service(self):
        self.write_file("src/user_service.py", """
import time

def fetch_external_records():
    time.sleep(0.5)
    return []
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        self.assertTrue(any(f.rule_id == "RULE_FAKE_LATENCY" for f in findings))

    def test_stubbed_code_detected(self):
        self.write_file("src/handler.py", """
def handle():
    raise NotImplementedError("mock stub")
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        self.assertTrue(any(f.rule_id == "RULE_STUBBED_CODE" for f in findings))

    def test_mock_bypass_flag_detected(self):
        self.write_file("src/auth.ts", """
export function getJwt() {
    if (process.env.NODE_ENV === 'test') {
        return "mock_token_123";
    }
    return realAuth();
}
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        self.assertTrue(any(f.rule_id == "RULE_MOCK_BYPASS_FLAG" for f in findings))

    def test_mocks_in_test_directory_are_allowed(self):
        self.write_file("tests/auth_test.py", """
from unittest.mock import MagicMock
import time

def test_something():
    mock = MagicMock()
    time.sleep(0.01)
    assert mock is not None
""")
        self.write_file("tests/repo_test.rs", """
use mockall::predicate::*;

#[test]
fn test_mock_call() {
    todo!("allow in tests");
}
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        self.assertEqual(len(findings), 0, "Test directories must be allowed to use mocks without violations")

    def test_rationalizing_comment_detected(self):
        self.write_file("src/gateway.py", """
def connect_upstream():
    # assume success for now
    return True
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        self.assertTrue(any(f.rule_id == "RULE_RATIONALIZING_COMMENT" for f in findings))

    def test_agent_note_pollution_detected(self):
        self.write_file("src/notes.md", "# Scratchpad for LLM agent")
        self.write_file("src/temp_test.py", "print('temp')")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        pollution_findings = [f for f in findings if f.rule_id == "RULE_AGENT_NOTE_POLLUTION"]
        self.assertEqual(len(pollution_findings), 2)

    def test_repo_ledger_json_exemption(self):
        # Create a stub that would normally be flagged
        self.write_file("src/driver.py", """
def sceAgcDriverSpecialOwner(param):
    raise NotImplementedError("mock stub")
""")
        # Create repo-level allowlist JSON
        self.write_file(".zero-mock-allowlist.json", json.dumps({
            "exemptions": [
                {
                    "symbol": "sceAgcDriverSpecialOwner",
                    "file": "src/driver.py",
                    "reason": "Hardware register unmeasured on consumer silicon",
                    "citation": "Issue #1234 / AMD RDNA2 ISA Table 24"
                }
            ]
        }))

        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        self.assertIn("sceAgcDriverSpecialOwner", detector.debt_ledger)
        findings = detector.scan()
        self.assertFalse(any(f.symbol_name == "sceAgcDriverSpecialOwner" for f in findings))

    def test_repo_ledger_markdown_exemption(self):
        self.write_file("src/hw.py", """
def scePadUnknownLotus(handle):
    raise NotImplementedError("mock stub")
""")
        # Create repo-level markdown technical debt ledger
        self.write_file("docs/TECHNICAL_DEBT.md", """
# Technical Debt Ledger

### Silent stubs
- `scePadUnknownLotus`: unmeasured DualSense extension register (Citation: PS5 Firmware 13.60 measurements)
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        self.assertIn("scePadUnknownLotus", detector.debt_ledger)
        findings = detector.scan()
        self.assertFalse(any(f.symbol_name == "scePadUnknownLotus" for f in findings))

    def test_incode_annotation_exemption(self):
        self.write_file("src/display.py", """
# @allow-stub: Fallback display timing (citation: RFC-8594 Section 3)
def sync_frame():
    raise NotImplementedError("mock stub")
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        self.assertFalse(any(f.rule_id == "RULE_STUBBED_CODE" for f in findings))

    def test_detector_self_scan_false_positive_prevention(self):
        # Tools, analyzers, and regex/message definitions should not trigger false positives
        self.write_file("src/analyzer.py", """
class MockScannerDetector:
    def __init__(self):
        self.desc = "Production code contains stubbed todo!() / unimplemented!() logic"
        self.msg = "Production code contains mock bypass flag (e.g. NODE_ENV === 'test' or MOCK_ENABLED)"
""")
        detector = ZeroMockDetector(self.test_dir, use_codegraph=False)
        findings = detector.scan()
        self.assertEqual(len(findings), 0)

if __name__ == "__main__":
    unittest.main()
