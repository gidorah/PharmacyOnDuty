// Plain step: open the draft pull request for a pushed build branch, or find
// the one a previous attempt of this run opened.
//
//   tsx steps/open-pr.ts --issue 45 --branch factory/issue-45 \
//     --base-sha <main commit> --head-sha <pushed commit> [--instructions-file <file>]
//
// Run it inside a checkout that has both commits, for the commit list.

import { execFileSync } from "node:child_process";
import * as fs from "node:fs";
import { parseArgs } from "node:util";
import { addLabels, githubFromEnv, runUrl, setOutputs } from "./github.ts";
import { sanitizeAgentText } from "./sanitize.ts";
import { fetchIssueSnapshot } from "./work-order.ts";

const { values } = parseArgs({
  options: {
    issue: { type: "string" },
    branch: { type: "string" },
    "base-sha": { type: "string" },
    "head-sha": { type: "string" },
    "instructions-file": { type: "string" },
  },
});
const issue = Number(values.issue);
const branch = values.branch;
const baseSha = values["base-sha"];
const headSha = values["head-sha"];
if (!Number.isInteger(issue) || !branch || !baseSha || !headSha) {
  throw new Error("Usage: open-pr.ts --issue <n> --branch <b> --base-sha <c> --head-sha <c>");
}

const github = githubFromEnv();
const [owner] = github.repo.split("/");

const subjects = execFileSync("git", ["log", "--reverse", "--format=%s", `${baseSha}..${headSha}`], {
  encoding: "utf8",
})
  .trim()
  .split("\n")
  .filter(Boolean);

const instructionsFile = values["instructions-file"];
const instructions =
  instructionsFile && fs.existsSync(instructionsFile)
    ? fs.readFileSync(instructionsFile, "utf8").trim()
    : "(not recorded)";

const title = fetchIssueSnapshot(github, issue)?.title ?? `Work order #${issue}`;
const body = [
  `Closes #${issue}`,
  "",
  `Built by the factory pipeline from work order #${issue}. The pull request stays a draft while the pipeline works on it.`,
  "",
  "**Commits from the build agent**",
  "",
  ...subjects.map((s) => `- ${sanitizeAgentText(s)}`),
  "",
  `Build run: ${runUrl()}`,
  "",
  "<details><summary>Instruction files the agent loaded (S0-5a)</summary>",
  "",
  "```text",
  sanitizeAgentText(instructions).replaceAll("```", "'''"),
  "```",
  "",
  "</details>",
].join("\n");

const existing = github.api<{ number: number; html_url: string }[]>(
  `repos/${github.repo}/pulls?state=open&head=${owner}:${branch}`,
);
let pr = existing[0];
if (!pr) {
  pr = github.api<{ number: number; html_url: string }>(`repos/${github.repo}/pulls`, {
    method: "POST",
    body: { title: `Work order #${issue}: ${title}`.slice(0, 256), head: branch, base: "main", body, draft: true },
  });
}
addLabels(github, pr.number, ["agent:in-progress"]);
setOutputs({ pr: pr.number });
console.log(`Pull request: ${pr.html_url}`);
