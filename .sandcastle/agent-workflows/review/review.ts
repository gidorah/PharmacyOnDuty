// Review station: Opus reports findings on a pull request and changes nothing.
// Adapted from Sandcastle v0.12.0 (agent-workflows/review/review.ts), whose
// reviewer changes code itself. Here the reviewer only reports (decision 9,
// sub-decision 2): the review workflow has no push step at all, and the
// findings go to the fix job.
//
// Inputs come from the plain prepare job (HANDOFF_DIR). The structured
// findings go to OUTPUT_DIR/review.json; the plain publish job checks them
// again before posting.

import * as fs from "node:fs";
import * as path from "node:path";
import * as sandcastle from "@ai-hero/sandcastle";
import { noSandbox } from "@ai-hero/sandcastle/sandboxes/no-sandbox";
import { parseReviewOutput, reviewOutputExample } from "../../steps/findings.ts";
import { type ReviewContext, readJson } from "../../steps/handoff.ts";
import { claudeAgent, reportInstructionFiles } from "../shared/agent.ts";
import { fail, git, readText, required, writeJson } from "../shared/common.ts";
import { diffFor } from "../shared/diff.ts";
import { runWithExtraction } from "../shared/run-with-extraction.ts";
import { standardSchema } from "../shared/schema.ts";

const PR_NUMBER = required("PR_NUMBER");
const WORK_DIR = required("WORK_DIR");
const HANDOFF_DIR = required("HANDOFF_DIR");
const here = import.meta.dirname;

const context = readJson<ReviewContext>(path.join(HANDOFF_DIR, "context.json"));

const roundSection = (): string => {
  if (context.round === 1 || !context.sinceSha) return "";
  return readText(path.join(here, "round-2.md"))
    .replace("{{SINCE_SHA}}", () => context.sinceSha ?? "")
    .replace("{{EARLIER_FINDINGS}}", () => JSON.stringify(context.earlierFindings, null, 2))
    .replace("{{EARLIER_RESPONSES}}", () => JSON.stringify(context.earlierResponses, null, 2))
    .replace("{{NEW_DIFF}}", () => diffFor(WORK_DIR, `${context.sinceSha}..HEAD`));
};

const review = async (): Promise<string | null> => {
  const head = git(WORK_DIR, ["rev-parse", "HEAD"]).trim();
  if (head !== context.headSha) return `Checked out ${head}, expected ${context.headSha}.`;

  const result = await runWithExtraction({
    name: `review-#${PR_NUMBER}-round-${context.round}`,
    agent: claudeAgent("review"),
    sandbox: noSandbox(),
    cwd: WORK_DIR,
    logging: { type: "stdout" },
    promptFile: path.join(here, "prompt.md"),
    promptArgs: {
      PR_NUMBER,
      ROUND: String(context.round),
      WORK_ORDER: readText(path.join(HANDOFF_DIR, "work-order.md")),
      COMMENTS: readText(path.join(HANDOFF_DIR, "comments.md")),
      DIFF: diffFor(WORK_DIR, "origin/main...HEAD"),
      ROUND_SECTION: roundSection(),
      HIGH_RISK: context.highRisk.join(", "),
    },
    output: sandcastle.Output.object({
      tag: "output",
      schema: standardSchema((value) => parseReviewOutput(value, context.highRisk)),
    }),
    extractionPrompt: readText(path.join(here, "extraction.md")).replace("{{OUTPUT_EXAMPLE}}", () =>
      reviewOutputExample(context.highRisk),
    ),
  });

  // Nothing from the work tree is used. Say so if the reviewer changed it.
  const changed = git(WORK_DIR, ["status", "--porcelain"]).trim();
  const moved = git(WORK_DIR, ["rev-parse", "HEAD"]).trim() !== head;
  if (changed || moved) {
    console.log("::warning::The reviewer changed the work tree or made commits. They are discarded.");
  }
  writeJson("review.json", result.output);
  console.log(`Review round ${context.round}: ${result.output.findings.length} finding(s).`);
  return null;
};

fs.mkdirSync(required("OUTPUT_DIR"), { recursive: true });
const failure = await review().catch((error: unknown) =>
  error instanceof Error ? error.message : String(error),
);
reportInstructionFiles();
if (failure) fail(failure);
