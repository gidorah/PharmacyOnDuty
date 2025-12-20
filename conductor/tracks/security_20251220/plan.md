# Track Plan: Fix Critical Security Vulnerabilities

## Phase 1: Configuration Hardening
- [ ] Task: Update `settings.py` to set `DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'`.
- [ ] Task: Audit and replace any hardcoded database passwords in `settings.py` and `docker-compose.yml` with env vars.
- [ ] Task: Conductor - User Manual Verification 'Configuration Hardening' (Protocol in workflow.md)

## Phase 2: API Security
- [ ] Task: Install and configure `django-ratelimit`.
- [ ] Task: Apply rate limiting to `get_pharmacy_points`.
- [ ] Task: Apply rate limiting to `google_maps_proxy`.
- [ ] Task: Investigate and implement stricter origin checks for `google_maps_proxy`.
- [ ] Task: Conductor - User Manual Verification 'API Security' (Protocol in workflow.md)
