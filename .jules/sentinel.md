## 2026-03-21 - [Bypass Google Maps Proxy Protection via Empty String in ALLOWED_REFERERS]
**Vulnerability:** Empty string default in `os.environ.get("ALLOWED_REFERERS", " ").split(" ")` resulted in an empty string in the allowed referers list. Any string `.startswith("")` evaluates to True, causing the `is_allowed_referer` check to pass unconditionally.
**Learning:** Defaulting to a single space `" "` and splitting by `" "` yields `['', '']`. Empty strings in security allow-lists that use `startswith()` checks or exact matches are extremely dangerous and can completely nullify the security controls.
**Prevention:** Always filter out empty strings after splitting environment variable strings, e.g., `[x for x in env.split(" ") if x]`.

## 2024-05-16 - [API Key Leaked via Exception Handling]
**Vulnerability:** In `pharmacies/views.py`, the `google_maps_proxy` view directly returns `str(e)` inside the `except requests.exceptions.RequestException as e:` block. The generic exception string naturally contains the full request URL, which includes sensitive parameter values such as the Google Maps API Key (`?key=...`).
**Learning:** Returning unhandled or broadly caught HTTP request exceptions directly to the user client can easily expose hardcoded credentials, sensitive tokens, or internal infrastructure details embedded within the URL path or query string.
**Prevention:** Instead of logging raw exceptions to the client, catch exceptions to log them server-side utilizing standard logging mechanisms (`logger.error()`), and return generic error messages (e.g., "Failed to proxy request.") to the client.
