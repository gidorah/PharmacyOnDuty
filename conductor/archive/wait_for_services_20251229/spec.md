# Specification: Fix Container Startup Connection Race Conditions

## Overview
Currently, the Django application and its associated Celery services (Worker, Beat, Flower) occasionally fail at startup with "Temporary failure in name resolution" errors for the `db` and `redis` hosts. This is caused by a race condition where the application starts before the Docker internal DNS is ready or the services themselves are accepting connections.

## Functional Requirements
- **Wait Script:** Create a Python script `scripts/wait_for_services.py` to:
    - Verify PostgreSQL connectivity using `psycopg2`.
    - Verify Redis connectivity using the `redis` client.
    - Implement a configurable timeout (default 60 seconds).
    - Provide clear logging of connection attempts and status.
- **Entrypoint Integration:** Update `scripts/entrypoint.sh` to execute the wait script before running migrations or starting the main application/worker process.
- **Service Coverage:** Ensure the mechanism applies to:
    - Django Web Server
    - Celery Worker
    - Celery Beat
    - Flower

## Non-Functional Requirements
- **Robustness:** The script should handle `OperationalError` and `ConnectionError` gracefully during the wait period.
- **Security:** Ensure database passwords or sensitive connection strings are not printed in plain text to the logs during failed attempts.

## Acceptance Criteria
- [ ] `scripts/wait_for_services.py` successfully verifies both DB and Redis connections.
- [ ] `scripts/entrypoint.sh` correctly blocks service execution until the wait script exits successfully.
- [ ] Containers wait during startup if DB/Redis are not yet ready, instead of crashing.
- [ ] Verification script works in both development and production Docker environments.

## Out of Scope
- Implementing health checks at the Docker/Compose level (this fix focuses on the application entrypoint).
- Handling network partitions that occur *after* successful startup.
