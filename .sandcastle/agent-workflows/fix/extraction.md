Emit your answer as a single `<output>` block, the last thing in your response.

Do not change files. Do not run commands. Do not write text outside the
`<output>` block.

The block holds one JSON object of this shape:

<output>
{
  "summary": "What you changed and why, in 2 to 6 sentences. Say so if you made no commit.",
  "cause": "For a CI failure: your best guess at its cause, in 1 to 3 sentences. Otherwise an empty string.",
  "responses": [
    { "id": "R1-1", "action": "fixed | removed | declined", "reason": "Why; required when declined" }
  ]
}
</output>

`responses` has one entry per review finding you were given, and is an empty
list when you were given none.
