# PressRadar

PressRadar helps PR teams detect relevant media opportunities and turn them into timely pitches. The MVP runs locally with SQLite and can be deployed to Google Cloud Run with Firestore and BigQuery.

## Prerequisites

- Docker with Docker Compose
- GNU Make (optional; commands can be run directly with Docker Compose)

No cloud or paid-provider credentials are required for local development.

Each account has isolated Prod and Demo workspaces. Demo uses deterministic simulated
media. Prod can ingest configured RSS feeds without credentials; add `NEWSAPI_API_KEY`
to `.env` only when enabling the suggested UAE NewsAPI source.

## Start locally

```bash
cp .env.example .env
docker compose up --build
```

Open the web application at <http://localhost:3000>. The API health endpoint is available at <http://localhost:8000/health> and interactive API documentation at <http://localhost:8000/docs>.

Docker Compose runs Ollama internally and ensures both the configured Qwen analysis model and
TranslateGemma translation model are downloaded before the API starts. Models are stored in the
`ollama-data` volume; the first download is several gigabytes and can take several minutes.

Stop the services with `docker compose down`.

### Outlook email verification and pitch delivery

The default `EMAIL_PROVIDER=fake` never sends email. To verify new accounts with email OTPs and
send approved pitches through the internal Nodemailer adapter, set these values in `.env`:

```env
EMAIL_PROVIDER=nodemailer
PITCH_SENDER=email
MAILER_INTERNAL_TOKEN=replace-with-a-long-random-internal-token
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your-account@outlook.com
SMTP_PASSWORD=your-outlook-app-password
SMTP_FROM=your-account@outlook.com
```

Do not commit the Outlook address, app password, or internal token. The Outlook account must permit
authenticated SMTP. SMS remains disabled unless the optional Twilio configuration is provided.

Local accounts, workspaces, and sessions are stored in the `api-data` Docker volume. Downloaded
models are stored in `ollama-data`. Use `docker compose down --volumes` only when you intentionally
want to remove both local application data and downloaded models.

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
make infra-validate
```

All commands run inside containers, so host installations of Python and Node.js are not required.

## Repository layout

```text
apps/api/   FastAPI backend
apps/web/   Next.js frontend
apps/mailer/ Internal Nodemailer SMTP adapter
docs/       Engineering guidance
infra/      Terraform and production deployment guidance
```

See [infra/terraform/README.md](infra/terraform/README.md) for the production deployment and rollback runbook.

Product requirements live in `PROJECT.md`, technology decisions in `TECHSTACK.md`, and agent workflow rules in `AGENTS.md`.
