# Decisions

One file per decision that is hard to reverse, would surprise someone without
the context, and came from a real trade-off. A decision that misses any of the
three goes in a PR description instead.

- Number files in order: `NNNN-what-was-decided.md`, named after the decision.
- Sections: Status, Context, Decision, Consequences. Keep it to a page.
- Never edit an accepted decision's substance. Write a new one that replaces
  it and set the old one's status to "Replaced by NNNN".
- Records 0001 to 0005 were written on 28 Oct 2026 from code, commit history,
  PR threads and the factory's run log, after the decisions were made.
