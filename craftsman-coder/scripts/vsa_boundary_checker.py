#!/usr/bin/env python3
"""
VSA Architectural Boundary Checker (Repo-Agnostic, MIT)

Deterministically enforces Vertical Slice Architecture (VSA) boundaries:
- Forbids direct cross-slice imports between independent business feature slices.
- Slices must communicate via Domain Events, Message Buses, or designated Shared Core contracts.
- Zero-dependency: Runs natively in Python 3 on any repo (Python, TS/JS, Go, Rust).
- Compatible with config files (.vsa-boundaries.json).
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Set, Optional


@dataclass
class BoundaryViolation:
    file_path: str
    line: int
    source_slice: str
    target_slice: str
    import_statement: str
    message: str


class VsaBoundaryChecker:
    IMPORT_PATTERNS = [
        # Python: from features.orders.service import X | import features.orders
        re.compile(r"^(?:from|import)\s+([a-zA-Z0-9_\.]+)"),
        # JS/TS/Go/Rust: import ... from '.../features/orders/...' | import ".../features/orders/..."
        re.compile(r"(?:import|from|require)\s*(?:\(?\s*['\"]([^'\"]+)['\"])"),
    ]

    def __init__(self, slice_root: str = "features", allowed_shared: Optional[List[str]] = None):
        self.slice_root = slice_root.strip("/")
        self.allowed_shared = set(allowed_shared or ["shared", "common", "core", "domain_events", "contracts"])

    @classmethod
    def from_config(cls, root_dir: Path) -> VsaBoundaryChecker:
        config_path = root_dir / ".vsa-boundaries.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                return cls(
                    slice_root=data.get("slice_root", "features"),
                    allowed_shared=data.get("allowed_shared", ["shared", "common", "core", "domain_events"]),
                )
            except Exception:
                pass
        return cls()

    def extract_slice_name(self, rel_path: str) -> Optional[str]:
        # rel_path e.g. "src/features/orders/create/handler.py" or "features/billing/charge.ts"
        parts = Path(rel_path).parts
        if self.slice_root in parts:
            idx = parts.index(self.slice_root)
            if idx + 1 < len(parts):
                slice_name = parts[idx + 1]
                if slice_name not in self.allowed_shared:
                    return slice_name
        return None

    def target_slice_from_import(self, import_str: str, current_file: Path, repo_dir: Path) -> Optional[str]:
        # Handle relative imports e.g. ../notifications/service
        if import_str.startswith("."):
            try:
                resolved_target = (current_file.parent / import_str).resolve()
                rel_to_repo = resolved_target.relative_to(repo_dir.resolve()).as_posix()
                return self.extract_slice_name(rel_to_repo)
            except Exception:
                pass

        # Normalize slashes and dots for package/alias imports (e.g. features.orders or @/features/orders)
        normalized = import_str.replace(".", "/").replace("\\", "/")
        parts = normalized.split("/")
        if self.slice_root in parts:
            idx = parts.index(self.slice_root)
            if idx + 1 < len(parts):
                candidate = parts[idx + 1]
                if candidate not in self.allowed_shared:
                    return candidate
        return None

    def scan(self, repo_dir: Path) -> List[BoundaryViolation]:
        violations: List[BoundaryViolation] = []
        exclude_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}

        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() not in [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"]:
                    continue

                rel_path = file_path.relative_to(repo_dir).as_posix()
                source_slice = self.extract_slice_name(rel_path)
                if not source_slice:
                    continue  # File does not belong to a specific feature slice

                try:
                    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
                except Exception:
                    continue

                for line_idx, line in enumerate(lines, start=1):
                    stripped = line.strip()
                    if not stripped or stripped.startswith(("#", "//", "/*", "*")):
                        continue

                    for pat in self.IMPORT_PATTERNS:
                        match = pat.search(stripped)
                        if match:
                            import_target = match.group(1)
                            target_slice = self.target_slice_from_import(import_target, file_path, repo_dir)
                            if target_slice and target_slice != source_slice:
                                violations.append(
                                    BoundaryViolation(
                                        file_path=rel_path,
                                        line=line_idx,
                                        source_slice=source_slice,
                                        target_slice=target_slice,
                                        import_statement=stripped,
                                        message=(
                                            f"Slice '{source_slice}' directly imports slice '{target_slice}' "
                                            f"('{import_target}'). Cross-slice direct coupling is forbidden in VSA. "
                                            f"Decouple via Domain Events, Message Bus, or Shared Contracts."
                                        ),
                                    )
                                )
        return violations


def format_report(violations: List[BoundaryViolation], slice_root: str) -> str:
    lines = [
        "=" * 68,
        f"🛡️  VERTICAL SLICE ARCHITECTURE (VSA) BOUNDARY AUDIT: '{slice_root}'",
        "=" * 68,
    ]
    if not violations:
        lines.append("✅ ALL SLICES COMPLIANT: Zero illegal cross-slice imports detected!")
        lines.append("=" * 68)
        return "\n".join(lines)

    lines.append(f"❌ DETECTED {len(violations)} VSA BOUNDARY VIOLATION(S):")
    lines.append("-" * 68)
    for v in violations:
        lines.append(f"• [{v.file_path}:{v.line}]")
        lines.append(f"  Violation : Slice '{v.source_slice}' ──❌──> Slice '{v.target_slice}'")
        lines.append(f"  Statement : {v.import_statement}")
        lines.append(f"  Fix       : {v.message}")
        lines.append("")
    lines.append("=" * 68)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Deterministic VSA Architectural Boundary Checker")
    parser.add_argument("path", nargs="?", default=".", help="Root of repository (default: .)")
    parser.add_argument("--slice-root", default=None, help="Root folder for slices (default: 'features' or from config)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    repo_dir = Path(args.path).resolve()
    if not repo_dir.exists():
        print(f"Error: Path '{repo_dir}' does not exist.", file=sys.stderr)
        sys.exit(2)

    checker = VsaBoundaryChecker.from_config(repo_dir)
    if args.slice_root:
        checker.slice_root = args.slice_root.strip("/")

    violations = checker.scan(repo_dir)

    if args.json:
        data = {
            "total_violations": len(violations),
            "compliant": len(violations) == 0,
            "violations": [asdict(v) for v in violations],
        }
        print(json.dumps(data, indent=2))
    else:
        print(format_report(violations, checker.slice_root))

    if violations:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
