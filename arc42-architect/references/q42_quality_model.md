# Q42 Quality Model Reference

The Q42 Quality Model provides a standardized taxonomy of 492 quality attributes structured across 8 core properties.
Use these tags in **Section 1.2 (Quality Goals)** and **Section 10 (Quality Requirements)** to ensure consistent traceability across all architectural documents.

---

## The 8 Core Properties & Common Tags

### 1. `#reliable` (Keandalan & Ketahanan)
- Focus: Availability, fault tolerance, data integrity, recovery, resilience.
- Example tags:
  - `#availability` — 99.9% uptime, graceful degradation.
  - `#fault-tolerance` — automated failover, circuit breaker pattern.
  - `#recoverability` — RTO (Recovery Time Objective) < 15m, RPO (Recovery Point Objective) < 1m.
  - `#data-integrity` — transactional consistency, zero silent data loss.

### 2. `#efficient` (Efisiensi & Kinerja)
- Focus: Response latency, throughput, compute/memory footprint.
- Example tags:
  - `#latency` — API p95 < 200ms under 1000 concurrent requests.
  - `#throughput` — >= 5000 transactions/second sustained.
  - `#resource-usage` — binary RAM < 35MB, CPU load < 15% idle.
  - `#scalability` — horizontal auto-scaling without shared state bottlenecks.

### 3. `#secure` (Keamanan & Kepatuhan)
- Focus: Confidentiality, authorization, integrity, auditability.
- Example tags:
  - `#authentication` — SAML 2.0 / OIDC SSO, token-based verification.
  - `#authorization` — RBAC / ABAC least-privilege enforcement.
  - `#confidentiality` — encryption-at-rest (AES-256), TLS 1.3 in-transit.
  - `#auditability` — immutable append-only audit trail for all write actions.

### 4. `#flexible` (Fleksibilitas & Pemeliharaan)
- Focus: Maintainability, extensibility, modularity, testability.
- Example tags:
  - `#maintainability` — file length < 350 lines, SRP compliance.
  - `#extensibility` — pluggable driver contracts (e.g. SQLite / PostgreSQL).
  - `#modularity` — Vertical Slice Architecture with zero cross-slice leaks.
  - `#reusability` — shared core utilities decoupled from framework dependencies.

### 5. `#operable` (Operasional & Observability)
- Focus: Deployability, monitoring, telemetry, configuration.
- Example tags:
  - `#deployability` — single binary / zero-dependency multi-stage container (< 35MB).
  - `#monitorability` — OpenTelemetry distributed tracing, Prometheus metrics.
  - `#configurability` — 12-factor environment variables with safe defaults.
  - `#debuggability` — structured JSON logging without ANSI pollution.

### 6. `#usable` (Kegunaan & Pengalaman Pengguna)
- Focus: Ergonomics, responsiveness, accessibility.
- Example tags:
  - `#responsiveness` — 120Hz/144Hz native refresh rate compositor animations.
  - `#ergonomics` — mobile touch target envelope >= 44px, one-handed reachability.
  - `#learnability` — zero-configuration setup for common development paths.
  - `#accessibility` — WCAG 2.1 AA compliant contrast and keyboard navigation.

### 7. `#safe` (Keamanan Operasional & Fail-Safe)
- Focus: Prevention of harmful states, fail-fast behavior.
- Example tags:
  - `#fail-fast` — explicit typed errors on unsupported operations (zero silent dummies).
  - `#safe-defaults` — non-destructive rollback on migration failure.
  - `#concurrency-safety` — lock-free atomics or WAL isolation preventing race conditions.

### 8. `#suitable` (Kesesuaian Fungsional)
- Focus: Functional completeness, regulatory adherence, domain precision.
- Example tags:
  - `#completeness` — 100% parity with BDD feature acceptance criteria.
  - `#precision` — sub-cent rounding compliance in financial computations.
  - `#regulatory` — GDPR / UU PDP compliance, data minimization.

---

## Traceability Invariant (RULE-3)

Every Q42 tag used in Section 10 (`#tag`) **MUST** be introduced in Section 1.2's Quality Goals table.
The automated linter (`arc42-lint`) validates this relationship deterministically.
