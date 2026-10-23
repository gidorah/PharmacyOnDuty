// Build station: Sonnet builds an approved work order on a new branch.
// Adapted from Sandcastle v0.12.0 (agent-workflows/implement/implement.ts).
//
// Inputs come from the plain prepare job, never from GitHub directly:
// WORK_ORDER_FILE holds the approved issue text with only Onur's comments.
// The run leaves its commits in WORK_DIR; the plain publish job pushes them.

import * as path from "node:path";
import * as sandcastle from "@ai-hero/sandcastle";
import { noSandbox } from "@ai-hero/sandcastle/sandboxes/no-sandbox";
import { claudeAgent, reportInstructionFiles } from "../shared/agent.ts";
import { fail, git, readText, required, writeJson } from "../shared/common.ts";

const ISSUE_NUMBER = required("ISSUE_NUMBER");
const ISSUE_TITLE = required("ISSUE_TITLE");
const BRANCH = required("BRANCH");
const WORK_DIR = required("WORK_DIR");
const BASE_SHA = required("BASE_SHA");
const WORK_ORDER = readText(required("WORK_ORDER_FILE"));

// Returns the reason the build failed, or null.
const build = async (): Promise<string | null> => {
  git(WORK_DIR, ["checkout", "-b", BRANCH]);

  const result = await sandcastle.run({
    name: `build-#${ISSUE_NUMBER}`,
    agent: claudeAgent("build"),
    sandbox: noSandbox(),
    cwd: WORK_DIR,
    logging: { type: "stdout" },
    promptFile: path.join(import.meta.dirname, "prompt.md"),
    promptArgs: { ISSUE_NUMBER, ISSUE_TITLE, BRANCH, WORK_ORDER },
  });

  const commits = Number(git(WORK_DIR, ["rev-list", "--count", `${BASE_SHA}..HEAD`]).trim());
  const uncommitted = git(WORK_DIR, ["status", "--porcelain"]).trim();
  writeJson("result.json", {
    commits,
    completed: result.completionSignal !== undefined,
    uncommittedFiles: uncommitted ? uncommitted.split("\n").length : 0,
  });
  if (uncommitted) {
    console.log(`::warning::The agent left uncommitted changes, which are dropped:\n${uncommitted}`);
  }
  if (!Number.isFinite(commits) || commits === 0) {
    return "The agent finished without making a commit. Its last message in the log says why.";
  }
  console.log(`Build produced ${commits} commit(s).`);
  return null;
};

const failure = await build().catch((error: unknown) =>
  error instanceof Error ? error.message : String(error),
);
reportInstructionFiles();
if (failure) fail(failure);
