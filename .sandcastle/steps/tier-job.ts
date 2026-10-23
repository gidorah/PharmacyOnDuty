// Plain step: decide a pull request's tier, label it, post the summary, and
// start the tier A merge step when the tier is A.
//
//   tsx steps/tier-job.ts --pr 123 --repo-root .. \
//     [--dependabot-updates updates.json --dependabot-ecosystem uv]
//
// Run it in a checkout of main with full history: the risk map and standing
// rules come from main, never from the pull request.

import { execFileSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import { parseArgs } from "node:util";
import { parse } from "yaml";
import { parse as parseToml } from "smol-toml";
import { type Clock, latestGateOnCommit, realClock } from "./gate.ts";
import {
  addLabels,
  BOT_LOGIN,
  comment,
  dispatchWorkflow,
  githubFromEnv,
  listComments,
  removeLabels,
  runUrl,
} from "./github.ts";
import { readMarkers, type ReviewMarker, sinceReset } from "./markers.ts";
import { fetchPullRequest } from "./pr-context.ts";
import {
  computeTier,
  type DependabotMetadata,
  parseNumstat,
  proposedTierFrom,
  type RiskMap,
  type StandingRule,
  type Tier,
} from "./tier.ts";
import { tierComment } from "./tier-report.ts";
import { fetchIssueSnapshot, issueForBranch } from "./work-order.ts";

const { values } = parseArgs({
  options: {
    pr: { type: "string" },
    "repo-root": { type: "string" },
    "dependabot-updates": { type: "string" },
    "dependabot-ecosystem": { type: "string" },
  },
});
const number = Number(values.pr);
const root = values["repo-root"];
if (!Number.isInteger(number) || !root) {
  throw new Error("Usage: tier-job.ts --pr <n> --repo-root <dir> [--dependabot-updates <file> --dependabot-ecosystem <name>]");
}

const git = (args: string[]): string =>
  execFileSync("git", args, { cwd: root, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
const show = (rev: string, file: string): string | null => {
  try {
    return git(["show", `${rev}:${file}`]);
  } catch {
    return null;
  }
};

const github = githubFromEnv();
const pr = fetchPullRequest(github, number);
if (pr.state !== "open" || pr.head.repo?.full_name !== github.repo) {
  console.log(`#${number} is closed or comes from another repository; no tier.`);
  process.exit(0);
}
removeLabels(github, number, ["tier:A", "tier:B", "tier:C"]);
addLabels(github, number, ["agent:in-progress"]);

// The gate result is evidence for the summary and a condition for the tier A
// merge. Dependabot's gate runs start with its own events, so wait for them.
const waitForGate = async (sha: string, clock: Clock = realClock) => {
  const deadline = clock.now() + 30 * 60 * 1000;
  const appearBy = clock.now() + 5 * 60 * 1000;
  for (;;) {
    const gate = latestGateOnCommit(github, sha);
    if (gate && !gate.pending) return gate;
    if ((!gate && clock.now() > appearBy) || clock.now() > deadline) return gate;
    await clock.sleep(20);
  }
};
const gate = await waitForGate(pr.head.sha);
const gateText =
  gate === null
    ? "has not run on this commit."
    : gate.pending
      ? `still running (${gate.run.html_url}).`
      : gate.green
        ? `green (${gate.url}).`
        : `**red** (${gate.url}); failed: ${gate.failedJobs.join(", ") || "none listed"}.`;

// The diff, from the merge base with main.
git(["fetch", "--no-tags", "origin", `+refs/pull/${number}/head:refs/factory/pr-head`, "+refs/heads/main:refs/remotes/origin/main"]);
const head = git(["rev-parse", "refs/factory/pr-head"]).trim();
if (head !== pr.head.sha) throw new Error(`Fetched ${head}, but the pull request's head is ${pr.head.sha}.`);
const base = git(["merge-base", "refs/remotes/origin/main", head]).trim();
const files = parseNumstat(git(["diff", "--numstat", "-z", "-M", base, head]));
const pyprojectDiff = git(["diff", "-U0", "--no-color", base, head, "--", "pyproject.toml"]).split("\n");
const basePyproject = show(base, "pyproject.toml");
const headPyproject = show(head, "pyproject.toml");
const baseLock = show(base, "uv.lock");
const headLock = show(head, "uv.lock");
const projectName = basePyproject
  ? String(((parseToml(basePyproject) as { project?: { name?: string } }).project?.name) ?? "")
  : "";

// Review findings since Onur's last restart.
const markers = readMarkers(listComments(github, number));
const reviews = sinceReset(markers).filter((m): m is ReviewMarker => m.kind === "review");
const findings = reviews.flatMap((r) => r.findings);
const lastReview = markers.findLast((m) => m.marker.kind === "review");
const reviewText =
  reviews.length === 0
    ? "no review ran."
    : `${reviews.length} round(s), ${findings.length} finding(s), blocking: ${reviews.at(-1)?.blocking.join(", ") || "none"} (${pr.html_url}#issuecomment-${lastReview?.commentId}).`;

// Check 5: the work order's proposed tier, for factory pull requests.
const issue = pr.user.login === BOT_LOGIN ? issueForBranch(pr.head.ref) : null;
const issueSnapshot = issue ? fetchIssueSnapshot(github, issue) : null;
const proposedTier: Tier | null = issueSnapshot ? proposedTierFrom(issueSnapshot.body) : null;

const readYaml = <T>(file: string): T => parse(fs.readFileSync(path.join(root, file), "utf8")) as T;
const riskMap = readYaml<RiskMap>("factory/risk-map.yml");
const rules = readYaml<{ rules: StandingRule[] }>("factory/standing-rules.yml").rules;

let dependabot: DependabotMetadata | null = null;
const updatesFile = values["dependabot-updates"];
if (updatesFile && fs.existsSync(updatesFile) && fs.readFileSync(updatesFile, "utf8").trim()) {
  const updates = JSON.parse(fs.readFileSync(updatesFile, "utf8")) as { dependencyName: string; updateType?: string | null }[];
  dependabot = {
    ecosystem: values["dependabot-ecosystem"] ?? "",
    updates: updates.map((u) => ({ dependencyName: u.dependencyName, updateType: u.updateType ?? null })),
  };
}

const result = computeTier({
  riskMap,
  rules,
  files,
  author: pr.user.login,
  dependabot,
  manifests: {
    pyproject: basePyproject !== null && headPyproject !== null ? { base: basePyproject, head: headPyproject } : null,
    lock: baseLock !== null && headLock !== null ? { base: baseLock, head: headLock } : null,
    pyprojectLines: {
      removed: pyprojectDiff.filter((l) => l.startsWith("-") && !l.startsWith("---")).map((l) => l.slice(1)),
      added: pyprojectDiff.filter((l) => l.startsWith("+") && !l.startsWith("+++")).map((l) => l.slice(1)),
    },
    projectName,
  },
  findings,
  proposedTier,
});

const commits = git(["log", "--reverse", "--format=%s", `${base}..${head}`]).trim().split("\n").filter(Boolean);
comment(
  github,
  number,
  tierComment(
    result,
    {
      sha: head,
      gate: gateText,
      review: reviewText,
      commits,
      files,
      workOrder: issueSnapshot ? `#${issueSnapshot.number} ${issueSnapshot.title}` : null,
    },
    runUrl(),
  ),
);
addLabels(github, number, [`tier:${result.tier}`]);
removeLabels(github, number, ["agent:in-progress"]);
if (pr.draft) {
  // The pipeline is done with it: Onur merges B and C, the merge step merges A.
  github.gh(["pr", "ready", String(number), "--repo", github.repo]);
}
console.log(`Tier ${result.tier}${result.rule ? ` (rule ${result.rule})` : ""} for ${head}.`);
for (const c of result.checks) console.log(`  ${c.check}: ${c.tier}. ${c.why.join(" ")}`);

if (result.tier === "A") {
  dispatchWorkflow(github, "factory-merge.yml", { pr: String(number), sha: head });
}
