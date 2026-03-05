# Specification: Comprehensive Location Testing Suite

## 1. Overview
This track aims to significantly enhance the reliability and correctness of the Pharmacy on Duty locator by implementing a data-driven test suite. We will test the system against a large, curated static dataset of user locations, covering in-scope cities, out-of-scope regions, and critical edge cases.

## 2. Functional Requirements

### 2.1 Static Test Data Fixture
- Create a dedicated fixture file (e.g., `tests/fixtures/test_locations.json`) containing a large set of coordinates.
- **Structure:** Each entry should include:
  - `latitude`, `longitude`
  - `description` (e.g., "Istanbul - Kadikoy Center")
  - `category` (e.g., "in_scope", "out_of_scope", "border", "anomaly")
  - `expected_behavior` (optional, e.g., "should_return_pharmacy")

### 2.2 Test Categories
The dataset must include:
- **In-Scope:** Random and specific points within Istanbul, Ankara, and Eskişehir.
- **City Borders:** Points sitting exactly on the administrative boundaries of these cities.
- **Unsupported Neighbors:** Locations in nearby non-supported cities (e.g., Bursa, Izmir, Kocaeli).
- **Geographic Anomalies:** Points in the Bosphorus, lakes, or unpopulated forest areas.
- **Global Distances:** International points to test extreme out-of-range behavior.

### 2.3 Assertions & Logic
For each location in the dataset, the test suite must perform:
1.  **Smoke Test:** Verify the API returns `200 OK` and a valid JSON structure.
2.  **Logic Verification:**
    - For **In-Scope**: Verify the returned pharmacy is indeed the closest one (can be validated against a pre-calculated expected ID or by mathematically checking distance to the result vs. other candidates).
    - For **Out-of-Scope**: Verify the system handles it gracefully (either returning the absolute nearest with a warning or an empty/error state as defined by current business logic).
    - **API Integration:** The logic verification must use mocked Google Distance Matrix API responses. However, these mocks must be based on **real recorded data** (snapshots) to ensure validity.
3.  **Performance:** Assert that the API response time is within acceptable limits (e.g., < 200ms) for spatial queries.

## 3. Non-Functional Requirements
- **Performance:** The test suite should use `pytest` markers (e.g., `@pytest.mark.benchmark` or similar) to allow excluding these high-volume tests during quick iteration if needed.
- **Maintainability:** The fixture file should be human-readable and easily extensible.
- **Deterministic:** Tests must not depend on live external APIs. All external calls must be mocked with recorded data.

## 4. Acceptance Criteria
- [ ] A JSON fixture file is created with at least 50+ diverse location entries.
- [ ] A "snapshot" file of real Google API responses for these locations is generated and saved.
- [ ] A new test module (e.g., `tests/test_location_coverage.py`) is implemented.
- [ ] Tests pass for all "In-Scope" locations, correctly identifying the nearest pharmacy using the snapshot data.
- [ ] Tests pass for "Out-of-Scope" and "Edge Case" locations, adhering to defined behavior.
- [ ] Response time assertions are implemented and passing.
