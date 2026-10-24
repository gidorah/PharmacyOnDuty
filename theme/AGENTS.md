# THEME KNOWLEDGE BASE

## OVERVIEW
Django-Tailwind frontend. Manages Tailwind CSS compilation, static assets, and core layout templates.

## STRUCTURE
- `static_src/`: Node.js project. Tailwind source, config, and build pipeline.
- `static/`: Compiled assets (`dist/`), icons, and favicons.
- `templates/`: Base layouts and policy pages using Tailwind classes.

## WHERE TO LOOK
- `static_src/tailwind.config.js`: Custom colors, plugins, and template content paths.
- `static_src/src/styles.css`: CSS entry point with `@tailwind` directives.
- `static_src/package.json`: NPM scripts for `dev` (watch) and `build` (minify).
- `templates/*.html`: HTML templates where Tailwind classes are applied.

## CONVENTIONS
- **Utility-First**: Use Tailwind classes directly in HTML.
- **Build Flow**: `just tailwind` from root triggers `npm run build` in `static_src`.
- **Customization**: Extend `theme` in `tailwind.config.js` for project-specific design tokens.
- **Organization**: Group icons and logos in `static/icons/`.

## ANTI-PATTERNS
- **Raw CSS**: Avoid adding manual `.css` files to `static/`.
- **Manual Dist Edits**: Never modify `static/css/dist/styles.css` (auto-generated).
- **Hardcoded Styles**: Avoid `style=""` attributes; use Tailwind utilities instead.
- **Node in Root**: Keep NPM/Node logic strictly within `static_src/`.
