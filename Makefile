.PHONY: help up down restart build logs status clean dev test test-unit lint typecheck

PROJECT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
ENV_FILE := $(PROJECT_DIR).env.podman
COMPOSE := podman compose -f $(PROJECT_DIR)podman-compose.yml

export $(shell grep -v '^#' $(ENV_FILE) | xargs 2>/dev/null || true)

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start the RAG-TRACK containers (build if needed)
	podman pod rm -f ragtrack-pod 2>/dev/null || true
	$(COMPOSE) up -d --build

down: ## Stop and remove all containers and the pod
	$(COMPOSE) down 2>/dev/null || true
	podman pod rm -f ragtrack-pod 2>/dev/null || true

restart: down up ## Rebuild and restart all containers

build: ## Build the ragtrack image without starting
	podman build -t ragtrack:latest -f Containerfile $(PROJECT_DIR)

logs: ## Stream container logs
	$(COMPOSE) logs -f

status: ## Show pod and container status
	@echo "=== Pod Status ==="
	podman pod inspect ragtrack-pod 2>/dev/null || echo "Pod 'ragtrack-pod' is not running"
	@echo ""
	@echo "=== Container Status ==="
	podman ps --filter "name=ragtrack" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

clean: down ## Remove all containers, pod, and volumes
	podman volume rm ragtrack-db-data ragtrack-data 2>/dev/null || true
	podman image rm ragtrack:latest 2>/dev/null || true

dev: ## Start in development mode (local LLM, debug logging)
	$(MAKE) up DEV=1

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

install-podman: ## Check if podman is installed
	@command -v podman >/dev/null 2>&1 && echo "Podman is installed: $$(podman --version)" || echo "Podman is NOT installed. See https://podman.io/getting-started/installation"

setup: ## Setup podman environment (copy .env.podman.example and build)
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_FILE).example $(ENV_FILE) && echo "Created $(ENV_FILE)"; \
	else \
		echo "$(ENV_FILE) already exists, skipping copy"; \
	fi

.PHONY: help