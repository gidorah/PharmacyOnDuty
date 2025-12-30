# Plan: Comprehensive Location Testing Suite

## Phase 1: Data Preparation & Snapshots
- [x] Task: Create Static Fixture
    - Create `tests/fixtures/location_scenarios.json`.
    - Populate with 50+ entries covering: In-Scope (Istanbul, Ankara, Eskisehir), Border cases, Neighboring cities (Bursa, etc.), and Anomalies (Water, International).
- [x] Task: Generate Real Data Snapshots
    - Create a temporary utility script (e.g., `scripts/record_distance_matrix.py`) to fetch REAL Google Distance Matrix data for every location in the fixture.
    - Save these responses to `tests/fixtures/google_api_snapshots.json`.
    - *Note:* This ensures our tests use realistic traffic/distance data without incurring repeated API costs.
- [~] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Test Implementation (TDD)
- [ ] Task: Create Test Module `tests/test_location_coverage.py`
- [ ] Task: Implement Replay Mocking
    - Update `tests/conftest.py` to mock `_get_distance_matrix_data`.
    - The mock must look up the correct response from `google_api_snapshots.json` based on the input coordinates.
- [ ] Task: Implement Smoke Tests (Status 200)
    - Use `pytest.mark.parametrize` to load from the JSON fixture.
    - Assert that valid locations return 200 and invalid/out-of-scope ones handled gracefully.
- [ ] Task: Implement Logic Verification
    - Verify that *given* the real snapshot data, the app correctly identifies the optimal pharmacy.
- [ ] Task: Implement Performance Benchmarks
    - Add assertions to ensure the view processing time (excluding the mocked API lookup) is efficient (<200ms).
- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: Final Verification
- [ ] Task: Run Full Suite & Refactor
    - Run all new tests.
    - Optimize any slow queries discovered by the benchmark.
- [ ] Task: Conductor - User Manual Verification 'Final Verification' (Protocol in workflow.md)
