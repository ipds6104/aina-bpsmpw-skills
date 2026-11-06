# VSA Architectural Boundary Enforcement & Repository-Level GEMINI.md

When a repository implements **Vertical Slice Architecture (VSA)** with **SOLID** and **Enterprise Integration Patterns (EIP)**, maintaining architectural boundaries must not rely on developer discipline alone. It must be **deterministically enforced via static linting tools**.

---

## 1. The Core Invariant: Slice Independence

In VSA, every feature slice is autonomous:
* ❌ **Forbidden:** Feature Slice A directly importing internal models, services, or handlers from Feature Slice B (`from features.orders import OrderService` inside `features.billing`).
* ✅ **Permitted:** Communication between slices must strictly occur via:
  1. **Domain Events / In-Memory Pub-Sub** (EIP)
  2. **Message Buses / Mediators** (EIP)
  3. **Shared Core Contracts** (`features/shared/` or `core/contracts/`)

---

## 2. Best-in-Class Open Source Architectural Linters (MIT / Permissive)

Rather than reinventing boundary tools from scratch, configure standard open-source linters in the repository:

### A. JavaScript / TypeScript: `dependency-cruiser` (MIT)
The industry standard for dependency rules and architectural validation.
* **Config file (`.dependency-cruiser.js`):**
```javascript
module.exports = {
  forbidden: [
    {
      name: "no-cross-slice-imports",
      comment: "Vertical slices must not import each other directly. Use events or shared contracts.",
      severity: "error",
      from: { path: "^src/features/([^/]+)/" },
      to: {
        path: "^src/features/([^/]+)/",
        pathNot: ["^src/features/$1/", "^src/features/shared/"]
      }
    }
  ]
};
```
* **Execution:** `npx depcruise --config .dependency-cruiser.js src`

### B. Python: `import-linter` (BSD-2)
Enforces architectural layers and independence contracts in Python.
* **Config file (`.importlinter`):**
```ini
[importlinter]
root_package = myapp

[importlinter:contract:vsa-slice-independence]
name = Vertical slice independence
type = independence
modules =
    myapp.features.orders
    myapp.features.billing
    myapp.features.notifications
    myapp.features.users
```
* **Execution:** `lint-imports`

### C. Go: `depguard` in `golangci-lint` (MIT / Apache-2.0)
Validates package import hierarchies in Go.
* **Config in `.golangci.yml`:**
```yaml
linters-settings:
  depguard:
    rules:
      prevent_cross_slice:
        list-mode: lax
        files:
          - "$all"
          - "!$test"
        deny:
          - pkg: "myapp/features/orders"
            desc: "Use event bus for inter-slice communication."
```

### D. Zero-Dependency Built-in: `vsa_boundary_checker.py` (MIT)
For repositories where installing external tools is undesirable or multi-language checks are required:
* Place `.vsa-boundaries.json` at repo root:
```json
{
  "slice_root": "features",
  "allowed_shared": ["shared", "common", "core", "domain_events"]
}
```
* Run: `python3 vsa_boundary_checker.py .`

---

## 3. Mandatory Repository-Level `GEMINI.md` Guidelines

When initializing any new coding repository, the agent **must create a project-level `GEMINI.md`** at the repository root.

### Strict Rules for Repo-Level `GEMINI.md`:
1. **Self-Contained & Portable:**
   - Because repo-level `GEMINI.md` is committed and pushed to git, it **MUST NOT reference any paths outside the repository** (e.g. no `~/.gemini/config/...`, no `/data/data/...`, no machine-specific absolute directories).
   - **Zero Secrets:** Never write credentials, tokens, or environment secrets in `GEMINI.md`. All secrets must be injected via Infisical or environment variables.
2. **Repository Architecture Scope:**
   - Clearly declare the architectural pattern (e.g. VSA + SOLID + EIP).
   - State the forbidden import rules and how cross-slice communication is achieved.
   - Specify the exact, reproducible Gauntlet commands (linter, boundary check, test runner) to run on that specific codebase.

### Example Template for Repo-Level `GEMINI.md`:

```markdown
# Repository Architecture & Engineering Guidelines

## 1. Architectural Style: Vertical Slice Architecture (VSA) + EIP
- Code is organized by business feature slices inside `src/features/<feature_name>/`.
- Each slice encapsulates its endpoints, request/response models, handlers, and validation (REPR pattern).
- **Boundary Enforcement:** Direct cross-slice imports are strictly forbidden. Slices communicate via Domain Events and Message Dispatchers.

## 2. The Verification Gauntlet
Before submitting any changes, verify correctness with these local deterministic checks:
1. **VSA Boundary Check:** `npx depcruise --config .dependency-cruiser.js src` (or `lint-imports`)
2. **Static Analysis & Linting:** `npm run lint` (or `ruff check .`)
3. **Typecheck:** `npm run typecheck` (or `mypy .`)
4. **Parallel Test Suite:** `npm test -- --maxWorkers=50%` (or `pytest -n auto`)

## 3. SOLID & Single Responsibility Principle
- Functions must remain under 50 lines; components/classes under 180 lines. Decompose bloated units into subcomponents.
- External dependencies (databases, payment clients, mailers) must be injected via constructor dependency injection.
```
