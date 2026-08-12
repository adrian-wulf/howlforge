# HowlForge - common tasks
PY ?= python3
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help install dev init run test lint doctor up down logs

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

$(VENV)/bin/python: ## Create virtualenv if missing
	$(PY) -m venv $(VENV)

install: $(VENV)/bin/python ## Install package (editable) + dev deps
	$(PIP) install -e ".[dev]"

dev: install ## Install and prepare for local development
	cp -n .env.example .env || true
	$(PYTHON) -m howlforge.cli init

init: install ## Bootstrap the vault folder layout
	$(PYTHON) -m howlforge.cli init

run: ## Run the web panel + API (uvicorn)
	$(PYTHON) -m uvicorn howlforge.server:app --host 0.0.0.0 --port 8000

bot: ## Run the Telegram bot (polling)
	$(PYTHON) -m howlforge.bot

test: install ## Run the test suite
	$(PYTHON) -m pytest -q

lint: install ## Lint with ruff
	$(VENV)/bin/ruff check .

doctor: install ## Show config / LLM models / vault
	$(PYTHON) -m howlforge.cli doctor

up: ## Start everything via Docker Compose (creates vault first)
	@mkdir -p vault
	docker compose up --build -d

down: ## Stop Docker Compose services
	docker compose down

logs: ## Tail Docker Compose logs
	docker compose logs -f
