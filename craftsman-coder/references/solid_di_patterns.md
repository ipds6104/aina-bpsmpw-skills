# SOLID Principles, Dependency Injection & Framework Conventions

## 1. Single Responsibility Principle (SRP)
- **Definition:** Every module, class, function, or service should have only one reason to change.
- **Signs of SRP Violation:**
  - "God classes" or files exceeding 150-200 lines handling multiple distinct concerns (e.g. data fetching, business rules, serialization, error notifications in one place).
  - High cyclomatic complexity and large parameter lists (> 4-5 parameters).
  - Changes to database schema forcing changes to presentation/API serialization logic.
- **Remediation & Decomposition Rule:**
  - When a component or class grows too long or assumes multiple duties, **immediately decompose it into smaller, single-responsibility subcomponents or services**.
  - Keep functions small (< 50 lines), focused on one single transformation or operation.

---

## 2. Practical Decomposition Examples

### Example A: Bloated UI Component Deconstruction
* **Before (Anti-Pattern):** A single 350-line `UserProfilePage.tsx` containing inline `fetch` calls, image compression for avatars, billing calculation logic, and raw HTML form inputs.
* **After (SRP Decomposed):**
  1. `useUserProfile(userId)` (Custom Hook): Exclusively handles data fetching & caching.
  2. `AvatarUploader`: Single responsibility for image file selection and compression.
  3. `BillingSummaryCard`: Presentational component strictly displaying billing status.
  4. `UserProfilePage`: High-level layout composer coordinating the subcomponents (< 60 lines).

### Example B: Bloated Service Deconstruction
* **Before (Anti-Pattern):** An `OrderService` that validates payment, sends HTTP requests to Stripe, issues raw SQL updates to inventory, and formats email templates.
* **After (SRP + DI):**
  1. `PaymentGateway` (Interface / Protocol): Injected into `OrderService`.
  2. `InventoryRepository` (Interface / Protocol): Injected into `OrderService`.
  3. `NotificationDispatcher` (Interface / Protocol): Injected into `OrderService`.
  4. `OrderService`: Orchestrates the order domain flow without knowing implementation details of SQL, Stripe, or SMTP.

---

## 3. Dependency Injection (DI) & Inversion of Control
- **Definition:** High-level policy modules should not depend directly on low-level detail modules. Both should depend on abstractions/interfaces.
- **Implementation Strategy:**
  - Use constructor injection: Pass dependencies (repositories, clients, loggers) into objects upon creation.
  - Avoid hardcoding singletons or concrete instantiations (`client = ThirdPartyApiClient()`) inside business logic.
  - Create interfaces/protocols (e.g., `typing.Protocol` in Python, interfaces in Go/TypeScript, traits in Rust).
- **Benefits:**
  - Zero-coupling test mocking: Swap real network/DB dependencies with in-memory test doubles without monkey-patching.
  - Allows parallel test execution without state contention.

---

## 4. Framework Convention First
- When a framework already defines clear architectural patterns and conventions, **always prioritize those conventions** over ad-hoc custom architecture:
  - **FastAPI:** Use `Depends()` for dependency injection, Pydantic for validation schemas.
  - **Django:** Leverage standard ORM models, Service layers, and Class-Based / Function-Based Views.
  - **NestJS:** Utilize `@Injectable()`, Modules, and constructor DI.
  - **Next.js:** Honor App Router conventions (`layout.tsx`, `page.tsx`, Server/Client Components boundary).
  - **Go:** Accept interfaces, return structs; use factory functions (`NewService(repo Repository) *Service`).
  - **Rust:** Use traits for abstractions, composition over inheritance, and explicit error handling (`Result<T, E>`).

---

## 5. Reusable Skill & Tool Creation Pattern
- Whenever an information-gathering or workflow task is repeated 2 or more times:
  - Extract the workflow into a repo-agnostic script or CLI tool.
  - Register it in global skills (`~/.gemini/config/skills/`) or global hooks.
  - Provide clear CLI interfaces with `--json` support for machine consumption.
