.PHONY: help up down restart build logs status clean dev test test-unit lint typecheck format \
  dc-up dc-down dc-build dc-logs dc-status dc-migrate migrate \
  install-podman setup

PROJECT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
ENV_FILE := $(PROJECT_DIR).env
COMPOSE_FILE := $(PROJECT_DIR)docker-compose.yml

# Detect container runtime: prefer Docker, fall back to Podman
ifneq ($(shell command -v docker 2> /dev/null),)
  COMPOSE := docker compose -f $(COMPOSE_FILE)
else ifneq ($(shell command -v podman 2> /dev/null),)
  COMPOSE := podman compose -f $(COMPOSE_FILE)
else
  COMPOSE := echo "Neither docker nor podman found" && exit 1
endif

# Export .env values for docker-compose variable substitution
ifneq ("$(wildcard $(ENV_FILE))","")
  export $(shell grep -v '^#' $(ENV_FILE) | xargs 2>/dev/null || true)
endif

# ─── Docker Compose Targets ───────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dc-up: ## Start the RAG-TRACK containers (build if needed) via Docker/Podman Compose
	$(COMPOSE) up -d --build

dc-down: ## Stop and remove all containers and networks
	$(COMPOSE) down

dc-build: ## Build the ragtrack image without starting
	$(COMPOSE) build

dc-logs: ## Stream container logs
	$(COMPOSE) logs -f

dc-migrate: ## Run database migrations (api container must be running)
	$(COMPOSE) exec api python3 -m alembic upgrade head

migrate: dc-migrate ## Run database migrations

# ─── Aliases (Docker Compose) ─────────────────────────────────────────────

up: dc-up ## Start containers
down: dc-down ## Stop containers
restart: down up ## Restart containers
build: dc-build ## Build image
logs: dc-logs ## Stream logs
status: ## Show container status
	@$(COMPOSE) ps

# ─── Development Targets ───────────────────────────────────────────────────

dev: ## Start in development mode (local LLM, debug logging)
	$(COMPOSE) up -d --build

# ─── Backend Development Targets ─────────────────────────────────────────

test: ## Run backend unit tests
	cd $(PROJECT_DIR)backend && python -m pytest tests/ -v

test-unit: ## Run auth-specific unit tests
	cd $(PROJECT_DIR)backend && python -m pytest tests/unit/test_auth.py -v

lint: ## Run ruff linter on Python code
	cd $(PROJECT_DIR)backend && python -m ruff check .

typecheck: ## Run mypy type checker on Python code
	cd $(PROJECT_DIR)backend && python -m mypy app/

format: ## Format Python code with ruff
	cd $(PROJECT_DIR)backend && python -m ruff format .

# ─── Setup Targets ─────────────────────────────────────────────────────────

install-podman: ## Check if podman is installed
	@command -v podman >/dev/null 2>&1 && echo "Podman is installed: $$(podman --version)" || echo "Podman is NOT installed. See https://podman.io/getting-started/installation"

install-docker: ## Check if docker is installed
	@command -v docker >/dev/null 2>&1 && echo "Docker is installed: $$(docker --version)" || echo "Docker is NOT installed. See https://docs.docker.com/get-docker/"

setup: ## Setup environment (copy .env.example if .env doesn't exist)
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_FILE).example $(ENV_FILE) && echo "Created $(ENV_FILE)"; \
	else \
		echo "$(ENV_FILE) already exists, skipping copy"; \
	fi

clean: dc-down ## Stop containers and remove all images and volumes
	$(COMPOSE) down -v --rmi all 2>/dev/null || true
