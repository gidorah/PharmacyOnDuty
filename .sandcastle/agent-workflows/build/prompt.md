# TASK

Build work order #{{ISSUE_NUMBER}}: {{ISSUE_TITLE}}

You are on branch `{{BRANCH}}`, created from `main`. The work order below is
the whole task. Onur approved it; nothing else is approved.

# WORK ORDER

{{WORK_ORDER}}

# CONTEXT

The project instructions in `AGENTS.md` apply. Read the `AGENTS.md` in a
subfolder before changing files there.

This runs on a GitHub Actions runner, not in the Docker Compose dev stack.
Where `AGENTS.md` says to use `just` or the container, run the same command
with `uv run` from the repository root instead. PostGIS and Redis run as
services on `localhost`, and the environment variables for them are set.

# SCOPE

- Change only what the work order's goal needs. Respect its "Out of scope"
  section.
- Write tests only at the work order's test points.
- Do not change the gate or the factory: `.github/`, `.sandcastle/`,
  `factory/`, `tests/conftest.py`, `tests/test_factory_files.py`,
  `.pre-commit-config.yaml`, or any `AGENTS.md`. Workflow changes cannot be
  pushed at all.
- Do not delete or skip tests. The gate fails a change that does.
- If the work order is unclear or cannot be done as written, make no commits
  and explain why in your final message.

# EXECUTION

Explore the code and the relevant tests before editing. Where a test seam
exists, work test first: write a failing test, make it pass, then tidy up.

Before each commit, run the gate's checks that apply to your change:

- `uv run ruff check .` and `uv run ruff format --check .`
- `uv run mypy .`
- `uv run python manage.py makemigrations --check --dry-run`
- `PYTHONPATH=.github/scripts uv run pytest -p factory_gate_pytest -x` (the
  same plugin as the gate: no outbound network, Celery tasks run inline)

Then run the work order's "Done check" commands.

# COMMIT

Make one or more commits on `{{BRANCH}}`. Use the repository's commit style:
a gitmoji plus a conventional prefix, for example `✨ feat(scrapers): ...` or
`🐛 fix: ...`.

You have no GitHub credentials. Do not push, open pull requests, edit labels,
or comment. Plain pipeline steps do that after you finish.

When the work is committed, output `<promise>COMPLETE</promise>`.
