.PHONY: install test format lint type up down logs

install:
	uv sync

test:
	uv run pytest

format:
	uv run black bladerunner tests

lint:
	uv run flake8 bladerunner tests

type:
	uv run mypy bladerunner

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f bladerunner-api
