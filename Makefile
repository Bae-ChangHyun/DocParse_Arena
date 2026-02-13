.PHONY: build up down logs logs-app clean restart seed

# Build Docker images
build:
	docker compose build

# Start all services in detached mode
up:
	docker compose up -d

# Start with build
up-build:
	docker compose up -d --build

# Stop all services
down:
	docker compose down

# View logs (follow mode)
logs:
	docker compose logs -f

# View service logs only
logs-app:
	docker compose logs -f docparse-arena

# Restart all services
restart:
	docker compose restart

# Seed the database with default models
seed:
	docker compose exec docparse-arena uv run python seed_db.py

# Remove containers and volumes
clean:
	docker compose down -v
	rm -rf data/

# Show service status
status:
	docker compose ps

# Copy .env.example to .env if .env doesn't exist
env:
	@test -f .env || cp .env.example .env && echo ".env created from .env.example"
	@test -f .env && echo ".env already exists"
