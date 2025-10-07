# Docker Compose Commands for PharmacyOnDuty

# Default recipe
default:
    @just --list

# Development commands
dev-up:
    docker-compose up -d
    @echo "Development environment started"

dev-down:
    docker-compose down
    @echo "Development environment stopped"

dev-logs:
    docker-compose logs -f

dev-rebuild:
    docker-compose up --build -d
    @echo "Development environment rebuilt and started"

dev-django:
    docker-compose exec django bash

dev-db:
    docker-compose exec db psql -U postgres -d gis

dev-redis:
    docker-compose exec redis redis-cli -a $REDIS_PASSWORD

# Production commands
prod-up:
    docker-compose -f docker-compose.prod.yml up -d
    @echo "Production environment started"

prod-down:
    docker-compose -f docker-compose.prod.yml down
    @echo "Production environment stopped"

prod-logs:
    docker-compose -f docker-compose.prod.yml logs -f

prod-rebuild:
    docker-compose -f docker-compose.prod.yml up --build -d
    @echo "Production environment rebuilt and started"

prod-django:
    docker-compose -f docker-compose.prod.yml exec django bash

# Worker commands
worker-up:
    docker-compose -f docker-compose.worker.yml up -d
    @echo "Worker environment started"

worker-down:
    docker-compose -f docker-compose.worker.yml down
    @echo "Worker environment stopped"

worker-logs:
    docker-compose -f docker-compose.worker.yml logs -f

worker-rebuild:
    docker-compose -f docker-compose.worker.yml up --build -d
    @echo "Worker environment rebuilt and started"

# Utility commands
clean:
    docker-compose down -v
    docker-compose -f docker-compose.prod.yml down -v
    docker-compose -f docker-compose.worker.yml down -v
    @echo "WARNING: This will remove unused Docker containers, images, and networks."
    @echo "Images older than 24 hours will be removed. Recent images will be kept."
    @echo "This operation is less destructive than 'docker system prune -f'."
    @echo ""
    @printf "Continue with cleanup? [y/N] " && read -r confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || exit 1
    docker container prune -f
    docker image prune --filter "until=24h" -f
    docker network prune -f
    @echo "Docker containers, old images, and networks cleaned"

ps:
    docker-compose ps
    docker-compose -f docker-compose.prod.yml ps
    docker-compose -f docker-compose.worker.yml ps

# Django management commands (dev)
migrate:
    docker-compose exec django uv run python manage.py migrate

makemigrations:
    docker-compose exec django uv run python manage.py makemigrations

collectstatic:
    docker-compose exec django uv run python manage.py collectstatic --noinput

shell:
    docker-compose exec django uv run python manage.py shell

test:
    docker-compose exec django uv run python manage.py test

# Full development setup
dev-setup: dev-up migrate
    @echo "Development environment setup complete"