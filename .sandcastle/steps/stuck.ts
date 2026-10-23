// The `agent:stuck` comment: what failed, what the worker tried, and its best
// guess at the cause (decision 9, sub-decision 4, point 4). Plain code.

import { addLabels, comment, type GitHub, removeLabels, runUrl } from "./github.ts";
import { type FixMarker, markerLine } from "./markers.ts";
import { sanitizeAgentText } from "./sanitize.ts";

export interface StuckReport {
  readonly headline: string;
  /** Markdown: the failure itself. */
  readonly failed: string;
  readonly tries: readonly FixMarker[];
}

const short = (sha: string) => sha.slice(0, 7);

export const stuckComment = (report: StuckReport, run = runUrl()): string => {
  const tried =
    report.tries.length === 0
      ? ["No fix try ran for this failure."]
      : report.tries.map((t, i) => {
          const commits = t.before === t.after ? "no new commits" : `${short(t.before)}..${short(t.after)}`;
          return `${i + 1}. ${t.reason === "ci" ? `CI fix try ${t.attempt}` : `Fix for the ${t.reason === "review" ? "review findings" : "comments"}`} (${commits}): ${sanitizeAgentText(t.summary)}`;
        });
  const guess = report.tries.findLast((t) => t.cause.trim() !== "")?.cause;
  return [
    markerLine({ kind: "stuck", why: report.headline }),
    `**Stuck: ${report.headline}**`,
    "",
    "**What failed**",
    "",
    report.failed,
    "",
    "**What the worker tried**",
    "",
    ...tried,
    "",
    "**The worker's best guess at the cause**",
    "",
    guess ? sanitizeAgentText(guess) : "The worker gave no guess.",
    "",
    `Pipeline run: ${run}`,
    "",
    "To unblock it, edit the work order or comment, then add `agent:implement` (fix) or `agent:review` (review) to this pull request. Adding the label resets the try counts.",
  ].join("\n");
};

export const markStuck = (github: GitHub, pr: number, report: StuckReport): void => {
  removeLabels(github, pr, ["agent:in-progress", "agent:review"]);
  addLabels(github, pr, ["agent:stuck"]);
  comment(github, pr, stuckComment(report));
};
