// Hidden markers in the pipeline's own comments, and the try counters built
// on them (decision 9, sub-decision 4, point 5).
//
// Each job that counts toward a limit posts a comment that starts with
//
//   <!-- factory:<kind> {json} -->
//
// The counters read only comments by the built-in token's account, and only a
// marker at the very start of a comment. Plain code writes that start; agent
// text inside a comment is passed through sanitizeAgentText, which breaks
// every `<!--`. So the counts come from GitHub's own record and survive
// restarts and reruns.

import { BOT_LOGIN, type IssueComment } from "./github.ts";
import type { Finding, FixResponse, PreviousStatus } from "./findings.ts";

export type FixReason = "ci" | "review" | "onur";

export interface ResetMarker {
  readonly kind: "reset";
  /** The label Onur added. */
  readonly label: string;
}

export interface ReviewMarker {
  readonly kind: "review";
  readonly round: number;
  /** The commit the reviewer read. */
  readonly sha: string;
  readonly findings: readonly Finding[];
  readonly previous: readonly PreviousStatus[];
  /** Findings that stop the pull request, as plain code counted them. */
  readonly blocking: readonly string[];
}

export interface FixMarker {
  readonly kind: "fix";
  readonly reason: FixReason;
  /** For CI fixes: the try number within this CI failure. */
  readonly attempt: number;
  readonly before: string;
  readonly after: string;
  readonly summary: string;
  readonly cause: string;
  readonly responses: readonly FixResponse[];
}

export interface StuckMarker {
  readonly kind: "stuck";
  readonly why: string;
}

export interface TierMarker {
  readonly kind: "tier";
  readonly tier: "A" | "B" | "C";
  readonly sha: string;
  readonly rule: string | null;
}

export type Marker = ResetMarker | ReviewMarker | FixMarker | StuckMarker | TierMarker;

export interface DatedMarker {
  readonly marker: Marker;
  readonly createdAt: string;
  readonly commentId: number;
}

// JSON with every character that could end an HTML comment, start a code
// span or form an entity written as a \u escape. JSON.parse reads it back.
const encode = (value: unknown): string =>
  JSON.stringify(value).replace(
    /[<>&`]/g,
    (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`,
  );

export const markerLine = (marker: Marker): string => {
  const { kind, ...data } = marker;
  return `<!-- factory:${kind} ${encode(data)} -->`;
};

const MARKER = /^<!-- factory:([a-z]+) (\{.*?\}) -->/;

export const parseMarker = (body: string): Marker | null => {
  const match = MARKER.exec(body);
  if (!match) return null;
  try {
    const data = JSON.parse(match[2] ?? "") as Record<string, unknown>;
    return { ...data, kind: match[1] } as Marker;
  } catch {
    return null;
  }
};

/** Markers from the pipeline's own comments, oldest first. */
export const readMarkers = (comments: readonly IssueComment[]): DatedMarker[] =>
  comments
    .filter((c) => c.user?.login === BOT_LOGIN && c.user.type === "Bot")
    .flatMap((c) => {
      const marker = parseMarker(c.body);
      return marker ? [{ marker, createdAt: c.created_at, commentId: c.id }] : [];
    })
    .sort((a, b) => a.commentId - b.commentId);

/** Markers since Onur last restarted the item by adding a label himself. */
export const sinceReset = (markers: readonly DatedMarker[]): Marker[] => {
  const last = markers.findLastIndex((m) => m.marker.kind === "reset");
  return markers.slice(last + 1).map((m) => m.marker);
};

export const reviewRounds = (markers: readonly Marker[]): ReviewMarker[] =>
  markers.filter((m): m is ReviewMarker => m.kind === "review");

/**
 * CI fix tries for the current CI failure: the CI fixes since the last
 * review or non-CI fix. A green gate always leads to a review, so this counts
 * the tries since the gate was last green.
 */
export const ciFixTries = (markers: readonly Marker[]): FixMarker[] => {
  const tries: FixMarker[] = [];
  for (const m of markers) {
    if (m.kind === "fix" && m.reason === "ci") tries.push(m);
    else if (m.kind === "review" || m.kind === "fix") tries.length = 0;
  }
  return tries;
};

/** The review-fix that answered the latest review, if there was one. */
export const reviewFixAfter = (
  markers: readonly Marker[],
  review: ReviewMarker,
): FixMarker | null => {
  const start = markers.indexOf(review);
  const later = markers.slice(start + 1);
  return later.find((m): m is FixMarker => m.kind === "fix" && m.reason === "review") ?? null;
};
