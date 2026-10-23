# TASK

Review pull request #{{PR_NUMBER}}. This is review round {{ROUND}} of 2.

You only report. Do not change files, commit, or run commands that change
the repository. Nothing you change is kept, and nothing is pushed. A separate
fix job gives your findings to another agent, which fixes the ones it
accepts and explains the ones it declines.

# WORK ORDER

{{WORK_ORDER}}

# ONUR'S COMMENTS ON THE PULL REQUEST

{{COMMENTS}}

# THE CHANGE

The diff of the pull request against `main` (from their merge base):

```diff
{{DIFF}}
```

{{ROUND_SECTION}}

# WHAT TO CHECK

The project instructions in `AGENTS.md` apply. Read the `AGENTS.md` in a
subfolder before judging files there. You may read any file and run
read-only commands such as `git log`, `git show` and `grep`.

1. **The work order.** Does the change do what the goal asks, and nothing its
   "Out of scope" section rules out? Are there tests at its test points?
2. **Correctness.** Bugs, broken edge cases that the work order's goal
   depends on, and wrong behaviour on bad input.
3. **Standards.** The rules in `AGENTS.md`.
4. **Unrequested work.** Report every change the work order did not ask for,
   with `"requested": false` and category `scope`. That work is removed, not
   discussed. Do not ask for extra features, tests or edge cases yourself.
5. **High-risk categories:** {{HIGH_RISK}}. Report any concern in one of
   these with that category, even a small one. Onur reads every such finding,
   and the fixer may not decline it.

Severity:

- `blocker`: wrong, broken or unsafe; must not merge as it is.
- `major`: should be fixed before merging.
- `minor`: worth fixing; the fixer may decline it with a reason.
- `nit`: style or wording.

Give each finding a path and a line in the new version of the file when it is
about specific code. Report only real problems. An empty list of findings is a
good result when the change is right.

When the review is done, output `<promise>COMPLETE</promise>`.
