// What happens to a pull request after the gate finished: plain code.
//
// Green goes to the review job. Red (after the one rerun) goes to the fix job
// while fix tries are left, and to `agent:stuck` when they run out
// (decision 9, sub-decision 4).

import type { GateOutcome } from "./gate.ts";

// The fix job is added in the next pull request of the pipeline; until then a
// red gate goes straight to `agent:stuck`.
export const MAX_CI_FIX_TRIES = 0;

export type NextStep =
  | { readonly action: "review" }
  | { readonly action: "fix"; readonly attempt: number }
  | { readonly action: "stuck"; readonly why: string };

export const decideAfterGate = (
  outcome: GateOutcome,
  ciFixTriesUsed: number,
  maxCiFixTries = MAX_CI_FIX_TRIES,
): NextStep => {
  if (outcome.final.green) return { action: "review" };
  if (ciFixTriesUsed < maxCiFixTries) {
    return { action: "fix", attempt: ciFixTriesUsed + 1 };
  }
  return {
    action: "stuck",
    why:
      maxCiFixTries === 0
        ? "The gate is red after one rerun, and the pipeline has no fix job yet."
        : `The gate is still red after ${ciFixTriesUsed} fix tries, the limit for one CI failure.`,
  };
};

export const describeGate = (outcome: GateOutcome): string => {
  const lines = [
    `- Gate run: ${outcome.first.url} (attempt ${outcome.first.attempt}: \`${outcome.first.conclusion}\`)`,
  ];
  if (outcome.rerun) {
    lines.push(
      `- Rerun of the failed jobs: attempt ${outcome.final.attempt}: \`${outcome.final.conclusion}\``,
    );
  }
  const failed = outcome.final.failedJobs;
  lines.push(`- Failed jobs: ${failed.length > 0 ? failed.join(", ") : "none listed"}`);
  return lines.join("\n");
};
