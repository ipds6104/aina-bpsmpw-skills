# High-Performance, Low-RAM Libraries & Enterprise License Compliance

When selecting third-party libraries, dependencies, and algorithms for any project, always prioritize:
1. **Peak Execution Performance & Low RAM Footprint** (Modern, cache-friendly, zero-copy, SIMD).
2. **Enterprise-Audit-Safe Licensing** (Permissive: MIT, Apache 2.0, BSD-2/3, ISC).

---

## 1. Enterprise License Compliance Policy

During enterprise security, M&A due diligence, and legal compliance audits (Black Duck, Snyk, Mend), dependencies undergo Software Bill of Materials (SBOM) verification.

### Traffic-Light License Matrix:

| Tier | Licenses | Audit Status | Enterprise Impact |
| :--- | :--- | :--- | :--- |
| 🟢 **Green (Permissive)** | **MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC** | **Auto-Approved** | Safe for commercial SaaS, proprietary distribution, and closed-source code. |
| 🟡 **Yellow (Weak Copyleft)** | **MPL-2.0, LGPL-2.1/3.0** | **Requires Review** | Permitted only with dynamic linking or file-level isolation. Must not bleed into proprietary logic. |
| 🔴 **Red (Strong/Network Copyleft)** | **AGPL-3.0, GPL-2.0/3.0, SSPL, Commons Clause** | **Default Deny / Blocked** | AGPL triggers full proprietary source disclosure over SaaS networks. Strictly avoid. |

> [!IMPORTANT]
> **Check Transitive Dependencies:** Ensure that a top-level permissive library does not pull deeply nested AGPL/GPL dependencies into production builds.

---

## 2. High-Performance & Memory-Efficient Library Matrix

When choosing open-source libraries, prefer modern alternatives optimized for low memory usage ($O(1)$ streaming, zero-copy) and SIMD hardware acceleration:

### Python Ecosystem
* **JSON Serialization:**
  - Prefer `orjson` (Rust-backed, fastest Python JSON library, low memory overhead) or `msgspec` (ultra-fast schema validation + zero-copy JSON/MessagePack, MIT).
  - Avoid slow standard `json` in high-throughput APIs.
* **Data Processing & Analytics:**
  - Prefer `polars` (Rust-based multi-threaded DataFrame engine with Apache Arrow zero-copy memory model, MIT) over `pandas` for large datasets.
* **HTTP & Event Loop:**
  - Prefer `uvloop` (libuv-backed fast event loop replacement for asyncio, MIT/Apache) and `httpx` / `aiohttp` for async I/O.
* **Validation:**
  - Prefer `msgspec.Struct` or `pydantic-core` (Rust-based validation, MIT).

### JavaScript / TypeScript / Node Ecosystem
* **JSON & Schema Validation:**
  - Prefer `fast-json-stringify` (compiles schemas into fast string serializers) and `valibot` / `arktype` (ultra-lightweight tree-shakable validators) over heavy runtimes.
* **Package Management:**
  - Prefer `pnpm` (content-addressable hard-link store saving gigabytes of disk and RAM during builds).
* **HTTP & Routing:**
  - Prefer `hono` or `fastify` (efficient radix tree routers with low allocations) over legacy bloated middlewares.

### Go Ecosystem
* **JSON Serialization:**
  - Prefer `bytedance/sonic` (JIT-compiled, SIMD-accelerated JSON, Apache-2.0) or `segmentio/encoding`.
* **Logging:**
  - Prefer `rs/zerolog` or `uber-go/zap` (zero-allocation JSON loggers, MIT).
* **Networking:**
  - Prefer `valyala/fasthttp` (zero memory allocations per request) or Go standard `net/http` with buffer pooling (`sync.Pool`).

### Rust Ecosystem
* **Concurrency & Memory:**
  - Prefer `dashmap` (concurrent lock-free hash map, MIT) and `bytes` (zero-copy byte slice manipulation).
* **Serialization:**
  - Prefer `simd-json` or `serde_json` with borrowed references (`&str`) to eliminate memory allocations.

---

## 3. Memory Optimization Principles in Code

1. **Zero-Copy Where Possible:**
   - Use string slices / byte views (`&str`, `std::string_view`, `memoryview`) rather than allocating duplicate strings.
2. **Buffer Pooling (`ObjectPool` / `sync.Pool`):**
   - Reuse byte buffers across requests instead of allocating new buffers in garbage-collected heaps.
3. **Streaming Pipelines ($O(1)$ Space):**
   - Process streams incrementally (generators, chunked byte streams) rather than buffering unbounded gigabyte payloads into RAM.
