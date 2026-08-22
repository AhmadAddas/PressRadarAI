.PHONY: dev test lint typecheck build infra-validate validate

dev:
	docker compose up --build

test:
	docker compose run --rm -e AI_PROVIDER=ollama api pytest
	docker compose run --rm web-tools npm test

lint:
	docker compose run --rm api ruff check src tests
	docker compose run --rm api ruff format --check src tests
	docker compose run --rm web-tools npm run lint
	docker compose run --rm web-tools npm run format:check

typecheck:
	docker compose run --rm api mypy src tests
	docker compose run --rm web-tools npm run typecheck

build:
	docker compose run --rm web-tools npm run build
	docker compose build

infra-validate:
	docker run --rm -v $(CURDIR)/infra/terraform:/workspace -w /workspace hashicorp/terraform:1.13 fmt -check
	docker run --rm -v $(CURDIR)/infra/terraform:/workspace -w /workspace hashicorp/terraform:1.13 init -backend=false
	docker run --rm -v $(CURDIR)/infra/terraform:/workspace -w /workspace hashicorp/terraform:1.13 validate

validate: lint typecheck test build infra-validate
