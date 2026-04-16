## 2026-03-21 - [Bypass Google Maps Proxy Protection via Empty String in ALLOWED_REFERERS]
**Vulnerability:** Empty string default in `os.environ.get("ALLOWED_REFERERS", " ").split(" ")` resulted in an empty string in the allowed referers list. Any string `.startswith("")` evaluates to True, causing the `is_allowed_referer` check to pass unconditionally.
**Learning:** Defaulting to a single space `" "` and splitting by `" "` yields `['', '']`. Empty strings in security allow-lists that use `startswith()` checks or exact matches are extremely dangerous and can completely nullify the security controls.
**Prevention:** Always filter out empty strings after splitting environment variable strings, e.g., `[x for x in env.split(" ") if x]`.

## 2025-05-24 - [API Key Leak via requests Exception Logging in Proxy]
**Vulnerability:** The `google_maps_proxy` view caught `requests.exceptions.RequestException` and returned `str(e)` in a 500 JSON response. The exception string from `requests` often includes the full URL, which contained `settings.GOOGLE_MAPS_API_KEY` in the query string, exposing the secret API key to users if the proxy failed (e.g. network timeout).
**Learning:** Returning or logging the raw string representation of third-party HTTP client exceptions (like `requests`) can inadvertently leak sensitive query parameters or authorization headers included in the failed request.
**Prevention:** Always return generic error messages to the client and scrub sensitive information before logging exceptions, or rely on proper server-side loggers instead of returning raw exception strings in API responses.
