# Track Specification: Fix Critical Security Vulnerabilities

## Objective
Remediate high-priority security risks identified in the code review to protect the application from data exposure, unauthorized API usage, and denial-of-service attacks.

## Scope
- **Configuration:** Ensure `DEBUG` is `False` by default in production.
- **API Protection:**
    - Improve `google_maps_proxy` security (Token/Rate Limit).
    - Secure `get_pharmacy_points` (Rate Limit, Review CSRF exemption).
- **Secrets Management:** Remove hardcoded credentials from settings and docker configurations.

## Implementation Guidelines
- Use `django-environ` or `python-dotenv` for all secrets.
- Implement `django-ratelimit` for API endpoints.
- Verify `Referer` checks are robust or replace with a better mechanism.
