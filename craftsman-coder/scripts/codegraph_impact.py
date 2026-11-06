#!/usr/bin/env python3
"""
CodeGraph & AST Impact Analyzer (Repo-Agnostic)

Analyzes symbol definitions, call graphs, references, and calculates the blast radius
(impact analysis) before making code modifications or refactoring.
Designed following SOLID principles (SRP, Dependency Injection, Interface Segregation).
"""

from __future__ import annotations
import ast
import argparse
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional


@dataclass
class SymbolNode:
    name: str
    kind: str  # 'function', 'class', 'method', 'variable'
    file_path: str
    line: int
    docstring: Optional[str] = None
    calls: Set[str] = field(default_factory=set)


@dataclass
class FileGraph:
    file_path: str
    imports: Set[str] = field(default_factory=set)
    symbols: Dict[str, SymbolNode] = field(default_factory=dict)
    all_referenced_names: Set[str] = field(default_factory=set)


class BaseAstParser(ABC):
    """Abstract interface for parsing source files into structured AST nodes."""

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        pass

    @abstractmethod
    def parse_file(self, file_path: Path) -> FileGraph:
        pass


class PythonAstParser(BaseAstParser):
    """Concrete parser using Python standard library 'ast'."""

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".py"

    def parse_file(self, file_path: Path) -> FileGraph:
        fg = FileGraph(file_path=str(file_path))
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return fg

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    fg.imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    fg.imports.add(node.module)
                for alias in node.names:
                    fg.imports.add(f"{node.module}.{alias.name}" if node.module else alias.name)
            elif isinstance(node, ast.Name):
                fg.all_referenced_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                fg.all_referenced_names.add(node.attr)

        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls = {n.id for n in ast.walk(stmt) if isinstance(n, ast.Name)} | {
                    n.attr for n in ast.walk(stmt) if isinstance(n, ast.Attribute)
                }
                fg.symbols[stmt.name] = SymbolNode(
                    name=stmt.name,
                    kind="function",
                    file_path=str(file_path),
                    line=stmt.lineno,
                    calls=calls,
                )
            elif isinstance(stmt, ast.ClassDef):
                calls = {n.id for n in ast.walk(stmt) if isinstance(n, ast.Name)} | {
                    n.attr for n in ast.walk(stmt) if isinstance(n, ast.Attribute)
                }
                fg.symbols[stmt.name] = SymbolNode(
                    name=stmt.name,
                    kind="class",
                    file_path=str(file_path),
                    line=stmt.lineno,
                    calls=calls,
                )
                for item in stmt.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_calls = {n.id for n in ast.walk(item) if isinstance(n, ast.Name)} | {
                            n.attr for n in ast.walk(item) if isinstance(n, ast.Attribute)
                        }
                        fg.symbols[f"{stmt.name}.{item.name}"] = SymbolNode(
                            name=f"{stmt.name}.{item.name}",
                            kind="method",
                            file_path=str(file_path),
                            line=item.lineno,
                            calls=method_calls,
                        )

        return fg


class GenericRegexParser(BaseAstParser):
    """Fallback parser for JS, TS, Go, Rust, Java, etc. using regex patterns."""

    SUPPORTED_EXTS = {".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".rb", ".php"}

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTS

    def parse_file(self, file_path: Path) -> FileGraph:
        fg = FileGraph(file_path=str(file_path))
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return fg

        import_pattern = re.compile(r'(?:import|from|require)\s+[\'"]([^\'"]+)[\'"]')
        for match in import_pattern.finditer(content):
            fg.imports.add(match.group(1))

        func_pattern = re.compile(
            r"(?:function\s+|def\s+|fn\s+|func\s+|(?:public|private|protected)\s+(?:async\s+)?(?:[a-zA-Z0-9_<>\[\]]+\s+)?)([a-zA-Z0-9_]+)\s*\("
        )
        for i, line in enumerate(content.splitlines(), start=1):
            m = func_pattern.search(line)
            if m:
                name = m.group(1)
                fg.symbols[name] = SymbolNode(
                    name=name,
                    kind="function",
                    file_path=str(file_path),
                    line=i,
                )

        class_pattern = re.compile(r"(?:class|struct|interface|type)\s+([a-zA-Z0-9_]+)")
        for i, line in enumerate(content.splitlines(), start=1):
            m = class_pattern.search(line)
            if m:
                name = m.group(1)
                fg.symbols[name] = SymbolNode(
                    name=name,
                    kind="class",
                    file_path=str(file_path),
                    line=i,
                )

        words = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", content))
        fg.all_referenced_names = words
        return fg


class CodeGraph:
    """Stores the aggregated graph of files and symbol cross-references."""

    def __init__(self, parsers: List[BaseAstParser]):
        self.parsers = parsers
        self.files: Dict[str, FileGraph] = {}

    def index_directory(self, root_dir: Path, exclude_dirs: Set[str] = None):
        if exclude_dirs is None:
            exclude_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", ".cache", "dist", "build"}

        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
            for file in files:
                file_path = Path(root) / file
                for parser in self.parsers:
                    if parser.can_parse(file_path):
                        fg = parser.parse_file(file_path)
                        self.files[str(file_path.resolve())] = fg
                        break


class ImpactAnalyzer:
    """Calculates downstream dependencies, callers, affected tests, and blast radius risk."""

    TEST_PATTERNS = [
        re.compile(r"test_", re.I),
        re.compile(r"_test\.", re.I),
        re.compile(r"\.test\.", re.I),
        re.compile(r"\.spec\.", re.I),
        re.compile(r"/tests?/", re.I),
    ]

    def __init__(self, graph: CodeGraph):
        self.graph = graph

    def is_test_file(self, path: str) -> bool:
        return any(pat.search(path) for pat in self.TEST_PATTERNS)

    def analyze_symbol(self, symbol_name: str) -> dict:
        declaring_files = []
        referencing_files = []
        affected_tests = []
        calling_symbols = []

        base_symbol = symbol_name.split(".")[-1]

        for fpath, fg in self.graph.files.items():
            for sym_name, sym_node in fg.symbols.items():
                if sym_name == symbol_name or sym_name.endswith(f".{symbol_name}") or sym_name == base_symbol:
                    if fpath not in declaring_files:
                        declaring_files.append(fpath)

            if base_symbol in fg.all_referenced_names:
                if fpath not in declaring_files:
                    referencing_files.append(fpath)
                    if self.is_test_file(fpath):
                        affected_tests.append(fpath)

            for sym_key, sym_node in fg.symbols.items():
                if base_symbol in sym_node.calls and sym_node.name != symbol_name and sym_node.name != base_symbol:
                    calling_symbols.append({
                        "caller": sym_node.name,
                        "kind": sym_node.kind,
                        "file": fpath,
                        "line": sym_node.line,
                    })

        total_impact = len(referencing_files) + len(calling_symbols)
        if total_impact == 0:
            risk = "ISOLATED / LOW"
        elif total_impact <= 3:
            risk = "LOW"
        elif total_impact <= 8:
            risk = "MEDIUM"
        elif total_impact <= 15:
            risk = "HIGH"
        else:
            risk = "CRITICAL / WIDE BLAST RADIUS"

        return {
            "symbol": symbol_name,
            "declared_in": declaring_files,
            "referencing_files_count": len(referencing_files),
            "referencing_files": referencing_files,
            "calling_symbols_count": len(calling_symbols),
            "calling_symbols": calling_symbols,
            "affected_tests": affected_tests,
            "blast_radius_risk": risk,
            "total_dependents": total_impact,
        }

    def summarize_graph(self) -> dict:
        total_files = len(self.graph.files)
        total_symbols = sum(len(fg.symbols) for fg in self.graph.files.values())
        test_files = [f for f in self.graph.files if self.is_test_file(f)]
        return {
            "indexed_files": total_files,
            "total_symbols": total_symbols,
            "test_files_count": len(test_files),
        }


def format_cli_report(analysis: dict) -> str:
    lines = [
        "=" * 60,
        f"🎯 CODEGRAPH IMPACT & BLAST RADIUS REPORT: '{analysis['symbol']}'",
        "=" * 60,
        f"Risk Level         : {analysis['blast_radius_risk']}",
        f"Total Dependents   : {analysis['total_dependents']}",
        f"Declared In        : {', '.join(analysis['declared_in']) if analysis['declared_in'] else 'External / Not found'}",
        "-" * 60,
        f"Direct Callers ({analysis['calling_symbols_count']}):"
    ]
    for caller in analysis['calling_symbols'][:10]:
        lines.append(f"  • {caller['caller']} ({caller['kind']}) @ {os.path.basename(caller['file'])}:{caller['line']}")
    if len(analysis['calling_symbols']) > 10:
        lines.append(f"  ... and {len(analysis['calling_symbols']) - 10} more callers.")

    lines.append("-" * 60)
    lines.append(f"Referencing Files ({analysis['referencing_files_count']}):")
    for f in analysis['referencing_files'][:8]:
        lines.append(f"  • {f}")
    if len(analysis['referencing_files']) > 8:
        lines.append(f"  ... and {len(analysis['referencing_files']) - 8} more files.")

    lines.append("-" * 60)
    lines.append(f"🧪 Affected Test Suites ({len(analysis['affected_tests'])}):")
    if analysis['affected_tests']:
        for t in analysis['affected_tests']:
            lines.append(f"  ✅ {t}")
    else:
        lines.append("  ⚠️  NO DIRECT TEST SUITE DETECTED! (High regression risk - write test first!)")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="CodeGraph AST Impact & Blast Radius Analyzer")
    parser.add_argument("path", nargs="?", default=".", help="Root path to inspect (default: .)")
    parser.add_argument("--symbol", "-s", type=str, help="Symbol to inspect blast radius for")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    target_dir = Path(args.path).resolve()
    if not target_dir.exists():
        print(f"Error: Path '{target_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Dependency Injection of parsers
    parsers: List[BaseAstParser] = [PythonAstParser(), GenericRegexParser()]
    graph = CodeGraph(parsers=parsers)
    graph.index_directory(target_dir)

    analyzer = ImpactAnalyzer(graph)

    if args.symbol:
        result = analyzer.analyze_symbol(args.symbol)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_cli_report(result))
    else:
        summary = analyzer.summarize_graph()
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"Indexed {summary['indexed_files']} files, {summary['total_symbols']} symbols, {summary['test_files_count']} test suites.")
            print("Tip: Use --symbol <symbol_name> to calculate blast radius for a specific function/class.")


if __name__ == "__main__":
    main()
