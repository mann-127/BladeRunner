.PHONY: install test format lint up down logs

install:
	uv sync

test:
	uv run pytest

format:
	uv run ruff format bladerunner tests

lint:
	uv run ruff check --fix bladerunner tests

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f bladerunner-api
