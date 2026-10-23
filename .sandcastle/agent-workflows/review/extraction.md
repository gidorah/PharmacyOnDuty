Emit your review as a single `<output>` block, the last thing in your response.

Do not change files. Do not run commands. Do not write text outside the
`<output>` block.

The block holds one JSON object of this shape:

<output>
{{OUTPUT_EXAMPLE}}
</output>

Use an empty `findings` list when there is nothing to report. In round 1,
`previous` is an empty list.
