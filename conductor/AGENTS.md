# AGENTS: CONDUCTOR

## OVERVIEW
Critical governance hub and AI orchestration center. Source of Truth for project evolution, architecture, and quality standards.

## STRUCTURE
- `tracks/`: Active work units. Mandatory for ALL changes.
- `archive/`: Historical record of completed/cancelled tracks.
- `code_styleguides/`: Language-specific standards (Python, HTML/CSS, JS).
- `workflow.md`: The core "Conductor" TDD protocol and verification lifecycle.
- `product.md` / `tech-stack.md`: Product mission and technical blueprints.
- `tracks.md`: Global index of current and upcoming efforts.

## WHERE TO LOOK
- **Active Track**: `conductor/tracks/<track_id>/`
- **TDD Protocol**: `conductor/workflow.md`
- **Architecture**: `conductor/tech-stack.md`
- **Style Rules**: `conductor/code_styleguides/`

## CONVENTIONS
- **TDD Mandatory**: RED (failing test) -> GREEN (pass) -> REFACTOR cycle.
- **Task Status**: `[ ]` (Pending), `[~]` (Active), `[x]` (Verified Done).
- **Spec Format**: MUST include `Acceptance Criteria` and `Out of Scope`.
- **Plan Format**: Phase-based sequential tasks + mandatory verification blocks.
- **Verification**: >80% coverage + manual user sign-off required for phase exit.
- **Checkpoints**: Commit + Git Notes report + SHA update in `plan.md`.

## ANTI-PATTERNS
- **Ghost Work**: Implementing code without an active track/plan.
- **Skipping RED**: Writing implementation before a failing test exists.
- **Broken Chain**: Updating code without marking `[~]` in `plan.md`.
- **Silent Phase**: Completing a phase without Git Notes verification report.
- **Tech Drift**: Implementation diverging from `tech-stack.md` without prior sync.
