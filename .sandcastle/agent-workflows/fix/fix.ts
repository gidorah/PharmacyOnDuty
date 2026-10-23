// Fix station: Sonnet fixes a red gate, answers review findings, or acts on
// Onur's comments. Adapted from Sandcastle v0.12.0
// (agent-workflows/implement-pr/implement-pr.ts).
//
// Inputs come from the plain prepare job (HANDOFF_DIR). The commits stay in
// WORK_DIR for the plain publish job; the answers go to OUTPUT_DIR/fix.json.

import * as fs from "node:fs";
import * as path from "node:path";
import * as sandcastle from "@ai-hero/sandcastle";
import { noSandbox } from "@ai-hero/sandcastle/sandboxes/no-sandbox";
import { parseFixOutput } from "../../steps/findings.ts";
import { type FixContext, readJson } from "../../steps/handoff.ts";
import { claudeAgent, reportInstructionFiles } from "../shared/agent.ts";
import { fail, git, readText, required, writeJson } from "../shared/common.ts";
import { diffFor } from "../shared/diff.ts";
import { runWithExtraction } from "../shared/run-with-extraction.ts";
import { standardSchema } from "../shared/schema.ts";

const PR_NUMBER = required("PR_NUMBER");
const WORK_DIR = required("WORK_DIR");
const HANDOFF_DIR = required("HANDOFF_DIR");
const here = import.meta.dirname;

const context = readJson<FixContext>(path.join(HANDOFF_DIR, "context.json"));

const fill = (template: string, values: Record<string, string>): string =>
  Object.entries(values).reduce((text, [key, value]) => text.replaceAll(`{{${key}}}`, () => value), template);

const taskSection = (): string => {
  const template = readText(path.join(here, `${context.reason}.md`));
  switch (context.reason) {
    case "ci":
      return fill(template, {
        ATTEMPT: String(context.attempt),
        GATE_URL: context.gate?.url ?? "(unknown)",
        FAILED_JOBS: context.gate?.failedJobs.join(", ") || "(none listed)",
        CI_LOGS: readText(path.join(HANDOFF_DIR, "ci-logs.txt")),
      });
    case "review":
      return fill(template, {
        FINDINGS: JSON.stringify(context.findings, null, 2),
        HIGH_RISK: context.highRisk.join(", "),
      });
    case "onur":
      return template;
  }
};

const fix = async (): Promise<string | null> => {
  git(WORK_DIR, ["checkout", "-B", context.headRef, context.headSha]);

  const result = await runWithExtraction({
    name: `fix-#${PR_NUMBER}-${context.reason}`,
    agent: claudeAgent("fix"),
    sandbox: noSandbox(),
    cwd: WORK_DIR,
    logging: { type: "stdout" },
    promptFile: path.join(here, "prompt.md"),
    promptArgs: {
      PR_NUMBER,
      BRANCH: context.headRef,
      TASK_SECTION: taskSection(),
      WORK_ORDER: readText(path.join(HANDOFF_DIR, "work-order.md")),
      COMMENTS: readText(path.join(HANDOFF_DIR, "comments.md")),
      DIFF: diffFor(WORK_DIR, "origin/main...HEAD"),
    },
    output: sandcastle.Output.object({ tag: "output", schema: standardSchema(parseFixOutput) }),
    extractionPrompt: readText(path.join(here, "extraction.md")),
  });

  const commits = Number(git(WORK_DIR, ["rev-list", "--count", `${context.headSha}..HEAD`]).trim());
  const uncommitted = git(WORK_DIR, ["status", "--porcelain"]).trim();
  if (uncommitted) {
    console.log(`::warning::The agent left uncommitted changes, which are dropped:\n${uncommitted}`);
  }
  writeJson("fix.json", result.output);
  writeJson("result.json", { commits });
  console.log(`Fix produced ${commits} commit(s) and ${result.output.responses.length} answer(s).`);
  return null;
};

fs.mkdirSync(required("OUTPUT_DIR"), { recursive: true });
const failure = await fix().catch((error: unknown) =>
  error instanceof Error ? error.message : String(error),
);
reportInstructionFiles();
if (failure) fail(failure);
