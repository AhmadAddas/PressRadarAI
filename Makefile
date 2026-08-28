.PHONY: dev test lint typecheck build security infra-validate validate

dev:
	docker compose up --build

test:
	docker compose run --rm --no-deps \
		-e APP_MODE=local \
		-e OPERATIONAL_PROVIDER=sqlite \
		-e ANALYTICS_PROVIDER=sqlite \
		-e AI_PROVIDER=fake \
		-e EMAIL_PROVIDER=fake \
		-e PITCH_SENDER=simulated \
		-e NOTIFICATION_PROVIDER=fake \
		-e CRM_PROVIDER=fake \
		-e NEWSAPI_API_KEY= \
		-e COVERAGE_FILE=/tmp/pressradar-coverage \
		api-tools pytest
	docker compose run --rm --no-deps web-tools npm run test:coverage
	docker compose run --rm --no-deps mailer-tools npm test

lint:
	docker compose run --rm --no-deps api-tools ruff check src tests
	docker compose run --rm --no-deps api-tools ruff format --check src tests
	docker compose run --rm --no-deps web-tools npm run lint
	docker compose run --rm --no-deps web-tools npm run format:check

typecheck:
	docker compose run --rm --no-deps api-tools mypy src tests
	docker compose run --rm --no-deps web-tools npm run typecheck

build:
	docker compose run --rm --no-deps web-tools npm run build
	docker compose build

security:
	docker compose run --rm --no-deps web-tools npm audit --audit-level=high
	docker compose run --rm --no-deps mailer-tools npm audit --audit-level=high
	docker compose run --rm --no-deps api-tools pip-audit --local
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v pressradar-trivy-cache:/root/.cache/ -v $(CURDIR)/.trivyignore.yaml:/workspace/.trivyignore.yaml:ro \
		ghcr.io/aquasecurity/trivy:0.74.0@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969 \
		image --ignorefile /workspace/.trivyignore.yaml --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 pressradarai-api:latest
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v pressradar-trivy-cache:/root/.cache/ \
		ghcr.io/aquasecurity/trivy:0.74.0@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969 \
		image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 pressradarai-web:latest
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v pressradar-trivy-cache:/root/.cache/ \
		ghcr.io/aquasecurity/trivy:0.74.0@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969 \
		image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 pressradarai-mailer:latest

infra-validate:
	docker run --rm -v $(CURDIR)/infra/terraform:/workspace -w /workspace hashicorp/terraform:1.16.0 fmt -check
	docker run --rm -v $(CURDIR)/infra/terraform:/workspace -w /workspace hashicorp/terraform:1.16.0 init -backend=false
	docker run --rm -v $(CURDIR)/infra/terraform:/workspace -w /workspace hashicorp/terraform:1.16.0 validate

validate: lint typecheck test build infra-validate
