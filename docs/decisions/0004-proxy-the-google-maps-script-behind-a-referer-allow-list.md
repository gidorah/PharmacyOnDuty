# Proxy the Google Maps script behind a referer allow-list

## Status

Accepted. Back-filled 28 Oct 2026. Includes the lessons from the Jules
security journal (`.jules/sentinel.md`, removed with this record).

## Context

The map page needs the Google Maps JavaScript API, which takes an API key in
the script URL. The project uses one `GOOGLE_MAPS_API_KEY` for the browser
script and for the server-side Geocoding, Places and Distance Matrix calls.

## Decision

The page loads the script from `google_maps_proxy`, which adds the key on the
server and fetches the script from Google. The proxy:

- serves only requests whose `Referer` starts with an entry of
  `ALLOWED_REFERERS`, checked before the cache;
- forwards only the client parameters in `ALLOWED_PROXY_PARAMS`; `key` and
  `libraries` are always set on the server;
- caches each URL for an hour, in each gunicorn process's own memory;
- on a network error, returns a fixed message and logs the details.

## Alternatives

- The key in the page template: simplest, but the key sits in every page's
  source.
- A separate browser key with a Google-side HTTP-referrer restriction: the
  standard control. Not in place; the shared key cannot carry a referrer
  restriction because the server uses it too.

## Consequences

- The proxy keeps the key out of the page source and fixes `key` and
  `libraries`. The script Google returns very likely contains the key, so it
  probably still reaches the browser (not verified). The referer check stops
  other sites hot-linking the proxy, not someone reading the key.
- `ALLOWED_REFERERS` is a security allow-list matched by prefix. An empty
  entry matches everything: filter empty strings when splitting the variable
  (PR #68, 21 Mar 2026).
- Never return a `requests` exception text to the client: it contains the
  request URL, and with it the key (PR #144, merged 9 Jul 2026). The server
  log line still contains it, and Sentry's logging integration may forward it.
- A non-2xx reply from Google is passed through as 200 JavaScript.
- The testenv adds `http://localhost:8000` and `http://127.0.0.1:` to the list
  so the map page works there.
