#!/usr/bin/env python3
"""Hermetic unit tests for arc42-lint with Git Provenance & Drift Analysis."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util
spec = importlib.util.spec_from_file_location("arc42_lint", SCRIPTS_DIR / "arc42-lint.py")
arc42_lint = importlib.util.module_from_spec(spec)
sys.modules["arc42_lint"] = arc42_lint
spec.loader.exec_module(arc42_lint)


class TestArc42LintHermetic(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.docs_dir = Path(self.temp_dir.name) / "docs" / "architecture"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.lang_en = arc42_lint.load_language("en", SCRIPTS_DIR / "arc42-lint.py")
        self.lang_id = arc42_lint.load_language("id", SCRIPTS_DIR / "arc42-lint.py")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_provenance_from_frontmatter(self):
        content = """---
arc42_section: 5
title: Building Block View
verified_commit: a1b2c3d4e5f6
verified_timestamp: 2026-10-25T18:00:00+07:00
branch: main
tracked_paths:
  - src/auth
  - src/gateway
---
# 5. Building Block View
"""
        prov = arc42_lint.extract_provenance(content, 5, "05_building_block_view.md")
        self.assertEqual(prov.verified_commit, "a1b2c3d4e5f6")
        self.assertEqual(prov.verified_timestamp, "2026-10-25T18:00:00+07:00")
        self.assertEqual(prov.branch, "main")
        self.assertEqual(prov.tracked_paths, ["src/auth", "src/gateway"])

    def test_extract_provenance_from_callout_block(self):
        content = """# 1. Introduction and Goals

> [!INFO] **Architecture Provenance & Freshness**
> - **Verified Commit**: `61d68c8`
> - **Verified Timestamp**: `2026-10-25T17:30:00Z`
> - **Tracked Paths**: `src/`, `crates/`
"""
        prov = arc42_lint.extract_provenance(content, 1, "01_introduction_and_goals.md")
        self.assertEqual(prov.verified_commit, "61d68c8")
        self.assertEqual(prov.verified_timestamp, "2026-10-25T17:30:00Z")
        self.assertEqual(prov.tracked_paths, ["src/", "crates/"])

    def test_extract_provenance_from_html_comment(self):
        content = """# 3. Context and Scope
<!-- provenance: commit=fedcba987654 timestamp=2026-10-20 branch=feature/auth -->
"""
        prov = arc42_lint.extract_provenance(content, 3, "03_context_and_scope.md")
        self.assertEqual(prov.verified_commit, "fedcba987654")
        self.assertEqual(prov.verified_timestamp, "2026-10-20")
        self.assertEqual(prov.branch, "feature/auth")

    def test_rule6_provenance_missing_triggers_warning_or_error(self):
        sec1 = self.docs_dir / "01_introduction_and_goals.md"
        sec1.write_text("# 1. Introduction and Goals\nNo provenance here.\n")

        data = arc42_lint.load_docs(self.docs_dir, self.lang_en)
        issues_warn = arc42_lint.rule_provenance_metadata(data, require_provenance=False)
        self.assertEqual(len(issues_warn), 1)
        self.assertEqual(issues_warn[0].rule, "RULE-6")
        self.assertEqual(issues_warn[0].severity, "warning")

        issues_err = arc42_lint.rule_provenance_metadata(data, require_provenance=True)
        self.assertEqual(len(issues_err), 1)
        self.assertEqual(issues_err[0].severity, "error")

    def test_numbered_files_and_interface_consistency_rule1(self):
        # Section 3 defines IF-01
        sec3 = self.docs_dir / "03_context_and_scope.md"
        sec3.write_text("""# 3. Context and Scope
| Interface ID | Partner | What Goes In | What Goes Out |
|---|---|---|---|
| IF-01 | Client Web | HTTP Request | HTTP Response |
""")
        # Section 5 references IF-01 and an extra IF-02
        sec5 = self.docs_dir / "05_building_block_view.md"
        sec5.write_text("""# 5. Building Block View
| Component | Responsibility | Interfaces |
|---|---|---|
| GatewayService | API Routing | IF-01, IF-02 |
""")
        data = arc42_lint.load_docs(self.docs_dir, self.lang_en)
        issues = arc42_lint.rule_interface_consistency(data)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule, "RULE-1")
        self.assertIn("IF-02", issues[0].message)

    def test_git_drift_and_staleness_detection(self):
        # Initialize a temporary git repository
        repo_root = Path(self.temp_dir.name)
        subprocess.check_call(["git", "-C", str(repo_root), "init", "-q"])
        subprocess.check_call(["git", "-C", str(repo_root), "config", "user.email", "agent@test.local"])
        subprocess.check_call(["git", "-C", str(repo_root), "config", "user.name", "Agent"])

        # Create an initial commit
        readme = repo_root / "README.md"
        readme.write_text("# Test Repo")
        subprocess.check_call(["git", "-C", str(repo_root), "add", "README.md"])
        subprocess.check_call(["git", "-C", str(repo_root), "commit", "-m", "Initial commit", "-q"])

        initial_commit = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"]
        ).decode().strip()

        # Write doc referencing initial commit
        sec1 = self.docs_dir / "01_introduction_and_goals.md"
        sec1.write_text(f"""---
arc42_section: 1
verified_commit: {initial_commit}
verified_timestamp: 2026-10-25T18:00:00Z
tracked_paths:
  - README.md
---
# 1. Introduction and Goals
""")

        # When at HEAD (distance 0)
        data = arc42_lint.load_docs(self.docs_dir, self.lang_en)
        arc42_lint.run_drift_analysis(data, repo_root, drift_threshold=5, max_age_days=30)
        self.assertEqual(data.provenance_by_section[1].drift_status, "fresh")
        self.assertEqual(data.provenance_by_section[1].commit_distance, 0)

        # Make 6 commits to exceed drift threshold of 5
        for i in range(6):
            readme.write_text(f"Update {i}")
            subprocess.check_call(["git", "-C", str(repo_root), "commit", "-am", f"Update {i}", "-q"])

        # Re-run drift analysis
        data = arc42_lint.load_docs(self.docs_dir, self.lang_en)
        arc42_lint.run_drift_analysis(data, repo_root, drift_threshold=5, max_age_days=30)
        self.assertEqual(data.provenance_by_section[1].drift_status, "drifting")
        self.assertEqual(data.provenance_by_section[1].commit_distance, 6)
        self.assertIn("README.md", data.provenance_by_section[1].changed_tracked_files)

        drift_issues = arc42_lint.rule_architecture_drift(data, drift_threshold=5, max_age_days=30)
        self.assertTrue(any("has drifted: 6 commits behind" in i.message for i in drift_issues))
        self.assertTrue(any("source drift" in i.message for i in drift_issues))

    def test_json_output_format(self):
        sec1 = self.docs_dir / "01_introduction_and_goals.md"
        sec1.write_text("""---
verified_commit: a1b2c3d4
verified_timestamp: 2026-10-25T18:00:00Z
---
# 1. Introduction and Goals
""")
        data = arc42_lint.load_docs(self.docs_dir, self.lang_en)
        issues = arc42_lint.run_all_rules(data, check_drift=False)
        json_str = arc42_lint.format_json(issues, data, self.docs_dir, "English")
        parsed = json.loads(json_str)
        self.assertIn("summary", parsed)
        self.assertIn("provenance", parsed)
        self.assertIn("issues", parsed)
        self.assertEqual(parsed["summary"]["total_sections_detected"], 1)
        self.assertEqual(parsed["provenance"]["01"]["verified_commit"], "a1b2c3d4")

    def test_indonesian_language_detection(self):
        sec1 = self.docs_dir / "01_pengantar_dan_tujuan.md"
        sec1.write_text("""---
verified_commit: c1d2e3f4
verified_timestamp: 2026-10-25T18:00:00Z
---
# 1. Pendahuluan dan Tujuan
""")
        data = arc42_lint.load_docs(self.docs_dir, self.lang_id)
        self.assertIn(1, data.provenance_by_section)

    def test_rule8_staged_source_drift(self):
        sec5 = self.docs_dir / "05_building_block_view.md"
        sec5.write_text("""---
arc42_section: 5
verified_commit: 11223344
verified_timestamp: 2026-10-25T18:00:00Z
tracked_paths:
  - src/auth
---
# 5. Building Block View
""")
        data = arc42_lint.load_docs(self.docs_dir, self.lang_en)
        # Case 1: Staged file modifies tracked path 'src/auth/handler.rs', but doc is not staged
        staged = ["src/auth/handler.rs"]
        issues = arc42_lint.rule_staged_source_drift(
            data, staged, Path(self.temp_dir.name), drift_threshold=5, strict_staged=True
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule, "RULE-8")
        self.assertEqual(issues[0].severity, "error")
        self.assertIn("src/auth/handler.rs", issues[0].message)

        # Case 2: Doc is also staged -> no issue
        rel_doc = str(sec5.relative_to(Path(self.temp_dir.name)))
        staged_with_doc = ["src/auth/handler.rs", rel_doc]
        issues_ok = arc42_lint.rule_staged_source_drift(
            data, staged_with_doc, Path(self.temp_dir.name), drift_threshold=5, strict_staged=True
        )
        self.assertEqual(len(issues_ok), 0)

    def test_install_pre_commit_hook(self):
        repo_root = Path(self.temp_dir.name)
        subprocess.check_call(["git", "-C", str(repo_root), "init", "-q"])
        res = arc42_lint.install_hook(repo_root)
        self.assertEqual(res, 0)

        hook_file = repo_root / ".git" / "hooks" / "pre-commit"
        self.assertTrue(hook_file.exists())
        self.assertTrue(os.access(hook_file, os.X_OK))
        content = hook_file.read_text()
        self.assertIn("arc42-lint --pre-commit", content)
        self.assertIn("SKIP_ARC42_LINT", content)


if __name__ == "__main__":
    unittest.main()
