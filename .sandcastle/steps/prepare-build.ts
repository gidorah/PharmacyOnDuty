// Plain step before the build agent runs: check the work order, move the
// labels, and write the text the agent will read.
//
//   tsx steps/prepare-build.ts --issue 45 --out "$RUNNER_TEMP/handoff/work-order.md"

import * as fs from "node:fs";
import * as path from "node:path";
import { parseArgs } from "node:util";
import {
  addLabels,
  comment,
  githubFromEnv,
  removeLabels,
  runUrl,
  setOutputs,
} from "./github.ts";
import { APPROVAL_LABEL, branchForIssue, readWorkOrder } from "./work-order.ts";

const { values } = parseArgs({
  options: { issue: { type: "string" }, out: { type: "string" } },
});
const issueNumber = Number(values.issue);
if (!Number.isInteger(issueNumber) || !values.out) {
  throw new Error("Usage: prepare-build.ts --issue <number> --out <file>");
}

const github = githubFromEnv();

const refuse = (reason: string): void => {
  removeLabels(github, issueNumber, [APPROVAL_LABEL]);
  addLabels(github, issueNumber, ["agent:blocked"]);
  comment(
    github,
    issueNumber,
    [`**Build refused.**`, "", reason, "", `Pipeline run: ${runUrl()}`].join("\n"),
  );
  setOutputs({ proceed: false });
  console.log(`Refused: ${reason}`);
};

const workOrder = readWorkOrder(github, issueNumber);
const branch = branchForIssue(issueNumber);
if (!workOrder.ok) {
  refuse(workOrder.reason);
} else if (workOrder.issue.state !== "OPEN") {
  refuse(`#${issueNumber} is closed.`);
} else {
  const open = github.api<{ html_url: string }[]>(
    `repos/${github.repo}/pulls?state=open&head=${github.repo.split("/")[0]}:${branch}`,
  );
  if (open.length > 0) {
    refuse(
      `${open[0]?.html_url} already builds this work order. Close it first, or add \`${APPROVAL_LABEL}\` to that pull request to start a fix run.`,
    );
  } else {
    removeLabels(github, issueNumber, [APPROVAL_LABEL, "agent:blocked", "agent:stuck"]);
    addLabels(github, issueNumber, ["agent:in-progress"]);
    fs.mkdirSync(path.dirname(values.out), { recursive: true });
    fs.writeFileSync(values.out, workOrder.text);
    setOutputs({ proceed: true, branch, title: workOrder.issue.title.replace(/[\r\n]+/g, " ") });
    console.log(`Work order #${issueNumber} approved and unchanged since; building on ${branch}.`);
  }
}
