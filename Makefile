.PHONY: dev test lint typecheck build validate

dev:
	docker compose up --build

test:
	docker compose run --rm api pytest
	docker compose run --rm web npm test

lint:
	docker compose run --rm api ruff check src tests
	docker compose run --rm api ruff format --check src tests
	docker compose run --rm web npm run lint
	docker compose run --rm web npm run format:check

typecheck:
	docker compose run --rm api mypy src tests
	docker compose run --rm web npm run typecheck

build:
	docker compose run --rm web npm run build
	docker compose build

validate: lint typecheck test build
