// What happens to a pull request after the gate finished: plain code.
//
// Green goes to the review job. Red (after the one rerun) goes to the fix job
// while fix tries are left, and to `agent:stuck` when they run out
// (decision 9, sub-decision 4).

import type { GateOutcome } from "./gate.ts";

/** Fix tries per CI failure. */
export const MAX_CI_FIX_TRIES = 2;

/** Review rounds per pull request. The second checks only the fixes. */
export const MAX_REVIEW_ROUNDS = 2;

/** The gate job that fails a change which removes or skips tests. */
export const TEST_REMOVAL_JOB = "Test-removal check";

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
  const failed = outcome.final.failedJobs;
  if (failed.length === 1 && failed[0] === TEST_REMOVAL_JOB) {
    // Only Onur can approve removing a test (S0-4). A fix try would restore
    // a test he may want gone, so wait for him instead.
    return {
      action: "stuck",
      why: `Only the test-removal check failed: the change removes or skips tests. If that is intended, add \`allow-test-removal\`; if not, say so in a comment and add \`agent:implement\` to start a fix.`,
    };
  }
  if (ciFixTriesUsed < maxCiFixTries) {
    return { action: "fix", attempt: ciFixTriesUsed + 1 };
  }
  return {
    action: "stuck",
    why: `The gate is still red after ${ciFixTriesUsed} fix tries, the limit for one CI failure.`,
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
