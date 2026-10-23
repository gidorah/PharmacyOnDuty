The CI gate is red on the current head commit, also after one rerun of the
failed jobs. This is fix try {{ATTEMPT}} of 2 for this failure. Make the
gate green without changing what the work order asks for.

Gate run: {{GATE_URL}}
Failed jobs: {{FAILED_JOBS}}

The log lines of the failed jobs:

```text
{{CI_LOGS}}
```

Find the cause first. If the failure has nothing to do with this change (for
example, a broken runner or a service that did not start), make no commit and
say so in `cause`.
