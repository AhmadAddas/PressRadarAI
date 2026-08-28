# PressRadar on Google Cloud

This configuration provisions the MVP production foundation: public Cloud Run services for the web and API, a native Firestore database, a partitioned BigQuery product-event table, Artifact Registry, and separate least-privilege service accounts. Terraform does not manage secret values.

## Prerequisites

- A GCP project with billing enabled
- Permission to enable APIs, manage IAM, and create the declared resources
- `gcloud`, Docker, and Terraform 1.16 or newer
- Application Default Credentials: `gcloud auth application-default login`
- An HTTPS Ollama-compatible endpoint reachable from Cloud Run

Create a dedicated, versioned GCS bucket for Terraform state before initialization. Grant state-bucket access only to deployment identities. Do not commit state, variable files, credentials, provider tokens, or a populated backend configuration.

## Validate

From the repository root:

```bash
make infra-validate
```

This runs Terraform formatting checks, initialization without a backend, and configuration validation in the pinned Terraform container.

## Deploy

Copy `backend.hcl.example` to an untracked `backend.hcl`, set the state bucket, and initialize the partial GCS backend. Copy `terraform.tfvars.example` to an untracked `terraform.tfvars` and replace every placeholder. Use immutable image digests for normal deployments.

The first deployment has a bootstrap step because Artifact Registry must exist before images can be pushed, while the frontend embeds the public API URL at build time:

```bash
cd infra/terraform
terraform init -backend-config=backend.hcl
terraform apply -target=google_artifact_registry_repository.pressradar
gcloud auth configure-docker REGION-docker.pkg.dev
```

Build and push the API production image. Build an initial web image with an HTTPS placeholder, then set those tags in `terraform.tfvars`:

```bash
docker build --target production -t REGION-docker.pkg.dev/PROJECT/pressradar/api:bootstrap ../../apps/api
docker push REGION-docker.pkg.dev/PROJECT/pressradar/api:bootstrap
docker build --target production --build-arg NEXT_PUBLIC_API_URL=https://bootstrap.invalid -t REGION-docker.pkg.dev/PROJECT/pressradar/web:bootstrap ../../apps/web
docker push REGION-docker.pkg.dev/PROJECT/pressradar/web:bootstrap
terraform plan -out=pressradar.tfplan
terraform apply pressradar.tfplan
terraform output -raw api_url
terraform output -raw web_url
```

Rebuild the web image with the reported API URL, set `web_origin` to the reported web URL, replace both image tags with registry digests, review a new plan, and apply it. Subsequent releases only require immutable image builds and a reviewed plan/apply.

The API uses Application Default Credentials through its Cloud Run service account. GCP mode refuses to start unless Firestore, BigQuery, the GCP project, and an HTTPS web origin are explicitly configured. Optional integration secrets remain disabled by default. Create required values in Secret Manager and map environment names to existing secret IDs through `api_secret_ids`; Terraform grants the API service account access and creates Cloud Run secret references without accepting secret values.

## Verify

After the final apply:

```bash
curl -fsS "$(terraform output -raw api_url)/health"
curl -fsS -o /dev/null "$(terraform output -raw web_url)"
```

Then sign up through the web UI and run the demo setup flow. Confirm an operational document appears in Firestore and a product event appears in the BigQuery `pressradar_analytics.product_events` table.

## Operations and rollback

- Cloud Run logs are available in Cloud Logging. Treat API startup failures, 5xx responses, and BigQuery insertion failures as deployment signals.
- Analytics failures do not block product actions; the analytics report returns unavailable until BigQuery recovers.
- Firestore point-in-time recovery and delete protection are enabled. The BigQuery table and Cloud Run services also have deletion protection.
- Roll back by restoring the previous API and web image digests in `terraform.tfvars`, reviewing `terraform plan`, and applying. Application documents are schemaless and this milestone introduces no destructive data migration.
- Terraform intentionally sets `disable_on_destroy = false` for project APIs and `ABANDON` for Firestore. Removing infrastructure requires a deliberate, separately reviewed change to deletion-protection settings.
