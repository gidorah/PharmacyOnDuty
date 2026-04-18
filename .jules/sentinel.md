## 2026-03-21 - [Bypass Google Maps Proxy Protection via Empty String in ALLOWED_REFERERS]
**Vulnerability:** Empty string default in `os.environ.get("ALLOWED_REFERERS", " ").split(" ")` resulted in an empty string in the allowed referers list. Any string `.startswith("")` evaluates to True, causing the `is_allowed_referer` check to pass unconditionally.
**Learning:** Defaulting to a single space `" "` and splitting by `" "` yields `['', '']`. Empty strings in security allow-lists that use `startswith()` checks or exact matches are extremely dangerous and can completely nullify the security controls.
**Prevention:** Always filter out empty strings after splitting environment variable strings, e.g., `[x for x in env.split(" ") if x]`.

## 2026-03-22 - [Exception Information Leakage via HTTP Responses]
**Vulnerability:** The proxy endpoint `google_maps_proxy` was returning `str(e)` directly to the user as the error string when `requests.exceptions.RequestException` was raised.
**Learning:** Returning raw Python exception representations such as `str(e)` from networking libraries like `requests` often leaks sensitive details such as full requested URLs including credentials/API keys embedded in query strings or server internal details.
**Prevention:** Never pass raw exceptions to HTTP response clients. Always return a generalized error message and log the exception server-side using the `logging` module so the raw data can be accessed safely for debugging without exposing vulnerabilities.
