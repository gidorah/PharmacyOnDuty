// Files a plain prepare job hands to the agent job and to its own publish job.

import * as fs from "node:fs";
import * as path from "node:path";
import type { Finding, FixResponse } from "./findings.ts";

export interface ReviewContext {
  readonly round: number;
  readonly headSha: string;
  readonly headRef: string;
  readonly highRisk: readonly string[];
  /** Round 2: the commit round 1 reviewed. */
  readonly sinceSha: string | null;
  readonly earlierFindings: readonly Finding[];
  readonly earlierResponses: readonly FixResponse[];
}

export interface FixContext {
  readonly reason: "ci" | "review" | "onur";
  /** The CI try number; 0 for other reasons. */
  readonly attempt: number;
  readonly headSha: string;
  readonly headRef: string;
  readonly highRisk: readonly string[];
  readonly findings: readonly Finding[];
  readonly gate: { readonly url: string; readonly failedJobs: readonly string[] } | null;
}

export const writeHandoff = (dir: string, files: Record<string, string | object>): void => {
  fs.mkdirSync(dir, { recursive: true });
  for (const [name, content] of Object.entries(files)) {
    fs.writeFileSync(path.join(dir, name), typeof content === "string" ? content : JSON.stringify(content, null, 2));
  }
};

export const readJson = <T>(file: string): T => JSON.parse(fs.readFileSync(file, "utf8")) as T;
