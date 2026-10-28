# Decisions

One file per decision that is hard to reverse or dangerous to undo by
accident, would surprise someone without the context, and came from a real
trade-off. A decision that misses any of the three goes in a PR description
instead.

- Number files in order: `NNNN-what-was-decided.md`, named after the decision.
- Sections: Status, Context, Decision, Alternatives, Consequences. Keep it to a
  page. Say what a change must not undo, and mark a reason that was inferred
  rather than recorded.
- Never edit an accepted decision's substance. Write a new one that replaces
  it and set the old one's status to "Replaced by NNNN".
- Records 0001 to 0006 were written on 28 Oct 2026 from code, commit history,
  PR threads and the factory's run log, after the decisions were made, and
  checked by two independent reviews against the code and history.
