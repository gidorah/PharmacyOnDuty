// Plain step: start the gate on a pull request's branch, wait for it, and hand
// the pull request to the next station.
//
//   tsx steps/gate-route.ts --pr 123 --branch factory/issue-45 --sha <head>

import { parseArgs } from "node:util";
import { Gate } from "./gate.ts";
import {
  addLabels,
  comment,
  dispatchWorkflow,
  githubFromEnv,
  removeLabels,
  runUrl,
  setOutputs,
} from "./github.ts";
import { decideAfterGate, describeGate } from "./route.ts";

const { values } = parseArgs({
  options: {
    pr: { type: "string" },
    branch: { type: "string" },
    sha: { type: "string" },
  },
});
const pr = Number(values.pr);
const branch = values.branch;
const sha = values.sha;
if (!Number.isInteger(pr) || !branch || !sha) {
  throw new Error("Usage: gate-route.ts --pr <number> --branch <name> --sha <commit>");
}

const github = githubFromEnv();
const outcome = await new Gate(github).check(branch, sha);
console.log(describeGate(outcome));

const next = decideAfterGate(outcome, 0);
setOutputs({ next: next.action, gate: outcome.final.green ? "green" : "red" });

switch (next.action) {
  case "review":
    removeLabels(github, pr, ["agent:in-progress"]);
    addLabels(github, pr, ["agent:review"]);
    // A label added with the built-in token starts no workflow (S0-7), so the
    // label only records the state and the dispatch starts the job.
    dispatchWorkflow(github, "factory-review.yml", { pr: String(pr) });
    console.log(`Gate green on ${sha}; review requested.`);
    break;
  case "fix":
    throw new Error("The fix job is not part of this pipeline version.");
  case "stuck":
    removeLabels(github, pr, ["agent:in-progress", "agent:review"]);
    addLabels(github, pr, ["agent:stuck"]);
    comment(
      github,
      pr,
      [
        "**Stuck: the gate is red.**",
        "",
        next.why,
        "",
        describeGate(outcome),
        `- Pipeline run: ${runUrl()}`,
        "",
        "To unblock it, push a fix or change the work order, then add the label again.",
      ].join("\n"),
    );
    console.log("Gate red; marked stuck.");
    break;
}
