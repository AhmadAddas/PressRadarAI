.PHONY: dev test lint typecheck build infra-validate validate

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
	docker compose run --rm --no-deps mailer npm test

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

infra-validate:
	docker run --rm -v $(CURDIR)/infra/terraform:/workspace -w /workspace hashicorp/terraform:1.13 fmt -check
	docker run --rm -v $(CURDIR)/infra/terraform:/workspace -w /workspace hashicorp/terraform:1.13 init -backend=false
	docker run --rm -v $(CURDIR)/infra/terraform:/workspace -w /workspace hashicorp/terraform:1.13 validate

validate: lint typecheck test build infra-validate
