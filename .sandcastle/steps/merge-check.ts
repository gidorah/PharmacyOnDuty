// Whether the tier A merge step may merge (decision 9, sub-decision 5,
// point 2). Plain code. Every condition is read again from GitHub when the
// merge step runs, not taken from the tier job's inputs.

import type { DatedMarker, ReviewMarker, TierMarker } from "./markers.ts";
import { sinceReset } from "./markers.ts";

export interface MergeState {
  readonly open: boolean;
  readonly sameRepo: boolean;
  readonly headSha: string;
  /** The commit the dispatch asked to merge. */
  readonly requestedSha: string;
  readonly labels: readonly string[];
  readonly markers: readonly DatedMarker[];
  readonly gate: { readonly pending: boolean; readonly green: boolean; readonly url: string } | null;
}

export type MergeDecision = { readonly ok: true } | { readonly ok: false; readonly reasons: readonly string[] };

const STOP_LABELS = ["agent:stuck", "agent:blocked", "agent:in-progress", "tier:B", "tier:C"];

export const checkMerge = (s: MergeState): MergeDecision => {
  const reasons: string[] = [];
  if (!s.open) reasons.push("the pull request is not open");
  if (!s.sameRepo) reasons.push("the pull request comes from another repository");
  if (!s.labels.includes("tier:A")) reasons.push("it is not labeled `tier:A`");
  const stops = STOP_LABELS.filter((l) => s.labels.includes(l));
  if (stops.length > 0) reasons.push(`it is labeled ${stops.map((l) => `\`${l}\``).join(", ")}`);
  if (s.headSha !== s.requestedSha) reasons.push(`the head moved from ${s.requestedSha.slice(0, 7)} to ${s.headSha.slice(0, 7)}`);

  const tier = s.markers.map((m) => m.marker).findLast((m): m is TierMarker => m.kind === "tier");
  if (!tier) reasons.push("the tier job has not checked it");
  else if (tier.tier !== "A") reasons.push(`the tier job's latest result is tier ${tier.tier}`);
  else if (tier.sha !== s.headSha) reasons.push(`the tier job checked ${tier.sha.slice(0, 7)}, not the head ${s.headSha.slice(0, 7)}`);

  if (!s.gate) reasons.push("the gate has not run on the head commit");
  else if (s.gate.pending) reasons.push("the gate is still running on the head commit");
  else if (!s.gate.green) reasons.push(`the gate is red on the head commit (${s.gate.url})`);

  const review = sinceReset(s.markers).findLast((m): m is ReviewMarker => m.kind === "review");
  if (review && review.blocking.length > 0) {
    reasons.push(`blocking findings are open: ${review.blocking.join(", ")}`);
  }
  return reasons.length === 0 ? { ok: true } : { ok: false, reasons };
};

/** Squash: one commit per change on main, easy to revert, as Dependabot merges were. */
export const MERGE_METHOD = "squash";
