# Track Specification: Add Dark Mode

## Objective
Implement a system-wide dark mode to improve user experience in low-light environments, aligning with modern mobile app standards.

## Scope
- **Tailwind Config:** Enable `class` based dark mode strategy.
- **UI Components:** Update all existing components (navbar, pharmacy cards, map controls, bottom sheet) to have `dark:` variant classes.
- **Toggle Switch:** Add a user-accessible toggle in the UI (e.g., in the navbar or settings menu).
- **Persistence:** Save the user's preference in `localStorage` and respect system preferences (`prefers-color-scheme`) by default.

## Implementation Guidelines
- Use Tailwind's `dark:` prefix.
- Ensure high contrast is maintained in dark mode.
- Test on both mobile and desktop views.
