// The tier job's comment. For tier B and C it is the summary Onur reads:
// what changed, the evidence from the checks, and why the change got its
// tier (decision 9, sub-decision 5, point 4). Plain code.

import { markerLine } from "./markers.ts";
import { sanitizeAgentText } from "./sanitize.ts";
import type { ChangedFile, TierResult } from "./tier.ts";

export interface TierEvidence {
  readonly sha: string;
  readonly gate: string;
  readonly review: string;
  readonly commits: readonly string[];
  readonly files: readonly ChangedFile[];
  readonly workOrder: string | null;
}

const WHAT_ONUR_DOES = {
  A: "**Tier A.** A standing rule matched. The merge step merges it when the gate is green and no blocking finding is open.",
  B: "**Tier B: read this summary, then press Merge** (or close the pull request).",
  C: "**Tier C: review the full diff, then press Merge** (or close the pull request).",
} as const;

export const tierComment = (result: TierResult, evidence: TierEvidence, run: string): string => {
  const lines = [
    markerLine({ kind: "tier", tier: result.tier, sha: evidence.sha, rule: result.rule }),
    WHAT_ONUR_DOES[result.tier],
    "",
    `Checked commit ${evidence.sha.slice(0, 7)}. New commits make this tier stale; the tier job runs again after them.`,
    "",
    "**Why this tier**",
    "",
    ...result.checks.map((c) => `- ${c.check}: **${c.tier}**. ${c.why.join(" ")}`),
    `- Result: the highest of these, **${result.tier}**.`,
  ];
  if (result.tier !== "A") {
    lines.push(
      "",
      "**What changed**",
      "",
      ...(evidence.workOrder ? [`Work order: ${evidence.workOrder}`, ""] : []),
      ...evidence.commits.map((s) => `- ${sanitizeAgentText(s)}`),
      "",
      `${evidence.files.length} file(s), ${result.changedLines} changed line(s):`,
      "",
      ...evidence.files.slice(0, 40).map((f) => `- \`${f.oldPath && f.oldPath !== f.path ? `${f.oldPath} → ` : ""}${f.path}\` +${f.added} −${f.deleted}`),
      ...(evidence.files.length > 40 ? [`- … and ${evidence.files.length - 40} more`] : []),
      "",
      "**Evidence from the checks**",
      "",
      `- Gate: ${evidence.gate}`,
      `- Review: ${evidence.review}`,
    );
  }
  lines.push("", `Tier run: ${run}`);
  return lines.join("\n");
};
