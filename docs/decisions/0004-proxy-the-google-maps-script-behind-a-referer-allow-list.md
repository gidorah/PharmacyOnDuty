# Proxy the Google Maps script behind a referer allow-list

## Status

Accepted. Back-filled 28 Oct 2026. Includes the lessons from the Jules
security journal (`.jules/sentinel.md`, removed with this record).

## Context

The map page needs the Google Maps JavaScript API, which takes the API key in
the script URL. A key in the page source can be copied and billed to the
project.

## Decision

The page loads the script from `google_maps_proxy`, which adds the key on the
server and fetches it from Google. The proxy:

- serves only requests whose `Referer` starts with an entry of
  `ALLOWED_REFERERS`, checked before the cache;
- forwards only the client parameters in `ALLOWED_PROXY_PARAMS`; `key` and
  `libraries` are always set on the server;
- caches each URL for an hour;
- returns a fixed error message on failure and logs the details server-side.

## Consequences

- `ALLOWED_REFERERS` is a security allow-list matched by prefix. An empty
  entry matches everything: filter empty strings when splitting the variable
  (fixed 21 Mar 2026).
- Never return a `requests` exception text to the client: it contains the
  request URL, and with it the key (fixed 16 May 2024).
- A referer can be forged by a non-browser client, so this limits casual reuse
  of the key, not abuse. Google-side key restrictions still matter.
- The testenv adds `http://localhost:8000` and `http://127.0.0.1:` to the list
  so the map page works there.
