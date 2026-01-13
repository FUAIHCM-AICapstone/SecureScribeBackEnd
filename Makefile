# SecureScribe Backend - Docker Compose Commands
.PHONY: help up down rebuild restart logs clean test shell db-shell redis-shell minio-shell

# Default target
help: ## Show this help message
	@echo "SecureScribe Backend - Docker Compose Commands"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Start all services
up: ## Start all services in detached mode
	docker-compose -f docker-compose.local.yml up -d

# Start services with logs (follow mode)
up-logs: ## Start all services and show logs
	docker-compose -f docker-compose.local.yml up

# Stop all services
down: ## Stop all services
	docker-compose -f docker-compose.local.yml down

# Rebuild all services
rebuild: ## Rebuild all services from scratch
	docker-compose -f docker-compose.local.yml down
	docker-compose -f docker-compose.local.yml build --no-cache
	docker-compose -f docker-compose.local.yml up -d

# Rebuild specific service
rebuild-%: ## Rebuild specific service (e.g., make rebuild-api)
	docker-compose -f docker-compose.local.yml build --no-cache $*
	docker-compose -f docker-compose.local.yml up -d $*

# Restart all services
restart: ## Restart all services
	docker-compose -f docker-compose.local.yml restart

# Restart specific service
restart-%: ## Restart specific service (e.g., make restart-api)
	docker-compose -f docker-compose.local.yml restart $*

# Show logs for all services
logs: ## Show logs for all services
	docker-compose -f docker-compose.local.yml logs -f

# Show logs for specific service
logs-%: ## Show logs for specific service (e.g., make logs-api)
	docker-compose -f docker-compose.local.yml logs -f $*

# Clean up everything (containers, volumes, images)
clean: ## Remove containers, volumes, and images
	docker-compose -f docker-compose.local.yml down -v --rmi all

# Run tests
test: ## Run tests using the test service
	docker-compose -f docker-compose.local.yml --profile test run --rm test

# Access API container shell
shell: ## Access API container shell
	docker-compose -f docker-compose.local.yml exec api bash

# Access database shell
db-shell: ## Access PostgreSQL database shell
	docker-compose -f docker-compose.local.yml exec db psql -U admin -d securescribe

# Access Redis shell
redis-shell: ## Access Redis CLI
	docker-compose -f docker-compose.local.yml exec redis redis-cli

# Access MinIO shell
minio-shell: ## Access MinIO container shell
	docker-compose -f docker-compose.local.yml exec minio sh

# Show service status
status: ## Show status of all services
	docker-compose -f docker-compose.local.yml ps

# Stop and remove volumes (destructive)
nuke: ## Stop everything and remove all volumes (WARNING: destroys data)
	docker-compose -f docker-compose.local.yml down -v

# Run backend image alone
run-backend: ## Run backend image alone with .env file
	docker run --rm -d \
		--name securescribe-backend \
		--env-file .env \
		-p 8000:8000 \
		luongnguyenminhan/securescribe:backend

# Run backend image in foreground
run-backend-fg: ## Run backend image alone in foreground with .env file
	docker run --rm \
		--name securescribe-backend \
		--env-file .env \
		-p 8000:8000 \
		luongnguyenminhan/securescribe:backend

# Stop backend container
stop-backend: ## Stop the running backend container
	docker stop securescribe-backend || true
	docker rm securescribe-backend || true
