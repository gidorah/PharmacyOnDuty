# Tech Stack - Eczanerede

## Backend
- **Python 3.13:** Primary language for business logic and scraping.
- **Django 5.1:** High-level web framework for rapid development and robust architecture.
- **GeoDjango:** Django module for handling geographic data.
- **Celery:** Asynchronous task queue for running scrapers and background tasks.
- **Redis:** Message broker for Celery and caching backend.
- **Gunicorn:** Production WSGI HTTP server.

## Frontend
- **HTML5 & Tailwind CSS:** Modern, utility-first CSS framework for responsive design.
- **JavaScript (ES6+):** Client-side interactivity.
- **jQuery:** DOM manipulation and AJAX handling.
- **Hammer.js:** Multi-touch gesture support for mobile swiping.
- **Google Maps JS API:** Interactive maps, geocoding, and routing.

## Database & Infrastructure
- **PostgreSQL 15 + PostGIS:** Relational database with spatial extensions for location-based queries.
- **Docker & Docker Compose:** Containerization for consistent development and production environments.
- **WhiteNoise:** Efficient static file serving for Django.
- **Sentry:** Real-time error monitoring.
- **Startup Synchronization:** Custom Python "wait-for" script to ensure service readiness before application boot.

## Deployment & CI/CD
- **Hetzner VPS:** Hosting provider for core services (Django app, Database, Redis).
- **Raspberry Pi 4:** Home server hosting Celery workers to bypass geoblocking restrictions on scraping targets.
- **Coolify:** Self-hosted PaaS on the cloud VPS used for:
  - **Reverse Proxy:** Manages SSL/HTTPS and traffic routing (replacing standalone Nginx).
  - **Auto-deployment:** Continuous delivery of the `main` branch.
  - **Preview Environments:** Automated deployments for Pull Requests.

## Development Tools
- **uv:** Extremely fast Python package and project manager.
- **just:** Command runner for common project tasks.
- **pytest:** Feature-rich testing framework (with pytest-django and pytest-cov).
- **Ruff:** Fast Python linter and formatter.
- **Mypy:** Static type checking.
- **debugpy:** Remote debugging support in Docker.
