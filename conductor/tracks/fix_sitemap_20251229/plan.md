# Plan: Fix Sitemap NoReverseMatch Error

This plan outlines the steps to resolve the `NoReverseMatch` error in the sitemap generation and ensure the `home` URL naming convention is consistently applied.

## Phase 1: Fix and Regression Testing [checkpoint: 4b3413d9661d5eee28cd50cb700523a0008fdd0b]

- [x] **Task 1: Create failing regression test (Red Phase)**
    - [x] Create `pharmacies/tests/test_sitemaps.py` (or update existing if found).
    - [x] Write a test case that attempts to reverse the `pharmacies_list` item in the sitemap or access the sitemap view.
    - [x] Confirm the test fails with `django.urls.exceptions.NoReverseMatch`.
- [x] **Task 2: Implement Fix (Green Phase)**
    - [x] Modify `PharmacyOnDuty/sitemaps.py` to replace `"pharmacies_list"` with `"home"`.
    - [x] Run the regression test and confirm it passes.
- [x] **Task 3: Search and Clean up Other References**
    - [x] Use `grep`/`ripgrep` to search for `"pharmacies_list"` usage in templates (`{% url ... %}`) and Python code (`reverse(...)`).
    - [x] Update any found occurrences to `"home"` if they refer to the main landing page URL name.
    - [x] *Note:* Do not change the view function name `pharmacies_list` in `views.py`.
- [x] **Task 4: Quality Assurance & Coverage**
    - [x] Run all tests using `uv run python manage.py test`.
    - [x] Verify code coverage for `sitemaps.py` and related logic.
    - [x] Run `ruff` and `mypy` to ensure code standards are met.
- [x] **Task 5: Conductor - User Manual Verification 'Phase 1: Fix and Regression Testing' (Protocol in workflow.md)**
