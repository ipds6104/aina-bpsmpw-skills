# Best Practices: Building AI-Agent-Ready CLI Tools & Skills

Designing Command Line Interfaces (CLIs) and custom skills for autonomous AI coding agents requires a different paradigm than designing for human users. Human CLIs optimize for visual aesthetics (spinners, multi-color tables, interactive arrow-key menus). For AI agents, these interactive embellishments cause deadlocks, parsing failures, and high token waste.

An **Agent-Ready Tool** treats the shell as a clean, programmatic API.

---

## 1. Machine-Readability First
* **Guaranteed `--json` Output:**
  Every data-querying, inspection, or status command must support `--json` (e.g., `tool status --json`). The JSON output must be strictly valid JSON sent to `stdout` with errors sent to `stderr`.
* **Deterministic Semantic Exit Codes:**
  - `0`: Success / Passed.
  - `1`: Domain or verification failure (e.g. tests failed, SRP violation detected).
  - `2`: CLI usage / argument syntax error.
  - `124`: Timeout.
  Never return exit code `0` when an error occurred, and avoid generic exit code `1` for all failure types.
* **No ANSI Noise & Progress Spinners:**
  Detect if output is non-interactive (`!isatty(stdout)`) or if `--json` is supplied, and automatically strip colors, ANSI escape codes, animated spinners, and interactive paging.

---

## 2. Eliminate Interactivity (No Blocking Prompts)
* **Never Block on `stdin`:**
  Never ask *"Are you sure? [y/N]"* or present arrow-key pickers during command execution. If arguments or inputs are missing, fail immediately with a descriptive error message indicating what parameter is needed.
* **Bypass Flags:**
  Always provide non-interactive bypass flags: `--yes`, `--force`, `--non-interactive`.
* **Environment Variable Fallbacks:**
  Allow all critical flags (credentials, API endpoints, tokens) to be passed via environment variables (e.g., `INFISICAL_TOKEN`, `API_URL`) so agents can inject context without manual prompt interaction.

---

## 3. Predictable Command Structure & Rich Help
* **Predictable Noun-Action Hierarchy:**
  Structure commands predictably: `tool <noun> <action>` (e.g., `infisical secrets get`, `codegraph impact analyze`).
* **Rich, Parseable `--help` Text:**
  Agents dynamically invoke `--help` to learn how to operate a tool. Help text must provide:
  1. Clear one-line description.
  2. Concrete copy-pasteable command examples.
  3. Explicit argument types and defaults.

---

## 4. Safety by Design & Idempotency
* **Mandatory `--dry-run` / `--preview`:**
  For any operation that mutates state (deploying containers, migrating databases, modifying files across repo), provide a `--dry-run` flag so the agent can simulate changes before committing.
* **Idempotency:**
  Make mutations idempotent. Re-running a creation command should return the current resource state or update it safely, rather than throwing a duplicate conflict error.
* **Actionable Self-Describing Error Messages:**
  When a tool fails, output:
  1. What failed.
  2. The root cause.
  3. Actionable remediation steps (suggested flags or next commands).

---

## 5. Synchronous vs Asynchronous Handling
* For background deployments or async tasks, provide a `--wait` and `--timeout <seconds>` flag so the agent receives the final completion status rather than needing to poll in a loop.
