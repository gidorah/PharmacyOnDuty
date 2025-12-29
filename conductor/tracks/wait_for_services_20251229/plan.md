# Plan: Fix Container Startup Connection Race Conditions

This plan addresses the "Temporary failure in name resolution" errors during container startup by implementing a robust "wait-for-services" mechanism.

## Phase 1: Preparation & Core Logic [checkpoint: 415506565c97f2d5a5cd2810bbf68e5454f16419]
In this phase, we create the standalone Python script that will handle the connection checks for PostgreSQL and Redis.

- [x] Task: Create `scripts/wait_for_services.py` with connectivity logic for DB and Redis.
- [x] Task: Create unit tests for `wait_for_services.py` (mocking socket/psycopg2/redis).
- [x] Task: Conductor - User Manual Verification 'Phase 1: Preparation & Core Logic' (Protocol in workflow.md)

## Phase 2: Integration & Deployment
In this phase, we integrate the wait script into the container entrypoint and verify it works across all relevant services.

- [ ] Task: Update `scripts/entrypoint.sh` to call `wait_for_services.py` before any other commands.
- [ ] Task: Verify `docker/dev/Dockerfile` and `docker/prod/Dockerfile` correctly include/access the new script.
- [ ] Task: Test the startup flow using `docker-compose` to ensure services wait appropriately.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Integration & Deployment' (Protocol in workflow.md)

## Phase 3: Verification & Cleanup
Final verification and removal of any temporary reproduction scripts.

- [ ] Task: Verify logs show successful "Waiting for..." messages during a fresh `just dev-up`.
- [ ] Task: Remove `reproduce_connection_issue.py`.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification & Cleanup' (Protocol in workflow.md)
