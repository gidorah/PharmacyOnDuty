A reviewer reported these findings on the pull request:

```json
{{FINDINGS}}
```

Answer every finding by its `id`:

- **Fix** the findings you accept.
- **Remove** the change behind every finding with `"requested": false`. That
  is work the work order did not ask for. It cannot be declined.
- Findings in the categories {{HIGH_RISK}} cannot be declined either. Fix
  them.
- **Decline** any other finding you think is wrong or out of scope, with a
  reason a reviewer can check. A second review checks every answer.
