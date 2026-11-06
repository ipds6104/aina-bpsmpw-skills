# Parallelizable Testing & The "Old Coder" Evidence-First Methodology

## 1. Designing Parallelizable, Hermetic Tests
For tests to run concurrently without flaky failures or race conditions:

1. **Zero Shared Mutable State:**
   - Never write to shared global variables, static class state, or common disk locations.
   - Use dynamic temporary directories (e.g. `tempfile.TemporaryDirectory()`, `tmp_path` fixture in Pytest).
2. **Hermetic Test Environments:**
   - Mock external network calls and third-party APIs using injected mocks or in-memory stubs.
   - For database tests, use per-test transactions with automatic rollback, or isolated in-memory instances (e.g., SQLite `:memory:` or isolated tenant schemas).
3. **Parallel Execution Commands:**
   - **Python:** `pytest -n auto` (via `pytest-xdist`)
   - **Go:** `go test -parallel <N> ./...`
   - **Rust:** `cargo test` (parallel by default across threads)
   - **Node/TS:** `vitest --threads` or `jest --maxWorkers=50%`

---

## 2. The "Old Coder" Methodology (Evidence-First Engineering)

Inspired by veteran software engineering principles (Robert C. "Uncle Bob" Martin):

> *"Review evidence, not code."*

Relying purely on line-by-line inspection of AI-generated code is error-prone. The agent must provide verifiable proof of correctness through automated gates.

### The 4-Step Cycle:
1. **The SPEC (Before Code):**
   - Formulate a concise specification, boundary cases, and test plan.
   - Map out the system impact using CodeGraph/AST analysis (`codegraph_impact.py`).
2. **The TDD Loop (Automated):**
   - **RED:** Write a targeted, failing test that asserts the new behavior or reproduces the bug.
   - **GREEN:** Write the minimal, single-responsibility code needed to pass the test.
   - **REFACTOR:** Clean up code, decompose bloated units into smaller SRP subcomponents, and enforce DI without breaking tests.
3. **The Gauntlet (Rigorous Deterministic Verification):**
   - **Step A: Deterministic Static Analysis (SRP & Abstraction):**
     Run `python3 ~/.gemini/config/skills/craftsman-coder/scripts/static_srp_analyzer.py <path> --strict` to verify no bloated components (> 180 lines) or raw SQL/HTTP abstraction bypasses exist.
   - **Step B: Linter & Static Analysis:**
     Run `ruff`, `eslint`, `golangci-lint`, or `clippy`.
   - **Step C: Type Checking:**
     Run `mypy`, `tsc --noEmit`, or `pyright`.
   - **Step D: Parallel Test Suite:**
     Run all hermetic tests concurrently.
4. **The EVIDENCE (Terminal Output):**
   - Present verifiable test execution logs, exit codes, and diff analysis to the user.
