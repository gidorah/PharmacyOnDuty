# Plan: Reduce Sentry Noise - DisallowedHost

This plan outlines the steps to filter out `DisallowedHost` exceptions from being sent to Sentry, reducing noise from automated scanners.

## Phase 1: Implement Sentry Filtering

- [ ] **Task 1: Verify Current Sentry Setup and Plan Fix (Red Phase)**
    - [ ] Create a temporary test or script to verify if `DisallowedHost` triggers a Sentry event (or identify how to mock this check).
    - [ ] Confirm that `DisallowedHost` is currently NOT ignored.
- [ ] **Task 2: Update Sentry Initialization (Green Phase)**
    - [ ] Modify `PharmacyOnDuty/settings.py` to add `django.http.DisallowedHost` to the `ignore_errors` list or implement a `before_send` filter in `sentry_sdk.init`.
    - [ ] Verify the change by running the verification script/test from Task 1.
- [ ] **Task 3: Quality Assurance**
    - [ ] Run `uv run python manage.py check` to ensure no settings errors.
    - [ ] Run `ruff` and `mypy` on `PharmacyOnDuty/settings.py`.
- [ ] **Task 4: Conductor - User Manual Verification 'Phase 1: Implement Sentry Filtering' (Protocol in workflow.md)**
