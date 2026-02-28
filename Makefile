.PHONY: install test format lint type

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
