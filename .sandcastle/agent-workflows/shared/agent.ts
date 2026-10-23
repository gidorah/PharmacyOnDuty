// The Claude agent for each station, on Sandcastle's Claude Code provider.
//
// Sandcastle runs `claude --print --verbose --dangerously-skip-permissions
// --output-format stream-json --model <id> -p -` (print mode, decision 10).
// This wrapper adds two flags to that command:
//   --max-turns   the turn limit per job (decision 10);
//   --debug-file  Claude's debug log, which names the instruction files it
//                 loaded (S0-5a). The log stays on the runner; only the lines
//                 about instruction files are printed.

import * as fs from "node:fs";
import * as path from "node:path";
import * as sandcastle from "@ai-hero/sandcastle";
import { outputDir, required } from "./common.ts";

type AgentProvider = ReturnType<typeof sandcastle.claudeCode>;

// Models from decision 8: Sonnet builds and fixes, Opus reviews. The turn
// limits are proposals for Onur to confirm (decision 10 left them to stage 0).
export const STATIONS = {
  build: { model: "claude-sonnet-5-5", maxTurns: 150 },
  fix: { model: "claude-sonnet-5-5", maxTurns: 100 },
  review: { model: "claude-opus-5-5", maxTurns: 60 },
} as const;

export type Station = keyof typeof STATIONS;

const quote = (value: string): string => `'${value.replaceAll("'", `'\\''`)}'`;

/** Insert extra flags into Sandcastle's print command. */
export const withExtraFlags = (
  provider: AgentProvider,
  flags: () => string[],
): AgentProvider => ({
  ...provider,
  buildPrintCommand(options) {
    const printCommand = provider.buildPrintCommand(options);
    const prefix = "claude --print";
    if (!printCommand.command.startsWith(prefix)) {
      throw new Error(`Unexpected Sandcastle command: ${printCommand.command}`);
    }
    return {
      ...printCommand,
      command: `${prefix} ${flags().join(" ")}${printCommand.command.slice(prefix.length)}`,
    };
  },
});

export const debugDir = (): string => path.join(outputDir(), "claude-debug");

export const claudeAgent = (station: Station): AgentProvider => {
  const { model, maxTurns } = STATIONS[station];
  let invocation = 0;
  const base = sandcastle.claudeCode(model, {
    env: {
      CLAUDE_CODE_OAUTH_TOKEN: required("CLAUDE_CODE_OAUTH_TOKEN"),
      // Don't update the pinned CLI in the middle of a job. Not
      // CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: it also stops the feature
      // flag fetch that direct AGENTS.md reading may depend on (S0-5).
      DISABLE_AUTOUPDATER: "1",
    },
  });
  fs.mkdirSync(debugDir(), { recursive: true });
  return withExtraFlags(base, () => {
    invocation += 1;
    const log = path.join(debugDir(), `${station}-${invocation}.log`);
    return ["--max-turns", String(maxTurns), "--debug-file", quote(log)];
  });
};

const INSTRUCTION_LINE = /cc-plugin-agents-md|AGENTS\.md|CLAUDE\.md|InstructionsLoaded/;

/** The debug-log lines about instruction files, for the job log (S0-5a). */
export const instructionFileLines = (logText: string): string[] =>
  logText
    .split("\n")
    .filter((line) => INSTRUCTION_LINE.test(line))
    // Keep the message, not the timestamp and level prefix.
    .map((line) => line.replace(/^\S+\s+\[[A-Z]+\]\s+/, "").slice(0, 400));

/**
 * Print which instruction files each Claude invocation loaded, and save the
 * lines for the publish job. Warns when no AGENTS.md load was logged.
 */
export const reportInstructionFiles = (): void => {
  const dir = debugDir();
  const files = fs.existsSync(dir) ? fs.readdirSync(dir).sort() : [];
  const report: string[] = [];
  for (const file of files) {
    const lines = instructionFileLines(fs.readFileSync(path.join(dir, file), "utf8"));
    report.push(`${file}:`, ...(lines.length ? lines.map((l) => `  ${l}`) : ["  (no lines)"]));
  }
  const text = report.join("\n");
  console.log("::group::Instruction files loaded by Claude (from its debug log)");
  console.log(text || "(no debug logs found)");
  console.log("::endgroup::");
  if (!/AGENTS\.md loaded:/.test(text)) {
    console.log(
      "::warning::Claude's debug log shows no AGENTS.md load. The agent may have run without the project instructions (S0-5a).",
    );
  }
  fs.writeFileSync(path.join(outputDir(), "instruction-files.txt"), `${text}\n`);
};
