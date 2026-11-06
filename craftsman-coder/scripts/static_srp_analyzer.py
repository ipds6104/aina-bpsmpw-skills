#!/usr/bin/env python3
"""
Static SRP & Abstraction Analyzer (Repo-Agnostic & Deterministic)

Detects Single Responsibility Principle (SRP) violations, bloated components/classes,
and abstraction bypasses (e.g., hard-coupled concrete I/O, SQL, or network calls instead of DI).
Integrates with the Old Coder 'Gauntlet' to provide deterministic verification.
"""

from __future__ import annotations
import argparse
import ast
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Set, Optional


@dataclass
class Violation:
    file_path: str
    line: int
    symbol: str
    category: str  # 'SRP_LENGTH', 'SRP_COMPLEXITY', 'ABSTRACTION_BYPASS'
    message: str
    recommendation: str
    severity: str  # 'ERROR', 'WARNING'


class BaseStaticRule(ABC):
    """Abstract contract for static analysis rules."""

    @abstractmethod
    def evaluate_python_ast(self, tree: ast.AST, file_path: str, lines: List[str]) -> List[Violation]:
        pass

    @abstractmethod
    def evaluate_text_file(self, content: str, file_path: str, lines: List[str]) -> List[Violation]:
        pass


class SrpLengthRule(BaseStaticRule):
    """Flags functions and classes/components that exceed single-responsibility length budgets."""

    def __init__(self, max_func_lines: int = 50, max_class_lines: int = 180):
        self.max_func_lines = max_func_lines
        self.max_class_lines = max_class_lines

    def evaluate_python_ast(self, tree: ast.AST, file_path: str, lines: List[str]) -> List[Violation]:
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_lineno = getattr(node, "end_lineno", node.lineno)
                span = end_lineno - node.lineno + 1
                if span > self.max_func_lines:
                    violations.append(
                        Violation(
                            file_path=file_path,
                            line=node.lineno,
                            symbol=node.name,
                            category="SRP_LENGTH",
                            message=f"Function/method '{node.name}' is {span} lines long (exceeds {self.max_func_lines} lines limit).",
                            recommendation="Break down function into smaller, single-responsibility helper functions or extract into a dedicated domain service.",
                            severity="ERROR" if span > self.max_func_lines * 1.5 else "WARNING",
                        )
                    )
            elif isinstance(node, ast.ClassDef):
                end_lineno = getattr(node, "end_lineno", node.lineno)
                span = end_lineno - node.lineno + 1
                if span > self.max_class_lines:
                    violations.append(
                        Violation(
                            file_path=file_path,
                            line=node.lineno,
                            symbol=node.name,
                            category="SRP_LENGTH",
                            message=f"Class/Component '{node.name}' is {span} lines long (exceeds {self.max_class_lines} lines limit).",
                            recommendation="Split class into distinct cohesive classes/subcomponents following SRP. Separate data, business logic, and presentation.",
                            severity="ERROR" if span > self.max_class_lines * 1.5 else "WARNING",
                        )
                    )
        return violations

    def evaluate_text_file(self, content: str, file_path: str, lines: List[str]) -> List[Violation]:
        violations = []
        # Check UI components (TSX/JSX) or functions exceeding threshold
        if file_path.endswith((".tsx", ".jsx", ".vue", ".svelte")):
            total_lines = len(lines)
            if total_lines > self.max_class_lines:
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=1,
                        symbol=os.path.basename(file_path),
                        category="SRP_LENGTH",
                        message=f"Component file '{os.path.basename(file_path)}' is {total_lines} lines long (exceeds {self.max_class_lines} lines limit).",
                        recommendation="Decompose large component into smaller atomic child components, custom hooks, or utility presenter modules.",
                        severity="ERROR" if total_lines > self.max_class_lines * 1.5 else "WARNING",
                    )
                )
        return violations


class AbstractionBypassRule(BaseStaticRule):
    """Detects concrete tight couplings (e.g. raw SQL/HTTP calls in UI or business logic instead of DI)."""

    DIRECT_HTTP_PATTERNS = [
        re.compile(r"\b(axios\.(get|post|put|delete)|fetch\s*\()\b"),
        re.compile(r"\b(requests\.(get|post|put|delete)|httpx\.(get|post|put|delete))\b"),
    ]

    RAW_DB_PATTERNS = [
        re.compile(r"\b(SELECT\s+.+\s+FROM|INSERT\s+INTO|UPDATE\s+.+\s+SET|DELETE\s+FROM)\b", re.IGNORECASE),
        re.compile(r"\b(sqlite3\.connect|psycopg2\.connect|create_engine)\b"),
    ]

    def evaluate_python_ast(self, tree: ast.AST, file_path: str, lines: List[str]) -> List[Violation]:
        violations = []
        # Exclude repository, gateway, or database migration files which legitimately handle raw I/O
        normalized_path = file_path.lower()
        if any(ign in normalized_path for ign in ["repo", "gateway", "db", "migration", "client", "test", "analyzer", "rule"]):
            return violations

        for i, line in enumerate(lines, start=1):
            if "re.compile" in line:
                continue
            for pat in self.DIRECT_HTTP_PATTERNS:
                if pat.search(line):
                    violations.append(
                        Violation(
                            file_path=file_path,
                            line=i,
                            symbol="direct_http_call",
                            category="ABSTRACTION_BYPASS",
                            message="Direct HTTP call detected outside of gateway/client adapter layer.",
                            recommendation="Introduce an API client interface and pass it via Dependency Injection.",
                            severity="WARNING",
                        )
                    )
            for pat in self.RAW_DB_PATTERNS:
                if pat.search(line):
                    violations.append(
                        Violation(
                            file_path=file_path,
                            line=i,
                            symbol="direct_db_coupling",
                            category="ABSTRACTION_BYPASS",
                            message="Raw database logic or direct connection detected in business/presentation layer.",
                            recommendation="Encapsulate database queries in a Repository or Data Access Object (DAO) abstraction.",
                            severity="ERROR",
                        )
                    )
        return violations

    def evaluate_text_file(self, content: str, file_path: str, lines: List[str]) -> List[Violation]:
        violations = []
        normalized_path = file_path.lower()
        if any(ign in normalized_path for ign in ["repo", "gateway", "service", "client", "api", "test"]):
            return violations

        # TSX/JSX direct fetch/axios checks
        if file_path.endswith((".tsx", ".jsx")):
            for i, line in enumerate(lines, start=1):
                for pat in self.DIRECT_HTTP_PATTERNS:
                    if pat.search(line):
                        violations.append(
                            Violation(
                                file_path=file_path,
                                line=i,
                                symbol="direct_network_fetch",
                                category="ABSTRACTION_BYPASS",
                                message="Direct network fetch called inside UI presentation component.",
                                recommendation="Extract data fetching into a custom hook or inject a service client abstraction.",
                                severity="WARNING",
                            )
                        )
        return violations


class StaticAnalysisRunner:
    """Coordinates rules and collects deterministic results."""

    def __init__(self, rules: List[BaseStaticRule]):
        self.rules = rules

    def scan_path(self, target_path: Path, exclude_dirs: Set[str] = None) -> List[Violation]:
        if exclude_dirs is None:
            exclude_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}

        violations: List[Violation] = []
        if target_path.is_file():
            files_to_scan = [target_path]
        else:
            files_to_scan = []
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
                for f in files:
                    files_to_scan.append(Path(root) / f)

        for file_path in files_to_scan:
            ext = file_path.suffix.lower()
            if ext not in [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"]:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
            except Exception:
                continue

            if ext == ".py":
                try:
                    tree = ast.parse(content, filename=str(file_path))
                    for rule in self.rules:
                        violations.extend(rule.evaluate_python_ast(tree, str(file_path), lines))
                except Exception:
                    pass

            for rule in self.rules:
                violations.extend(rule.evaluate_text_file(content, str(file_path), lines))

        return violations


def format_report(violations: List[Violation]) -> str:
    lines = [
        "=" * 65,
        "🔍 STATIC CODE ANALYSIS REPORT: SRP & ABSTRACTION INTEGRITY",
        "=" * 65,
    ]
    if not violations:
        lines.append("✅ ALL CHECKS PASSED: No SRP or Abstraction violations detected!")
        lines.append("=" * 65)
        return "\n".join(lines)

    errors = [v for v in violations if v.severity == "ERROR"]
    warnings = [v for v in violations if v.severity == "WARNING"]

    lines.append(f"Summary: {len(errors)} Errors, {len(warnings)} Warnings")
    lines.append("-" * 65)

    for v in violations:
        icon = "❌" if v.severity == "ERROR" else "⚠️"
        lines.append(f"{icon} [{v.category}] {os.path.basename(v.file_path)}:{v.line} ({v.symbol})")
        lines.append(f"   Issue : {v.message}")
        lines.append(f"   Action: {v.recommendation}")
        lines.append("")

    lines.append("=" * 65)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Deterministic Static SRP & Abstraction Analyzer")
    parser.add_argument("path", nargs="?", default=".", help="Target file or directory (default: .)")
    parser.add_argument("--max-func-lines", type=int, default=50, help="Max lines for a single function (default: 50)")
    parser.add_argument("--max-class-lines", type=int, default=180, help="Max lines for class/component (default: 180)")
    parser.add_argument("--strict", action="store_true", help="Fail with exit code 1 if any warning or error is found")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    if not target.exists():
        print(f"Error: Path '{target}' does not exist.", file=sys.stderr)
        sys.exit(2)

    # Dependency Injection
    rules: List[BaseStaticRule] = [
        SrpLengthRule(max_func_lines=args.max_func_lines, max_class_lines=args.max_class_lines),
        AbstractionBypassRule(),
    ]
    runner = StaticAnalysisRunner(rules=rules)
    violations = runner.scan_path(target)

    if args.json:
        data = {
            "total_violations": len(violations),
            "errors": sum(1 for v in violations if v.severity == "ERROR"),
            "warnings": sum(1 for v in violations if v.severity == "WARNING"),
            "violations": [asdict(v) for v in violations],
        }
        print(json.dumps(data, indent=2))
    else:
        print(format_report(violations))

    errors_count = sum(1 for v in violations if v.severity == "ERROR")
    if errors_count > 0 or (args.strict and len(violations) > 0):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
