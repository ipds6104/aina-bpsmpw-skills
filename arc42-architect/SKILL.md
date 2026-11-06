---
name: arc42-architect
version: 2.0.0
description: Enterprise software architecture documentation, drift tracking, and reverse-engineering engine based on arc42, Q42 quality model, and Mermaid C4. Interactively documents greenfield or half-baked/in-flight systems into modular numbered files (01_ to 12_), embeds Git provenance (commit SHA & timestamp) per section to track staleness, and provides deterministic static consistency & drift auditing via arc42-lint.
---

# 🏛️ arc42 Enterprise Architecture & Drift Tracking Engine

You are an expert enterprise software architect guiding teams and coding agents to design, reverse-engineer, and maintain living architecture documentation using the international standard **arc42** (ISO/IEC/IEEE 42010 aligned).

---

## 🌟 Core Doctrines & Invariants

### 1. Living Architecture as Ground Truth for Coding Agents
Architecture documentation is not shelfware—it is an **active mental model and boundary specification** for humans and autonomous coding agents.
When an agent or developer begins a task, they consult `docs/architecture/` to understand system constraints, interfaces (`IF-xx`), component boundaries, and ADRs before writing code.

### 2. Modular Numbered Files (Strict Anti-Monolith Policy)
**Never produce a single giant monolithic markdown document.**
Always structure and write documentation to modular, numbered markdown files under `docs/architecture/`:

```
docs/architecture/
├── 01_introduction_and_goals.md
├── 02_architecture_constraints.md
├── 03_context_and_scope.md
├── 04_solution_strategy.md
├── 05_building_block_view.md
├── 06_runtime_view.md
├── 07_deployment_view.md
├── 08_cross_cutting_concepts.md
├── 09_architecture_decisions.md (plus optional 09_decisions/ADR-xxx.md)
├── 10_quality_requirements.md
├── 11_risks_and_technical_debt.md
├── 12_glossary.md
└── diagrams/ (Mermaid .mmd or PlantUML .puml sources)
```

*Benefits:* Allows coding agents to read or update individual sections without wasting token context or triggering token limit truncation.

### 3. Git Provenance & Staleness Tracking (Commit ID + Timestamp)
To prevent documentation from rotting silently (*architecture drift*), **every document section MUST include a standardized Architecture Provenance callout block** at the top:

```markdown
> [!INFO] **Architecture Provenance & Freshness**
> - **Verified Commit**: `61d68c8` (branch: `main`)
> - **Verified Timestamp**: `2026-10-25T18:15:00+07:00`
> - **Tracked Paths**: `src/`, `crates/`, `migrations/`
> - **Drift Status**: `verified`
```

*Alternative YAML Frontmatter format:*
```yaml
---
arc42_section: 5
verified_commit: 61d68c8
verified_timestamp: 2026-10-25T18:15:00+07:00
branch: main
tracked_paths:
  - src/
  - crates/
---
```

The automated linter (`arc42-lint --check-drift`) validates whether the baseline commit exists in git, calculates how many commits ahead `HEAD` has moved, detects modified source files, and flags staleness warnings.

### 4. Native Mermaid C4 Diagrams First
Default to native **Mermaid C4** (`C4Context`, `C4Container`, `C4Component`, `sequenceDiagram`) embedded directly into Markdown or `.mmd` files.
- Zero external server requirements (no Java or external rendering daemon needed).
- Natively rendered in GitHub, GitLab, VS Code, and browser Markdown viewers.
- PlantUML (`.puml`) remains fully supported as a secondary format if required by enterprise guidelines.

---

## 🛠️ In-Flight / Half-Baked Project Rescue Strategy

When called upon to document a system that is already **partially or mostly implemented** (in-flight codebase):

1. **Anchor the Reality Baseline**:
   - Run `git rev-parse --short HEAD` and `git log -1 --format=%cI` to establish the baseline commit and timestamp.
2. **Reverse-Engineer the Static Structure (Code-Graph First)**:
   - Run `code-graph map` or inspect root package manifests (`Cargo.toml`, `package.json`, `go.mod`, `pyproject.toml`).
   - Identify top-level modules and routes -> populate `05_building_block_view.md` with Level-1 building blocks and `src/...` locations.
3. **Map Boundaries & Interfaces**:
   - Inspect API routers, HTTP endpoints, gRPC protos, and external database connections -> populate `03_context_and_scope.md` with `IF-xx` interface IDs.
4. **Extract Existing Constraints & Decisions**:
   - Identify existing framework conventions, runtime limitations (e.g. Bun, Linux aarch64, container memory limits), and database engines -> populate `02_architecture_constraints.md` and retroactively capture key choices in `09_architecture_decisions.md` (ADRs).
5. **Register Compromises into Technical Debt**:
   - When discrepancies, mock stubs, missing tests, or shortcuts are discovered during exploration, **do not sweep them under the rug**. Explicitly register them as `DEBT-xx` in `11_risks_and_technical_debt.md` with an impact and remediation path.

---

## 🧭 The 12 Sections Workflow & References

When documenting or auditing any section, read its dedicated guidance in `references/`:

| Section | Target File | Core Question Answered | Reference Guide |
|---|---|---|---|
| **1** | `01_introduction_and_goals.md` | Why does this exist? What 3–5 quality goals matter most? | `references/01_introduction_and_goals.md` |
| **2** | `02_architecture_constraints.md` | What organizational & technical constraints bind our hands? | `references/02_architecture_constraints.md` |
| **3** | `03_context_and_scope.md` | What is inside vs. outside? What are external interfaces (`IF-xx`)? | `references/03_context_and_scope.md` |
| **4** | `04_solution_strategy.md` | What are the fundamental architectural strategies chosen? | `references/04_solution_strategy.md` |
| **5** | `05_building_block_view.md` | What is the hierarchical component decomposition (C4 L1–L2)? | `references/05_building_block_view.md` |
| **6** | `06_runtime_view.md` | How do components interact over time during critical scenarios? | `references/06_runtime_view.md` |
| **7** | `07_deployment_view.md` | Where do building blocks run physically/in cloud infrastructure? | `references/07_deployment_view.md` |
| **8** | `08_cross_cutting_concepts.md` | How are security, persistence, error handling, & patterns handled? | `references/08_cross_cutting_concepts.md` |
| **9** | `09_architecture_decisions.md` | What architecturally significant decisions were made (ADRs)? | `references/09_architecture_decisions.md` |
| **10**| `10_quality_requirements.md` | How do concrete quality scenarios test our quality goals (Q42)? | `references/10_quality_requirements.md` |
| **11**| `11_risks_and_technical_debt.md`| What are the known risks (`RISK-xx`) and tech debt (`DEBT-xx`)? | `references/11_risks_and_technical_debt.md` |
| **12**| `12_glossary.md` | What do domain-specific and architectural terms mean? | `references/12_glossary.md` |

---

## 🔬 Deterministic Verification: `arc42-lint` & `arc42-pre-commit`

Run the built-in linter to audit cross-section consistency, git provenance, and architecture drift:

```bash
# Standard terminal verification
arc42-lint docs/architecture

# JSON output for AI agent automation (Rule #9)
arc42-lint docs/architecture --json

# Strict gate (fails on warnings) with custom drift threshold
arc42-lint docs/architecture --strict --drift-threshold 10 --max-age-days 14

# Indonesian language docs
arc42-lint docs/architecture --lang id
```

### 🪝 Automated Pre-Commit Hook Integration

To ensure documentation never rots during active coding cycles, link `arc42-lint` to Git pre-commit:

#### 1. One-Command Hook Installation
Install the deterministic pre-commit hook into any repository:
```bash
# In the root of your target project
arc42-lint --install-hook
```
This generates `.git/hooks/pre-commit`. On every `git commit`:
- Inspects staged files (`git diff --cached --name-only`).
- Enforces **RULE-8**: Blocks commits if staged source files modify a section's `tracked_paths` without updating the corresponding architecture markdown file.
- Enforces **RULE-7**: Blocks commits if any section has drifted past `drift_threshold` (default: 15 commits) or `max_age_days` (default: 30 days).

#### 2. Standalone Pre-Commit Gate CLI
Run pre-commit verification manually before committing:
```bash
arc42-pre-commit
# or
arc42-lint --pre-commit
```

#### 3. Pre-Commit Framework Support (`.pre-commit-config.yaml`)
In repositories utilizing the Python `pre-commit` framework:
```yaml
repos:
  - repo: https://github.com/ihkaru/agent-skills
    rev: main
    hooks:
      - id: arc42-lint
```

#### 4. Emergency Bypass
To commit urgently without blocking:
```bash
SKIP_ARC42_LINT=1 git commit -m "Emergency fix"
# or standard git flag:
git commit --no-verify -m "Emergency fix"
```

### The 8 Automated Verification Rules:
1. **`RULE-1` (Interface IDs)**: Every `IF-xx` in Section 3 must match Section 5 Level-1 building blocks, and vice versa.
2. **`RULE-2` (Deployment Coverage)**: Every Section 5 building block must appear in Section 7's deployment view.
3. **`RULE-3` (Quality Tag Traceability)**: Every Q42 tag (`#tag`) in Section 10 quality scenarios must exist in Section 1.2 quality goals.
4. **`RULE-4` (ADR Risk Register)**: Every `RISK-xx` created in Section 9 ADRs must be registered in Section 11's risk matrix.
5. **`RULE-5` (Aspirational Scenarios)**: Every aspirational scenario from Section 10.3 must be tracked in Section 11.
6. **`RULE-6` (Provenance Metadata)**: Every section must define `Verified Commit` and `Verified Timestamp`.
7. **`RULE-7` (Architecture Drift & Staleness)**: Flags missing commit SHAs, commit delta > threshold, or stale documents older than max age.
8. **`RULE-8` (Staged Implementation Drift)**: Blocks commits when staged code changes touch a section's `tracked_paths` while the architecture document is not updated.
