# Docker Compose Commands for PharmacyOnDuty
# 
# Default recipe
default:
    @just --list
 
# Development commands
dev-up:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . up -d
    @echo "Development environment started"
 
dev-down:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . down
    @echo "Development environment stopped"
 
dev-logs:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . logs -f
 
dev-rebuild:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . up --build -d
    @echo "Development environment rebuilt and started"
 
dev-django:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django bash
 
dev-db:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . exec db psql -U postgres -d gis
 
dev-redis:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . exec redis redis-cli -a $REDIS_PASSWORD
 
# Production commands
prod-up:
    docker-compose -f docker/prod/services/docker-compose.yml --project-directory . up -d
    @echo "Production environment started"
 
prod-down:
    docker-compose -f docker/prod/services/docker-compose.yml --project-directory . down
    @echo "Production environment stopped"
 
prod-logs:
    docker-compose -f docker/prod/services/docker-compose.yml --project-directory . logs -f
 
prod-rebuild:
    docker-compose -f docker/prod/services/docker-compose.yml --project-directory . up --build -d
    @echo "Production environment rebuilt and started"
 
prod-django:
    docker-compose -f docker/prod/services/docker-compose.yml --project-directory . exec django bash
 
# Worker commands
worker-up:
    docker-compose -f docker/prod/workers/docker-compose.yml --project-directory . up -d
    @echo "Worker environment started"
 
worker-down:
    docker-compose -f docker/prod/workers/docker-compose.yml --project-directory . down
    @echo "Worker environment stopped"
 
worker-logs:
    docker-compose -f docker/prod/workers/docker-compose.yml --project-directory . logs -f
 
worker-rebuild:
    docker-compose -f docker/prod/workers/docker-compose.yml --project-directory . up --build -d
    @echo "Worker environment rebuilt and started"
 
# Utility commands
clean:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . down -v
    docker-compose -f docker/prod/services/docker-compose.yml --project-directory . down -v
    docker-compose -f docker/prod/workers/docker-compose.yml --project-directory . down -v
    @echo "WARNING: This will remove unused Docker containers, images, and networks."
    @echo "Images older than 24 hours will be removed. Recent images will be kept."
    @echo "This operation is less destructive than 'docker system prune -f'."
    @echo ""
    @printf "Continue with cleanup? [y/N] " &amp;&amp; read -r confirm &amp;&amp; [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || exit 1
    docker container prune -f
    docker image prune --filter "until=24h" -f
    docker network prune -f
    @echo "Docker containers, old images, and networks cleaned"
 
ps:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . ps
    docker-compose -f docker/prod/services/docker-compose.yml --project-directory . ps
    docker-compose -f docker/prod/workers/docker-compose.yml --project-directory . ps
 
# Django management commands (dev)
manage command:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django uv run python manage.py {{command}}

migrate:
    @just manage "migrate"

makemigrations:
    @just manage "makemigrations"

createsuperuser:
    @just manage "createsuperuser"

collectstatic:
    @just manage "collectstatic --noinput"

shell:
    @just manage "shell"

test:
    @just manage "test"

# Utility commands
seed:
    @just manage "seed_cities"

urls:
    @just manage "show_urls"

celery-logs:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . logs -f celery

# Tail logs of a specific service
logs service:
    docker-compose -f docker/dev/docker-compose.yml --project-directory . logs -f {{service}}

# Full development setup
dev-setup: dev-up migrate
    @echo "Development environment setup complete"