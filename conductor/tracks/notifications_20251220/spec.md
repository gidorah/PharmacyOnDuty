# Track Specification: Improve User Notifications

## Objective
Enhance the user experience by providing clear, timely, and visually distinct notifications for edge cases and system states. Specifically, address scenarios where the service is unavailable in a user's region or when no pharmacies can be found.

## Scope
- **Scenarios:**
    - "System not available in user's region" (e.g., user is outside supported cities).
    - "No open pharmacies found" (e.g., data issue or extreme hours).
    - "Location services denied/unavailable".
    - "Network errors" (offline/API failure).
- **UI Components:** Implement non-blocking notification toasts or modal alerts depending on severity.
- **Backend:** Ensure API returns appropriate error codes or status messages to trigger these notifications.

## Implementation Guidelines
- Use existing Tailwind CSS for styling.
- Ensure notifications are mobile-friendly and accessible.
- Follow the project's "Empathetic & Direct" tone.
