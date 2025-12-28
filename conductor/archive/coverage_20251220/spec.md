# Track Specification: Improve Test Coverage & Reliability

## Objective
Increase the project's test coverage to at least 80% by implementing comprehensive unit and integration tests for core components. This will ensure system stability and prevent regressions during future development.

## Scope
- **Models:** Verify all model methods, custom managers, and signal handlers.
- **Scrapers:** Create tests for utility scrapers (mocking external HTTP requests).
- **API Views:** Test all endpoints (, ) for correct responses, error handling, and permission checks.
- **Tasks:** Verify Celery task execution (mocking the broker).

## Implementation Guidelines
- Use pytest.
- Follow the TDD workflow outlined in `conductor/workflow.md`.
