#!/usr/bin/env python3
"""
CLI Entrypoint for Zero-Mock Static Analysis Detector.
Run via: detect-mocks [path] [--json] [--strict]
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add script directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from detector import ZeroMockDetector
from rules import Severity

COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_GREEN = "\033[92m"
COLOR_CYAN = "\033[96m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

def print_banner():
    print(f"{COLOR_BOLD}{COLOR_CYAN}=================================================================={COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}    🛡️  ZERO-MOCK & SILENT MOCK STATIC DETECTOR (AST / CODE-GRAPH)  {COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}    Enterprise High-Assurance Codebase Gatekeeper (Oct 2026)      {COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}=================================================================={COLOR_RESET}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Zero-Mock & Silent Mock Static Detector based on AST Code-Graph"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Target project directory to analyze (default: current directory)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output findings in structured JSON format"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero on any finding (even Medium/Low)"
    )
    parser.add_argument(
        "--no-codegraph",
        action="store_true",
        help="Disable automatic code-graph index synchronization"
    )

    args = parser.parse_args()
    target_path = Path(args.path).resolve()

    if not target_path.exists():
        if args.json:
            print(json.dumps({"error": f"Path not found: {target_path}"}))
        else:
            print(f"{COLOR_RED}Error: Target path does not exist: {target_path}{COLOR_RESET}")
        sys.exit(1)

    if not args.json:
        print_banner()
        print(f"[*] Scanning workspace: {COLOR_BOLD}{target_path}{COLOR_RESET}")

    detector = ZeroMockDetector(str(target_path), use_codegraph=not args.no_codegraph)

    if not args.json and detector.debt_ledger:
        print(f"[*] Repository Debt Ledger: {COLOR_BOLD}{len(detector.debt_ledger)} documented exemptions loaded{COLOR_RESET}")

    findings = detector.scan()

    if args.json:
        output = {
            "workspace": str(target_path),
            "documented_exemptions": len(detector.debt_ledger),
            "total_findings": len(findings),
            "findings": [f.to_dict() for f in findings],
        }
        print(json.dumps(output, indent=2))
    else:
        if not findings:
            print(f"\n{COLOR_BOLD}{COLOR_GREEN}[✓] ZERO-MOCK COMPLIANT:{COLOR_RESET} No untracked mock leakage, silent mocks, or fake latency detected in production paths.")
            sys.exit(0)

        print(f"\n{COLOR_BOLD}{COLOR_RED}[!] VIOLATIONS DETECTED: Found {len(findings)} mock pattern(s) in production paths:{COLOR_RESET}\n")
        counts = {Severity.CRITICAL: 0, Severity.HIGH: 0, Severity.MEDIUM: 0, Severity.LOW: 0}

        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
            badge = f"{COLOR_RED}[CRITICAL]{COLOR_RESET}" if f.severity == Severity.CRITICAL else (
                f"{COLOR_YELLOW}[HIGH]{COLOR_RESET}" if f.severity == Severity.HIGH else f"{COLOR_YELLOW}[{f.severity.value}]{COLOR_RESET}"
            )
            print(f"  {badge} {COLOR_BOLD}{f.file_path}:{f.line_number}{COLOR_RESET}")
            print(f"      Rule: {f.rule_id}")
            print(f"      Issue: {f.message}")
            if f.code_snippet:
                print(f"      Code: {COLOR_CYAN}{f.code_snippet}{COLOR_RESET}")
            print()

        print("------------------------------------------------------------------")
        print(f"Summary: {COLOR_RED}{counts[Severity.CRITICAL]} Critical{COLOR_RESET}, "
              f"{COLOR_YELLOW}{counts[Severity.HIGH]} High{COLOR_RESET}, "
              f"{counts[Severity.MEDIUM]} Medium, {counts[Severity.LOW]} Low")

    # Determine exit code
    has_critical_or_high = any(f.severity in (Severity.CRITICAL, Severity.HIGH) for f in findings)
    if has_critical_or_high or (args.strict and len(findings) > 0):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
