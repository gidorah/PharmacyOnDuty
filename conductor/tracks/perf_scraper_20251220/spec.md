# Track Specification: Optimize Scraper Performance

## Objective
Eliminate the N+1 query problem in the `add_scraped_data_to_db` function to ensure the application scales efficiently as the number of pharmacies increases.

## Scope
- **File:** `pharmacies/utils/utils.py`
- **Function:** `add_scraped_data_to_db`
- **Logic:** Refactor the loop that checks for existing pharmacies.

## Implementation Guidelines
- Fetch all existing pharmacy IDs/Phones for the target city into a `set` *before* iterating through scraped data.
- Check existence against this in-memory set.
- Use `bulk_create` and `bulk_update` if not already fully utilized.
