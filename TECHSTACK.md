# TECHSTACK.md

PressRadar AI technology and infrastructure specification.

This document is authoritative for:

- Languages
- Frameworks
- Runtime modes
- AI runtime/providers
- Persistence
- Analytics infrastructure
- External integrations
- Cloud architecture
- Infrastructure as Code
- Development tooling constraints

Product requirements belong in `PROJECT.md`.

Engineering principles belong in `AGENTS.md` and `docs/ENGINEERING.md`.

---

# Index

Codex should use this index to load only technology sections relevant to the current task.

1. [Architecture Strategy](#1-architecture-strategy)
2. [Repository Structure](#2-repository-structure)
3. [Backend](#3-backend)
4. [Frontend](#4-frontend)
5. [API Communication](#5-api-communication)
6. [AI Architecture](#6-ai-architecture)
7. [Local AI](#7-local-ai)
8. [Fake AI](#8-fake-ai)
9. [Future Hosted AI Providers](#9-future-hosted-ai-providers)
10. [Local Development](#10-local-development)
11. [Docker Compose](#11-docker-compose)
12. [Runtime Modes](#12-runtime-modes)
13. [Configuration](#13-configuration)
14. [Operational Persistence](#14-operational-persistence)
15. [Firestore](#15-firestore)
16. [Local Firestore Development](#16-local-firestore-development)
17. [Analytics](#17-analytics)
18. [BigQuery](#18-bigquery)
19. [Notifications](#19-notifications)
20. [Twilio](#20-twilio)
21. [CRM Integration](#21-crm-integration)
22. [HubSpot](#22-hubspot)
23. [Google Cloud Platform](#23-google-cloud-platform)
24. [Cloud Run](#24-cloud-run)
25. [Terraform](#25-terraform)
26. [GCP Authentication](#26-gcp-authentication)
27. [Secrets](#27-secrets)
28. [Provider Activation](#28-provider-activation)
29. [Background Processing](#29-background-processing)
30. [Observability](#30-observability)
31. [Testing Technology](#31-testing-technology)
32. [Linting / Formatting / Type Safety](#32-linting--formatting--type-safety)
33. [CI/CD Expectations](#33-cicd-expectations)
34. [Technology Non-Goals](#34-technology-non-goals)
35. [Technology Decision Summary](#35-technology-decision-summary)

---

# 1. Architecture Strategy

PressRadar should begin as a:

**Modular monolith**

Do not start with microservices.

Maintain clear conceptual boundaries:

```text
Presentation
    ↓
Application / Use Cases
    ↓
Domain
    ↑
Infrastructure / Providers
```

Provider-specific code should remain outside the domain and core application rules.

The goal is to make infrastructure replaceable without rewriting product logic.

---

# 2. Repository Structure

Prefer a monorepo.

Suggested shape:

```text
pressradar/
├── AGENTS.md
├── PROJECT.md
├── TECHSTACK.md
├── README.md
│
├── docs/
│   └── ENGINEERING.md
│
├── apps/
│   ├── api/
│   │   └── ...
│   │
│   └── web/
│       └── ...
│
├── infra/
│   └── terraform/
│
├── docker/
│
├── docker-compose.yml
└── .env.example
```

The exact internal application structure should follow existing conventions and `AGENTS.md`.

---

# 3. Backend

Required backend stack:

```text
Python
FastAPI
Pydantic
```

Use modern Python typing.

Backend responsibilities include:

- Domain/application behavior
- Authentication/authorization
- Media ingestion
- Opportunity processing
- AI orchestration
- Pitch workflow
- Provider integrations
- Persistence access
- Analytics/event emission
- Server-side validation

FastAPI must not become the domain architecture.

Framework-specific request/response objects should remain near presentation boundaries.

---

# 4. Frontend

Required frontend stack:

```text
TypeScript
Next.js
React
```

Use strict TypeScript.

The frontend handles:

- Authentication UI
- Dashboard
- Client management
- Opportunity review
- Pitch editing
- Approval actions
- Settings
- Integration status

Do not duplicate authoritative backend business rules in React components.

---

# 5. API Communication

The frontend communicates with the FastAPI backend through HTTP APIs.

Conceptually:

```text
Next.js
   ↓
HTTP API
   ↓
FastAPI
   ↓
Application
```

Do not allow the browser to communicate directly with:

- Ollama
- Firestore administrative APIs
- BigQuery
- Twilio
- HubSpot
- Cloud service credentials

Sensitive provider interactions belong on the backend.

---

# 6. AI Architecture

AI must be provider-agnostic.

Core business/application logic should depend on capabilities conceptually similar to:

```text
RelevanceAnalyzer
PitchGenerator
```

Possible infrastructure implementations:

```text
Fake
Ollama
Future hosted provider
```

Do not couple the domain to one model vendor.

---

# 7. Local AI

Default AI runtime:

```text
Ollama
```

Local AI is the default development/demo mode.

Conceptually:

```text
Next.js
    ↓
FastAPI
    ↓
Application
    ↓
AI Port
    ↓
Ollama Adapter
    ↓
Local Model
```

The local model name must be configurable.

Do not hardcode model selection throughout the codebase.

Example configuration concept:

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=<configured-model>
```

---

# 8. Fake AI

Automated tests must not require:

- Ollama
- Network access
- Paid API calls
- External LLM providers

Provide deterministic fake AI implementations.

Use fake AI for:

- Unit tests
- Integration tests where model behavior is not under test
- CI
- Deterministic workflow tests

Fake AI responses should be stable and predictable.

---

# 9. Future Hosted AI Providers

The architecture may later support providers such as:

- OpenAI
- Gemini
- Anthropic
- Other compatible providers

These are not required for the default MVP.

Adding a hosted provider should primarily require a new infrastructure adapter and configuration.

It should not require rewriting domain logic.

---

# 10. Local Development

Local development is the default environment.

A developer should not need:

- GCP credentials
- Terraform
- Twilio credentials
- HubSpot credentials
- Paid LLM API credentials

to demonstrate the product.

---

# 11. Docker Compose

Default development/demo workflow:

```bash
docker compose up
```

Docker Compose should start the services needed for the local demo.

Conceptually:

```text
web
api
ollama
local/emulated persistence
```

Only add other services when they provide clear value.

Do not reproduce unnecessary production infrastructure locally.

---

# 12. Runtime Modes

PressRadar supports explicit runtime modes.

## Local Demo — Default

```text
Next.js
FastAPI
Ollama
local/emulated persistence
simulated media source
simulated sender
fake/console notifications
fake/no-op CRM
```

No paid external services.

---

## Local Integration Mode

Docker-based application with selected external adapters enabled.

Potential example:

```text
Ollama
+
real Twilio
+
real HubSpot
```

Integrations must be explicitly enabled.

---

## GCP Mode

Production-oriented mode:

```text
Next.js → Cloud Run
FastAPI → Cloud Run
Firestore
BigQuery
Terraform-managed infrastructure
```

Optional:

```text
Twilio
HubSpot
```

---

# 13. Configuration

Backend configuration should be:

- Centralized
- Typed
- Validated
- Environment-aware

Use an appropriate Pydantic settings approach.

Provider configuration should be explicit.

Conceptual example:

```env
APP_MODE=local

AI_PROVIDER=ollama

PERSISTENCE_PROVIDER=local
ANALYTICS_PROVIDER=none
NOTIFICATION_PROVIDER=fake
CRM_PROVIDER=fake
```

Alternative explicit feature flags may be used where clearer.

Do not scatter:

```python
if environment == "local":
```

through business logic.

Resolve implementations at application composition/bootstrap boundaries.

---

# 14. Operational Persistence

Operational application data should use a persistence abstraction appropriate to the business boundary.

Operational data includes:

- Users
- Workspaces
- Clients
- Monitoring rules
- Media items
- Opportunities
- Pitches
- Integration metadata
- Audit events

Production operational persistence is Firestore.

---

# 15. Firestore

Production operational database:

```text
Google Cloud Firestore
```

Firestore should serve transactional/product workflows.

Do not use BigQuery as the ordinary application database.

Firestore schema design should follow actual access/query patterns.

Avoid blindly recreating relational database designs in document form.

Application code should not contain Firestore SDK calls everywhere.

Keep persistence behind meaningful boundaries where appropriate.

---

# 16. Local Firestore Development

Prefer:

```text
Firestore Emulator
```

for local development if it provides a reliable workflow.

Local mode must never accidentally connect to production Firestore.

Environment selection must be explicit.

Conceptual example:

```env
FIRESTORE_EMULATOR_HOST=firestore-emulator:8080
```

If an alternative local persistence adapter provides a substantially simpler MVP workflow, it may be used provided the production Firestore boundary remains clear.

---

# 17. Analytics

Analytics must remain separate from core operational persistence.

Analytics should not block ordinary product actions.

Conceptually:

```text
Core operation
    ↓
Analytics event
    ↓
Analytics adapter
    ↓
BigQuery
```

If analytics infrastructure is unavailable, normal PressRadar workflows should generally continue.

---

# 18. BigQuery

Production analytical storage:

```text
Google BigQuery
```

Suitable use cases:

- Opportunity volumes
- Relevance trends
- Approval rates
- Pitch send rates
- Response times
- Client trends
- Source performance

BigQuery should not be required to render or execute the core operational workflow.

---

# 19. Notifications

Notifications must use an abstraction.

Conceptually:

```text
NotificationSender
        ↑
FakeNotificationSender
TwilioNotificationSender
```

The default local implementation must not contact a real external service.

---

# 20. Twilio

Twilio is an optional notification provider.

Potential MVP use:

```text
urgent opportunity → SMS alert
```

Twilio must be disabled by default.

Real Twilio calls require explicit configuration.

Conceptually:

```env
NOTIFICATION_PROVIDER=twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
```

Tests and seed/demo flows must never send real SMS accidentally.

---

# 21. CRM Integration

CRM functionality must use a provider abstraction.

Conceptually:

```text
CRMIntegration
       ↑
FakeCRMIntegration
HubSpotCRMIntegration
```

Provider-specific response objects should remain inside infrastructure boundaries.

---

# 22. HubSpot

HubSpot is an optional CRM integration.

Potential functionality:

- Sync selected client/contact information
- Record opportunities
- Record pitch activity
- Record sent status

HubSpot must be disabled by default.

Conceptual configuration:

```env
CRM_PROVIDER=hubspot
HUBSPOT_ACCESS_TOKEN=
```

HubSpot is not PressRadar's primary database.

---

# 23. Google Cloud Platform

Target production cloud:

```text
Google Cloud Platform
```

Primary services:

```text
Cloud Run
Firestore
BigQuery
```

Additional GCP services may be introduced only when justified.

Do not add GKE/Kubernetes for the MVP.

---

# 24. Cloud Run

Frontend and backend should be deployable as stateless Cloud Run services.

Conceptually:

```text
Cloud Run
├── web
└── api
```

Additional worker services may be introduced later if background workloads justify them.

Do not prematurely split the backend into many services.

---

# 25. Terraform

Infrastructure as Code:

```text
Terraform
```

Suggested structure:

```text
infra/
└── terraform/
    ├── modules/
    ├── environments/
    │   ├── dev/
    │   └── prod/
    └── README.md
```

Avoid unnecessary Terraform abstraction.

A module should exist because it provides meaningful reuse or isolation.

Terraform must not be required for local development.

---

# 26. GCP Authentication

Do not use hardcoded generic API keys as the primary GCP authentication strategy.

Prefer appropriate mechanisms such as:

- Application Default Credentials
- Service accounts
- Workload Identity
- CI/CD OIDC federation

Local Docker Compose should not require GCP credentials.

Terraform credentials must never be committed.

---

# 27. Secrets

Never commit:

- AI provider credentials
- Twilio secrets
- HubSpot tokens
- GCP credentials
- Private keys
- Production passwords

Provide:

```text
.env.example
```

with placeholders.

Production secrets should use appropriate environment/secret-management mechanisms.

---

# 28. Provider Activation

Optional providers activate only when explicitly configured.

Examples:

```text
AI
Persistence
Analytics
Notifications
CRM
```

Do not make an optional provider mandatory merely because its SDK exists.

Do not initialize disabled providers unnecessarily during startup.

Configuration validation should be conditional.

Example:

```text
NOTIFICATION_PROVIDER=fake
```

does not require Twilio credentials.

But:

```text
NOTIFICATION_PROVIDER=twilio
```

must validate required Twilio configuration.

---

# 29. Background Processing

Media ingestion and AI analysis may eventually require asynchronous/background processing.

For MVP, use the simplest reliable architecture consistent with the project.

Do not introduce:

- Kafka
- Kubernetes
- Large distributed job architectures

without demonstrated need.

Background processing must consider:

- Retries
- Idempotency
- Duplicate processing
- Timeouts
- Partial failures
- Observability

---

# 30. Observability

Production-relevant services should support useful observability.

Potential mechanisms:

- Structured logging
- Request IDs
- Health checks
- Metrics
- Tracing where justified

Local development should remain simple.

Never log secrets.

---

# 31. Testing Technology

Testing should support:

- Backend unit tests
- Backend integration tests
- Frontend component/unit tests where useful
- API integration tests
- Critical end-to-end workflow tests

AI tests must use deterministic fake providers unless explicitly testing local AI integration.

External integrations should use fake adapters in ordinary automated tests.

Tests must not make accidental real calls to:

- Twilio
- HubSpot
- GCP production resources
- Paid AI providers

---

# 32. Linting / Formatting / Type Safety

Backend should use project-configured tools for:

- Formatting
- Linting
- Type checking

Frontend should use project-configured:

- TypeScript checks
- ESLint
- Prettier or equivalent formatting

Exact tooling versions/configurations should live in the repository rather than being repeatedly specified here.

Existing repository configuration is authoritative once established.

---

# 33. CI/CD Expectations

CI should eventually validate at minimum:

```text
backend lint
backend type checks
backend tests
frontend lint
frontend type checks
frontend tests where configured
frontend build
```

Infrastructure validation may include:

```text
terraform fmt
terraform validate
```

Do not deploy production infrastructure automatically unless the deployment workflow explicitly requires it.

---

# 34. Technology Non-Goals

Do not introduce these for the initial MVP without a concrete requirement:

- Kubernetes
- GKE
- Kafka
- Microservices
- Service mesh
- Vector database
- GraphQL solely for architectural novelty
- Multiple databases without need
- Complex event streaming
- Self-hosted distributed observability stacks
- Custom ML infrastructure
- Multiple cloud providers
- Premature multi-region architecture

Prefer boring, proven infrastructure.

---

# 35. Technology Decision Summary

The project technology direction is:

```text
Architecture
    Modular monolith
    Clean boundaries

Backend
    Python
    FastAPI
    Pydantic

Frontend
    TypeScript
    Next.js
    React

AI
    Ollama by default
    Fake provider for tests
    Hosted providers optional later

Development
    Docker Compose by default

Operational Production Data
    Firestore

Analytics
    BigQuery

Cloud
    Google Cloud Platform

Compute
    Cloud Run

Infrastructure as Code
    Terraform

Notifications
    Fake/local by default
    Twilio optional

CRM
    Fake/no-op by default
    HubSpot optional
```

The core architectural objective is:

```text
Local first.
Cloud ready.
Provider agnostic.
Optional integrations stay optional.
Core business logic does not depend on vendor SDKs.
```