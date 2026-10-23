// Plain step after the review agent: check its findings, post them, and hand
// the pull request on.
//
//   tsx steps/publish-review.ts --pr 123 --handoff "$RUNNER_TEMP/handoff" \
//     --output "$RUNNER_TEMP/agent-out/review.json"
//
// Round 1 with findings goes to the fix job. Round 2 goes to the tier job, or
// to `agent:stuck` when findings of a blocking kind are still open.

import { parseArgs } from "node:util";
import { assignIds, blockingIds, parseReviewOutput } from "./findings.ts";
import { comment, dispatchWorkflow, githubFromEnv, listComments, removeLabels, runUrl } from "./github.ts";
import { type ReviewContext, readJson } from "./handoff.ts";
import { markerLine, readMarkers, reviewFixAfter, reviewRounds, sinceReset } from "./markers.ts";
import { earlierTable, findingsTable } from "./render.ts";
import { sanitizeAgentText } from "./sanitize.ts";
import { markStuck } from "./stuck.ts";

const { values } = parseArgs({
  options: { pr: { type: "string" }, handoff: { type: "string" }, output: { type: "string" } },
});
const pr = Number(values.pr);
if (!Number.isInteger(pr) || !values.handoff || !values.output) {
  throw new Error("Usage: publish-review.ts --pr <n> --handoff <dir> --output <review.json>");
}

const context = readJson<ReviewContext>(`${values.handoff}/context.json`);
const { round, headSha, highRisk } = context;
// The agent job's output is checked again here, on a runner it never touched.
const output = parseReviewOutput(readJson<unknown>(values.output), highRisk);
const findings = assignIds(round, output.findings);
const earlierIds = new Set(context.earlierFindings.map((f) => f.id));
const previous = output.previous.filter((p) => earlierIds.has(p.id));
const blocking = blockingIds(
  round,
  findings,
  highRisk,
  round > 1 ? { findings: context.earlierFindings, responses: context.earlierResponses, previous } : undefined,
);

const nextText =
  round === 1
    ? findings.length > 0
      ? "Next: the fix job answers every finding."
      : "Next: the tier job."
    : blocking.length > 0
      ? `Next: \`agent:stuck\`. ${blocking.length} finding(s) of a blocking kind are still open after two rounds.`
      : "Next: the tier job.";

const github = githubFromEnv();
comment(
  github,
  pr,
  [
    markerLine({ kind: "review", round, sha: headSha, findings, previous, blocking }),
    `**Review round ${round} of 2** (Opus, commit ${headSha.slice(0, 7)})`,
    "",
    sanitizeAgentText(output.summary),
    "",
    ...(round > 1
      ? ["**Round 1 findings**", "", ...earlierTable(context.earlierFindings, context.earlierResponses, previous, blocking), "", "**New findings in the fix commits**", ""]
      : []),
    ...findingsTable(findings, highRisk),
    "",
    `Blocking: ${blocking.length > 0 ? blocking.join(", ") : "none"}. ${nextText}`,
    "",
    `Review run: ${runUrl()}`,
  ].join("\n"),
);
removeLabels(github, pr, ["agent:review", "agent:in-progress"]);

if (round === 1 && findings.length > 0) {
  dispatchWorkflow(github, "factory-fix.yml", { pr: String(pr), reason: "review" });
} else if (round > 1 && blocking.length > 0) {
  const current = sinceReset(readMarkers(listComments(github, pr)));
  const first = reviewRounds(current)[0];
  const fix = first ? reviewFixAfter(current, first) : null;
  const titles = [...context.earlierFindings, ...findings]
    .filter((f) => blocking.includes(f.id))
    .map((f) => `- ${f.id} (${f.severity}, ${f.category}): ${sanitizeAgentText(f.title)}`);
  markStuck(github, pr, {
    headline: "review findings are still open after two rounds.",
    failed: ["These findings of a blocking kind are not resolved:", "", ...titles].join("\n"),
    tries: fix ? [fix] : [],
  });
} else {
  dispatchWorkflow(github, "factory-tier.yml", { pr: String(pr) });
}
