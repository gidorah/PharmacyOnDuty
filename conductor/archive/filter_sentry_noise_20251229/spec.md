# Specification: Reduce Sentry Noise - DisallowedHost

## Overview
The application is reporting `DisallowedHost` errors in Sentry (Issue `ECZANEREDE-B`). These errors occur when automated scanners or health checks hit the application with invalid or empty `Host` headers. Since these are not actionable application bugs, this track aims to filter them out of Sentry to reduce noise and quota usage.

## Functional Requirements
1.  **Sentry Filtering:** Update the Sentry SDK initialization in `PharmacyOnDuty/settings.py` to ignore `django.http.DisallowedHost` exceptions.
2.  **Verification:** Ensure that legitimate errors are still captured and only the specific `DisallowedHost` noise is suppressed.

## Non-Functional Requirements
1.  **Maintainability:** Use standard Sentry SDK filtering methods (e.g., `before_send` or `ignore_errors` list).

## Acceptance Criteria
1.  The `sentry_sdk.init` call in `settings.py` is updated to exclude `DisallowedHost`.
2.  Triggering a `DisallowedHost` error locally (if possible) confirms it is no longer sent to Sentry.
3.  Code style (Ruff/Mypy) remains valid.

## Out of Scope
*   Configuring Nginx or load balancer level filtering.
*   Filtering other transient infrastructure errors (e.g., Redis/DB connection issues) at this time.
