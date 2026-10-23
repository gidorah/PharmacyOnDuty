// Plain step: start the gate on a pull request's branch, wait for it, and hand
// the pull request to the next station.
//
//   tsx steps/gate-route.ts --pr 123 --branch factory/issue-45 --sha <head>

import { parseArgs } from "node:util";
import { Gate } from "./gate.ts";
import {
  addLabels,
  dispatchWorkflow,
  githubFromEnv,
  listComments,
  removeLabels,
  setOutputs,
} from "./github.ts";
import { ciFixTries, readMarkers, sinceReset } from "./markers.ts";
import { decideAfterGate, describeGate } from "./route.ts";
import { markStuck } from "./stuck.ts";

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

const tries = ciFixTries(sinceReset(readMarkers(listComments(github, pr))));
const next = decideAfterGate(outcome, tries.length);
setOutputs({ next: next.action, gate: outcome.final.green ? "green" : "red" });

// Labels added with the built-in token start no workflow (S0-7), so labels
// only record the state and each dispatch starts the next job.
switch (next.action) {
  case "review":
    removeLabels(github, pr, ["agent:in-progress"]);
    addLabels(github, pr, ["agent:review"]);
    dispatchWorkflow(github, "factory-review.yml", { pr: String(pr) });
    console.log(`Gate green on ${sha}; review requested.`);
    break;
  case "fix":
    removeLabels(github, pr, ["agent:in-progress"]);
    dispatchWorkflow(github, "factory-fix.yml", { pr: String(pr), reason: "ci" });
    console.log(`Gate red on ${sha}; CI fix try ${next.attempt} requested.`);
    break;
  case "stuck":
    markStuck(github, pr, {
      headline: "the gate is red.",
      failed: `${next.why}\n\n${describeGate(outcome)}`,
      tries,
    });
    console.log("Gate red; marked stuck.");
    break;
}
