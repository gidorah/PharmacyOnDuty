// Plain step before the review agent runs.
//
//   tsx steps/prepare-review.ts --pr 123 --out "$RUNNER_TEMP/handoff" \
//     --risk-map ../factory/risk-map.yml [--started-by-owner]

import { parseArgs } from "node:util";
import { loadHighRiskCategories } from "./findings.ts";
import { githubFromEnv, setOutputs } from "./github.ts";
import { reviewFixAfter, reviewRounds } from "./markers.ts";
import { fetchOwnerComments } from "./pr-context.ts";
import { startPrJob } from "./pr-job.ts";
import { type ReviewContext, writeHandoff } from "./handoff.ts";
import { MAX_REVIEW_ROUNDS } from "./route.ts";
import { markStuck } from "./stuck.ts";

const { values } = parseArgs({
  options: {
    pr: { type: "string" },
    out: { type: "string" },
    "risk-map": { type: "string" },
    "started-by-owner": { type: "boolean", default: false },
  },
});
const number = Number(values.pr);
if (!Number.isInteger(number) || !values.out || !values["risk-map"]) {
  throw new Error("Usage: prepare-review.ts --pr <n> --out <dir> --risk-map <file> [--started-by-owner]");
}

const github = githubFromEnv();
const job = startPrJob(github, {
  number,
  job: "review",
  label: "agent:review",
  startedByOwner: values["started-by-owner"] ?? false,
});

if (job) {
  const rounds = reviewRounds(job.current);
  const round = rounds.length + 1;
  if (round > MAX_REVIEW_ROUNDS) {
    markStuck(github, number, {
      headline: `the ${MAX_REVIEW_ROUNDS} review rounds are used up.`,
      failed: "Another review was requested after the last allowed round.",
      tries: [],
    });
    setOutputs({ proceed: false });
  } else {
    const first = rounds[0];
    const fix = first ? reviewFixAfter(job.current, first) : null;
    const context: ReviewContext = {
      round,
      headSha: job.pr.head.sha,
      headRef: job.pr.head.ref,
      highRisk: loadHighRiskCategories(values["risk-map"]),
      sinceSha: round > 1 && first ? first.sha : null,
      earlierFindings: round > 1 && first ? first.findings : [],
      earlierResponses: fix?.responses ?? [],
    };
    writeHandoff(values.out, {
      "work-order.md": job.workOrder,
      "comments.md": fetchOwnerComments(github, number),
      "context.json": context,
    });
    setOutputs({ proceed: true, round, head_sha: job.pr.head.sha });
    console.log(`Review round ${round} of #${number} at ${job.pr.head.sha}.`);
  }
}
