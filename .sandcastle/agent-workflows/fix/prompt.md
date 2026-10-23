# TASK

Fix pull request #{{PR_NUMBER}} on branch `{{BRANCH}}`.

{{TASK_SECTION}}

# WORK ORDER

{{WORK_ORDER}}

# ONUR'S COMMENTS ON THE PULL REQUEST

{{COMMENTS}}

# THE CHANGE SO FAR

The diff of the pull request against `main`:

```diff
{{DIFF}}
```

# CONTEXT

The project instructions in `AGENTS.md` apply. Read the `AGENTS.md` in a
subfolder before changing files there.

This runs on a GitHub Actions runner, not in the Docker Compose dev stack.
Where `AGENTS.md` says to use `just` or the container, run the same command
with `uv run` from the repository root instead. PostGIS and Redis run as
services on `localhost`, and the environment variables for them are set.

# SCOPE

- Change only what this task needs. The work order's "Out of scope" section
  still applies.
- Do not change the gate or the factory: `.github/`, `.sandcastle/`,
  `factory/`, `tests/conftest.py`, `tests/test_factory_files.py`,
  `.pre-commit-config.yaml`, or any `AGENTS.md`. Workflow changes cannot be
  pushed at all.
- Do not delete or skip tests to make the gate pass. The gate fails a change
  that does, and only Onur can approve removing a test.

# CHECKS

Before each commit, run the gate's checks that apply to your change:

- `uv run ruff check .` and `uv run ruff format --check .`
- `uv run mypy .`
- `uv run python manage.py makemigrations --check --dry-run`
- `PYTHONPATH=.github/scripts uv run pytest -p factory_gate_pytest -x`

# COMMIT

Add commits on top of `{{BRANCH}}`; do not rewrite or squash the existing
ones. Use the repository's commit style: a gitmoji plus a conventional
prefix, for example `🐛 fix: ...`.

You have no GitHub credentials. Do not push, comment, or edit labels. Plain
pipeline steps post your answers after you finish.

When you are done, output `<promise>COMPLETE</promise>`.
