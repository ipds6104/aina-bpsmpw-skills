#!/usr/bin/env python3
"""arc42 cross-section consistency, git provenance, drift & pre-commit linter.

Usage:
    arc42-lint [docs_path] [--lang LANG] [--format text|github|json] [--json]
                           [--strict] [--check-drift] [--drift-threshold N]
                           [--max-age-days DAYS] [--require-provenance]
                           [--pre-commit] [--install-hook [REPO_PATH]]

Commands:
    arc42-lint                    Audit architecture documents in docs/architecture
    arc42-lint --pre-commit       Run pre-commit gate (checks staged files & drift thresholds)
    arc42-lint --install-hook     Install pre-commit hook into current git repository (.git/hooks/pre-commit)

Rules:
    RULE-1  Section 3 ↔ Section 5: Interface IDs (IF-xx)
    RULE-2  Section 5 ↔ Section 7: Building block deployment coverage
    RULE-3  Section 1 ↔ Section 10: Quality goal tag coverage (Q42)
    RULE-4  Section 9 ↔ Section 11: ADR risk references (RISK-xx)
    RULE-5  Section 10 ↔ Section 11: Aspirational scenario traceability
    RULE-6  Architecture Provenance: Commit SHA & timestamp presence
    RULE-7  Architecture Drift: Git commit distance & staleness verification
    RULE-8  Staged Implementation Drift: Staged source files modified without doc updates

Exit codes:
    0  no issues (or only warnings in non-strict mode)
    1  one or more errors found (or warnings with --strict / --pre-commit)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Language loading
# ---------------------------------------------------------------------------

def load_language(lang_code: str, script_path: Path) -> dict:
    """Load language definition from languages/{lang_code}.json."""
    lang_dir = script_path.parent / "languages"
    lang_file = lang_dir / f"{lang_code}.json"

    if not lang_file.exists():
        available = sorted(p.stem for p in lang_dir.glob("*.json")) if lang_dir.exists() else []
        print(f"arc42-lint: language '{lang_code}' not found.", file=sys.stderr)
        if available:
            print(f"  Available languages: {', '.join(available)}", file=sys.stderr)
        else:
            print(f"  No language files found in {lang_dir}", file=sys.stderr)
            print("  Make sure the languages/ directory is present alongside scripts/", file=sys.stderr)
        sys.exit(1)

    with open(lang_file, encoding="utf-8") as f:
        return json.load(f)


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Return True if text matches any pattern (case-insensitive regex)."""
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)


def _section_from_number(heading_text: str) -> int | None:
    """Detect section from numeric prefix of a heading (1–12)."""
    m = re.match(r"^(\d+)[.\s:]", heading_text.strip())
    if m:
        num = int(m.group(1))
        if 1 <= num <= 12:
            return num
    return None


def _section_from_keyword(heading_text: str, section_keywords: dict) -> int | None:
    """Detect section from language-specific keyword patterns."""
    for sec_str, patterns in section_keywords.items():
        if _matches_any(heading_text, patterns):
            return int(sec_str)
    return None


def detect_section(path: Path, content: str, lang: dict) -> int | None:
    """Return the arc42 section number for a file, or None if undetermined.

    Detection order:
      1. Numeric digits in filename stem (e.g. '01_intro.md', 'section-05.md')
      2. Numeric prefix in the first heading
      3. Keyword match in the first heading
    """
    m = re.search(r"(?<!\d)(1[0-2]|0?[1-9])(?!\d)", path.stem)
    if m:
        return int(m.group(1))

    for hm in _HEADING_RE.finditer(content):
        heading = hm.group(1)
        num = _section_from_number(heading)
        if num is not None:
            return num
        num = _section_from_keyword(heading, lang["section_keywords"])
        if num is not None:
            return num

    return None


def split_monolithic(content: str, path: Path, lang: dict) -> list[tuple[int, str, Path]]:
    """Split a monolithic arc42 file into (section_num, content_slice, path) windows."""
    lines = content.splitlines(keepends=True)
    segments: list[tuple[int, list[str], Path]] = []
    current_sec: int | None = None
    current_lines: list[str] = []

    for line in lines:
        m = re.match(r"^(#{1,2})\s+(.+)$", line)
        if m:
            heading = m.group(2)
            sec = _section_from_number(heading)
            if sec is None:
                sec = _section_from_keyword(heading, lang["section_keywords"])
            if sec is not None:
                if current_sec is not None:
                    segments.append((current_sec, current_lines, path))
                current_sec = sec
                current_lines = [line]
                continue
        current_lines.append(line)

    if current_sec is not None:
        segments.append((current_sec, current_lines, path))

    return [(sec, "".join(lines_), p) for sec, lines_, p in segments]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class SectionProvenance:
    section: int
    file_path: str
    verified_commit: str | None = None
    verified_timestamp: str | None = None
    branch: str = "main"
    tracked_paths: list[str] = field(default_factory=list)
    commit_distance: int | None = None
    days_old: int | None = None
    changed_tracked_files: list[str] = field(default_factory=list)
    drift_status: str = "unknown"  # "fresh" | "drifting" | "stale" | "unverified" | "error"


@dataclass
class SectionData:
    sec1_quality_tags:    set[str]            = field(default_factory=set)
    sec3_interfaces:      dict[str, int]       = field(default_factory=dict)
    sec5_interfaces:      dict[str, int]       = field(default_factory=dict)
    sec5_component_names: set[str]             = field(default_factory=set)
    sec7_content:         str | None           = None
    sec7_path:            str                  = ""
    sec9_adr_risks:       dict[str, list[str]] = field(default_factory=dict)
    sec10_quality_tags:   dict[str, str]       = field(default_factory=dict)
    sec10_aspirational:   set[str]             = field(default_factory=set)
    sec11_risks:          set[str]             = field(default_factory=set)
    sec11_content:        str                  = ""
    sec11_path:           str                  = ""
    sec1_path:  str = ""
    sec3_path:  str = ""
    sec5_path:  str = ""
    sec9_path:  str = ""
    sec10_path: str = ""
    provenance_by_section: dict[int, SectionProvenance] = field(default_factory=dict)


@dataclass
class LintIssue:
    rule:     str
    severity: str   # "error" | "warning"
    file:     str
    line:     int   # -1 if not line-specific
    message:  str


# ---------------------------------------------------------------------------
# Provenance Extractor
# ---------------------------------------------------------------------------

def extract_provenance(content: str, sec_num: int, file_path: str) -> SectionProvenance:
    """Extract provenance metadata from frontmatter, callout block, or HTML comment."""
    prov = SectionProvenance(section=sec_num, file_path=file_path)

    # 1. Frontmatter YAML check
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            m_commit = re.search(r"^\s*verified_commit:\s*['\"]?([a-fA-F0-9]+)['\"]?", fm, re.MULTILINE)
            if m_commit:
                prov.verified_commit = m_commit.group(1).strip()
            m_time = re.search(r"^\s*verified_timestamp:\s*['\"]?([^'\"\n]+)['\"]?", fm, re.MULTILINE)
            if m_time:
                prov.verified_timestamp = m_time.group(1).strip()
            m_branch = re.search(r"^\s*branch:\s*['\"]?([^'\"\n]+)['\"]?", fm, re.MULTILINE)
            if m_branch:
                prov.branch = m_branch.group(1).strip()

            m_paths = re.search(r"tracked_paths:\s*\n((?:\s*-\s*[^\n]+\n?)+)", fm)
            if m_paths:
                for line in m_paths.group(1).splitlines():
                    path_str = re.sub(r"^\s*-\s*", "", line).strip().strip("'\"")
                    if path_str:
                        prov.tracked_paths.append(path_str)

    # 2. Blockquote / Callout / Markdown Header check (e.g. '> - **Verified Commit**: `61d68c8`')
    if not prov.verified_commit:
        m_commit = re.search(
            r"(?:\*{1,2}|_{1,2})?(?:Verified Commit|commit_id|commit_sha)(?:\*{1,2}|_{1,2})?\s*[:=]\s*[`'\"]?([a-fA-F0-9]{6,40})[`'\"]?",
            content,
            re.IGNORECASE,
        )
        if m_commit:
            prov.verified_commit = m_commit.group(1).strip()

    if not prov.verified_timestamp:
        m_time = re.search(
            r"(?:\*{1,2}|_{1,2})?(?:Verified Timestamp|verified_at|verified_date|timestamp)(?:\*{1,2}|_{1,2})?\s*[:=]\s*[`'\"]?([0-9T:+\-Z]+|(?:\d{4}-\d{2}-\d{2}))[`'\"]?",
            content,
            re.IGNORECASE,
        )
        if m_time:
            prov.verified_timestamp = m_time.group(1).strip()

    if not prov.tracked_paths:
        m_paths = re.search(
            r"(?:\*{1,2}|_{1,2})?(?:Tracked Paths?|tracked_sources?)(?:\*{1,2}|_{1,2})?\s*[:=]\s*([^\n]+)",
            content,
            re.IGNORECASE,
        )
        if m_paths:
            raw_paths = m_paths.group(1).strip()
            for p in raw_paths.split(","):
                cleaned = p.strip().strip("`'\" \t")
                if cleaned:
                    prov.tracked_paths.append(cleaned)

    # 3. HTML comment check <!-- provenance: commit=... timestamp=... -->
    if not prov.verified_commit or not prov.verified_timestamp:
        m_html = re.search(r"<!--\s*provenance:\s*(.+?)\s*-->", content, re.IGNORECASE)
        if m_html:
            params = m_html.group(1)
            mc = re.search(r"commit=([a-fA-F0-9]{6,40})", params)
            if mc and not prov.verified_commit:
                prov.verified_commit = mc.group(1)
            mt = re.search(r"timestamp=([0-9T:+\-Z]+|\d{4}-\d{2}-\d{2})", params)
            if mt and not prov.verified_timestamp:
                prov.verified_timestamp = mt.group(1)
            mb = re.search(r"branch=([^\s]+)", params)
            if mb and prov.branch == "main":
                prov.branch = mb.group(1)

    return prov


# ---------------------------------------------------------------------------
# Extractors for Standard arc42 Rules
# ---------------------------------------------------------------------------

def _line_of(content: str, match_start: int) -> int:
    return content.count("\n", 0, match_start) + 1


def extract_sec1_quality_tags(content: str) -> set[str]:
    """Q42 tags from the Section 1.2 quality goals table."""
    tags: set[str] = set()
    for m in re.finditer(r"^\|\s*\d+\s*\|\s*(#\w+)", content, re.MULTILINE):
        tags.add(m.group(1))
    return tags


def extract_sec3_interfaces(content: str) -> dict[str, int]:
    """IF-xx IDs from Section 3 interface table."""
    result: dict[str, int] = {}
    for m in re.finditer(r"^\|\s*(IF-\d+)\s*\|", content, re.MULTILINE):
        if_id = m.group(1)
        if if_id not in result:
            result[if_id] = _line_of(content, m.start())
    return result


def extract_sec5_data(content: str, lang: dict) -> tuple[dict[str, int], set[str]]:
    """IF-xx IDs and component names from Section 5 building block table."""
    interfaces: dict[str, int] = {}
    names: set[str] = set()
    header_names = lang["patterns"]["section5_header_names"]

    in_bb_table = False
    for line_num, line in enumerate(content.splitlines(), start=1):
        if not line.strip().startswith("|"):
            if in_bb_table:
                in_bb_table = False
            continue

        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3:
            continue

        name_cell = cells[0]
        iface_cell = cells[2]

        if re.match(r"^[-:\s]+$", name_cell):
            continue

        if _matches_any(name_cell, header_names):
            in_bb_table = True
            continue

        if not in_bb_table or not name_cell:
            continue

        names.add(name_cell)
        for if_id in re.findall(r"IF-\d+", iface_cell):
            if if_id not in interfaces:
                interfaces[if_id] = line_num

    return interfaces, names


def extract_sec9_adr_risks(content: str, lang: dict) -> dict[str, list[str]]:
    """Map ADR_ID → [RISK_IDs] from Section 9 ADR Implications blocks."""
    result: dict[str, list[str]] = {}
    current_adr: str | None = None
    risks_labels = lang["patterns"]["risks_created_label"]

    for line in content.splitlines():
        heading_m = re.match(r"^#{1,3}\s+(.+)$", line)
        if heading_m:
            adr_m = re.search(r"(ADR-\d+)", heading_m.group(1))
            if adr_m:
                current_adr = adr_m.group(1)
                result.setdefault(current_adr, [])
            else:
                current_adr = None
            continue

        if current_adr and _matches_any(line, risks_labels):
            result[current_adr].extend(re.findall(r"RISK-\d+", line))

    return result


def extract_sec10_data(content: str, lang: dict) -> tuple[dict[str, str], set[str]]:
    """Extract quality tags and aspirational scenario IDs from Section 10."""
    quality_tags: dict[str, str] = {}
    aspirational: set[str] = set()
    quality_prop_labels = lang["patterns"]["quality_property_label"]
    not_measured_values = lang["patterns"]["not_measured"]

    current_qs: str | None = None
    for line in content.splitlines():
        qs_match = re.match(r"^#{1,4}\s+(QS-\d+)\s*:", line)
        if qs_match:
            current_qs = qs_match.group(1)
            continue

        if re.search(r"[├└│]", line) and current_qs is None:
            tree_match = re.search(r"\b(QS-\d+)\s*:", line)
            if tree_match:
                current_qs = tree_match.group(1)

        if current_qs and _matches_any(line, quality_prop_labels):
            tag_m = re.search(r"(#\w+)", line)
            if tag_m:
                quality_tags[current_qs] = tag_m.group(1)

        asp_row = re.match(r"^\|\s*(QS-\d+)\s*\|([^|]*)\|\s*([^|]+)\|", line)
        if asp_row:
            current_state = asp_row.group(3).strip()
            if _matches_any(current_state, not_measured_values):
                aspirational.add(asp_row.group(1))

    return quality_tags, aspirational


def extract_sec11_risks(content: str) -> set[str]:
    """RISK-xx IDs from Section 11 risk matrix."""
    return set(re.findall(r"^\|\s*(RISK-\d+)\s*\|", content, re.MULTILINE))


# ---------------------------------------------------------------------------
# Document loader
# ---------------------------------------------------------------------------

def load_docs(docs_path: Path, lang: dict) -> SectionData:
    """Read all .md files under docs_path and populate SectionData."""
    data = SectionData()

    if docs_path.is_file() and docs_path.suffix.lower() == ".md":
        md_files = [docs_path]
    else:
        md_files = sorted(docs_path.rglob("*.md"))

    if not md_files:
        return data

    for path in md_files:
        content = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path)

        sec = detect_section(path, content, lang)
        windows: list[tuple[int, str, str]] = []

        if sec is not None:
            windows = [(sec, content, rel)]
        else:
            splits = split_monolithic(content, path, lang)
            if splits:
                windows = [(s, c, rel) for s, c, _ in splits]

        for sec_num, sec_content, src in windows:
            _populate(data, sec_num, sec_content, src, lang)

    return data


def _populate(data: SectionData, sec: int, content: str, src: str, lang: dict) -> None:
    prov = extract_provenance(content, sec, src)
    data.provenance_by_section[sec] = prov

    if sec == 1:
        data.sec1_quality_tags = extract_sec1_quality_tags(content)
        data.sec1_path = src
    elif sec == 3:
        data.sec3_interfaces = extract_sec3_interfaces(content)
        data.sec3_path = src
    elif sec == 5:
        data.sec5_interfaces, data.sec5_component_names = extract_sec5_data(content, lang)
        data.sec5_path = src
    elif sec == 7:
        data.sec7_content = content
        data.sec7_path = src
    elif sec == 9:
        data.sec9_adr_risks = extract_sec9_adr_risks(content, lang)
        data.sec9_path = src
    elif sec == 10:
        data.sec10_quality_tags, data.sec10_aspirational = extract_sec10_data(content, lang)
        data.sec10_path = src
    elif sec == 11:
        data.sec11_risks = extract_sec11_risks(content)
        data.sec11_content = content
        data.sec11_path = src


# ---------------------------------------------------------------------------
# Git Inspection & Drift Analysis
# ---------------------------------------------------------------------------

def find_git_toplevel(start_path: Path) -> Path | None:
    """Find the root of the git repository containing start_path."""
    try:
        cmd = ["git", "-C", str(start_path if start_path.is_dir() else start_path.parent), "rev-parse", "--show-toplevel"]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=5)
        root = Path(out.decode().strip())
        if root.exists():
            return root
    except Exception:
        pass
    return None


def get_staged_files(git_root: Path) -> list[str]:
    """Retrieve list of files currently staged for commit."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(git_root), "diff", "--cached", "--name-only"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return [f.strip() for f in out.decode().splitlines() if f.strip()]
    except Exception:
        return []


def _matches_tracked_path(file_path: str, tracked_paths: list[str]) -> bool:
    """Check if file_path falls under any tracked path pattern."""
    for tp in tracked_paths:
        tp_clean = tp.strip().rstrip("/")
        if not tp_clean:
            continue
        if file_path == tp_clean or file_path.startswith(tp_clean + "/"):
            return True
    return False


def run_drift_analysis(
    data: SectionData,
    git_root: Path | None,
    drift_threshold: int = 15,
    max_age_days: int = 30,
) -> None:
    """Inspect git history to calculate commit distance, age, and file drift for each section."""
    if not git_root:
        for prov in data.provenance_by_section.values():
            if prov.verified_commit and prov.verified_timestamp:
                prov.drift_status = "unverified"
            else:
                prov.drift_status = "untracked"
        return

    now_ts = int(time.time())

    for sec, prov in data.provenance_by_section.items():
        if not prov.verified_commit:
            prov.drift_status = "untracked"
            continue

        commit = prov.verified_commit

        # 1. Verify commit exists in repository
        try:
            subprocess.check_call(
                ["git", "-C", str(git_root), "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except subprocess.CalledProcessError:
            prov.drift_status = "error"
            continue

        # 2. Count commits behind HEAD
        try:
            out = subprocess.check_output(
                ["git", "-C", str(git_root), "rev-list", "--count", f"{commit}..HEAD"],
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            prov.commit_distance = int(out.decode().strip())
        except Exception:
            prov.commit_distance = None

        # 3. Calculate age in days from commit timestamp
        try:
            out = subprocess.check_output(
                ["git", "-C", str(git_root), "log", "-1", "--format=%ct", commit],
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            commit_ts = int(out.decode().strip())
            prov.days_old = max(0, (now_ts - commit_ts) // 86400)
        except Exception:
            prov.days_old = None

        # 4. Check changed files in tracked paths if specified
        if prov.tracked_paths:
            try:
                cmd = ["git", "-C", str(git_root), "diff", "--name-only", f"{commit}..HEAD", "--"] + prov.tracked_paths
                out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=5)
                changed = [f.strip() for f in out.decode().splitlines() if f.strip()]
                prov.changed_tracked_files = changed
            except Exception:
                pass

        # 5. Determine overall drift status
        is_stale = (prov.days_old is not None and prov.days_old > max_age_days)
        is_drifting = (
            (prov.commit_distance is not None and prov.commit_distance > drift_threshold)
            or bool(prov.changed_tracked_files)
        )

        if is_stale:
            prov.drift_status = "stale"
        elif is_drifting:
            prov.drift_status = "drifting"
        else:
            prov.drift_status = "fresh"


# ---------------------------------------------------------------------------
# Consistency, Drift & Pre-Commit Rules
# ---------------------------------------------------------------------------

def rule_interface_consistency(data: SectionData) -> list[LintIssue]:
    """Rule 1: IF-xx IDs must be identical in Section 3 and Section 5."""
    issues: list[LintIssue] = []

    if not data.sec3_interfaces and not data.sec5_interfaces:
        return issues

    if not data.sec3_interfaces:
        return [LintIssue("RULE-1", "warning", data.sec5_path, -1,
                          "Section 3 not found; cannot verify interface ID consistency with Section 5")]
    if not data.sec5_interfaces:
        return [LintIssue("RULE-1", "warning", data.sec3_path, -1,
                          "Section 5 not found; cannot verify interface ID consistency with Section 3")]

    for if_id in sorted(data.sec3_interfaces.keys() - data.sec5_interfaces.keys()):
        issues.append(LintIssue(
            "RULE-1", "error", data.sec3_path, data.sec3_interfaces[if_id],
            f"{if_id} defined in Section 3 but missing from Section 5 building blocks",
        ))
    for if_id in sorted(data.sec5_interfaces.keys() - data.sec3_interfaces.keys()):
        issues.append(LintIssue(
            "RULE-1", "error", data.sec5_path, data.sec5_interfaces[if_id],
            f"{if_id} referenced in Section 5 but not defined in Section 3 interface table",
        ))
    return issues


def rule_component_in_deployment(data: SectionData) -> list[LintIssue]:
    """Rule 2: Every Section 5 building block name must appear in Section 7."""
    issues: list[LintIssue] = []

    if not data.sec5_component_names:
        return issues

    if data.sec7_content is None:
        return [LintIssue("RULE-2", "warning", data.sec5_path, -1,
                          "Section 7 not found; cannot verify building block deployment coverage")]

    for name in sorted(data.sec5_component_names):
        pattern = r"\b" + re.escape(name) + r"\b"
        if not re.search(pattern, data.sec7_content, re.IGNORECASE):
            issues.append(LintIssue(
                "RULE-2", "error", data.sec5_path, -1,
                f'Building block "{name}" (Section 5) not found in Section 7 deployment view',
            ))
    return issues


def rule_quality_tag_coverage(data: SectionData) -> list[LintIssue]:
    """Rule 3: Every Q42 tag used in Section 10 must appear in Section 1.2 quality goals."""
    issues: list[LintIssue] = []

    if not data.sec10_quality_tags:
        return issues

    if not data.sec10_quality_tags:
        return issues

    if not data.sec1_quality_tags:
        return [LintIssue("RULE-3", "warning", data.sec10_path, -1,
                          "Section 1 not found; cannot verify quality tag coverage")]

    tags_in_10 = set(data.sec10_quality_tags.values())
    for tag in sorted(tags_in_10 - data.sec1_quality_tags):
        qs_ids = sorted(qs for qs, t in data.sec10_quality_tags.items() if t == tag)
        issues.append(LintIssue(
            "RULE-3", "error", data.sec10_path, -1,
            f"Q42 tag {tag} used in {', '.join(qs_ids)} (Section 10) but not present in Section 1.2 quality goals",
        ))
    return issues


def rule_adr_risks_in_register(data: SectionData) -> list[LintIssue]:
    """Rule 4: Every RISK-xx in a Section 9 ADR 'Risks created' must exist in Section 11."""
    issues: list[LintIssue] = []

    if not data.sec9_adr_risks:
        return issues

    if not data.sec11_risks and not data.sec11_content:
        return [LintIssue("RULE-4", "warning", data.sec9_path, -1,
                          "Section 11 not found; cannot verify ADR risk references")]

    for adr_id, risk_ids in sorted(data.sec9_adr_risks.items()):
        for risk_id in sorted(risk_ids):
            if risk_id not in data.sec11_risks:
                issues.append(LintIssue(
                    "RULE-4", "error", data.sec9_path, -1,
                    f"{risk_id} referenced in {adr_id} (Section 9 'Risks created') but not found in Section 11 risk matrix",
                ))
    return issues


def rule_aspirational_in_risks(data: SectionData) -> list[LintIssue]:
    """Rule 5: Every Section 10 aspirational scenario must be referenced in Section 11."""
    issues: list[LintIssue] = []

    if not data.sec10_aspirational:
        return issues

    if not data.sec11_content:
        return [LintIssue("RULE-5", "warning", data.sec10_path, -1,
                          "Section 11 not found; cannot verify aspirational scenario traceability")]

    for qs_id in sorted(data.sec10_aspirational):
        if qs_id not in data.sec11_content:
            issues.append(LintIssue(
                "RULE-5", "error", data.sec10_path, -1,
                f"Aspirational scenario {qs_id} (Section 10.3) not referenced in Section 11 risks/debt",
            ))
    return issues


def rule_provenance_metadata(data: SectionData, require_provenance: bool = False) -> list[LintIssue]:
    """Rule 6: Every arc42 section must record its verified commit and timestamp."""
    issues: list[LintIssue] = []
    sev = "error" if require_provenance else "warning"

    for sec, prov in sorted(data.provenance_by_section.items()):
        missing = []
        if not prov.verified_commit:
            missing.append("verified_commit")
        if not prov.verified_timestamp:
            missing.append("verified_timestamp")

        if missing:
            issues.append(LintIssue(
                "RULE-6", sev, prov.file_path, -1,
                f"Section {sec:02d} missing Architecture Provenance metadata: {', '.join(missing)}. "
                "Document freshness cannot be tracked.",
            ))
    return issues


def rule_architecture_drift(
    data: SectionData,
    drift_threshold: int = 15,
    max_age_days: int = 30,
) -> list[LintIssue]:
    """Rule 7: Flag architecture drift, stale documents, and invalid baseline commits."""
    issues: list[LintIssue] = []

    for sec, prov in sorted(data.provenance_by_section.items()):
        if not prov.verified_commit:
            continue

        if prov.drift_status == "error":
            issues.append(LintIssue(
                "RULE-7", "error", prov.file_path, -1,
                f"Section {sec:02d} references commit '{prov.verified_commit}' which does not exist in git history",
            ))
            continue

        if prov.drift_status == "stale":
            issues.append(LintIssue(
                "RULE-7", "warning", prov.file_path, -1,
                f"Section {sec:02d} is stale: last verified {prov.days_old} days ago (> {max_age_days}d threshold). "
                f"Baseline commit: {prov.verified_commit[:8]}",
            ))

        if prov.commit_distance is not None and prov.commit_distance > drift_threshold:
            issues.append(LintIssue(
                "RULE-7", "warning", prov.file_path, -1,
                f"Section {sec:02d} has drifted: {prov.commit_distance} commits behind HEAD (> {drift_threshold} threshold). "
                f"Baseline commit: {prov.verified_commit[:8]}",
            ))

        if prov.changed_tracked_files:
            sample = ", ".join(prov.changed_tracked_files[:3])
            more = f" (+{len(prov.changed_tracked_files) - 3} more)" if len(prov.changed_tracked_files) > 3 else ""
            issues.append(LintIssue(
                "RULE-7", "warning", prov.file_path, -1,
                f"Section {sec:02d} source drift: {len(prov.changed_tracked_files)} tracked source file(s) modified since verification ({sample}{more})",
            ))

    return issues


def rule_staged_source_drift(
    data: SectionData,
    staged_files: list[str],
    git_root: Path | None,
    drift_threshold: int = 15,
    max_age_days: int = 30,
    strict_staged: bool = False,
) -> list[LintIssue]:
    """Rule 8: Flag staged implementation changes that modify tracked paths without updating doc."""
    issues: list[LintIssue] = []
    if not staged_files or not git_root:
        return issues

    staged_set = set(staged_files)

    for sec, prov in sorted(data.provenance_by_section.items()):
        if not prov.tracked_paths:
            continue

        try:
            rel_doc = str(Path(prov.file_path).resolve().relative_to(git_root.resolve()))
        except Exception:
            rel_doc = prov.file_path

        doc_is_staged = rel_doc in staged_set or any(rel_doc.endswith(s) for s in staged_set)

        matching_staged: list[str] = []
        for sf in staged_files:
            if _matches_tracked_path(sf, prov.tracked_paths):
                matching_staged.append(sf)

        if matching_staged and not doc_is_staged:
            is_critical = (
                strict_staged
                or (prov.commit_distance is not None and prov.commit_distance >= drift_threshold)
                or (prov.days_old is not None and prov.days_old >= max_age_days)
            )
            sev = "error" if is_critical else "warning"
            sample = ", ".join(matching_staged[:3])
            more = f" (+{len(matching_staged) - 3} more)" if len(matching_staged) > 3 else ""
            issues.append(LintIssue(
                "RULE-8", sev, prov.file_path, -1,
                f"Section {sec:02d} implementation modified in staged commit ({sample}{more}) "
                f"but architecture document '{rel_doc}' is NOT staged for update. "
                f"Baseline commit: {prov.verified_commit[:8] if prov.verified_commit else 'missing'}",
            ))

    return issues


RULE_DESCRIPTIONS = {
    "RULE-1": "Section 3 ↔ Section 5  Interface IDs (IF-xx)",
    "RULE-2": "Section 5 ↔ Section 7  Building block deployment coverage",
    "RULE-3": "Section 1 ↔ Section 10 Quality goal tag coverage (Q42)",
    "RULE-4": "Section 9 ↔ Section 11 ADR risk references (RISK-xx)",
    "RULE-5": "Section 10 ↔ Section 11 Aspirational scenario traceability",
    "RULE-6": "Provenance Metadata   Commit SHA & timestamp tracking",
    "RULE-7": "Architecture Drift    Git baseline staleness & source drift",
    "RULE-8": "Staged Implementation Staged source files modified without doc update",
}


def run_all_rules(
    data: SectionData,
    require_provenance: bool = False,
    check_drift: bool = True,
    drift_threshold: int = 15,
    max_age_days: int = 30,
    staged_files: list[str] | None = None,
    git_root: Path | None = None,
    strict_staged: bool = False,
) -> list[LintIssue]:
    issues: list[LintIssue] = []
    issues.extend(rule_interface_consistency(data))
    issues.extend(rule_component_in_deployment(data))
    issues.extend(rule_quality_tag_coverage(data))
    issues.extend(rule_adr_risks_in_register(data))
    issues.extend(rule_aspirational_in_risks(data))
    issues.extend(rule_provenance_metadata(data, require_provenance=require_provenance))
    if check_drift:
        issues.extend(rule_architecture_drift(data, drift_threshold=drift_threshold, max_age_days=max_age_days))
    if staged_files and git_root:
        issues.extend(rule_staged_source_drift(
            data, staged_files, git_root,
            drift_threshold=drift_threshold,
            max_age_days=max_age_days,
            strict_staged=strict_staged,
        ))
    return issues


# ---------------------------------------------------------------------------
# Output Formatters
# ---------------------------------------------------------------------------

def format_text(issues: list[LintIssue], data: SectionData, docs_path: Path, lang_name: str) -> str:
    lines: list[str] = [f"arc42-lint: checking {docs_path} [{lang_name}]\n"]

    if data.provenance_by_section:
        lines.append("─" * 78)
        lines.append("Architecture Provenance & Staleness Overview:")
        lines.append(f"{'Sec':<4} {'File':<34} {'Commit':<10} {'Age':<8} {'Behind':<8} {'Status':<10}")
        lines.append("─" * 78)
        for sec, prov in sorted(data.provenance_by_section.items()):
            file_name = Path(prov.file_path).name[:33]
            commit_str = (prov.verified_commit[:8]) if prov.verified_commit else "missing"
            age_str = f"{prov.days_old}d" if prov.days_old is not None else "-"
            behind_str = f"{prov.commit_distance}c" if prov.commit_distance is not None else "-"
            status_str = prov.drift_status.upper()
            lines.append(f"{sec:<4} {file_name:<34} {commit_str:<10} {age_str:<8} {behind_str:<8} {status_str:<10}")
        lines.append("─" * 78)
        lines.append("")

    if not issues:
        lines.append(f"arc42-lint: no issues found — all consistency and provenance rules passed. [{lang_name}]")
        return "\n".join(lines)

    by_rule: dict[str, list[LintIssue]] = {}
    for issue in issues:
        by_rule.setdefault(issue.rule, []).append(issue)

    for rule_id in sorted(by_rule):
        desc = RULE_DESCRIPTIONS.get(rule_id, rule_id)
        lines.append(f"[{rule_id}] {desc}")
        for issue in by_rule[rule_id]:
            loc = f"{issue.file}:{issue.line}" if issue.line > 0 else issue.file
            lines.append(f"  [{issue.severity.upper()}] {loc}: {issue.message}")
        lines.append("")

    errors   = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    parts = []
    if errors:
        parts.append(f"{errors} error{'s' if errors != 1 else ''}")
    if warnings:
        parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")
    lines.append("Found " + ", ".join(parts))
    return "\n".join(lines)


def format_pre_commit(issues: list[LintIssue], data: SectionData, docs_path: Path) -> str:
    """Format an actionable pre-commit terminal report blocking commit."""
    lines = [
        "═" * 78,
        "🛑 [arc42 Pre-Commit Gate] Architecture Documentation Update Required!",
        "═" * 78,
        "The commit cannot proceed because architecture documentation has drifted",
        "past configured thresholds or source files were modified without doc updates:\n",
    ]

    by_file: dict[str, list[LintIssue]] = {}
    for issue in issues:
        by_file.setdefault(issue.file, []).append(issue)

    for f, iss in by_file.items():
        fname = Path(f).name
        lines.append(f"  📄 {fname} ({f}):")
        for i in iss:
            lines.append(f"     • [{i.rule}] {i.message}")
        lines.append("")

    lines.extend([
        "💡 Action Required:",
        "   1. Review and update the relevant architecture files in docs/architecture/",
        "   2. Update 'Verified Commit' to HEAD and bump 'Verified Timestamp'",
        "   3. Stage the documentation update: git add docs/architecture/",
        "",
        "ℹ️  To bypass this check in an emergency:",
        "   SKIP_ARC42_LINT=1 git commit -m '...'",
        "═" * 78,
    ])
    return "\n".join(lines)


def format_github(issues: list[LintIssue]) -> str:
    lines: list[str] = []
    for issue in issues:
        level = "error" if issue.severity == "error" else "warning"
        title = RULE_DESCRIPTIONS.get(issue.rule, issue.rule)
        loc_parts = []
        if issue.file:
            loc_parts.append(f"file={issue.file}")
        if issue.line > 0:
            loc_parts.append(f"line={issue.line}")
        loc_str = ("," + ",".join(loc_parts)) if loc_parts else ""
        lines.append(f"::{level}{loc_str} title={title}::{issue.message}")
    return "\n".join(lines)


def format_json(issues: list[LintIssue], data: SectionData, docs_path: Path, lang_name: str) -> str:
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")

    provenance_summary: dict[str, dict] = {}
    for sec, prov in sorted(data.provenance_by_section.items()):
        provenance_summary[f"{sec:02d}"] = {
            "section": sec,
            "file": prov.file_path,
            "verified_commit": prov.verified_commit,
            "verified_timestamp": prov.verified_timestamp,
            "branch": prov.branch,
            "commit_distance": prov.commit_distance,
            "days_old": prov.days_old,
            "changed_tracked_files": prov.changed_tracked_files,
            "drift_status": prov.drift_status,
        }

    out = {
        "summary": {
            "docs_path": str(docs_path),
            "language": lang_name,
            "total_sections_detected": len(data.provenance_by_section),
            "errors": errors,
            "warnings": warnings,
            "passed": errors == 0,
        },
        "provenance": provenance_summary,
        "issues": [
            {
                "rule": i.rule,
                "description": RULE_DESCRIPTIONS.get(i.rule, i.rule),
                "severity": i.severity,
                "file": i.file,
                "line": i.line,
                "message": i.message,
            }
            for i in issues
        ],
    }
    return json.dumps(out, indent=2)


# ---------------------------------------------------------------------------
# Pre-Commit Hook Installer
# ---------------------------------------------------------------------------

def install_hook(target_dir: Path | None = None) -> int:
    """Install standalone pre-commit hook into target git repository."""
    base = target_dir or Path.cwd()
    git_root = find_git_toplevel(base)
    if not git_root:
        print(f"arc42-lint: error: '{base}' is not inside a git repository.", file=sys.stderr)
        return 1

    hook_path = git_root / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    hook_script = """#!/usr/bin/env bash
# ==============================================================================
# Agent Skills Unified Pre-Commit Security & Architecture Gate
# ==============================================================================
set -e

# 1. Dependency Vulnerability CVE Gate (Google OSV-Scanner)
if [ "${SKIP_OSV_SCANNER:-0}" != "1" ]; then
    if command -v osv-scanner-gate >/dev/null 2>&1; then
        osv-scanner-gate --staged
    elif [ -f "${HOME}/.local/bin/osv-scanner-gate" ]; then
        "${HOME}/.local/bin/osv-scanner-gate" --staged
    fi
fi

# 2. arc42 Architecture Drift & Consistency Gate
if [ "${SKIP_ARC42_LINT:-0}" = "1" ] || [ "${SKIP_DOC_GATE:-0}" = "1" ]; then
    echo "ℹ️  arc42-lint: Pre-commit architecture gate bypassed via SKIP_ARC42_LINT=1"
    exit 0
fi

if command -v arc42-lint >/dev/null 2>&1; then
    exec arc42-lint --pre-commit
elif command -v arc42-pre-commit >/dev/null 2>&1; then
    exec arc42-pre-commit
elif [ -f "${HOME}/.local/bin/arc42-lint" ]; then
    exec "${HOME}/.local/bin/arc42-lint" --pre-commit
else
    echo "⚠️  arc42-lint not found in PATH; skipping pre-commit architecture gate."
    exit 0
fi
"""
    hook_path.write_text(hook_script, encoding="utf-8")
    hook_path.chmod(0o755)
    print(f"✅ Successfully installed arc42 pre-commit hook to {hook_path}")
    print("   The hook will deterministically verify architecture freshness on every 'git commit'.")
    print("   To bypass in emergency: SKIP_ARC42_LINT=1 git commit -m '...'")
    return 0


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    # 0. Check bypass environment variables
    if os.environ.get("SKIP_ARC42_LINT") == "1" or os.environ.get("SKIP_DOC_GATE") == "1":
        print("ℹ️  arc42-lint: Architecture gate bypassed via SKIP_ARC42_LINT=1")
        sys.exit(0)

    # Threshold environment variables fallback
    env_drift = os.environ.get("ARC42_DRIFT_THRESHOLD")
    default_drift = int(env_drift) if env_drift and env_drift.isdigit() else 15

    env_age = os.environ.get("ARC42_MAX_AGE_DAYS")
    default_age = int(env_age) if env_age and env_age.isdigit() else 30

    parser = argparse.ArgumentParser(
        description="arc42 architecture consistency, git provenance, drift & pre-commit linter.",
    )
    parser.add_argument(
        "docs_path", nargs="?", default="docs/architecture",
        help="Path to arc42 docs directory or markdown file (default: docs/architecture or docs/)",
    )
    parser.add_argument(
        "--lang", default="en", metavar="LANG",
        help="Documentation language, e.g. en, id, de, fr, it, es, pt (default: en)",
    )
    parser.add_argument(
        "--format", choices=["text", "github", "json"], default="text",
        help="Output format: 'text' (default), 'github' (Actions annotations), 'json'",
    )
    parser.add_argument(
        "--json", dest="json_flag", action="store_true",
        help="Shortcut for --format json",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Treat warnings as errors (non-zero exit code)",
    )
    parser.add_argument(
        "--check-drift", action="store_true", default=True,
        help="Perform git commit distance & staleness verification (default: True)",
    )
    parser.add_argument(
        "--no-check-drift", dest="check_drift", action="store_false",
        help="Disable git drift verification",
    )
    parser.add_argument(
        "--drift-threshold", type=int, default=default_drift,
        help=f"Max commit delta allowed before triggering a drift warning (default: {default_drift})",
    )
    parser.add_argument(
        "--max-age-days", type=int, default=default_age,
        help=f"Max days since verification before triggering a staleness warning (default: {default_age})",
    )
    parser.add_argument(
        "--require-provenance", action="store_true",
        help="Treat missing provenance metadata as error instead of warning",
    )
    parser.add_argument(
        "--pre-commit", action="store_true",
        help="Run in Git pre-commit mode: inspects staged changes & blocks stale/drifting commits",
    )
    parser.add_argument(
        "--install-hook", nargs="?", const=".", metavar="REPO_PATH",
        help="Install pre-commit hook into specified repository (.git/hooks/pre-commit)",
    )

    args = parser.parse_args()

    # Handle --install-hook
    if args.install_hook is not None:
        target = Path(args.install_hook).resolve()
        sys.exit(install_hook(target))

    # Fallback if first argument was 'install-hook'
    if args.docs_path == "install-hook":
        sys.exit(install_hook(Path.cwd()))

    if args.json_flag:
        args.format = "json"

    script_path = Path(__file__).resolve()
    lang = load_language(args.lang, script_path)

    docs = Path(args.docs_path)
    if not docs.exists() and args.docs_path == "docs/architecture":
        if Path("docs").exists():
            docs = Path("docs")

    git_root = find_git_toplevel(docs if docs.exists() else Path.cwd())

    # In pre-commit mode, if docs don't exist, don't fail unrelated repositories
    if not docs.exists():
        if args.pre_commit:
            sys.exit(0)
        if args.format == "json":
            print(json.dumps({"error": f"Path '{docs}' does not exist", "summary": {"passed": True, "errors": 0}}))
        else:
            print(f"arc42-lint: '{docs}' does not exist — nothing to lint.")
        sys.exit(0)

    data = load_docs(docs, lang)

    if not data.provenance_by_section:
        if args.pre_commit:
            sys.exit(0)
        if args.format == "json":
            print(json.dumps({"error": f"No arc42 sections detected in '{docs}'", "summary": {"passed": True, "errors": 0}}))
        else:
            print(f"arc42-lint: no arc42 sections detected in '{docs}' — nothing to lint.")
        sys.exit(0)

    staged_files: list[str] = []
    if git_root:
        staged_files = get_staged_files(git_root)

    if args.check_drift and git_root:
        run_drift_analysis(
            data,
            git_root,
            drift_threshold=args.drift_threshold,
            max_age_days=args.max_age_days,
        )

    strict_staged = args.pre_commit or args.strict
    require_prov = args.require_provenance or args.pre_commit

    issues = run_all_rules(
        data,
        require_provenance=require_prov,
        check_drift=args.check_drift and bool(git_root),
        drift_threshold=args.drift_threshold,
        max_age_days=args.max_age_days,
        staged_files=staged_files if (args.pre_commit or staged_files) else None,
        git_root=git_root,
        strict_staged=strict_staged,
    )

    lang_name = lang.get("name", args.lang)
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")

    # Pre-commit mode formatting
    if args.pre_commit:
        blocking_issues = [i for i in issues if i.severity == "error" or (args.strict and i.severity == "warning")]
        drift_blockers = [i for i in issues if i.rule in ("RULE-7", "RULE-8") and ("drift" in i.message.lower() or "stale" in i.message.lower() or "staged" in i.message.lower() or "modified" in i.message.lower())]
        all_blockers = list({id(x): x for x in (blocking_issues + drift_blockers)}.values())

        if all_blockers:
            print(format_pre_commit(all_blockers, data, docs), file=sys.stderr)
            sys.exit(1)
        else:
            print("✅ [arc42 Pre-Commit Gate] Architecture documentation is fresh & verified.")
            sys.exit(0)

    if args.format == "json":
        output = format_json(issues, data, docs, lang_name)
    elif args.format == "github":
        output = format_github(issues)
    else:
        output = format_text(issues, data, docs, lang_name)

    if output:
        print(output)

    if errors:
        sys.exit(1)
    if args.strict and warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
