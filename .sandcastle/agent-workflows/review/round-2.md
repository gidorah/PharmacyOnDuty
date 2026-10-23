# ROUND 2: CHECK THE FIXES

Round 1 reviewed commit `{{SINCE_SHA}}` and reported these findings:

```json
{{EARLIER_FINDINGS}}
```

The fixer answered them like this (`fixed`, `removed`, `declined` with a
reason, or `none` when it gave no answer; `declineRefused` means the rules did
not allow that decline):

```json
{{EARLIER_RESPONSES}}
```

The commits since round 1:

```diff
{{NEW_DIFF}}
```

In this round, check only two things:

1. For every round 1 finding, add an entry to `previous` with its id and a
   status:
   - `fixed`: the new commits fix it;
   - `declined_accepted`: the fixer declined it with a sound reason;
   - `declined_rejected`: the decline is not convincing;
   - `not_fixed`: not fixed and not properly declined.
   Unrequested work (`"requested": false`) and findings in the high-risk
   categories cannot be declined. A decline of those is `declined_rejected`.
2. New problems in the new commits. Report them as findings. Do not review
   the unchanged code again.
