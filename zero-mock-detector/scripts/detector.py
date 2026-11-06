"""
Zero-Mock Static Analysis Engine leveraging AST Code-Graph.
Combines Code-Graph index queries with deep file-level AST heuristics
and repository-level technical debt ledger verification.
"""
import json
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rules import (
    EXCLUDED_SYMBOLS,
    DebtEntry,
    Finding,
    MOCK_IMPORT_PATTERNS,
    POLLUTION_FILENAME_PATTERNS,
    RE_FAKE_LATENCY,
    RE_INCODE_ALLOW_STUB,
    RE_MOCK_BYPASS_FLAG,
    RE_MOCK_SYMBOL,
    RE_RATIONALIZING_COMMENT,
    RE_SILENT_FALLBACK,
    RE_STUB_BODY_C,
    RE_STUB_BODY_PY,
    RE_STUB_BODY_RUST,
    RE_STUB_BODY_TS,
    RE_STUBBED_CODE,
    Severity,
)

class ZeroMockDetector:
    def __init__(self, root_dir: str, use_codegraph: bool = True):
        self.root_dir = Path(root_dir).resolve()
        self.use_codegraph = use_codegraph
        self.index_db_path = self.root_dir / ".code-graph" / "index.db"
        self.debt_ledger: Dict[str, DebtEntry] = {}
        self.load_repo_ledger()

    def load_repo_ledger(self) -> None:
        """
        Loads repository-level technical debt ledgers.
        Separates global detection rules from repository-specific exemptions.
        """
        # 1. Check for JSON allowlist (.zero-mock-allowlist.json)
        json_path = self.root_dir / ".zero-mock-allowlist.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("exemptions", []):
                        sym = item.get("symbol")
                        if sym:
                            self.debt_ledger[sym] = DebtEntry(
                                symbol_name=sym,
                                file_path=item.get("file"),
                                reason=item.get("reason", "No reason provided"),
                                citation=item.get("citation", "N/A"),
                                source_ledger=".zero-mock-allowlist.json"
                            )
            except Exception:
                pass

        # 2. Check for Single-File Markdown Ledgers (docs/TECHNICAL_DEBT.md, docs/ENTERPRISE_ISSUE_REFERENCE_LEDGER.md)
        for md_name in ["docs/TECHNICAL_DEBT.md", "TECHNICAL_DEBT.md", "docs/ENTERPRISE_ISSUE_REFERENCE_LEDGER.md"]:
            md_path = self.root_dir / md_name
            if md_path.exists():
                self._parse_markdown_ledger(md_path)

        # 3. Check for AnyPS5 multi-file debt directory (docs/dev/debt/*.md)
        debt_dir = self.root_dir / "docs" / "dev" / "debt"
        if debt_dir.is_dir():
            for debt_file in debt_dir.glob("*.md"):
                self._parse_markdown_ledger(debt_file)

    def _parse_markdown_ledger(self, path: Path) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            rel_ledger = str(path.relative_to(self.root_dir)).replace("\\", "/")

            # Pattern A: `[symbol_name](path)` or `- `symbol_name`: reason (citation)`
            matches = re.findall(r"""(?:-\s*\[([A-Za-z0-9_]+)\]\(([^)]+)\)|-\s*`([A-Za-z0-9_]+)`(?:\s*\([^)]*\))?\s*[-:]\s*([^\n]+))""", content)
            for m in matches:
                sym = m[0] or m[2]
                target_file = m[1] if m[0] else None
                reason_line = m[3] if m[2] else "Documented in technical debt ledger"
                if sym:
                    self.debt_ledger[sym] = DebtEntry(
                        symbol_name=sym,
                        file_path=target_file,
                        reason=reason_line,
                        citation=rel_ledger,
                        source_ledger=rel_ledger
                    )

            # Pattern B: Headers or Silent stubs section
            silent_stubs_idx = content.find("Silent stubs")
            if silent_stubs_idx != -1:
                sub_text = content[silent_stubs_idx:silent_stubs_idx + 4000]
                stub_syms = re.findall(r"""`([A-Za-z0-9_]+)`|\[([A-Za-z0-9_]+)\]""", sub_text)
                for s1, s2 in stub_syms:
                    sym = s1 or s2
                    if sym and sym not in self.debt_ledger:
                        self.debt_ledger[sym] = DebtEntry(
                            symbol_name=sym,
                            file_path=None,
                            reason="Listed under Silent stubs in repo technical debt ledger",
                            citation=rel_ledger,
                            source_ledger=rel_ledger
                        )
        except Exception:
            pass

    def is_symbol_exempted(self, symbol_name: Optional[str], file_path: str, context_lines: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifies if an exemption exists in the repo-level debt ledger or in-code annotation.
        Returns: (is_exempted, reason, citation)
        """
        # 1. In-code annotation check (@allow-stub: reason (citation: ref))
        if context_lines:
            match = RE_INCODE_ALLOW_STUB.search(context_lines)
            if match:
                reason = match.group(1).strip()
                citation = match.group(2).strip() if match.group(2) else "In-code citation"
                return True, reason, citation

        # 2. Repo-level ledger check by symbol name
        if symbol_name and symbol_name in self.debt_ledger:
            entry = self.debt_ledger[symbol_name]
            # If entry specifies file_path, ensure it matches
            if entry.file_path:
                norm_entry = entry.file_path.replace("\\", "/").lstrip("./")
                norm_target = file_path.replace("\\", "/").lstrip("./")
                if not (norm_entry in norm_target or norm_target in norm_entry):
                    return False, None, None
            return True, entry.reason, entry.citation

        return False, None, None

    def is_production_file(self, rel_path: str) -> bool:
        normalized = rel_path.replace("\\", "/")
        lower = normalized.lower()

        # Discard documentation, build outputs, version control, and caches
        if any(lower.startswith(p) or f"/{p}" in lower for p in [
            "target/", "node_modules/", "dist/", "build/", ".git/", ".agents/", "docs/", ".gemini/"
        ]):
            return False

        # Exclude recognized test directories and test suffixes
        test_patterns = [
            "/tests/", "/test/", "/spec/", "/__tests__/", "/testing/",
            "/benches/", "/evals/", "/examples/"
        ]
        if any(tp in f"/{lower}" for tp in test_patterns):
            return False

        test_file_suffixes = [
            "_test.rs", ".test.ts", ".test.js", ".spec.ts", ".spec.js",
            "_test.go", "_test.py"
        ]
        if any(lower.endswith(s) for s in test_file_suffixes) or Path(lower).name.startswith("test_"):
            return False

        # Must be valid source code
        valid_exts = {".rs", ".ts", ".js", ".tsx", ".jsx", ".py", ".go", ".java", ".kt", ".c", ".cpp", ".cc", ".h", ".hpp"}
        return Path(lower).suffix in valid_exts

    def ensure_codegraph_index(self) -> bool:
        if self.index_db_path.exists():
            return True
        if not self.use_codegraph:
            return False

        try:
            res = subprocess.run(
                ["code-graph", "incremental-index"],
                cwd=str(self.root_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False
            )
            return self.index_db_path.exists()
        except Exception:
            return False

    def scan_codegraph_nodes(self) -> List[Finding]:
        findings: List[Finding] = []
        if not self.index_db_path.exists():
            return findings

        try:
            conn = sqlite3.connect(str(self.index_db_path))
            cur = conn.cursor()
            query = """
                SELECT n.id, f.path, n.type, n.name, n.start_line, n.code_content, n.is_test
                FROM nodes n
                JOIN files f ON n.file_id = f.id
                WHERE n.is_test = 0
            """
            cur.execute(query)
            rows = cur.fetchall()
            conn.close()

            for _, rel_path, ntype, name, start_line, code_content, is_test in rows:
                if not self.is_production_file(rel_path):
                    continue

                # Check 1: Mock Symbol Name in Production
                clean_name = name.lower()
                is_analyzer = any(clean_name.endswith(suffix) for suffix in ("detector", "auditor", "analyzer", "checker", "scanner"))
                if clean_name not in EXCLUDED_SYMBOLS and not is_analyzer and RE_MOCK_SYMBOL.search(name):
                    exempted, reason, citation = self.is_symbol_exempted(name, rel_path, code_content)
                    if not exempted:
                        findings.append(Finding(
                            rule_id="RULE_MOCK_SYMBOL_NAME",
                            severity=Severity.HIGH,
                            file_path=rel_path,
                            line_number=start_line,
                            symbol_name=name,
                            message=f"Production {ntype} '{name}' contains forbidden mock/fake/stub naming",
                            code_snippet=code_content.splitlines()[0] if code_content else None
                        ))

                # Check 2: Stubbed Code in Production
                if code_content and RE_STUBBED_CODE.search(code_content):
                    exempted, reason, citation = self.is_symbol_exempted(name, rel_path, code_content)
                    if not exempted:
                        findings.append(Finding(
                            rule_id="RULE_STUBBED_CODE",
                            severity=Severity.HIGH,
                            file_path=rel_path,
                            line_number=start_line,
                            symbol_name=name,
                            message=f"Production symbol '{name}' contains stubbed todo!() / unimplemented!() logic",
                            code_snippet=code_content.splitlines()[0] if code_content else None
                        ))

                # Check 3: Bodyless / Trivial Constant Return (AnyPS5 STUB_BODY check)
                if code_content:
                    ext = Path(rel_path).suffix.lower()
                    lines = [ln.strip() for ln in code_content.splitlines() if ln.strip()]
                    body_content = " ".join(lines[1:-1]) if len(lines) > 2 else (lines[1] if len(lines) == 2 else "")
                    
                    is_stub_body = False
                    if ext in (".c", ".cpp", ".cc", ".h", ".hpp") and RE_STUB_BODY_C.match(body_content):
                        is_stub_body = True
                    elif ext == ".rs" and RE_STUB_BODY_RUST.match(body_content):
                        is_stub_body = True
                    elif ext == ".py" and RE_STUB_BODY_PY.match(body_content):
                        is_stub_body = True
                    elif ext in (".ts", ".js", ".tsx", ".jsx") and RE_STUB_BODY_TS.match(body_content):
                        is_stub_body = True

                    if is_stub_body and len(lines) <= 4:
                        exempted, reason, citation = self.is_symbol_exempted(name, rel_path, code_content)
                        if not exempted:
                            findings.append(Finding(
                                rule_id="RULE_STUB_BODY_UNTRACKED",
                                severity=Severity.HIGH,
                                file_path=rel_path,
                                line_number=start_line,
                                symbol_name=name,
                                message=f"Production symbol '{name}' is an untracked bodyless stub. Register in repo-level docs/TECHNICAL_DEBT.md or implement logic.",
                                code_snippet=lines[0] if lines else None
                            ))

                # Check 4: Fake Latency in Repository/Service symbols
                is_service = any(k in rel_path.lower() for k in ["repo", "service", "client", "gateway", "driver"])
                if is_service and code_content and RE_FAKE_LATENCY.search(code_content):
                    findings.append(Finding(
                        rule_id="RULE_FAKE_LATENCY",
                        severity=Severity.HIGH,
                        file_path=rel_path,
                        line_number=start_line,
                        symbol_name=name,
                        message=f"Simulated latency/sleep found in production service symbol '{name}'",
                        code_snippet=code_content.splitlines()[0] if code_content else None
                    ))

        except Exception:
            pass

        return findings

    def scan_files_directly(self) -> List[Finding]:
        findings: List[Finding] = []

        for root, dirs, files in os.walk(str(self.root_dir)):
            # Fast prune ignored directories
            dirs[:] = [d for d in dirs if d not in [
                ".git", "node_modules", "target", "dist", "build", ".agents", "docs", ".gemini", ".code-graph"
            ]]

            rel_root = os.path.relpath(root, str(self.root_dir))
            if rel_root != "." and not self.is_production_file(rel_root + "/dummy.py"):
                continue

            for fname in files:
                rel_path = os.path.join(rel_root, fname).replace("\\", "/").lstrip("./")

                # Check A: Agent Note & Scratch File Pollution
                for pol_pattern in POLLUTION_FILENAME_PATTERNS:
                    if pol_pattern.match(fname):
                        findings.append(Finding(
                            rule_id="RULE_AGENT_NOTE_POLLUTION",
                            severity=Severity.HIGH,
                            file_path=rel_path,
                            line_number=1,
                            symbol_name=None,
                            message=f"Temporary agent scratch/note/log file '{fname}' detected in production directory. Remove before shipping.",
                            code_snippet=fname
                        ))

                if not self.is_production_file(rel_path):
                    continue

                full_path = Path(root) / fname
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except Exception:
                    continue

                ext = full_path.suffix.lower()

                for idx, line in enumerate(lines, start=1):
                    # Check 1: Mock Import Patterns
                    for rule_id, pattern, desc in MOCK_IMPORT_PATTERNS:
                        if pattern.search(line):
                            findings.append(Finding(
                                rule_id=rule_id,
                                severity=Severity.CRITICAL,
                                file_path=rel_path,
                                line_number=idx,
                                symbol_name=None,
                                message=desc,
                                code_snippet=line.strip()
                            ))

                    stripped = line.strip()
                    is_meta_def = (
                        stripped.startswith(("message=", "message =", "desc=", "desc =", "r\"\"\"", "r'''", "re.compile("))
                        or "Finding(" in line
                    )
                    line_no_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', '""', line)

                    # Check 2: Mock Bypass Environment Flags
                    has_bypass_flag = False
                    if re.search(r"""\b(?:process\.env\.NODE_ENV|process\.env\[['"]NODE_ENV['"]\])\s*===?\s*['"]test['"]""", line):
                        has_bypass_flag = True
                    elif re.search(r"""\b(?:MOCK_ENABLED|USE_MOCK|IS_MOCK|MOCK_DATA|MOCK_MODE)\b""", line_no_str):
                        has_bypass_flag = True

                    if not is_meta_def and has_bypass_flag:
                        findings.append(Finding(
                            rule_id="RULE_MOCK_BYPASS_FLAG",
                            severity=Severity.MEDIUM,
                            file_path=rel_path,
                            line_number=idx,
                            symbol_name=None,
                            message="Production code contains mock bypass flag (e.g. NODE_ENV === 'test' or MOCK_ENABLED)",
                            code_snippet=line.strip()
                        ))

                    # Check 3: Mock Symbol Definition in Production File
                    mock_def_match = re.search(r"""^\s*(?:pub\s+)?(?:class|struct|fn|def|interface|type)\s+([A-Za-z0-9_]*mock[A-Za-z0-9_]*)""", line, re.IGNORECASE)
                    if mock_def_match:
                        sym = mock_def_match.group(1)
                        clean_sym = sym.lower()
                        is_analyzer = any(clean_sym.endswith(suffix) for suffix in ("detector", "auditor", "analyzer", "checker", "scanner"))
                        if clean_sym not in EXCLUDED_SYMBOLS and not is_analyzer:
                            prev_lines = "".join(lines[max(0, idx - 4):idx])
                            exempted, reason, citation = self.is_symbol_exempted(sym, rel_path, prev_lines)
                            if not exempted:
                                findings.append(Finding(
                                    rule_id="RULE_MOCK_SYMBOL_NAME",
                                    severity=Severity.HIGH,
                                    file_path=rel_path,
                                    line_number=idx,
                                    symbol_name=sym,
                                    message=f"Production symbol '{sym}' contains forbidden mock/fake naming",
                                    code_snippet=line.strip()
                                ))

                    # Check 4: Stubbed Code in Production
                    has_stubbed_code = False
                    if re.search(r"""\b(?:todo!|unimplemented!)\s*\(""", line_no_str):
                        has_stubbed_code = True
                    elif re.search(r"""\b(?:throw\s+new\s+Error|raise\s+NotImplementedError)\b""", line_no_str):
                        if re.search(r"""(?:todo|stub|mock|not\s+implemented)""", line, re.IGNORECASE):
                            has_stubbed_code = True

                    if not is_meta_def and has_stubbed_code:
                        prev_lines = "".join(lines[max(0, idx - 4):idx])
                        exempted, reason, citation = self.is_symbol_exempted(None, rel_path, prev_lines)
                        if not exempted:
                            findings.append(Finding(
                                rule_id="RULE_STUBBED_CODE",
                                severity=Severity.HIGH,
                                file_path=rel_path,
                                line_number=idx,
                                symbol_name=None,
                                message="Production code contains stubbed todo!() / unimplemented!() logic",
                                code_snippet=line.strip()
                            ))

                    # Check 5: Fake Latency in Repository/Service Files
                    is_service = any(k in rel_path.lower() for k in ["repo", "service", "client", "gateway", "driver"])
                    if is_service and RE_FAKE_LATENCY.search(line):
                        findings.append(Finding(
                            rule_id="RULE_FAKE_LATENCY",
                            severity=Severity.HIGH,
                            file_path=rel_path,
                            line_number=idx,
                            symbol_name=None,
                            message="Simulated latency/sleep found in production service/driver",
                            code_snippet=line.strip()
                        ))

                    # Check 6: Silent Fallback / Swallowed Error in Production Files
                    if RE_SILENT_FALLBACK.search(line):
                        prev_lines = "".join(lines[max(0, idx - 4):idx])
                        exempted, reason, citation = self.is_symbol_exempted(None, rel_path, prev_lines)
                        if not exempted:
                            findings.append(Finding(
                                rule_id="RULE_SILENT_FALLBACK",
                                severity=Severity.HIGH,
                                file_path=rel_path,
                                line_number=idx,
                                symbol_name=None,
                                message="Production code contains empty catch/except block silently swallowing errors",
                                code_snippet=line.strip()
                            ))

                    # Check 7: Rationalizing Comments (Attempting to justify fake behavior)
                    if RE_RATIONALIZING_COMMENT.search(line):
                        findings.append(Finding(
                            rule_id="RULE_RATIONALIZING_COMMENT",
                            severity=Severity.MEDIUM,
                            file_path=rel_path,
                            line_number=idx,
                            symbol_name=None,
                            message="Rationalizing comment detected justifying fake/mock behavior. Replace with real implementation or register in repo technical debt ledger.",
                            code_snippet=line.strip()
                        ))

        return findings

    def scan(self) -> List[Finding]:
        self.ensure_codegraph_index()
        all_findings = self.scan_codegraph_nodes() + self.scan_files_directly()

        # Deduplicate findings by (rule_id, file_path, line_number)
        seen: Set[str] = set()
        deduped: List[Finding] = []
        for f in all_findings:
            key = f"{f.rule_id}:{f.file_path}:{f.line_number}"
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        # Sort by severity (CRITICAL first), then file, line
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        deduped.sort(key=lambda x: (severity_order.get(x.severity, 99), x.file_path, x.line_number))
        return deduped
