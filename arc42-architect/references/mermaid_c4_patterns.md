# Mermaid C4 Architecture Diagram Patterns

This reference provides native Mermaid C4 syntax patterns for arc42 architecture documentation.
Unlike PlantUML, Mermaid diagrams render natively in Markdown viewers, GitHub, GitLab, and web artifacts with zero external server dependencies.

---

## 1. System Context Diagram (Section 3: Context and Scope)

Illustrates external actors, systems, and primary high-level boundaries.

```mermaid
C4Context
    title System Context: [System Name]

    Person(user, "End User", "Interacts via Web/Mobile application")
    Person_Ext(admin, "Operator / Admin", "Manages configurations and tenants")

    System(system, "[System Name]", "Core application solving domain problems")

    System_Ext(idp, "Identity Provider / SSO", "SAML 2.0 / OIDC authentication service")
    System_Ext(db, "External Storage / DB", "Persistent document or analytical storage")
    System_Ext(notification, "Notification Service", "Email / WhatsApp delivery gateway")

    Rel(user, system, "Uses", "HTTPS / JSON")
    Rel(admin, system, "Administers", "HTTPS / Admin UI")
    Rel(system, idp, "Authenticates via", "OIDC / SAML")
    Rel(system, db, "Reads / Writes", "TLS / TCP")
    Rel(system, notification, "Triggers alerts", "REST / Webhooks")
```

---

## 2. Container Diagram (Section 5: Building Block View Level 1)

Illustrates deployable software units (APIs, web applications, databases, workers).

```mermaid
C4Container
    title Container Diagram: [System Name]

    Person(user, "User", "Client consumer")

    Container_Boundary(system, "[System Name]") {
        Container(spa, "Single Page App", "Svelte 5 / TypeScript", "Delivers interactive user interface")
        Container(api, "API Gateway / Core Backend", "Rust / Axum", "Handles routing, business logic, and security")
        Container(worker, "Background Worker", "Python / Go", "Processes async jobs and scheduled tasks")
        ContainerDb(database, "Relational Database", "PostgreSQL / SQLite WAL", "Stores transactional domain state")
        ContainerDb(cache, "In-Memory Cache", "Redis / Valkey", "Session storage and transient rate limiting")
    }

    Rel(user, spa, "Visits", "HTTPS")
    Rel(spa, api, "API Calls (IF-01)", "JSON / REST / SSE")
    Rel(api, database, "Queries / Mutates", "SQL / Pool")
    Rel(api, cache, "Reads / Writes tokens", "RESP")
    Rel(api, worker, "Dispatches jobs", "Pub/Sub")
    Rel(worker, database, "Batches data", "SQL")
```

---

## 3. Component Diagram (Section 5: Building Block View Level 2)

Illustrates internal structural components/slices inside a single container.

```mermaid
C4Component
    title Component Diagram: API Backend Container

    Container_Boundary(api, "API Gateway Container") {
        Component(router, "HTTP Router", "Axum / Express", "Dispatches inbound HTTP requests to handlers")
        Component(auth_slice, "Auth Feature Slice", "VSA REPR Handler", "Validates JWTs and permissions")
        Component(core_service, "Domain Service Layer", "Pure Domain Logic", "Executes business rules and workflows")
        Component(repo, "Data Repository", "SQLx / Prisma", "Encapsulates database access abstractions")
    }

    ContainerDb_Ext(db, "Database", "Relational persistence")

    Rel(router, auth_slice, "Routes /api/auth", "In-Process")
    Rel(router, core_service, "Routes business actions", "In-Process")
    Rel(auth_slice, repo, "Persists credentials", "Repository Interface")
    Rel(core_service, repo, "Queries entities", "Repository Interface")
    Rel(repo, db, "Executes queries", "TCP / Driver")
```

---

## 4. Runtime Sequence Diagram (Section 6: Runtime View)

Illustrates temporal step-by-step request flow across components.

```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant Router as Ingress / Router
    participant Auth as Auth Middleware
    participant Service as Domain Service
    participant DB as Database Engine

    User->>Router: POST /api/v1/resource (with Bearer Token)
    Router->>Auth: Validate Token & Claims
    alt Token Invalid / Expired
        Auth-->>User: 401 Unauthorized (JSON)
    else Token Valid
        Auth->>Service: Forward Request Context
        Service->>DB: Query current state (SELECT ...)
        DB-->>Service: State record
        Service->>Service: Execute business rule validation
        Service->>DB: Write updated entity (UPDATE / INSERT)
        DB-->>Service: Commit OK
        Service-->>Router: Domain Response DTO
        Router-->>User: 200 OK (Payload JSON)
    end
```
