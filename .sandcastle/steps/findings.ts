// Review findings: their shape, which ones block a pull request, and the
// rules for declining them (decision 9, sub-decision 2). Plain code.
//
// The reviewer (Opus) only reports. Plain code checks its output against
// this shape again in the publish job, assigns the ids, and decides what
// blocks. The fixer (Sonnet) may decline a finding with a reason, except:
//   - a finding in a high-risk category from factory/risk-map.yml
//     (`reviewer_findings`), which also raises the tier to C;
//   - unrequested work (`requested: false`), which must be removed.

import * as fs from "node:fs";
import { parse } from "yaml";

export const SEVERITIES = ["blocker", "major", "minor", "nit"] as const;
export type Severity = (typeof SEVERITIES)[number];

// The high-risk categories come from the risk map; these are the others.
export const OTHER_CATEGORIES = [
  "correctness",
  "tests",
  "scope",
  "standards",
  "performance",
  "maintainability",
  "docs",
] as const;

export interface Finding {
  readonly id: string;
  readonly category: string;
  readonly severity: Severity;
  /** Whether the work order asked for the change this finding is about. */
  readonly requested: boolean;
  readonly path: string | null;
  readonly line: number | null;
  readonly title: string;
  readonly detail: string;
}

export const PREVIOUS_STATUSES = ["fixed", "declined_accepted", "declined_rejected", "not_fixed"] as const;
export type PreviousStatusValue = (typeof PREVIOUS_STATUSES)[number];

/** Round 2: the reviewer's verdict on a round 1 finding. */
export interface PreviousStatus {
  readonly id: string;
  readonly status: PreviousStatusValue;
  readonly note: string;
}

export const FIX_ACTIONS = ["fixed", "removed", "declined"] as const;
export type FixAction = (typeof FIX_ACTIONS)[number];

export interface FixResponse {
  readonly id: string;
  readonly action: FixAction | "none";
  readonly reason: string;
  /** Set by plain code when the fixer declined a finding it may not decline. */
  readonly declineRefused?: boolean;
}

export interface ReviewOutput {
  readonly summary: string;
  readonly findings: readonly Omit<Finding, "id">[];
  readonly previous: readonly PreviousStatus[];
}

export interface FixOutput {
  readonly summary: string;
  readonly cause: string;
  readonly responses: readonly { id: string; action: FixAction; reason: string }[];
}

export const loadHighRiskCategories = (riskMapPath: string): string[] => {
  const map = parse(fs.readFileSync(riskMapPath, "utf8")) as {
    reviewer_findings?: { categories?: unknown };
  };
  const categories = map.reviewer_findings?.categories;
  if (!Array.isArray(categories) || !categories.every((c) => typeof c === "string")) {
    throw new Error(`${riskMapPath} has no reviewer_findings.categories list`);
  }
  return categories;
};

// --- Validation of agent output -------------------------------------------

const obj = (v: unknown, label: string): Record<string, unknown> => {
  if (typeof v !== "object" || v === null || Array.isArray(v)) throw new Error(`${label} must be an object`);
  return v as Record<string, unknown>;
};
const str = (v: unknown, label: string, max: number, allowEmpty = false): string => {
  if (typeof v !== "string" || (!allowEmpty && v.trim() === "")) throw new Error(`${label} must be a non-empty string`);
  return v.slice(0, max);
};
const arr = (v: unknown, label: string): unknown[] => {
  if (v === undefined) return [];
  if (!Array.isArray(v)) throw new Error(`${label} must be an array`);
  return v;
};
const oneOf = <T extends string>(v: unknown, allowed: readonly T[], label: string): T => {
  if (typeof v !== "string" || !allowed.includes(v as T)) {
    throw new Error(`${label} must be one of: ${allowed.join(", ")}`);
  }
  return v as T;
};

export const parseReviewOutput = (value: unknown, categories: readonly string[]): ReviewOutput => {
  const record = obj(value, "review output");
  const allCategories = [...categories, ...OTHER_CATEGORIES];
  return {
    summary: str(record.summary, "summary", 6000),
    findings: arr(record.findings, "findings").slice(0, 30).map((f, i) => {
      const r = obj(f, `findings[${i}]`);
      if (typeof r.requested !== "boolean") throw new Error(`findings[${i}].requested must be true or false`);
      const line = r.line;
      return {
        category: oneOf(r.category, allCategories, `findings[${i}].category`),
        severity: oneOf(r.severity, SEVERITIES, `findings[${i}].severity`),
        requested: r.requested,
        path: typeof r.path === "string" && r.path.trim() ? r.path.slice(0, 300) : null,
        line: typeof line === "number" && Number.isInteger(line) && line > 0 ? line : null,
        title: str(r.title, `findings[${i}].title`, 200),
        detail: str(r.detail, `findings[${i}].detail`, 4000),
      };
    }),
    previous: arr(record.previous, "previous").map((p, i) => {
      const r = obj(p, `previous[${i}]`);
      return {
        id: str(r.id, `previous[${i}].id`, 20),
        status: oneOf(r.status, PREVIOUS_STATUSES, `previous[${i}].status`),
        note: str(r.note ?? "", `previous[${i}].note`, 2000, true),
      };
    }),
  };
};

export const parseFixOutput = (value: unknown): FixOutput => {
  const record = obj(value, "fix output");
  return {
    summary: str(record.summary, "summary", 4000),
    cause: str(record.cause ?? "", "cause", 2000, true),
    responses: arr(record.responses, "responses").map((x, i) => {
      const r = obj(x, `responses[${i}]`);
      return {
        id: str(r.id, `responses[${i}].id`, 20),
        action: oneOf(r.action, FIX_ACTIONS, `responses[${i}].action`),
        reason: str(r.reason ?? "", `responses[${i}].reason`, 2000, true),
      };
    }),
  };
};

/** Plain code numbers the findings, so the agent cannot reuse or clash ids. */
export const assignIds = (round: number, findings: readonly Omit<Finding, "id">[]): Finding[] =>
  findings.map((f, i) => ({ ...f, id: `R${round}-${i + 1}` }));

// --- Rules -------------------------------------------------------------------

export const isHighRisk = (f: Finding, highRisk: readonly string[]): boolean =>
  highRisk.includes(f.category);

/** The fixer may decline this finding with a reason. */
export const isDeclinable = (f: Finding, highRisk: readonly string[]): boolean =>
  f.requested && !isHighRisk(f, highRisk);

/** Serious enough to stop the pull request if it is left unresolved. */
export const isBlockingKind = (f: Finding, highRisk: readonly string[]): boolean =>
  f.severity === "blocker" || f.severity === "major" || !isDeclinable(f, highRisk);

/**
 * Match the fixer's responses to the findings. Every finding gets one; a
 * decline the rules do not allow is recorded as refused.
 */
export const reconcileResponses = (
  findings: readonly Finding[],
  output: FixOutput,
  highRisk: readonly string[],
): FixResponse[] =>
  findings.map((f) => {
    const r = output.responses.find((x) => x.id === f.id);
    if (!r) return { id: f.id, action: "none", reason: "" };
    if (r.action === "declined" && !isDeclinable(f, highRisk)) {
      return { ...r, declineRefused: true };
    }
    return r;
  });

/** Whether a round 1 finding is settled after the fix and the round 2 review. */
export const isResolved = (
  f: Finding,
  response: FixResponse | undefined,
  status: PreviousStatus | undefined,
  highRisk: readonly string[],
): boolean => {
  if (status?.status === "fixed") return true;
  return (
    status?.status === "declined_accepted" &&
    response?.action === "declined" &&
    !response.declineRefused &&
    isDeclinable(f, highRisk)
  );
};

/**
 * The ids that block the pull request after a review round.
 *
 * Round 1: every finding of a blocking kind (they go to the fixer first).
 * Round 2: round 1 findings of a blocking kind that are not resolved, plus
 * new findings of a blocking kind. Minor findings never block.
 */
export const blockingIds = (
  round: number,
  findings: readonly Finding[],
  highRisk: readonly string[],
  earlier?: {
    readonly findings: readonly Finding[];
    readonly responses: readonly FixResponse[];
    readonly previous: readonly PreviousStatus[];
  },
): string[] => {
  const fresh = findings.filter((f) => isBlockingKind(f, highRisk)).map((f) => f.id);
  if (round === 1 || !earlier) return fresh;
  const open = earlier.findings
    .filter((f) => isBlockingKind(f, highRisk))
    .filter(
      (f) =>
        !isResolved(
          f,
          earlier.responses.find((r) => r.id === f.id),
          earlier.previous.find((p) => p.id === f.id),
          highRisk,
        ),
    )
    .map((f) => f.id);
  return [...open, ...fresh];
};

/** An example of the reviewer's output, shown to the agent in its prompt. */
export const reviewOutputExample = (categories: readonly string[]): string =>
  JSON.stringify(
    {
      summary: "1 to 3 paragraphs: what the change does and how it measures up to the work order.",
      findings: [
        {
          category: [...categories, ...OTHER_CATEGORIES].join(" | "),
          severity: SEVERITIES.join(" | "),
          requested: "true if the work order asked for the change this finding is about, false for unrequested work",
          path: "relative/path.py or null",
          line: "line number in the new file, or null",
          title: "one line",
          detail: "what is wrong, why it matters, and what would fix it",
        },
      ],
      previous: [
        { id: "R1-1 (round 2 only)", status: PREVIOUS_STATUSES.join(" | "), note: "one or two sentences" },
      ],
    },
    null,
    2,
  );
