---
name: osv-scanner
description: >-
  Fast polyglot vulnerability scanner and remediation engine (Google OSV-Scanner)
  for dependency manifests and lockfiles (PHP composer.lock, Node package-lock.json/yarn/pnpm/bun,
  Python poetry/Pipfile/requirements/uv, Go go.mod, Rust Cargo.lock, Java pom.xml).
  Use whenever modifying dependencies or before committing code changes to prevent CVE leakage.
---

# Google OSV-Scanner: Fast Polyglot Dependency Security Gate

A high-performance, language-agnostic vulnerability scanning and remediation skill built on **Google OSV-Scanner** and **OSV.dev**.

---

## ⚡ Core Tenets & Capabilities

1. **Ultra-Fast & Memory-Lightweight:**
   - Powered by Go static binaries and the **OSV-SCALIBR** core extraction library.
   - Queries `api.osv.dev` in parallel via lightweight batch HTTP calls rather than downloading hundreds of megabytes of monolithic local CVE databases.
2. **100% Polyglot / Language Agnostic:**
   - **PHP:** `composer.json`, `composer.lock`
   - **JavaScript / TypeScript:** `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`
   - **Python:** `requirements.txt`, `poetry.lock`, `Pipfile.lock`, `uv.lock`, `pdm.lock`
   - **Go:** `go.mod`, `go.sum`
   - **Rust:** `Cargo.toml`, `Cargo.lock`
   - **Java / JVM:** `pom.xml`, Gradle lockfiles (`gradle.lockfile`, `verification-metadata.xml`)
   - **Ruby / .NET:** `Gemfile.lock`, `packages.lock.json`, `*.deps.json`
   - **Containers & SBOM:** Layer-aware OCI containers, SPDX, and CycloneDX specifications.
3. **Pre-Commit Zero Overhead (`--staged`):**
   - In staged mode, execution completes in `<0.05s` if no dependency manifest was changed, avoiding developer friction during regular code commits.
4. **Guided Remediation (`osv-scanner fix`):**
   - Automatically computes optimal dependency upgrade paths with the highest Return on Investment (ROI): fixing the maximum vulnerabilities while introducing minimal breaking changes.
5. **Declarative Debt & Audit Ledger (`osv-scanner.toml`):**
   - Exemptions are strictly auditable with mandatory rationale and expiration dates (`ignoreUntil`).

---

## 🛠️ When AI Agents Must Use This Skill

1. **Whenever Modifying Dependencies:**
   - Running `composer require`, `npm install`, `pnpm add`, `uv add`, `poetry add`, or `cargo add`.
   - Editing any dependency manifest or lockfile manually.
2. **Before Final Git Commit:**
   - Run `osv-scanner-gate --staged` or `osv-scanner scan source .` as part of **The Gauntlet** before committing dependency changes.
3. **When Auditing Existing Codebases:**
   - Running full-project vulnerability audits or triaging CVEs in legacy repositories.

---

## 🚀 Common CLI Commands

### 1. Fast Pre-Commit Gate (Staged Files Only)
Scans only if dependency manifests are staged in git:
```bash
osv-scanner-gate --staged
```
*If no lockfiles/manifests are staged, it exits `0` in <0.05 seconds.*

### 2. Full Project Scan
Scans the current repository recursively:
```bash
osv-scanner-gate --path .
```
Or directly with native OSV-Scanner:
```bash
osv-scanner scan source -r .
```

### 3. Filter by Severity Threshold (CVSS)
Only fail if vulnerabilities meet or exceed a specific CVSS score (e.g., High/Critical >= 7.0):
```bash
osv-scanner-gate --path . --min-severity 7.0
```

### 4. Machine-Readable JSON Output (For Agent / CI Parsing)
```bash
osv-scanner-gate --path . --json
```

### 5. Guided Remediation (Auto-Fix Vulnerable Packages)
Let OSV-Scanner calculate and apply non-breaking patches in-place:
```bash
# Via gate wrapper
osv-scanner-gate --fix

# Or native command targeting specific lockfile
osv-scanner fix -M composer.json -L composer.lock --strategy in-place
osv-scanner fix -M package.json -L package-lock.json --strategy in-place
```

---

## 📝 Documenting Audited Vulnerability Exemptions

When a vulnerability is deemed acceptable (e.g. non-reachable, internal dev dependency, or blocked by upstream framework compatibility), record it in the project root's `osv-scanner.toml`:

```toml
# osv-scanner.toml
[[IgnoredVulns]]
id = "GHSA-7m6h-rg42-m449"
ignoreUntil = 2026-12-31
reason = "Vulnerable path not reachable in current application controller workflow."

[[PackageOverrides]]
name = "internal-core-*"
nameIsRegex = true
ignore = true
reason = "Proprietary internal package namespace."
```

---

## 🧪 Script & Verification Details

- CLI Script: [`scripts/osv_scanner_gate.py`](./scripts/osv_scanner_gate.py)
- Hermetic Unit Tests: [`tests/test_osv_scanner_gate.py`](./tests/test_osv_scanner_gate.py)
- Exit Codes:
  - `0`: Clean / No vulnerabilities (or no staged manifest).
  - `1`: Known vulnerabilities detected above threshold.
  - `2`: System configuration error (e.g., binary missing).
