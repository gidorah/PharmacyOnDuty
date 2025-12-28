# Track Plan: Improve Test Coverage & Reliability

## Phase 1: Model & Utility Tests
- [x] Task: Create tests for `City` model methods (e.g., `is_open`, `get_or_create_dummy`).
- [x] Task: Create tests for `WorkingSchedule` model logic.
- [x] Task: Create tests for `Pharmacy` model and spatial queries.
- [x] Task: Create unit tests for `utils.py` functions (mocking Google Maps API where needed).
- [~] Task: Conductor - User Manual Verification 'Model & Utility Tests' (Protocol in workflow.md)

## Phase 2: Scraper Tests
- [ ] Task: Implement tests for `ankaraeo_scraper.py` (using mocks for HTML responses).
- [ ] Task: Implement tests for `eskisehireo_scraper.py` (using mocks).
- [ ] Task: Implement tests for `istanbul_saglik_scraper.py` (using mocks).
- [ ] Task: Conductor - User Manual Verification 'Scraper Tests' (Protocol in workflow.md)

## Phase 3: API & Integration Tests
- [ ] Task: Create integration tests for `get_pharmacy_points` view (happy path and error cases).
- [ ] Task: Create tests for `google_maps_proxy` view (security and caching).
- [ ] Task: Conductor - User Manual Verification 'API & Integration Tests' (Protocol in workflow.md)
