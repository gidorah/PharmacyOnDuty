// Markdown for the review and fix comments. Agent text is sanitized here.

import type { Finding, FixResponse, PreviousStatus } from "./findings.ts";
import { sanitizeAgentText } from "./sanitize.ts";

/** Agent text in a table cell: one line, no column breaks. */
export const cell = (text: string): string =>
  sanitizeAgentText(text).replace(/\r?\n+/g, " ").replaceAll("|", "\\|");

export const where = (f: Finding): string =>
  f.path ? `\`${cell(f.path)}${f.line ? `:${f.line}` : ""}\`` : "";

export const findingsTable = (findings: readonly Finding[], highRisk: readonly string[]): string[] => {
  if (findings.length === 0) return ["No findings."];
  return [
    "| Id | Severity | Category | Asked for by the work order | Where | Finding |",
    "|---|---|---|---|---|---|",
    ...findings.map(
      (f) =>
        `| ${f.id} | ${f.severity} | ${highRisk.includes(f.category) ? `**${f.category}** (high risk)` : f.category} | ${f.requested ? "yes" : "**no**"} | ${where(f)} | ${cell(f.title)} |`,
    ),
    "",
    "<details><summary>Details</summary>",
    "",
    ...findings.flatMap((f) => [`**${f.id}: ${cell(f.title)}**`, "", sanitizeAgentText(f.detail), ""]),
    "</details>",
  ];
};

const ANSWER: Record<FixResponse["action"], string> = {
  fixed: "fixed",
  removed: "removed",
  declined: "declined",
  none: "no answer",
};

export const answer = (r: FixResponse | undefined): string => {
  if (!r) return "no answer";
  if (r.declineRefused) return "declined, **but this finding cannot be declined**";
  return ANSWER[r.action];
};

export const earlierTable = (
  findings: readonly Finding[],
  responses: readonly FixResponse[],
  previous: readonly PreviousStatus[],
  blocking: readonly string[],
): string[] => [
  "| Id | Finding | Fixer's answer | Reviewer's verdict | Still blocking |",
  "|---|---|---|---|---|",
  ...findings.map((f) => {
    const p = previous.find((x) => x.id === f.id);
    return `| ${f.id} | ${cell(f.title)} | ${answer(responses.find((r) => r.id === f.id))} | ${p ? `${p.status}${p.note ? `: ${cell(p.note)}` : ""}` : "not checked"} | ${blocking.includes(f.id) ? "**yes**" : "no"} |`;
  }),
];
