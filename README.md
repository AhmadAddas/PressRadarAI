# PressRadar

PressRadar helps PR teams detect relevant media opportunities and turn them into timely pitches. This repository currently contains the project foundation for the MVP: a FastAPI backend and a Next.js frontend in a modular monorepo.

## Prerequisites

- Docker with Docker Compose
- GNU Make (optional; commands can be run directly with Docker Compose)

No cloud or paid-provider credentials are required for local development.

## Start locally

```bash
cp .env.example .env
docker compose up --build
```

Open the web application at <http://localhost:3000>. The API health endpoint is available at <http://localhost:8000/health> and interactive API documentation at <http://localhost:8000/docs>.

Stop the services with `docker compose down`.

Local accounts, workspaces, and sessions are stored in the `api-data` Docker volume. Use
`docker compose down --volumes` only when you intentionally want to remove local application data.

## Validate

Run the full foundation validation suite:

```bash
make validate
```

Individual commands are also available:

```bash
make lint
make typecheck
make test
make build
```

All commands run inside containers, so host installations of Python and Node.js are not required.

## Repository layout

```text
apps/api/   FastAPI backend
apps/web/   Next.js frontend
docs/       Engineering guidance
```

Product requirements live in `PROJECT.md`, technology decisions in `TECHSTACK.md`, and agent workflow rules in `AGENTS.md`.
