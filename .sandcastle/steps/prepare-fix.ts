// Plain step before the fix agent runs.
//
//   tsx steps/prepare-fix.ts --pr 123 --reason ci|review|onur \
//     --out "$RUNNER_TEMP/handoff" --risk-map ../factory/risk-map.yml [--started-by-owner]
//
// A fix starts for one of three reasons: the gate is red (`ci`), the review
// found something (`review`), or Onur added `agent:implement` to the pull
// request (`onur`, which also resets the try counts).

import { parseArgs } from "node:util";
import { loadHighRiskCategories } from "./findings.ts";
import { failedLogs, latestGateOnCommit } from "./gate.ts";
import { githubFromEnv, setOutputs } from "./github.ts";
import { ciFixTries, type FixReason, reviewFixAfter, reviewRounds } from "./markers.ts";
import { fetchOwnerComments } from "./pr-context.ts";
import { startPrJob } from "./pr-job.ts";
import { type FixContext, writeHandoff } from "./handoff.ts";
import { MAX_CI_FIX_TRIES } from "./route.ts";

const { values } = parseArgs({
  options: {
    pr: { type: "string" },
    reason: { type: "string" },
    out: { type: "string" },
    "risk-map": { type: "string" },
    "started-by-owner": { type: "boolean", default: false },
  },
});
const number = Number(values.pr);
const startedByOwner = values["started-by-owner"] ?? false;
const reason = (startedByOwner ? "onur" : values.reason) as FixReason;
if (!Number.isInteger(number) || !values.out || !values["risk-map"] || !["ci", "review", "onur"].includes(reason)) {
  throw new Error("Usage: prepare-fix.ts --pr <n> --reason ci|review --out <dir> --risk-map <file> [--started-by-owner]");
}

const github = githubFromEnv();
const job = startPrJob(github, { number, job: "fix", label: "agent:implement", startedByOwner });

const skip = (why: string) => {
  setOutputs({ proceed: false });
  console.log(`Not running: ${why}`);
};

if (job) {
  const highRisk = loadHighRiskCategories(values["risk-map"]);
  const base = { reason, headSha: job.pr.head.sha, headRef: job.pr.head.ref, highRisk };
  const files: Record<string, string | object> = {
    "work-order.md": job.workOrder,
    "comments.md": fetchOwnerComments(github, number),
  };
  let context: FixContext | null = null;

  if (reason === "ci") {
    const tries = ciFixTries(job.current).length;
    const gate = latestGateOnCommit(github, job.pr.head.sha);
    if (tries >= MAX_CI_FIX_TRIES) skip(`the ${MAX_CI_FIX_TRIES} CI fix tries are used up.`);
    else if (!gate || gate.pending || gate.green) skip("the gate on the head commit is not red.");
    else {
      files["ci-logs.txt"] = failedLogs(github, gate.runId);
      context = { ...base, attempt: tries + 1, findings: [], gate: { url: gate.url, failedJobs: gate.failedJobs } };
    }
  } else if (reason === "review") {
    const latest = reviewRounds(job.current).at(-1);
    if (!latest || latest.findings.length === 0) skip("there is no review with findings to fix.");
    else if (latest.round !== 1) skip("only round 1 findings go to a fix; round 2 ends in the tier job or agent:stuck.");
    else if (reviewFixAfter(job.current, latest)) skip("the round 1 findings were already answered.");
    else context = { ...base, attempt: 0, findings: latest.findings, gate: null };
  } else {
    context = { ...base, attempt: 0, findings: [], gate: null };
  }

  if (context) {
    writeHandoff(values.out, { ...files, "context.json": context });
    setOutputs({ proceed: true, reason, head_sha: job.pr.head.sha, head_ref: job.pr.head.ref });
    console.log(`Fix (${reason}${context.attempt ? ` try ${context.attempt}` : ""}) of #${number} at ${job.pr.head.sha}.`);
  }
}
