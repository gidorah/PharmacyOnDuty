// Plain step: the tier A merge. It merges only when the pull request is
// labeled `tier:A`, the gate is green on the head commit, no blocking finding
// is open, and the head is the commit the tier job checked.
//
//   tsx steps/merge-job.ts --pr 123 --sha <commit the tier job checked>
//
// The merge itself passes the commit to GitHub, which refuses it if the head
// moved in between.

import { parseArgs } from "node:util";
import { type Clock, latestGateOnCommit, realClock } from "./gate.ts";
import { addLabels, comment, githubFromEnv, listComments, runUrl } from "./github.ts";
import { readMarkers } from "./markers.ts";
import { checkMerge, MERGE_METHOD } from "./merge-check.ts";
import { fetchPullRequest } from "./pr-context.ts";

const { values } = parseArgs({ options: { pr: { type: "string" }, sha: { type: "string" } } });
const number = Number(values.pr);
const sha = values.sha;
if (!Number.isInteger(number) || !sha) throw new Error("Usage: merge-job.ts --pr <n> --sha <commit>");

const github = githubFromEnv();

const waitForGate = async (head: string, clock: Clock = realClock) => {
  const deadline = clock.now() + 20 * 60 * 1000;
  for (;;) {
    const gate = latestGateOnCommit(github, head);
    if (!gate?.pending || clock.now() > deadline) return gate;
    await clock.sleep(20);
  }
};

const pr = fetchPullRequest(github, number);
const gate = await waitForGate(pr.head.sha);
const decision = checkMerge({
  open: pr.state === "open",
  sameRepo: pr.head.repo?.full_name === github.repo,
  headSha: pr.head.sha,
  requestedSha: sha,
  labels: pr.labels.map((l) => l.name),
  markers: readMarkers(listComments(github, number)),
  gate: gate === null ? null : gate.pending ? { pending: true, green: false, url: gate.run.html_url } : { pending: false, green: gate.green, url: gate.url },
});

if (!decision.ok) {
  addLabels(github, number, ["agent:blocked"]);
  comment(
    github,
    number,
    [
      "**The tier A merge step did not merge this pull request.**",
      "",
      ...decision.reasons.map((r) => `- ${r[0]?.toUpperCase()}${r.slice(1)}.`),
      "",
      `Merge run: ${runUrl()}`,
      "",
      "Onur can merge it himself, or fix the cause and start the tier job again.",
    ].join("\n"),
  );
  console.log(`Not merged: ${decision.reasons.join("; ")}`);
} else {
  if (pr.draft) github.gh(["pr", "ready", String(number), "--repo", github.repo]);
  github.api(`repos/${github.repo}/pulls/${number}/merge`, {
    method: "PUT",
    body: { sha, merge_method: MERGE_METHOD },
  });
  console.log(`Merged #${number} at ${sha} (${MERGE_METHOD}).`);
}
