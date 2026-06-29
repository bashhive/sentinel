.PHONY: install test lint check health publish configure install-agent uninstall-agent

install:
	uv sync --extra dev

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src

check: lint test

health:
	uv run hivesec-sentinel health

publish:
	uv run hivesec-sentinel publish

configure:
	./scripts/configure.sh

install-agent:
	./scripts/install_launch_agent.sh

uninstall-agent:
	./scripts/uninstall_launch_agent.sh
