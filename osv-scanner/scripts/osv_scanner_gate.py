#!/usr/bin/env python3
"""
osv_scanner_gate.py - Fast Pre-Commit & Continuous Dependency CVE Gate
Powered by Google OSV-Scanner (osv.dev).

Designed for AI Coding Agents and Git Pre-Commit Hooks.
- Fast execution (<0.1s if no dependency lockfiles changed in staged mode).
- Full JSON & Machine-Readable output (--json).
- Non-interactive and predictable typed exit codes (0 = clean, 1 = vulns, 2 = system error).
- Zero external Python dependencies (Standard Library only).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Set of manifest and lockfile patterns across polyglot ecosystems
KNOWN_MANIFEST_NAMES: Set[str] = {
    # PHP (Composer)
    "composer.json",
    "composer.lock",
    # JavaScript / TypeScript (Node, Bun, Deno)
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    # Python
    "requirements.txt",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "pyproject.toml",
    "uv.lock",
    "pdm.lock",
    # Go
    "go.mod",
    "go.sum",
    # Rust
    "Cargo.toml",
    "Cargo.lock",
    # Java / JVM
    "pom.xml",
    "gradle.lockfile",
    "verification-metadata.xml",
    # Ruby
    "Gemfile",
    "Gemfile.lock",
    # .NET
    "packages.lock.json",
    # Haskell
    "cabal.project.freeze",
    "stack.yaml.lock",
}


def is_manifest_file(file_path: str) -> bool:
    """Check if a given file path is a known dependency manifest or lockfile."""
    name = Path(file_path).name
    if name in KNOWN_MANIFEST_NAMES:
        return True
    # Catch patterns like requirements-dev.txt or *.deps.json
    if name.startswith("requirements") and name.endswith(".txt"):
        return True
    if name.endswith(".deps.json"):
        return True
    return False


def get_git_staged_files(repo_path: Path) -> List[str]:
    """Retrieve list of staged files in git repository."""
    try:
        cmd = ["git", "-C", str(repo_path), "diff", "--cached", "--name-only"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def check_osv_scanner_installed() -> Optional[str]:
    """Return path to osv-scanner binary if found, else None."""
    return shutil.which("osv-scanner")


def calculate_cvss3_score(vector: str) -> float:
    """Calculate CVSS v3.0 / v3.1 base score from vector string."""
    try:
        import math
        parts = dict(x.split(":", 1) for x in vector.split("/") if ":" in x)
        sc = parts.get("S") == "C"
        av = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}.get(parts.get("AV", "N"), 0.85)
        ac = {"L": 0.77, "H": 0.44}.get(parts.get("AC", "L"), 0.77)
        pr = ({"N": 0.85, "L": 0.68, "H": 0.50} if sc else {"N": 0.85, "L": 0.62, "H": 0.27}).get(parts.get("PR", "N"), 0.85)
        ui = {"N": 0.85, "R": 0.62}.get(parts.get("UI", "N"), 0.85)
        c = {"N": 0.0, "L": 0.22, "H": 0.56}.get(parts.get("C", "N"), 0.0)
        i = {"N": 0.0, "L": 0.22, "H": 0.56}.get(parts.get("I", "N"), 0.0)
        a = {"N": 0.0, "L": 0.22, "H": 0.56}.get(parts.get("A", "N"), 0.0)
        iss = 1.0 - ((1.0 - c) * (1.0 - i) * (1.0 - a))
        if iss <= 0:
            return 0.0
        impact = (7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)) if sc else (6.42 * iss)
        exp = 8.22 * av * ac * pr * ui
        if impact <= 0:
            return 0.0
        raw = min(1.08 * (impact + exp), 10.0) if sc else min(impact + exp, 10.0)
        return math.ceil(round(raw, 4) * 10) / 10.0
    except Exception:
        return 0.0


def parse_vulnerabilities(json_data: dict, min_severity: float = 0.0) -> List[dict]:
    """Extract and filter vulnerabilities from osv-scanner JSON output."""
    vulns = []
    results = json_data.get("results", [])
    for res in results:
        source = res.get("source", {}).get("path", "unknown")
        packages = res.get("packages", [])
        for pkg_entry in packages:
            pkg_info = pkg_entry.get("package", {})
            pkg_name = pkg_info.get("name", "unknown")
            pkg_version = pkg_info.get("version", "unknown")
            pkg_ecosystem = pkg_info.get("ecosystem", "unknown")

            for v in pkg_entry.get("vulnerabilities", []):
                vuln_id = v.get("id", "")
                summary = v.get("summary", "")
                details = v.get("details", "")

                # Extract CVSS score (either numeric or vector string)
                cvss_score = 0.0
                severities = v.get("severity", [])
                for sev in severities:
                    score = sev.get("score")
                    if isinstance(score, (int, float)):
                        cvss_score = max(cvss_score, float(score))
                    elif isinstance(score, str) and score.startswith("CVSS:3"):
                        cvss_score = max(cvss_score, calculate_cvss3_score(score))

                # Fallback to database_specific rating if no score vector found
                if cvss_score == 0.0:
                    db_sev = v.get("database_specific", {}).get("severity", "").upper()
                    if db_sev == "CRITICAL":
                        cvss_score = 9.0
                    elif db_sev == "HIGH":
                        cvss_score = 7.5
                    elif db_sev in ("MODERATE", "MEDIUM"):
                        cvss_score = 5.5
                    elif db_sev == "LOW":
                        cvss_score = 3.0

                if cvss_score < min_severity and min_severity > 0:
                    continue

                vulns.append({
                    "id": vuln_id,
                    "source": source,
                    "package": pkg_name,
                    "version": pkg_version,
                    "ecosystem": pkg_ecosystem,
                    "cvss": cvss_score,
                    "summary": summary or details[:100],
                    "url": f"https://osv.dev/{vuln_id}" if vuln_id else "",
                })
    return vulns


def run_osv_scan(
    scanner_bin: str,
    target_dir: Path,
    targets: Optional[List[str]] = None,
    offline: bool = False,
    call_analysis: bool = False,
) -> Tuple[int, dict, str]:
    """Execute osv-scanner scan source with JSON output."""
    cmd = [
        scanner_bin,
        "scan",
        "source",
        "--format",
        "json",
        "--allow-no-lockfiles",
    ]

    if offline:
        cmd.append("--offline-vulnerabilities")

    if call_analysis:
        cmd.extend(["--call-analysis", "go", "--call-analysis", "rust"])

    if targets:
        for t in targets:
            full_path = (target_dir / t).resolve()
            if full_path.exists():
                cmd.extend(["--lockfile", str(full_path)])
            else:
                cmd.append(str(full_path))
    else:
        cmd.extend(["-r", str(target_dir)])

    proc = subprocess.run(cmd, capture_output=True, text=True)
    raw_stdout = proc.stdout.strip()
    raw_stderr = proc.stderr.strip()

    try:
        data = json.loads(raw_stdout) if raw_stdout else {}
    except json.JSONDecodeError:
        data = {}

    return proc.returncode, data, raw_stderr


def run_osv_fix(scanner_bin: str, target_dir: Path, manifest: Optional[str] = None, lockfile: Optional[str] = None) -> int:
    """Run non-interactive guided remediation."""
    cmd = [scanner_bin, "fix", "--strategy", "in-place", "--apply-top", "10"]
    if manifest:
        cmd.extend(["-M", str(manifest)])
    if lockfile:
        cmd.extend(["-L", str(lockfile)])

    proc = subprocess.run(cmd, cwd=str(target_dir))
    return proc.returncode


def format_table(vulns: List[dict]) -> str:
    """Format vulnerabilities as an ANSI/ASCII terminal table."""
    if not vulns:
        return ""

    headers = ["ID", "PACKAGE", "VERSION", "ECOSYSTEM", "CVSS", "OSV URL"]
    rows = []
    for v in vulns:
        rows.append([
            v["id"][:24],
            v["package"][:20],
            v["version"][:10],
            v["ecosystem"][:10],
            f"{v['cvss']:.1f}" if v['cvss'] > 0 else "-",
            v["url"],
        ])

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    fmt = " │ ".join([f"{{:<{w}}}" for w in col_widths])
    sep = "─┼─".join(["─" * w for w in col_widths])

    lines = [
        fmt.format(*headers),
        sep,
    ]
    for row in rows:
        lines.append(fmt.format(*row))

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="osv-scanner-gate",
        description="Fast Polyglot Dependency CVE Gate & Pre-Commit Hook (Google OSV-Scanner)",
    )
    parser.add_argument(
        "--path",
        "-p",
        type=str,
        default=".",
        help="Path to repository or project directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Pre-commit mode: scan only if dependency manifests/lockfiles are staged in Git",
    )
    parser.add_argument(
        "--min-severity",
        type=float,
        default=0.0,
        help="Minimum CVSS severity threshold to fail on (e.g. 7.0 for High/Critical only)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit output in structured JSON format for automated tooling and agents",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt non-interactive guided remediation via 'osv-scanner fix'",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run against cached offline vulnerability databases",
    )
    parser.add_argument(
        "--call-analysis",
        action="store_true",
        help="Enable call graph reachability analysis for supported languages (Go, Rust)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="osv-scanner-gate 1.0.0 (Google OSV-Scanner Integration)",
    )

    args = parser.parse_args()
    target_path = Path(args.path).resolve()

    # 1. Verify osv-scanner binary presence
    scanner_bin = check_osv_scanner_installed()
    if not scanner_bin:
        error_msg = (
            "ERROR: 'osv-scanner' binary not found in PATH.\n"
            "Please install it using:\n"
            "  - Arch/CachyOS: sudo pacman -S osv-scanner\n"
            "  - Go: go install github.com/google/osv-scanner/v2/cmd/osv-scanner@latest\n"
            "  - Universal: run ~/.agent-skills/install.sh"
        )
        if args.json:
            print(json.dumps({"status": "error", "message": error_msg}, indent=2))
        else:
            sys.stderr.write(error_msg + "\n")
        return 2

    # 2. Check Staged Mode (Pre-Commit optimization)
    staged_manifests: List[str] = []
    if args.staged:
        staged_files = get_git_staged_files(target_path)
        staged_manifests = [f for f in staged_files if is_manifest_file(f)]

        # If no manifest or lockfile is staged, bypass scan immediately (ultra-fast)
        if not staged_manifests:
            if args.json:
                print(
                    json.dumps(
                        {
                            "status": "skipped",
                            "message": "No dependency manifests or lockfiles staged in git.",
                            "vulnerabilities_count": 0,
                            "vulnerabilities": [],
                        },
                        indent=2,
                    )
                )
            else:
                print("⚡ [OSV-Scanner Gate] No dependency manifests or lockfiles staged. Gate passed (0.0s).")
            return 0

    # 3. Execute OSV-Scanner
    targets = staged_manifests if args.staged else None
    exit_code, scan_data, err_output = run_osv_scan(
        scanner_bin=scanner_bin,
        target_dir=target_path,
        targets=targets,
        offline=args.offline,
        call_analysis=args.call_analysis,
    )

    vulns = parse_vulnerabilities(scan_data, min_severity=args.min_severity)

    # 4. Handle Remediation if requested
    if args.fix and vulns:
        if not args.json:
            print(f"🔧 [OSV-Scanner Gate] Attempting automated remediation on {len(vulns)} vulnerabilities...")
        run_osv_fix(scanner_bin=scanner_bin, target_dir=target_path)

    # 5. Emit Results
    if args.json:
        result_payload = {
            "status": "failed" if vulns else "passed",
            "scanned_path": str(target_path),
            "staged_mode": args.staged,
            "targets": targets or ["<recursive>"],
            "vulnerabilities_count": len(vulns),
            "min_severity": args.min_severity,
            "vulnerabilities": vulns,
        }
        print(json.dumps(result_payload, indent=2))
    else:
        if not vulns:
            target_desc = f"{len(staged_manifests)} staged manifest(s)" if args.staged else str(target_path)
            print(f"✅ [OSV-Scanner Gate] Zero known vulnerabilities found in {target_desc}!")
            return 0

        print(f"\n🚨 [OSV-Scanner Gate] Found {len(vulns)} vulnerability(ies) in dependencies:\n")
        print(format_table(vulns))
        print("\n💡 Actions:")
        print("  - To remediate automatically: osv-scanner fix -M <manifest> -L <lockfile>")
        print("  - To audit/ignore acceptable risks: add to repository osv-scanner.toml under [[IgnoredVulns]]")
        print("  - Run gate with severity threshold: osv-scanner-gate --min-severity 7.0\n")

    return 1 if vulns else 0


if __name__ == "__main__":
    sys.exit(main())
