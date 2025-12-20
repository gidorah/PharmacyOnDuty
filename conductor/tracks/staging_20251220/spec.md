# Track Specification: Add Staging Environment & Enforce Workflow

## Objective
Establish a formal staging environment and enforce a strict git workflow to improve deployment stability. This ensures that changes are tested in a production-like environment before reaching users.

## Scope
- **Git Workflow:**
    - Create a long-lived `dev` branch.
    - Protect `main` branch (require PRs, no direct commits).
    - PRs must target `dev` first.
    - Merges to `main` happen only from `dev` (or via release tags).
- **Deployment:**
    - Configure Coolify to auto-deploy the `dev` branch to a Staging environment (e.g., `staging.eczanerede.com` or similar).
    - Configure Coolify to trigger preview deployments for PRs targeting `dev`.
    - Production continues to deploy from `main`.

## Implementation Guidelines
- Document the new workflow in `Docs/git-workflow.md`.
- Update Coolify configuration (verify via screenshots or config files if accessible).
- Ensure environment variables are correctly isolated between Staging and Production.
