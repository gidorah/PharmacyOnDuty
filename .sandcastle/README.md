# Factory label pipeline

The scripts and prompts behind the `factory-*` workflows. They are adapted
from [Sandcastle](https://github.com/mattpocock/sandcastle) v0.12.0, which is
pinned in `package.json` together with the Claude Code CLI.

The design is in the software-factory repository: `factory-design.md`,
decision 9 in `decisions.md`, and `pilot/stage-0.md`.

## Layout

- `agent-workflows/`: the parts that run Claude, one folder per station, with
  its prompt. They read files that a plain job wrote and write results to
  `OUTPUT_DIR`. They never call GitHub and get no GitHub token.
- `steps/`: plain code with no Claude. These scripts hold the built-in
  `GITHUB_TOKEN` and do everything that writes to GitHub: labels, comments,
  pushes, pull requests, starting the next workflow.
- `tests/`: unit tests for both, run with `npm test`.

Nothing in `steps/` imports Sandcastle, and nothing in `agent-workflows/`
imports `steps/github.ts`.

## How a work order moves

Each workflow splits into jobs, and a job boundary is a fresh runner:

1. **prepare** (plain): checks who started it and that the work order is
   approved and unchanged, moves the labels, writes the agent's input.
2. **agent** (Claude): read-only token, `persist-credentials: false`, no
   `GH_TOKEN`. Its commits leave the job as a git bundle.
3. **publish** (plain): checks the bundle, pushes, comments, starts the gate
   with `gh workflow run`, waits for its `gate` job, and starts the next
   station the same way (decision S0-7).

## Running the tests

```bash
npm ci --ignore-scripts
npm run typecheck
npm test
```
