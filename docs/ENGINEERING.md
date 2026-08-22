# ENGINEERING.md

Detailed engineering reference for this repository.

This file contains the full engineering standards previously kept in the root `AGENTS.md`.
It is **not** intended to be loaded in full for every task.

Agents should consult only the sections relevant to the current work, as directed by the root `AGENTS.md`.

---

This file defines the engineering rules, architecture principles, coding standards, testing expectations, Git workflow, and quality requirements that all AI coding agents must follow when working in this repository.

The goal is not merely to produce code that works.

The goal is to produce code that is:

- Correct
- Simple
- Maintainable
- Testable
- Secure
- Observable
- Scalable
- Consistent
- Easy to review
- Easy to modify
- Safe to deploy

These rules apply to all generated, modified, or refactored code unless a more specific applicable `AGENTS.md` or an explicit current task overrides them. Product requirements remain owned by `PROJECT.md`, and technology/infrastructure decisions remain owned by `TECHSTACK.md`.

---

# 00. Instruction Sources, Ownership, and Precedence

Before substantial implementation work, read and apply the repository instructions in this order:

1. `PROJECT.md`
2. `TECHSTACK.md`
3. The most specific applicable `AGENTS.md`
4. Relevant existing source code and tests
5. The current explicit task

These sources do not have the same responsibility. Each owns a different kind of decision.

## Document Ownership

### `PROJECT.md`

`PROJECT.md` is authoritative for:

- Product requirements
- Business rules
- User workflows
- Domain behavior
- Feature scope
- MVP boundaries
- Acceptance criteria
- In-scope and out-of-scope behavior

It answers:

> What should the product do, and why?

Do not place technology-selection rules or general code-style rules in `PROJECT.md` unless they are genuinely part of the product contract.

### `TECHSTACK.md`

`TECHSTACK.md` is authoritative for:

- Programming languages
- Frameworks
- Databases
- AI providers
- Cloud providers
- Infrastructure
- External integrations
- Runtime modes
- Deployment architecture
- Build/development tooling choices
- Approved technology constraints

It answers:

> What technology should be used to build and run the product?

Do not copy product requirements or general engineering principles into `TECHSTACK.md`.

### `AGENTS.md`

This file is authoritative for:

- Engineering behavior
- Architecture principles
- Clean Code
- SOLID
- Testing
- Security
- Error handling
- Documentation
- Refactoring
- Git workflow
- Code review
- Implementation discipline
- Definition of Done

It answers:

> How should the solution be engineered?

### Current Task

The current explicit task defines:

> What should be changed now?

The current task should normally be narrow and should not restate the entire product, stack, or engineering constitution.

Do not turn every task into a redesign of the whole repository.

---

# 00.1 Do Not Duplicate Decisions Across Instruction Files

Avoid copying the same decision into multiple instruction files.

Prefer references over duplication.

Correct:

```text
Use the AI provider and runtime mode defined in TECHSTACK.md.
```

Incorrect:

```text
Repeating the complete AI provider configuration in AGENTS.md,
PROJECT.md, and the task prompt.
```

If a decision changes, update its authoritative document instead of copying the new value into several files.

This prevents contradictory states such as:

```text
PROJECT.md   → Provider A
TECHSTACK.md → Provider B
AGENTS.md    → Provider C
README.md    → Provider D
```

The repository should have one authoritative source for each kind of decision.

---

# 00.2 Conflict Resolution

When instructions appear to conflict, resolve them using the following order:

```text
Current explicit task
        ↓
Most specific applicable AGENTS.md
        ↓
Document ownership
        ├── Product / business behavior → PROJECT.md
        ├── Technology / infrastructure → TECHSTACK.md
        └── Engineering practice        → AGENTS.md
        ↓
Existing repository conventions and implementation
        ↓
Smallest reasonable documented assumption
```

A current explicit task may intentionally override a lower-level instruction.

A nested or more specific `AGENTS.md` may refine engineering rules for a subdirectory.

For example:

```text
/AGENTS.md
/apps/api/AGENTS.md
/apps/web/AGENTS.md
```

The deeper file may add framework-specific rules for its scope.

Do not silently reconcile a material contradiction by guessing.

If a conflict materially affects:

- Product behavior
- Data integrity
- Security
- Public contracts
- Architecture
- Technology selection

identify the conflict clearly.

For minor, reversible implementation details, choose the simplest option consistent with the authoritative documents and continue.

---

# 00.3 Inspect Before Assuming

Instruction files describe intended behavior, but the repository remains important evidence of how the system currently works.

Before implementation:

- Read the applicable instruction files.
- Inspect the actual project structure.
- Inspect similar existing implementations.
- Inspect relevant tests.
- Inspect configuration and dependency manifests.
- Verify that documentation and implementation have not drifted.

Do not invent missing repository details.

If documentation and implementation disagree, determine which document owns the disputed decision and make the smallest safe correction.

---

# 00.4 Task Prompt Discipline

A good task prompt should usually contain only:

- The requested feature or fix
- The intended outcome
- Important task-specific constraints
- Explicit acceptance criteria when needed

Do not repeatedly paste:

- The whole product specification
- The whole stack definition
- The whole engineering constitution

into every task.

The agent must read the repository instruction files instead.

A typical task should begin conceptually with:

```text
Read PROJECT.md, TECHSTACK.md, and the applicable AGENTS.md files first.
Inspect the existing implementation before making changes.

Implement <specific task>.
```

Then implement the task completely unless the user explicitly requested planning only.

---

# 00.5 Architecture and Technology Ownership

Architecture principles belong here.

Concrete stack choices belong in `TECHSTACK.md`.

For example:

```text
AGENTS.md:
Keep domain logic independent from vendor-specific infrastructure.

TECHSTACK.md:
Use FastAPI, Next.js, Firestore, BigQuery, and the configured AI provider.
```

Do not hardcode project-specific framework or vendor decisions into generic architectural rules.

Likewise, product-specific workflows belong in `PROJECT.md`, not here.

---

---

# 01. Understand Before Writing Code

Before modifying the repository:

1. Inspect the existing project structure.
2. Read relevant source files.
3. Read configuration files.
4. Read dependency manifests.
5. Read tests related to the feature.
6. Understand existing naming and architectural patterns.
7. Identify existing utilities before creating new ones.
8. Determine which files actually need to change.
9. Identify potential side effects.
10. Identify unclear requirements or assumptions.

Never begin by blindly generating files.

Do not assume that a requested feature requires a new service, class, abstraction, dependency, database table, or architectural layer.

First understand what already exists.

---

# 02. Plan Before Implementing Large Changes

For non-trivial tasks, establish an implementation plan before writing code.

Determine:

- What needs to change
- Why it needs to change
- Which architectural layer owns the behavior
- Which modules are affected
- Whether database changes are required
- Whether API contracts change
- Whether backward compatibility matters
- What tests are required
- What security concerns exist
- What failure scenarios exist

Prefer incremental implementation over large uncontrolled changes.

---

# 03. Follow Existing Project Architecture

The existing architecture is the default source of truth.

Do not introduce a second architecture simply because another approach is theoretically cleaner.

Before creating new patterns, inspect similar functionality already present in the repository.

Reuse established:

- Folder structures
- Naming conventions
- Dependency injection patterns
- Error-handling approaches
- Logging approaches
- Validation approaches
- Data-access patterns
- API patterns
- Testing utilities
- Configuration mechanisms

Consistency is more valuable than personal preference.

---

# 04. Follow Clean Architecture Principles

When the project architecture permits it, organize code according to Clean Architecture concepts.

Dependencies should generally point inward toward business rules.

Typical separation:

```text
Presentation / Interface
        ↓
Application / Use Cases
        ↓
Domain / Business Rules
        ↑
Infrastructure / Frameworks / Database
```

Possible project organization:

```text
src/
├── domain/
│   ├── entities/
│   ├── value-objects/
│   ├── services/
│   └── repositories/
│
├── application/
│   ├── use-cases/
│   ├── commands/
│   ├── queries/
│   ├── dto/
│   └── ports/
│
├── infrastructure/
│   ├── database/
│   ├── repositories/
│   ├── integrations/
│   ├── messaging/
│   └── configuration/
│
└── presentation/
    ├── controllers/
    ├── routes/
    ├── handlers/
    ├── middleware/
    └── views/
```

The exact folder names may differ depending on the language and framework.

Do not force this structure where the framework has a simpler established convention.

The important rule is separation of responsibilities, not folder ceremony.

---

# 05. Protect the Domain Layer

Business rules should not unnecessarily depend on:

- HTTP frameworks
- UI frameworks
- Database implementations
- Cloud SDKs
- Message brokers
- External APIs
- Framework-specific request objects
- Framework-specific response objects

Core business logic should ideally remain testable without starting the application infrastructure.

Prefer:

```text
Controller
    → Use Case
        → Domain
            → Repository Interface
```

instead of:

```text
Controller
    → ORM
    → Business Rules
    → External API
    → Response Formatting
```

all mixed into one function.

---

# 06. Use Clear Layer Responsibilities

### Domain

Contains:

- Business rules
- Entities
- Value objects
- Domain services
- Domain invariants

The domain should contain the most stable logic.

### Application

Contains:

- Use cases
- Commands
- Queries
- Application services
- Workflow orchestration
- Ports/interfaces

Application code coordinates business behavior.

### Infrastructure

Contains:

- Database access
- ORM implementations
- File systems
- Queues
- External API clients
- Cloud services
- Email providers
- Caches

Infrastructure implements interfaces required by higher-level layers.

### Presentation

Contains:

- HTTP handlers
- Controllers
- Routes
- GraphQL resolvers
- CLI handlers
- UI adapters
- Request/response formatting

Presentation should translate external input into application-level operations.

---

# 07. Follow SOLID Principles

SOLID principles should guide design decisions without becoming an excuse for unnecessary abstraction.

## Single Responsibility Principle

A module, class, or function should have one primary reason to change.

Avoid components that simultaneously:

- Query databases
- Perform business logic
- Format responses
- Send emails
- Log analytics
- Manage transactions

Separate responsibilities where doing so improves clarity.

## Open/Closed Principle

Code should be reasonably open for extension but closed for unnecessary modification.

Prefer extension points when multiple implementations are expected.

Do not pre-build extensibility for hypothetical future requirements.

## Liskov Substitution Principle

Implementations of an abstraction must honor the behavior promised by that abstraction.

Derived implementations must not surprise callers.

## Interface Segregation Principle

Prefer small interfaces that describe a specific capability.

Avoid large interfaces forcing implementations to depend on methods they do not need.

Prefer:

```text
ReadableRepository
WritableRepository
```

over a huge multipurpose interface when consumers only need one operation.

## Dependency Inversion Principle

High-level business rules should depend on abstractions rather than concrete infrastructure implementations.

Prefer injecting:

```text
UserRepository
PaymentGateway
EmailSender
Clock
```

instead of directly constructing infrastructure dependencies inside business logic.

---

# 08. Do Not Apply SOLID Mechanically

SOLID is guidance, not a requirement to create interfaces and classes everywhere.

Do not create:

- Interfaces with only one foreseeable implementation without a reason
- Factories that add no value
- Wrapper classes around trivial framework calls
- Abstract base classes for hypothetical reuse
- Dependency injection layers around pure helper functions

Prefer the simplest design that preserves maintainability.

---

# 09. Follow Clean Code Principles

Code should communicate intent clearly.

Prefer names that explain purpose.

Bad:

```text
data
temp
x
obj
doStuff()
handle()
process()
manager
helper
utils2
```

Better:

```text
activeSubscriptions
invoiceTotal
calculateRenewalDate()
validatePaymentMethod()
createUserSession()
```

Avoid names that require reading the implementation to understand their purpose.

---

# 10. Keep Functions Focused

Functions should generally perform one coherent operation.

Prefer:

```text
validateOrder()
calculateOrderTotal()
reserveInventory()
processPayment()
createShipment()
```

rather than a single massive:

```text
processOrder()
```

containing hundreds of lines.

However, do not split functions simply to satisfy an arbitrary line-count rule.

Extract functions when doing so improves:

- Clarity
- Reuse
- Testability
- Separation of concerns

---

# 11. Keep Classes and Modules Focused

Avoid "God objects" and oversized modules.

Warning signs include classes named:

```text
ApplicationManager
SystemService
CoreUtils
MainHandler
GlobalService
```

that contain unrelated responsibilities.

Split modules around domain or feature boundaries rather than arbitrary technical categories when appropriate.

---

# 12. Avoid Premature Abstraction

Do not extract an abstraction after seeing a pattern only once.

Duplication is sometimes cheaper than the wrong abstraction.

Create abstractions when:

- Behavior is repeated
- The concept has a meaningful domain name
- Multiple implementations genuinely exist
- Testing requires isolation
- A dependency boundary needs protection

Do not create abstractions simply because they appear architecturally sophisticated.

---

# 13. Prefer Composition Over Inheritance

Use composition when behavior can be assembled cleanly.

Inheritance should represent a genuine "is-a" relationship and must preserve Liskov Substitution.

Avoid deep inheritance hierarchies.

Prefer:

```text
OrderService
  ├── PaymentProcessor
  ├── InventoryService
  └── NotificationService
```

over large chains of inherited service classes.

---

# 14. Follow Code Specifications

Follow the established language and framework style guides.

Examples include:

### Python

Follow:

- PEP 8
- PEP 257 where appropriate
- Project formatter configuration
- Project type-checking rules

### Java

Follow:

- Google Java Style Guide
- Existing Checkstyle configuration
- Existing project conventions

### JavaScript / TypeScript

Follow:

- ESLint configuration
- Prettier configuration
- TypeScript configuration
- Framework conventions

### Go

Follow:

- `gofmt`
- Effective Go conventions
- Project lint rules

### Rust

Follow:

- `rustfmt`
- Clippy recommendations where appropriate
- Idiomatic Rust conventions

Existing repository configuration takes precedence over generic style guides.

Do not manually fight automated formatters.

---

# 15. Use Automated Formatting and Linting

Whenever configured, run the project's formatter and linter.

Examples:

```bash
ruff
black
eslint
prettier
gofmt
golangci-lint
cargo fmt
cargo clippy
checkstyle
```

Do not introduce formatting changes across unrelated files unless required.

Avoid giant formatting-only diffs mixed with functional changes.

---

# 16. Documentation and Comments

Good code should explain itself through naming and structure.

Comments should primarily explain:

- Why a decision was made
- Why an unusual workaround exists
- Why an edge case matters
- Why a particular algorithm or tradeoff was chosen

Avoid comments that merely repeat the code.

Bad:

```python
# Increment count by one
count += 1
```

Better:

```python
# Include the current retry because the upstream API counts
# the initial request as attempt zero.
attempt += 1
```

Comments must stay synchronized with the implementation.

Incorrect comments are worse than missing comments.

---

# 17. Document Public Contracts

Public APIs, reusable modules, complex services, and important abstractions should be documented appropriately.

Document:

- Inputs
- Outputs
- Side effects
- Exceptions/errors
- Important invariants
- Expected behavior
- Non-obvious constraints

Avoid excessive documentation for trivial private implementation details.

---

# 18. Favor Self-Documenting Code

Before adding a comment, ask whether clearer code would eliminate the need.

Prefer:

```text
isSubscriptionExpired(subscription)
```

over:

```text
check(subscription) // checks whether subscription expired
```

Use expressive:

- Variable names
- Type names
- Function names
- Domain terminology

---

# 19. Build Robust Software

Software should behave predictably when receiving unexpected inputs or encountering failures.

Handle expected failure scenarios deliberately.

Examples include:

- Invalid input
- Missing records
- Network timeouts
- External API failures
- Duplicate requests
- Partial data
- Database conflicts
- Missing configuration
- Permission errors
- Concurrent updates

Do not allow predictable errors to become unexplained crashes.

---

# 20. Do Not Catch Exceptions Blindly

Avoid:

```text
try:
    ...
except:
    pass
```

or equivalent broad exception swallowing.

Exceptions should be:

- Handled meaningfully
- Translated into appropriate application/domain errors
- Logged where useful
- Re-thrown when the current layer cannot resolve them

Never hide failures simply to make the application appear stable.

---

# 21. Fail Fast for Invalid Internal State

Validate assumptions near system boundaries.

If required configuration is missing, fail clearly during startup rather than producing mysterious runtime behavior later.

Internal invariant violations should surface clearly.

Do not silently continue with corrupt or impossible state.

---

# 22. Validate All External Input

Treat external input as untrusted.

Validate:

- HTTP requests
- Query parameters
- Path parameters
- Headers
- Uploaded files
- CLI arguments
- Environment variables
- Webhooks
- Queue messages
- Third-party API responses
- Database data when historical corruption is possible

Validation should occur at appropriate system boundaries.

---

# 23. Make Testing Easy

Testability is an architectural requirement.

Code should make it easy to isolate business behavior.

Prefer:

- Dependency injection
- Pure functions
- Explicit dependencies
- Small interfaces
- Deterministic behavior
- Mockable infrastructure boundaries

Avoid:

- Hidden global state
- Direct network calls deep inside business logic
- Hardcoded current time
- Randomness without injectable control
- Static dependencies that cannot be replaced

---

# 24. Follow the Testing Pyramid Where Appropriate

Prefer a healthy balance of:

1. Unit tests
2. Integration tests
3. End-to-end tests

Unit tests should provide fast feedback.

Integration tests should verify boundaries such as:

- Databases
- APIs
- Queues
- Filesystems

End-to-end tests should cover critical user workflows.

Do not rely exclusively on end-to-end tests.

Do not mock everything either.

---

# 25. Test Behavior, Not Implementation Details

Tests should verify observable behavior and business rules.

Avoid tests that break merely because a private method was renamed.

Prefer testing:

```text
Given an expired subscription,
when renewal is attempted,
then payment is requested and the expiration date is updated.
```

rather than asserting internal call sequences unless those calls are part of the required contract.

---

# 26. Always Test Important Edge Cases

Consider:

- Empty input
- Null / `None`
- Missing values
- Minimum values
- Maximum values
- Invalid formats
- Duplicate requests
- Concurrent requests
- Timeout conditions
- Permission failures
- Partial failures
- Boundary dates
- Time zones
- Unicode
- Large datasets

Do not test only the happy path.

---

# 27. Never Weaken Tests to Make Them Pass

Do not:

- Delete failing tests without justification
- Remove assertions
- Increase timeout values blindly
- Mark failing tests as skipped
- Disable static analysis
- Add broad ignores
- Change expected values simply to match broken behavior

Fix the underlying issue.

If a test itself is incorrect, explain why and update it deliberately.

---

# 28. Use ACID Principles for Transactional Data

For systems using transactional databases, respect ACID properties.

## Atomicity

A transaction should either complete fully or not occur.

Operations that logically belong together should not leave partial state.

Example:

```text
Create order
Reserve inventory
Record payment
```

If these must represent one atomic business operation, handle failures safely.

## Consistency

Transactions must preserve business and database invariants.

Use:

- Constraints
- Validation
- Foreign keys
- Unique indexes
- Domain rules

Do not rely exclusively on application code when the database can enforce critical invariants.

## Isolation

Concurrent operations must not corrupt each other's state.

Consider:

- Race conditions
- Double spending
- Duplicate purchases
- Lost updates
- Concurrent edits
- Inventory overselling

Use suitable locking, transaction isolation, optimistic concurrency, or idempotency mechanisms.

## Durability

Once a transaction commits successfully, the system should treat it as persistent according to the storage guarantees.

Do not report successful completion before critical writes are safely committed.

---

# 29. Understand Transaction Boundaries

Transactions should generally align with business operations.

Avoid:

- Transactions that are too broad and lock excessive resources
- Transactions that are too narrow and permit partial business state

Do not hold database transactions open while waiting on slow external APIs unless absolutely necessary.

Where distributed operations are involved, consider:

- Outbox pattern
- Saga pattern
- Idempotency
- Retry strategies
- Compensating actions

Do not pretend distributed systems provide simple database transactions when they do not.

---

# 30. Design for Idempotency Where Needed

Operations that may be retried should ideally be safe to execute multiple times.

Examples:

- Payment webhooks
- Queue consumers
- Order submissions
- Background jobs
- External callbacks

Use:

- Idempotency keys
- Unique constraints
- Processed-event records
- Safe upserts
- Deduplication

when appropriate.

---

# 31. Reduce Global Dependencies

Global mutable state should be avoided.

Prefer dependencies passed explicitly through:

- Function arguments
- Constructors
- Dependency injection
- Context objects when appropriate

Global state makes code harder to:

- Understand
- Test
- Parallelize
- Debug
- Reuse

Constants and immutable configuration may be global when appropriate.

Mutable application state should generally not be.

---

# 32. Minimize Side Effects

Prefer pure functions for transformation and business calculation where practical.

Pure functions:

- Produce the same output for the same input
- Do not modify global state
- Do not perform hidden I/O

Keep side effects near system boundaries.

Examples of side effects:

- Database writes
- Network requests
- Filesystem access
- Sending email
- Publishing messages
- Logging
- Mutating shared state

Make side effects explicit.

---

# 33. Use Dependency Injection Appropriately

Dependencies should generally be supplied rather than secretly constructed deep inside business logic.

Prefer:

```text
PaymentService(paymentGateway, orderRepository)
```

instead of:

```text
PaymentService()
    internally creates StripeClient()
    internally creates DatabaseClient()
```

This improves:

- Testing
- Flexibility
- Separation of concerns
- Configuration

Do not create a complex DI framework if normal constructor/function injection is sufficient.

---

# 34. Use Abstraction Carefully

Abstraction should hide irrelevant complexity and expose meaningful concepts.

Good abstractions:

- Improve readability
- Protect architectural boundaries
- Reduce meaningful duplication
- Enable substitution
- Capture domain concepts

Bad abstractions:

- Hide simple logic
- Introduce unnecessary indirection
- Require navigating many files to understand trivial behavior
- Exist only because "clean architecture says so"

Aim for moderate abstraction.

---

# 35. Use Design Patterns When They Solve Real Problems

Design patterns are tools, not objectives.

Potential patterns include:

- Repository
- Factory
- Strategy
- Adapter
- Decorator
- Observer
- Command
- CQRS
- Builder
- State
- Specification
- Mediator
- Outbox
- Saga

Use them only when the problem justifies them.

Do not use patterns simply to make the architecture appear sophisticated.

---

# 36. Avoid Over-Engineering

Prefer boring, obvious solutions.

Do not create:

- Microservices when a modular monolith is enough
- Message queues for simple synchronous operations
- Event buses for trivial internal communication
- Generic frameworks for one use case
- Plugin systems without plugin requirements
- Factories for objects constructed once
- Repositories that merely rename ORM methods without creating a useful boundary

Complexity must earn its place.

---

# 37. Prefer Explicitness Over Magic

Code should be understandable without deep knowledge of hidden behavior.

Avoid excessive:

- Reflection
- Metaprogramming
- Runtime monkey patching
- Implicit registration
- Invisible dependency lookup
- Global hooks

Use framework magic only where it is idiomatic and well understood.

---

# 38. Continuous Refactoring

Refactor regularly when working in an area of the codebase.

Apply the Boy Scout Rule:

> Leave the code you touched slightly better than you found it.

However, do not turn every task into a repository-wide cleanup.

Refactoring should be:

- Related to the current task
- Small
- Safe
- Tested
- Reviewable

Large unrelated refactors should be separate tasks and commits.

---

# 39. Remove Dead Code

Do not leave:

- Commented-out code
- Unused variables
- Unused imports
- Abandoned experiments
- Duplicate implementations
- Temporary debugging logic

Version control already preserves history.

Delete code that is genuinely obsolete.

---

# 40. Avoid Duplication Intelligently

Follow DRY where duplication represents the same concept.

But do not merge unrelated code merely because it looks similar.

Two pieces of code can look identical today but represent different business concepts and evolve independently.

Prefer meaningful abstraction over mechanical deduplication.

---

# 41. Follow KISS

Keep It Simple.

When two solutions satisfy the same requirements, prefer the one that:

- Has fewer moving parts
- Is easier to test
- Is easier to explain
- Uses fewer dependencies
- Requires less hidden knowledge
- Has fewer failure modes

Simple does not mean simplistic.

---

# 42. Follow YAGNI

You Aren't Gonna Need It.

Do not build capabilities solely because they may be useful someday.

Avoid speculative:

- Extension systems
- Configuration flags
- Generic frameworks
- Interfaces
- Database columns
- Services
- APIs

Implement current requirements cleanly.

Leave the code structured enough that future change remains possible.

---

# 43. Use Domain-Driven Naming

Use terminology from the actual business domain.

If the business calls something an:

```text
Invoice
Subscription
Shipment
Workspace
Organization
Reservation
```

use that terminology consistently.

Avoid technical names that obscure domain intent.

---

# 44. Make Invalid States Hard to Represent

Where the language supports it, use types and domain models to prevent invalid combinations.

Prefer:

```text
EmailAddress
Money
OrderStatus
SubscriptionPeriod
```

over passing unrelated primitive strings everywhere when the domain complexity justifies it.

Use enums, tagged unions, value objects, validation, and database constraints appropriately.

Do not create value objects for every primitive without reason.

---

# 45. Security Is a Top Priority

Security is part of normal software quality.

Consider OWASP-style risks including:

- Injection
- Broken access control
- Authentication failures
- Sensitive-data exposure
- Security misconfiguration
- Cross-site scripting
- CSRF
- SSRF
- Unsafe deserialization
- Path traversal
- Open redirects
- File upload vulnerabilities
- Dependency vulnerabilities

Never knowingly introduce insecure shortcuts.

---

# 46. Never Commit Secrets

Never commit:

- Passwords
- API keys
- Access tokens
- Refresh tokens
- Private keys
- Database credentials
- Cloud credentials
- Production secrets

Use environment variables or an appropriate secret-management system.

Provide safe examples such as:

```text
.env.example
```

with placeholder values only.

---

# 47. Apply Least Privilege

Users, services, tokens, database roles, and cloud identities should receive only the permissions they need.

Avoid broad privileges such as:

```text
admin
*
root
superuser
```

unless genuinely required.

Authorization should be checked server-side.

Never rely solely on UI restrictions.

---

# 48. Handle Authentication and Authorization Separately

Authentication answers:

> Who are you?

Authorization answers:

> Are you allowed to perform this action?

Do not treat a logged-in user as automatically authorized to access every resource.

Verify ownership, role, permission, or policy where appropriate.

---

# 49. Protect Sensitive Data

Do not log sensitive values.

Potentially sensitive data includes:

- Passwords
- Tokens
- Cookies
- Authorization headers
- Payment information
- Personal information
- Secret keys

Mask or omit sensitive fields in logs and error messages.

---

# 50. Use Secure Defaults

Defaults should favor safety.

Examples:

- Secure cookies
- HTTP-only cookies
- Appropriate SameSite settings
- TLS in production
- Restricted CORS
- Input validation
- Parameterized queries
- Escaped output
- Deny-by-default authorization

Avoid insecure defaults that require developers to remember to enable security later.

---

# 51. Manage Dependencies Carefully

Before adding a dependency, ask:

1. Can this be implemented simply without another dependency?
2. Is the package actively maintained?
3. Does the project already contain a suitable library?
4. What security and licensing implications exist?
5. How much transitive dependency weight does it add?

Do not install a library for trivial functionality.

Use lockfiles where appropriate.

Do not arbitrarily upgrade unrelated dependencies during a feature task.

---

# 52. Keep Configuration External

Environment-specific behavior should be controlled through configuration.

Avoid hardcoding:

- URLs
- Credentials
- Ports
- Environment names
- Provider-specific settings
- Feature switches

Validate required configuration during startup.

Do not silently substitute dangerous production defaults.

Do not scatter environment/provider branching throughout domain and application code.

Resolve environment-specific implementations at an appropriate composition/bootstrap boundary so core business logic depends on stable interfaces rather than environment checks.

---

# 53. Build Observability Into Important Systems

Where appropriate, important workflows should provide:

- Structured logs
- Metrics
- Tracing
- Correlation/request IDs
- Health checks

Logging should help answer:

- What happened?
- When?
- For which operation?
- Why did it fail?

Avoid excessive noisy logging.

Never log secrets.

---

# 54. Use Appropriate Logging Levels

Use levels intentionally.

Example:

```text
DEBUG
INFO
WARN
ERROR
```

Do not log routine successful requests as errors.

Do not hide actual failures at debug level.

Logs should contain useful context without exposing confidential information.

---

# 55. Handle Time Correctly

Time-related logic is frequently error-prone.

Prefer storing timestamps in UTC unless domain requirements say otherwise.

Be explicit about:

- Time zones
- Daylight saving transitions
- Date boundaries
- Expiration semantics

Avoid relying on system-local time implicitly.

For testable time-dependent code, inject a clock when appropriate.

---

# 56. Handle Money Correctly

Never use floating-point arithmetic for monetary values when precision matters.

Prefer:

- Integer minor units
- Decimal types
- Dedicated money types

Always make currency explicit where relevant.

Be careful with:

- Rounding
- Tax calculations
- Currency conversion
- Precision

---

# 57. Design APIs Consistently

Follow existing API conventions.

Maintain consistency in:

- Resource naming
- HTTP methods
- Status codes
- Pagination
- Filtering
- Sorting
- Validation errors
- Authentication
- Versioning

Do not create unique response conventions for individual endpoints without reason.

---

# 58. Preserve Backward Compatibility

Before changing a public contract, consider existing clients.

Public contracts may include:

- APIs
- Database schemas
- Events
- CLI arguments
- Configuration
- SDK interfaces
- Serialization formats

Avoid breaking changes unless explicitly required.

When breaking changes are necessary, document them clearly.

---

# 59. Treat Database Migrations Carefully

Database migrations should be:

- Deterministic
- Reviewable
- Safe
- Compatible with deployment strategy

Avoid destructive schema operations without considering existing production data.

For large systems, consider backward-compatible multi-stage migrations.

Do not modify historical migrations that have already been deployed unless the project explicitly permits it.

---

# 60. Design for Concurrency

When multiple workers or requests can modify the same state, consider race conditions.

Potential techniques include:

- Transactions
- Optimistic locking
- Pessimistic locking
- Atomic database operations
- Unique constraints
- Idempotency keys
- Distributed locks where truly required

Do not assume single-threaded execution in production.

---

# 61. Handle External Services Defensively

External services can fail.

Consider:

- Timeouts
- Retries
- Backoff
- Rate limits
- Partial failure
- Invalid responses
- Authentication expiration
- Circuit breaking
- Idempotency

Always configure reasonable timeouts.

Do not retry non-idempotent operations blindly.

---

# 62. Avoid N+1 and Obvious Performance Problems

Correctness comes first, but avoid known performance anti-patterns.

Watch for:

- N+1 database queries
- Unbounded database reads
- Loading huge datasets into memory
- Repeated external API calls
- Blocking operations in async paths
- Expensive computation inside loops

Measure before introducing complex optimization.

---

# 63. Optimize Based on Evidence

Do not sacrifice readability for speculative performance improvements.

Prefer:

1. Correctness
2. Clarity
3. Measurement
4. Optimization

Use profiling and metrics when performance actually matters.

---

# 64. Keep Pull-Request-Sized Changes

Changes should remain easy to review.

Avoid combining:

- Feature development
- Large refactors
- Dependency upgrades
- Formatting entire directories
- Unrelated bug fixes

into a single change set.

Separate independent work.

---

# 65. Use Disciplined Git Commits

Use Git throughout implementation.

Never put an entire project or unrelated features into one massive commit.

Each commit should represent one coherent change.

Use Conventional Commit style.

Examples:

```text
feat: add user registration
feat(auth): add refresh token rotation
fix: prevent duplicate invoice creation
fix(api): return 404 for missing workspace
refactor: extract payment gateway interface
test: add checkout integration tests
docs: document local development setup
chore: configure eslint
build: configure production docker image
ci: add pull request validation workflow
perf: reduce dashboard query count
style: apply formatter to auth module
```

---

# 66. Use the Correct Commit Type

Prefer the following Conventional Commit types.

### `feat`

New functionality.

```text
feat: add password reset flow
```

### `fix`

Bug fix.

```text
fix: prevent expired sessions from refreshing
```

### `refactor`

Code restructuring without intended behavior change.

```text
refactor: move billing logic into application service
```

### `test`

Tests only.

```text
test: add invoice calculation edge cases
```

### `docs`

Documentation only.

```text
docs: add deployment instructions
```

### `chore`

Maintenance work.

```text
chore: configure pre-commit hooks
```

### `build`

Build system or dependency-related work.

```text
build: configure production container
```

### `ci`

Continuous integration changes.

```text
ci: add lint and test jobs
```

### `perf`

Performance improvement.

```text
perf: batch product lookup queries
```

### `style`

Formatting or stylistic changes without logic changes.

```text
style: format billing module
```

Do not label a bug fix as `feat`.

Do not label functional changes as `chore`.

---

# 67. Avoid Bad Commit Messages

Never use vague commit messages such as:

```text
update
changes
fix stuff
work
more work
final
done
cleanup
wip
misc
```

A commit message should explain the purpose of the change.

---

# 68. Keep Commits Atomic

A commit should ideally be independently understandable.

Good sequence:

```text
chore: initialize application configuration
feat: add user persistence model
feat: add user registration use case
feat: expose registration endpoint
test: add registration integration tests
docs: document registration endpoint
```

Bad:

```text
feat: build entire backend
```

Do not artificially create dozens of meaningless micro-commits either.

Commit boundaries should correspond to logical changes.

---

# 69. Review Before Every Commit

Before committing:

1. Inspect `git status`.
2. Inspect the staged diff.
3. Remove accidental files.
4. Ensure no secrets are present.
5. Ensure no debug code remains.
6. Run relevant tests.
7. Run lint/type checks where available.
8. Confirm the commit contains one coherent change.
9. Use an accurate Conventional Commit message.

Never blindly run:

```bash
git add .
```

without reviewing what will be committed.

---

# 70. Do Not Rewrite Git History Without Permission

Never perform actions such as:

```text
git push --force
git reset --hard
git rebase
git commit --amend
history rewriting
squashing existing commits
```

unless explicitly requested or clearly required by the task.

Preserve other contributors' work.

---

# 71. Never Destroy Unrelated Work

Assume uncommitted changes may belong to someone else.

Do not:

- Delete unrelated modifications
- Reset the working tree
- Checkout over changed files
- Revert unrelated commits
- Run destructive cleanup commands

unless explicitly instructed.

---

# 72. Implement Incrementally

For each feature:

1. Understand the requirement.
2. Inspect related code.
3. Identify the correct architectural layer.
4. Make the smallest coherent change.
5. Add or update tests.
6. Run validation.
7. Review the diff.
8. Commit the logical change.
9. Continue to the next unit of work.

Avoid generating an entire system in one pass.

---

# 73. Keep Changes Scoped

Do not change unrelated code.

Avoid:

- Opportunistic rewrites
- Repository-wide renaming
- Unrelated dependency upgrades
- Unrelated formatting
- Unrequested features

If an unrelated issue is discovered, mention it separately rather than silently expanding scope.

---

# 74. Preserve Existing Behavior

Unless requirements say otherwise, existing behavior is part of the contract.

Refactoring should not silently change behavior.

When behavior changes intentionally:

- Update tests
- Update documentation
- Update API contracts
- Update migrations where needed
- Explain the change

---

# 75. Verify Instead of Guessing

Never invent:

- File names
- Database columns
- API endpoints
- Package methods
- Configuration fields
- Environment variables
- Function signatures
- Internal conventions

Search the codebase first.

When external documentation is available and needed, verify against the relevant version.

If something cannot be verified, clearly identify the assumption.

---

# 76. Reuse Before Creating

Before creating a new:

- Helper
- Utility
- Component
- Hook
- Service
- Repository
- Type
- DTO
- Validator
- Error class

search the repository for an existing equivalent.

Avoid parallel implementations of the same concept.

---

# 77. Avoid Generic Utility Dumping Grounds

Do not put unrelated functions into giant files such as:

```text
utils.ts
helpers.py
common.java
misc.go
```

Prefer domain-specific modules.

Examples:

```text
money.ts
date-range.ts
password-policy.ts
invoice-calculator.ts
```

A generic utilities module is acceptable only for genuinely generic behavior.

---

# 78. Keep Boundaries Explicit

When data crosses boundaries, use clear contracts.

Examples:

- DTOs
- Schemas
- Commands
- Events
- Interfaces
- Typed request objects

Do not allow database models to leak throughout every application layer unless that is an intentional framework pattern.

---

# 79. Separate Domain Models From Transport Models When Needed

An HTTP request shape is not necessarily a domain object.

A database record is not necessarily a domain object.

A third-party API response is not necessarily a domain object.

Transform external representations at boundaries where separation provides value.

Avoid unnecessary mapping layers for trivial CRUD applications.

---

# 80. Error Handling Should Be Consistent

Use a consistent error taxonomy.

Potential categories:

```text
ValidationError
AuthenticationError
AuthorizationError
NotFoundError
ConflictError
DomainError
InfrastructureError
ExternalServiceError
```

Translate errors at appropriate boundaries.

Do not expose raw database or framework errors directly to users.

---

# 81. Preserve Useful Error Context

When wrapping errors, preserve enough context for debugging.

Bad:

```text
Something went wrong
```

Better internal context:

```text
Failed to create invoice for order 123 because payment authorization was rejected.
```

User-facing errors should remain safe and understandable.

Internal logs may include additional diagnostic information without sensitive data.

---

# 82. Do Not Ignore Compiler or Type Errors

If the project uses static typing, treat type errors seriously.

Do not bypass errors through:

```text
any
@ts-ignore
unsafe cast
type: ignore
#pragma disable
```

unless there is a documented and justified reason.

Fix the type model where practical.

---

# 83. Avoid Excessive `any` and Equivalent Escape Hatches

Strong typing improves correctness only when types are meaningful.

Prefer precise types for:

- API contracts
- Domain values
- Function inputs
- Function outputs
- Events

Use escape hatches sparingly and locally.

---

# 84. Make Side Effects Visible in Names and Structure

A function named:

```text
getUser()
```

should not unexpectedly:

- Update database state
- Send notifications
- Modify global variables

Names should reflect important effects.

Prefer explicit commands such as:

```text
loadUser()
updateUser()
sendWelcomeEmail()
```

when those distinctions matter.

---

# 85. Prefer Immutability Where Practical

Immutable data reduces accidental state changes.

Prefer:

- `const`
- Immutable records
- Read-only structures
- Copy-on-write patterns

when appropriate.

Do not force immutability where it makes normal framework code excessively awkward.

---

# 86. Treat Background Jobs as Production Code

Background workers, schedulers, and queue consumers require the same quality standards as request handlers.

Consider:

- Retries
- Idempotency
- Dead-letter behavior
- Timeout handling
- Concurrency
- Monitoring
- Partial failures

Do not assume a job runs only once.

---

# 87. Keep Deployment Safety in Mind

Changes should consider how they behave during deployment.

Potential issues include:

- Old application + new database schema
- New application + old database schema
- Rolling deployments
- Cached clients
- Mixed application versions

Prefer backward-compatible transitions when production architecture requires them.

---

# 88. Provide Useful README and Setup Documentation

A new developer should be able to understand how to run the project.

Document at minimum when relevant:

- Prerequisites
- Installation
- Environment setup
- Running locally
- Database setup
- Tests
- Linting
- Builds
- Common commands

Do not document commands that were not verified.

---

# 89. Document Architectural Decisions When Important

For significant architectural decisions, consider Architecture Decision Records.

Example:

```text
docs/adr/0001-use-postgresql.md
```

An ADR may contain:

```text
Context
Decision
Alternatives
Consequences
```

Do not create ADRs for trivial implementation details.

---

# 90. Keep Generated Files Separate

Do not manually edit generated files unless required.

Examples include:

- ORM-generated clients
- OpenAPI-generated clients
- Compiled assets
- Lock files except through package managers

Modify the source configuration or schema and regenerate instead.

---

# 91. Respect Repository Tooling

Use the tools already configured by the project.

Examples:

```text
Makefile
Taskfile
npm scripts
pnpm scripts
poetry
uv
Gradle
Maven
Cargo
Docker Compose
```

Prefer documented repository commands over inventing new command sequences.

---

# 92. Do Not Replace Working Technology Without Requirement

Do not switch:

```text
PostgreSQL → MongoDB
REST → GraphQL
Express → Fastify
React → Vue
Jest → Vitest
```

simply because another tool may be preferable.

Technology replacement must solve a concrete requirement and justify migration cost.

---

# 93. Review Your Own Diff

Before declaring work complete, inspect the full diff like a reviewer.

Look for:

- Incorrect assumptions
- Bugs
- Security problems
- Dead code
- Duplicate code
- Missing validation
- Missing tests
- Debugging statements
- Hardcoded values
- Accidental formatting changes
- Missing error handling
- Broken imports
- Type errors
- Unnecessary dependencies
- Scope creep

Fix discovered problems before finishing.

---

# 94. Run Validation Before Completion

Run relevant available checks.

Examples:

```text
format
lint
typecheck
unit tests
integration tests
build
security checks
```

Use the repository's established commands.

Do not claim something passed if it was not run.

---

# 95. Do Not Fake Successful Verification

Never write:

```text
All tests pass.
```

unless tests were actually run and passed.

If something could not be tested, say so explicitly.

Example:

```text
Not run: integration tests require a database service that is unavailable in the current environment.
```

Accuracy is more important than presenting a perfectly successful result.

---

# 96. Fix Root Causes

When encountering a failure, understand why it occurs.

Do not automatically:

- Add retries
- Add null checks everywhere
- Catch exceptions broadly
- Disable rules
- Ignore warnings
- Increase timeouts
- Add sleeps

Those approaches may hide the actual problem.

Fix the root cause whenever practical.

---

# 97. Prefer Deterministic Behavior

Tests and application logic should avoid unnecessary nondeterminism.

Control:

- Randomness
- Current time
- External dependencies
- Execution order where relevant

Inject clocks or random generators when deterministic testing materially helps.

---

# 98. Maintain Dependency Direction

Higher-level policies should not unnecessarily depend on lower-level details.

A domain service should not know:

```text
PostgreSQL
Stripe SDK
AWS SDK
Express Request
Django HttpRequest
React component state
```

unless the architecture intentionally combines these layers.

Dependencies should point toward stable business abstractions where practical.

---

# 99. Architecture Should Serve the Product

Do not follow architecture principles dogmatically.

Clean Architecture, SOLID, DDD, CQRS, and design patterns are tools.

The real objectives are:

- Understandability
- Correctness
- Maintainability
- Testability
- Security
- Evolvability

A five-file solution is not automatically better than a one-file solution.

Use the amount of architecture appropriate for the project's complexity.

---

# 100. Definition of Done

A task is complete only when applicable requirements have been satisfied.

Before finishing, verify:

- [ ] `PROJECT.md` requirements relevant to the task were followed.
- [ ] `TECHSTACK.md` constraints relevant to the task were followed.
- [ ] The most specific applicable `AGENTS.md` rules were followed.
- [ ] Requirements are implemented.
- [ ] Existing code was inspected before changes.
- [ ] Architecture remains coherent.
- [ ] SOLID principles were considered appropriately.
- [ ] No unnecessary abstractions were introduced.
- [ ] Code follows project style specifications.
- [ ] Names clearly communicate intent.
- [ ] Complex decisions are documented where needed.
- [ ] External inputs are validated.
- [ ] Expected failures are handled.
- [ ] Security implications were considered.
- [ ] Sensitive data is protected.
- [ ] Database transactions preserve required invariants.
- [ ] ACID properties were considered where relevant.
- [ ] Concurrency issues were considered where relevant.
- [ ] Tests were added or updated where appropriate.
- [ ] Relevant tests pass.
- [ ] Type checking passes when configured.
- [ ] Linting passes when configured.
- [ ] Build passes when configured.
- [ ] No debug code remains.
- [ ] No secrets are committed.
- [ ] No unrelated files were modified.
- [ ] Git commits are logical and atomic.
- [ ] Conventional Commit messages are used.
- [ ] The final diff was reviewed.
- [ ] Documentation was updated where needed.

---

# 100.1 Task Sizing and Agent Autonomy

Process should support engineering quality, not become bureaucracy.

## Small Tasks

For small, obvious, low-risk changes, do not over-plan.

Examples include:

- Typo fixes
- Minor copy changes
- Small configuration corrections
- Isolated, well-understood bug fixes
- Straightforward test corrections

Inspect the relevant area, make the smallest safe change, validate it, and commit it appropriately.

Do not create unnecessary architecture documents or implementation plans for trivial work.

## Large or Non-Trivial Tasks

For larger work, identify before implementation:

- Scope
- Affected architectural layers
- Data model or migration impact
- Public API or contract impact
- External integration impact
- Security implications
- Failure modes
- Backward compatibility concerns
- Test strategy
- Logical commit boundaries

Then implement incrementally.

## Reasonable Decisions Without Blocking

Make reasonable engineering decisions independently when they are:

- Low risk
- Reversible
- Consistent with `PROJECT.md`
- Consistent with `TECHSTACK.md`
- Consistent with applicable `AGENTS.md`
- Consistent with existing repository conventions
- Not product-defining

Prefer:

- Simplicity
- Maintainability
- Security
- Testability
- Existing conventions
- Small reversible changes

Do not block implementation on trivial choices.

If a decision is product-defining, security-sensitive, destructive, difficult to reverse, or conflicts with authoritative documentation, surface it clearly rather than guessing.

---

---

# 101. Required Agent Workflow

For every substantial coding task, follow this sequence:

```text
1. Read PROJECT.md
2. Read TECHSTACK.md
3. Read the most specific applicable AGENTS.md
4. Inspect the repository and relevant tests
5. Understand the requested change
6. Plan when the task is non-trivial
7. Identify architectural and data boundaries
8. Implement the smallest correct change
9. Add/update tests
10. Run validation
11. Review the diff
12. Fix discovered issues
13. Commit the logical unit
14. Repeat if additional units remain
15. Perform final repository review
```

Do not skip directly from requirement to generated implementation.

---

# 102. Required Final Handoff

At the end of a task, provide a concise summary using this structure:

## Implemented

Explain what was added, changed, or fixed.

## Architecture

Mention important architectural decisions or boundaries affected.

## Files

List the important files created or modified.

## Tests

State which tests were added or updated.

## Validation

State exactly what was run.

Example:

```text
- npm run lint
- npm run typecheck
- npm test
- npm run build
```

Do not claim commands were run if they were not.

## Git

List the commits created using their exact commit messages.

Example:

```text
feat(auth): add user registration use case
feat(api): expose registration endpoint
test(auth): add registration integration tests
docs: document registration flow
```

## Remaining

List genuine:

- Limitations
- Risks
- TODOs
- Follow-up work

If nothing remains, say so.

---

# 103. Core Engineering Principles Summary

When deciding between different implementations, prioritize these principles:

```text
Correctness over cleverness.
Clarity over brevity.
Simplicity over unnecessary abstraction.
Explicitness over magic.
Composition over inheritance.
Cohesion over convenience.
Low coupling over global dependencies.
Testability over hidden state.
Security over shortcuts.
Measured optimization over speculation.
Existing conventions over personal preference.
Small commits over giant commits.
Root-cause fixes over symptom suppression.
Maintainability over temporary speed.
Business value over architectural ceremony.
```

---

# 103.1 Responsibility Map

Keep these responsibilities distinct:

```text
PROJECT.md   = WHAT the product does and WHY
TECHSTACK.md = WITH WHAT technologies and runtime modes
AGENTS.md    = HOW the work must be engineered
Current task = WHAT must change NOW
README.md    = HOW humans set up, run, and use the repository
```

When adding or changing documentation, put the decision in the document that owns it.

Do not create a second source of truth.

---

# 104. Final Rule

Write code as though another experienced engineer will need to understand, review, debug, test, extend, and safely operate it years from now.

Do not merely make the code work.

Make the solution understandable, maintainable, testable, secure, and appropriately simple.