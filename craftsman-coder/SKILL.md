---
name: craftsman-coder
description: >-
  Enforces SOLID principles (specifically Single Responsibility), Dependency Injection,
  Vertical Slice Architecture with Enterprise Integration Patterns (as architectural fallback),
  deterministic VSA boundary linting, portable repository-level GEMINI.md generation,
  real-time web research for optimal Big-O algorithmic complexity, high-performance & low-RAM
  open-source libraries with enterprise-safe licensing (MIT/Apache-2.0/BSD), deterministic static
  analysis for SRP & abstraction bypasses, framework-first conventions, parallel-ready test suites,
  CodeGraph/AST blast radius impact analysis, centralized secret injection via Infisical,
  AI-agent-ready tool design, and the Old Coder evidence-first TDD methodology.
  Activate whenever planning, exploring, refactoring, deploying, or writing code in any project.
---

# Craftsman Coder: SOLID, AST CodeGraph Impact, & Evidence-First Engineering

A disciplined, repo-agnostic engineering workflow for building robust, decoupled, and verifiable software.

---

## Core Tenets

1. **AST & CodeGraph Exploration First:**
   Never modify or refactor code blindly. Always map out symbol definitions, callers, callees, and the **blast radius** before altering implementation.
2. **SOLID & Single Responsibility Principle (SRP):**
   Every module, function, and class must have one single reason to change. Separate business logic from I/O, persistence, and external APIs.
   - *Decomposition Rule:* If 1 component, class, or function is too long or handles multiple concerns, immediately break it down into smaller, atomic subcomponents/services with single responsibilities.
3. **Dependency Injection (DI) & Inversion of Control:**
   Inject dependencies (repositories, clients, loggers) via constructors or framework mechanisms. Decouple logic from concrete infrastructure. Avoid hardcoded direct external instantiations.
4. **Fallback Architecture: Vertical Slice Architecture (VSA) + EIP:**
   If a repository does not possess an established framework convention, **always prioritize Vertical Slice Architecture (VSA) coupled with SOLID and Enterprise Integration Patterns (EIP)**:
   - Organize code by business capabilities (`features/<feature_name>/`) using the Request-Endpoint-Response (REPR) pattern rather than horizontal technical layers.
   - Employ EIP patterns for slice coordination: Command/Query Routers, Pipes and Filters, Idempotent Receivers, and Domain Event Pub/Sub.
   - Detailed guide: [Vertical Slice & EIP Guide](./references/vertical_slice_eip_architecture.md)
5. **Deterministic VSA Architectural Boundary Linting:**
   When a repo implements VSA, configure a deterministic boundary linter (e.g. `dependency-cruiser` for JS/TS, `import-linter` for Python, `depguard` for Go, or `vsa_boundary_checker.py`) to forbid direct cross-slice imports.
   - Detailed guide: [VSA Boundary Enforcement & Repo GEMINI.md Guide](./references/vsa_boundary_enforcement.md)
6. **Mandatory Repository-Level `GEMINI.md` (Portable & Git-Ready):**
   When creating or initializing any repository, **always generate a project-level `GEMINI.md` at the repo root** to persist architectural choices, boundary rules, and Gauntlet commands.
   - *Strict Portability Rule:* Because this file is committed and pushed, **NEVER reference external host paths** (e.g. no `~/.gemini/config/...`, no `/data/data/...`) or machine-specific secrets. It must be 100% self-contained and portable.
7. **Real-Time Web Research & Optimal Big-O Complexity:**
   Always select algorithm and data structure patterns with the most optimal Big-O time and space complexity ($O(1)$ lookups, $O(N \log N)$ sorting, streaming $O(1)$ memory).
   - *Mandatory Web Research:* Never rely solely on pre-trained assumptions as knowledge may be outdated. Always research the web based on the current month and year to discover state-of-the-art algorithmic patterns, optimal data structures, and latest high-performance library implementations.
8. **High-Performance, Low-RAM Libraries & Enterprise License Compliance:**
   - **Peak Performance & Low Memory:** Prefer modern, cache-friendly, zero-copy, SIMD-accelerated libraries (e.g. `orjson`/`msgspec`, `polars`, `sonic`, `zerolog`, `simd-json`, `fast-json-stringify`).
   - **Enterprise License Compliance:** Select permissive open-source licenses (**MIT, Apache 2.0, BSD-2/3, ISC**). Strictly avoid viral copyleft (`GPL`, `AGPL`, `SSPL`) to ensure seamless passing of enterprise audits without source disclosure liabilities.
   - Detailed guide: [High-Performance Libraries & Licensing Guide](./references/high_performance_libraries_licensing.md)
9. **Deterministic Static Code Analysis for SRP & Abstractions:**
   Always prioritize deterministic static analysis tools to audit code for SRP violations (e.g., bloated length, excessive responsibilities) and abstraction bypasses (e.g. direct raw SQL or HTTP calls inside presentation/business logic).
10. **Centralized Secret Injection (Infisical):**
    Never hardcode secrets or store raw credentials in git/local env files. Treat secrets as runtime injected dependencies via Infisical (`infisical run -- ...`).
    - Detailed guide: [Infisical Secret Management Guide](./references/secret_management_infisical.md)
11. **Framework Convention First:**
    Respect idiomatic conventions of the existing framework (e.g. FastAPI `Depends`, NestJS `@Injectable`, React hooks, Go interfaces) rather than inventing ad-hoc abstractions.
12. **Parallelizable, Hermetic Testing:**
    All tests must be stateless, isolated, and parallel-ready (e.g., `pytest -n auto`, `go test -parallel`). No shared mutable state or static singleton side-effects.
13. **The "Old Coder" Evidence-First Discipline:**
    Review evidence, not code. Follow the Spec -> RED -> GREEN -> REFACTOR loop and verify through automated terminal checks before reporting completion.
14. **AI-Agent-Ready Tool & Skill Engineering:**
    When extracting repeating patterns into tools and skills: guarantee `--json` output, non-interactive execution (zero prompts), `--dry-run` safety, predictable noun-action verbs, and typed exit codes.
    - Detailed guide: [AI-Agent-Ready CLI Design Guide](./references/agent_ready_cli_design.md)

---

## Step-by-Step Workflow

### Step 1: Pre-Change Blast Radius Analysis (CodeGraph AST)
Before modifying a function, class, or service, inspect the blast radius to determine downstream impact:

```bash
python3 ~/.gemini/config/skills/craftsman-coder/scripts/codegraph_impact.py <path_to_repo> --symbol <TargetSymbol>
```

- Review **Direct Callers** and **Referencing Files**.
- Review **Affected Test Suites**: If no tests cover this symbol, you must create one before refactoring.

### Step 2: Architecture, Algorithmic Big-O & Repo-Level GEMINI.md
- Formulate a clear specification and design:
  - If creating/initializing a repo, create a self-contained **`GEMINI.md` at repo root** (zero external paths, zero secrets).
  - If no framework convention exists, organize into **Vertical Slices** (`features/<name>/`) with REPR and EIP patterns.
  - Set up or verify **architectural boundary linter** (e.g. `dependency-cruiser`, `import-linter`, or `vsa_boundary_checker.py`).
  - Is the class/function/component doing more than one thing or exceeding length thresholds? Decompose it into focused subcomponents (SRP).
  - Are external systems tightly coupled? Define an interface/protocol and use Dependency Injection.
  - **Algorithmic Complexity & Web Search:** Benchmark the Big-O time/space complexity. Actively search the web per the current month and year for modern algorithmic optimizations.
  - **Dependency Audit:** Choose low-RAM, high-throughput libraries with enterprise-safe licenses (**MIT / Apache 2.0 / BSD**). Ensure zero copyleft/AGPL transitive dependencies.
- Detailed reference: [SOLID & DI Patterns Guide](./references/solid_di_patterns.md)
- Detailed reference: [Vertical Slice & EIP Guide](./references/vertical_slice_eip_architecture.md)
- Detailed reference: [VSA Boundary Enforcement & Repo GEMINI.md Guide](./references/vsa_boundary_enforcement.md)
- Detailed reference: [High-Performance Libraries & Licensing Guide](./references/high_performance_libraries_licensing.md)

### Step 3: Write Parallelizable Tests (RED)
- Write an isolated, hermetic unit or integration test verifying the expected behavior or bug fix.
- Ensure the test uses independent temporary resources or in-memory mocks.
- Run the test to confirm it fails (**RED**).
- Detailed reference: [Parallel Testing & Old Coder Guide](./references/parallel_testing.md)

### Step 4: Implement Minimal, Clean Solution (GREEN)
- Implement only what is required to satisfy the test.
- Keep components cohesive and single-purposed.
- Inject dependencies cleanly.

### Step 5: Refactor & The Gauntlet (REFACTOR & EVIDENCE)
- Clean up the code while tests stay green.
- Run **The Gauntlet** (all verification must be automated & deterministic):
  1. **VSA Boundary Check:**
     Run architectural boundary check (e.g., `npx depcruise --config .dependency-cruiser.js src` or `python3 ~/.gemini/config/skills/craftsman-coder/scripts/vsa_boundary_checker.py <path_to_repo>`).
  2. **Deterministic Static SRP & Abstraction Analysis:**
     ```bash
     python3 ~/.gemini/config/skills/craftsman-coder/scripts/static_srp_analyzer.py <path_to_repo> --strict
     ```
  3. **Zero-Mock & Silent Fallback Audit (Dual-Tier Verification Gate):**
     ```bash
     detect-mocks <path_to_repo> --strict
     ```
  4. **Dependency Security & CVE Gate (Google OSV-Scanner):**
     ```bash
     osv-scanner-gate --staged
     ```
     *(If manifests/lockfiles were modified, scans for known CVEs before committing. Resolves via `osv-scanner fix`).*
  5. **Linter & Static Analysis** (e.g. `ruff check .`, `eslint`, `golangci-lint`)
  6. **Type Checking** (e.g. `mypy`, `tsc --noEmit`)
  7. **Full Test Suite** executed in parallel (e.g. `pytest -n auto`, `go test -parallel 4 ./...`)
- Provide terminal evidence (exit codes, passing test summary) in your final response.

---

## Built-in Scripts & Tools

- **Google OSV-Scanner Dependency Gate:**
  `osv-scanner-gate` / [`skills/osv-scanner/`](../osv-scanner/)
  - High-performance, language-agnostic dependency CVE scanner and remediation gate.
  - Zero-overhead git staged mode (`osv-scanner-gate --staged`), machine-readable JSON output, and `osv-scanner fix` guided remediation.

- **Zero-Mock & Silent Fallback Static Detector:**
  `detect-mocks` / [`skills/zero-mock-detector/`](../zero-mock-detector/)
  - Inspects AST and code paths for mock frameworks, fake latency, silent fallbacks, bodyless stubs, and agent note pollution.
  - Automatically respects repository-level debt ledgers (`docs/TECHNICAL_DEBT.md` / `.zero-mock-allowlist.json`) while enforcing zero-mock in global tools.

- **CodeGraph AST Impact Analyzer:**
  [`scripts/codegraph_impact.py`](./scripts/codegraph_impact.py)
  - Inspects AST and cross-references across Python, JS/TS, Go, Rust, Java.
  - Computes blast radius risk level (Low, Medium, High, Critical).
  - Identifies direct callers and affected test suites.

- **Deterministic Static SRP & Abstraction Analyzer:**
  [`scripts/static_srp_analyzer.py`](./scripts/static_srp_analyzer.py)
  - Evaluates code for SRP length/complexity violations.
  - Flags abstraction bypasses (raw SQL/HTTP calls outside repositories/adapters).
  - Emits machine-readable `--json` and deterministic exit codes for CI/Old Coder verification.

- **VSA Architectural Boundary Checker:**
  [`scripts/vsa_boundary_checker.py`](./scripts/vsa_boundary_checker.py)
  - Enforces slice isolation by preventing illegal cross-slice imports.
  - Configurable via `.vsa-boundaries.json`. Zero-dependency, repo-agnostic (MIT).
