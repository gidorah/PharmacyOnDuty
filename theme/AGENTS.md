# THEME KNOWLEDGE BASE

`django-tailwind` app: Tailwind sources in `static_src/` (a Node project), templates in `templates/`, built assets in `static/`.

## Build

- `npm ci && npm run build` in `static_src` (`dev` watches). The app images have no Node, so run it on the host or in a `node` container; there is no `just` recipe.
- The production image does not build CSS: the committed `static/css/dist/styles.css` is what ships. Rebuild and commit it when templates or `static_src/tailwind.config.js` change.

## Conventions

- Utility-first: Tailwind classes directly in HTML. Extend `theme` in `static_src/tailwind.config.js` for design tokens.
- Templates are checked by djlint in CI (see the root `AGENTS.md`).

## Anti-patterns

- Raw CSS: no hand-written `.css` files in `static/`.
- Never edit `static/css/dist/styles.css` by hand (generated).
- No `style=""` attributes; use utilities.
- Keep npm/Node logic inside `static_src/`.
