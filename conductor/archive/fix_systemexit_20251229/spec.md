# Specification: Fix SystemExit: 1 Error

## Overview
The application is reporting a `SystemExit: 1` error (Issue `ECZANEREDE-A` in Sentry). This indicates that a Python process (likely a management command, Celery worker, or startup script) is exiting with a failure status. This track aims to identify the root cause of these exits and implement a fix to ensure stable operation.

## Functional Requirements
1.  **Identify Root Cause:** Analyze Sentry stack traces and event details for Issue `ECZANEREDE-A` to determine which specific script or command is failing.
2.  **Resolve Underlying Bug:** Fix the code logic error that leads to the `SystemExit: 1`.
3.  **Enhance Error Handling:** Implement robust error handling (e.g., `try-except` blocks) in the failing script to capture and log detailed error information before exiting, or to allow the process to recover if appropriate.
4.  **Logging:** Ensure that any fatal errors are logged clearly to assist in future debugging.

## Non-Functional Requirements
1.  **Stability:** Prevent unexpected process terminations that impact service availability (especially for background workers).

## Acceptance Criteria
1.  The specific cause of `SystemExit: 1` is identified and documented.
2.  The underlying bug is fixed, and the script no longer exits prematurely under the identified conditions.
3.  Error handling is improved to provide more context in logs/Sentry if a similar failure occurs.
4.  Sentry reports for `ECZANEREDE-A` cease after the fix is deployed.

## Out of Scope
*   Fixing other unrelated Sentry issues.
*   Major architectural changes to the task queue or deployment pipeline unless directly required for the fix.
