## 2026-03-21 - [Bypass Google Maps Proxy Protection via Empty String in ALLOWED_REFERERS]
**Vulnerability:** Empty string default in `os.environ.get("ALLOWED_REFERERS", " ").split(" ")` resulted in an empty string in the allowed referers list. Any string `.startswith("")` evaluates to True, causing the `is_allowed_referer` check to pass unconditionally.
**Learning:** Defaulting to a single space `" "` and splitting by `" "` yields `['', '']`. Empty strings in security allow-lists that use `startswith()` checks or exact matches are extremely dangerous and can completely nullify the security controls.
**Prevention:** Always filter out empty strings after splitting environment variable strings, e.g., `[x for x in env.split(" ") if x]`.

## 2024-05-09 - [Information Exposure via RequestException in proxy views]
**Vulnerability:** Returning `str(e)` for `requests.exceptions.RequestException` directly to clients in `google_maps_proxy` view.
**Learning:** `requests` exception strings often embed the full requested URL, including sensitive query parameters like `?key=...`. Returning this to the client leaks API credentials.
**Prevention:** Catch external request exceptions, log them securely on the server (e.g. `traceback.print_exc()` or `logger.exception()`), and return a generic, static error message to the client.
