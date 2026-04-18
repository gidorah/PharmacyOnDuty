## 2026-03-21 - [Bypass Google Maps Proxy Protection via Empty String in ALLOWED_REFERERS]
**Vulnerability:** Empty string default in `os.environ.get("ALLOWED_REFERERS", " ").split(" ")` resulted in an empty string in the allowed referers list. Any string `.startswith("")` evaluates to True, causing the `is_allowed_referer` check to pass unconditionally.
**Learning:** Defaulting to a single space `" "` and splitting by `" "` yields `['', '']`. Empty strings in security allow-lists that use `startswith()` checks or exact matches are extremely dangerous and can completely nullify the security controls.
**Prevention:** Always filter out empty strings after splitting environment variable strings, e.g., `[x for x in env.split(" ") if x]`.

## 2026-04-11 - [Sensitive Data Leak via Raw Exception Strings in HTTP Clients]
**Vulnerability:** In `google_maps_proxy`, returning `str(e)` on `requests.exceptions.RequestException` exposed the full request URL, including sensitive query parameters like the `GOOGLE_MAPS_API_KEY`.
**Learning:** External API errors often embed sensitive context in exception messages. Directly passing these to API consumers leaks credentials, structure, and internal data.
**Prevention:** Never return raw exception strings from HTTP clients to the end user. Catch exceptions, log them server-side for debugging, and return a sanitized, generic error message (e.g., `An error occurred while communicating with the Maps API.`).
