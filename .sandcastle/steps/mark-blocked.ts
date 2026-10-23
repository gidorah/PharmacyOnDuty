// Plain step for `if: failure()`: label the item `agent:blocked` and say why.
//
//   tsx steps/mark-blocked.ts --number 45 --job build --retry-label agent:implement \
//     [--reason-file "$RUNNER_TEMP/agent-out/failure_reason.txt"]
//
// `agent:blocked` means the job itself failed or refused (a runner, network or
// precondition problem), not that the work ran out of tries; that is
// `agent:stuck`.

import * as fs from "node:fs";
import { parseArgs } from "node:util";
import { addLabels, comment, githubFromEnv, removeLabels, runUrl } from "./github.ts";
import { sanitizeAgentText } from "./sanitize.ts";

const { values } = parseArgs({
  options: {
    number: { type: "string" },
    job: { type: "string" },
    "retry-label": { type: "string" },
    "reason-file": { type: "string" },
  },
});
const number = Number(values.number);
if (!Number.isInteger(number) || !values.job || !values["retry-label"]) {
  throw new Error("Usage: mark-blocked.ts --number <n> --job <name> --retry-label <label>");
}

const reasonFile = values["reason-file"];
let reason = "No reason was recorded. The workflow run's log has the details.";
if (reasonFile && fs.existsSync(reasonFile)) {
  // The agent job writes this file, so treat it as agent text.
  reason = sanitizeAgentText(fs.readFileSync(reasonFile, "utf8").trim().slice(0, 4000));
}

const github = githubFromEnv();
removeLabels(github, number, ["agent:in-progress"]);
addLabels(github, number, ["agent:blocked"]);
comment(
  github,
  number,
  [
    `**The ${values.job} job failed to run.**`,
    "",
    `Reason: ${reason}`,
    "",
    `Pipeline run: ${runUrl()}`,
    "",
    `Add \`${values["retry-label"]}\` again to retry.`,
  ].join("\n"),
);
