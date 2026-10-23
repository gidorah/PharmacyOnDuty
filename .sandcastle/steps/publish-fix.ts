// Plain step after the fix agent and the push: record the try and post the
// fixer's answers, including a reason for every finding it declined.
//
//   tsx steps/publish-fix.ts --pr 123 --handoff "$RUNNER_TEMP/handoff" \
//     --output "$RUNNER_TEMP/agent-out/fix.json" --before <sha> --after <sha>
//
// The workflow runs gate-route.ts next, with the new head.

import { parseArgs } from "node:util";
import { parseFixOutput, reconcileResponses } from "./findings.ts";
import { comment, githubFromEnv, removeLabels, runUrl } from "./github.ts";
import { type FixContext, readJson } from "./handoff.ts";
import { markerLine } from "./markers.ts";
import { answer, cell } from "./render.ts";
import { sanitizeAgentText } from "./sanitize.ts";

const { values } = parseArgs({
  options: {
    pr: { type: "string" },
    handoff: { type: "string" },
    output: { type: "string" },
    before: { type: "string" },
    after: { type: "string" },
  },
});
const pr = Number(values.pr);
const { before, after } = values;
if (!Number.isInteger(pr) || !values.handoff || !values.output || !before || !after) {
  throw new Error("Usage: publish-fix.ts --pr <n> --handoff <dir> --output <fix.json> --before <sha> --after <sha>");
}

const context = readJson<FixContext>(`${values.handoff}/context.json`);
const output = parseFixOutput(readJson<unknown>(values.output));
const responses = context.reason === "review" ? reconcileResponses(context.findings, output, context.highRisk) : [];
const summary = sanitizeAgentText(output.summary);
const cause = sanitizeAgentText(output.cause);

const title = {
  ci: `**CI fix try ${context.attempt} of 2**`,
  review: "**Fix for the round 1 review findings**",
  onur: "**Fix for Onur's comments**",
}[context.reason];

const lines = [
  markerLine({ kind: "fix", reason: context.reason, attempt: context.attempt, before, after, summary, cause, responses }),
  `${title} (${before === after ? "no new commits" : `${before.slice(0, 7)}..${after.slice(0, 7)}`})`,
  "",
  summary,
];
if (cause) lines.push("", `Likely cause: ${cause}`);
if (responses.length > 0) {
  lines.push("", "| Id | Finding | Answer | Reason |", "|---|---|---|---|");
  for (const r of responses) {
    const f = context.findings.find((x) => x.id === r.id);
    lines.push(`| ${r.id} | ${cell(f?.title ?? "")} | ${answer(r)} | ${cell(r.reason) || "–"} |`);
  }
}
lines.push("", `Fix run: ${runUrl()}`, "", "Next: the gate runs on the new head.");

const github = githubFromEnv();
comment(github, pr, lines.join("\n"));
if (before !== after) {
  // New commits make earlier approvals and tiers stale. Pushes with the built-in
  // token start no workflow, so factory-label-reset.yml does not do this here.
  removeLabels(github, pr, ["allow-test-removal", "tier:A", "tier:B", "tier:C"]);
}
