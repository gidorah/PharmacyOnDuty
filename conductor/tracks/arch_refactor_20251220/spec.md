# Track Specification: Architecture Refactoring

## Objective
Improve code maintainability and flexibility by decoupling Celery task management from Model `save()` methods and removing hardcoded city strings.

## Scope
- **Models:** Remove `PeriodicTask` management from `WorkingSchedule.save` and `ScraperConfig.save`.
- **Signals/Services:** Move the task scheduling logic to Django Signals (`post_save`) or a dedicated service class.
- **City Configuration:** Refactor `get_city_name_from_location` and scraper dispatch logic to use a configuration object or database model instead of hardcoded strings ('istanbul', etc.).

## Implementation Guidelines
- Ensure strict separation of concerns: Models should only handle data.
- Use `django.dispatch` for signals.
- Ensure backward compatibility or provide a migration path for city configurations.
