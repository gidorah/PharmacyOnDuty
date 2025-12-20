# Track Plan: Architecture Refactoring

## Phase 1: Decouple Tasks from Models
- [ ] Task: Identify all side-effects in `WorkingSchedule` and `ScraperConfig` models.
- [ ] Task: Create `signals.py` in `pharmacies` app.
- [ ] Task: Move task management logic to `post_save` signals.
- [ ] Task: Clean up `save()` methods in models.
- [ ] Task: Conductor - User Manual Verification 'Decouple Tasks' (Protocol in workflow.md)

## Phase 2: Dynamic City Configuration
- [ ] Task: Design a configuration structure (dict or class) for supported cities and their scrapers.
- [ ] Task: Refactor `utils.py` to use this configuration instead of hardcoded strings.
- [ ] Task: Update scrapers to register themselves in this configuration.
- [ ] Task: Conductor - User Manual Verification 'Dynamic City Config' (Protocol in workflow.md)
