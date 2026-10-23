// Helpers shared by the agent runners, adapted from Sandcastle v0.12.0
// (.sandcastle/agent-workflows/shared/common.ts).
//
// Agent runners never call GitHub. They read the files the prepare job wrote,
// run Claude through Sandcastle, and write their results to OUTPUT_DIR for the
// plain publish job. The agent step has no GitHub token.

import * as fs from "node:fs";
import * as path from "node:path";
import { execFileSync } from "node:child_process";

export const outputDir = (): string => required("OUTPUT_DIR");

export function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    console.error(`Missing required env var: ${name}`);
    process.exit(1);
  }
  return value;
}

export const fail = (message: string): never => {
  console.error(`\nFAILED: ${message}`);
  fs.mkdirSync(outputDir(), { recursive: true });
  fs.writeFileSync(path.join(outputDir(), "failure_reason.txt"), message);
  process.exit(1);
};

export const git = (cwd: string, args: string[]): string =>
  execFileSync("git", args, {
    cwd,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });

export const writeJson = (filename: string, value: unknown): void => {
  fs.mkdirSync(outputDir(), { recursive: true });
  fs.writeFileSync(path.join(outputDir(), filename), JSON.stringify(value, null, 2));
};

export const readText = (file: string): string => fs.readFileSync(file, "utf8");
