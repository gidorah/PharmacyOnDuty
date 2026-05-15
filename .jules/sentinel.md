## 2026-03-21 - [Bypass Google Maps Proxy Protection via Empty String in ALLOWED_REFERERS]
**Vulnerability:** Empty string default in `os.environ.get("ALLOWED_REFERERS", " ").split(" ")` resulted in an empty string in the allowed referers list. Any string `.startswith("")` evaluates to True, causing the `is_allowed_referer` check to pass unconditionally.
**Learning:** Defaulting to a single space `" "` and splitting by `" "` yields `['', '']`. Empty strings in security allow-lists that use `startswith()` checks or exact matches are extremely dangerous and can completely nullify the security controls.
**Prevention:** Always filter out empty strings after splitting environment variable strings, e.g., `[x for x in env.split(" ") if x]`.

## 2026-03-22 - [API Key Leak in Exception Message]
**Vulnerability:** The Google Maps proxy endpoint caught `requests.exceptions.RequestException` and returned `str(e)` in its JSON response. Because the original request `params` included the Google Maps API key, the exception string contained the full requested URL, exposing the API key to the client.
**Learning:** Returning raw exception strings from HTTP clients (`requests`, `httpx`, etc.) to end users is extremely dangerous, as these strings often embed full URLs, request headers, or payloads that contain sensitive credentials.
**Prevention:** Always log HTTP client exceptions server-side (e.g., using `logging.error`) and return a generic, sanitized error message to the client.
