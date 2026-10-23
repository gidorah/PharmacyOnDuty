// A small wrapper around the `gh` CLI for the plain pipeline steps.
//
// Plain steps hold the job's built-in GITHUB_TOKEN (through GH_TOKEN) and
// never run Claude. Agent steps never import this file: they get no GitHub
// token at all.

import { execFileSync } from "node:child_process";
import * as fs from "node:fs";

// Onur's account. Only labels he adds start jobs, only his comments reach the
// agents, and only his edits to a work order are accepted after approval.
export const OWNER_LOGIN = "gidorah";

// The account the built-in token acts as. Comments from this account are the
// pipeline's own, so the try counters read markers only from them.
export const BOT_LOGIN = "github-actions[bot]";

export interface GitHub {
  readonly repo: string;
  /** One REST call. `body` is sent as JSON. */
  api<T>(path: string, options?: { method?: string; body?: unknown }): T;
  /** A paginated REST GET, with the pages joined into one list. */
  paginate<T>(path: string): T[];
  graphql<T>(query: string, variables: Record<string, unknown>): T;
  /** Any other `gh` command, for example `workflow run`. */
  gh(args: string[]): string;
}

const run = (args: string[], input?: string): string =>
  execFileSync("gh", args, {
    encoding: "utf8",
    input,
    stdio: [input === undefined ? "ignore" : "pipe", "pipe", "pipe"],
    maxBuffer: 64 * 1024 * 1024,
  });

export const ghCli = (repo: string): GitHub => ({
  repo,
  api<T>(path: string, options?: { method?: string; body?: unknown }): T {
    const args = ["api", "--method", options?.method ?? "GET", path];
    if (options?.body !== undefined) args.push("--input", "-");
    const out = run(
      args,
      options?.body === undefined ? undefined : JSON.stringify(options.body),
    );
    return (out.trim() === "" ? null : JSON.parse(out)) as T;
  },
  paginate<T>(path: string): T[] {
    const pages = JSON.parse(
      run(["api", "--paginate", "--slurp", path]),
    ) as unknown[];
    return pages.flatMap((page) => {
      if (Array.isArray(page)) return page as T[];
      // List endpoints that wrap the items, such as workflow runs and jobs.
      const values = Object.values(page as Record<string, unknown>);
      const list = values.find(Array.isArray);
      return (list ?? []) as T[];
    });
  },
  graphql<T>(query: string, variables: Record<string, unknown>): T {
    const out = JSON.parse(
      run(["api", "graphql", "--input", "-"], JSON.stringify({ query, variables })),
    ) as { data?: T; errors?: unknown };
    if (out.errors) {
      throw new Error(`GraphQL error: ${JSON.stringify(out.errors)}`);
    }
    return out.data as T;
  },
  gh(args: string[]): string {
    return run(args);
  },
});

export const githubFromEnv = (): GitHub => {
  const repo = process.env.GH_REPO ?? process.env.GITHUB_REPOSITORY;
  if (!repo) throw new Error("GH_REPO or GITHUB_REPOSITORY must be set");
  return ghCli(repo);
};

export const addLabels = (
  github: GitHub,
  number: number,
  labels: readonly string[],
): void => {
  if (labels.length === 0) return;
  github.api(`repos/${github.repo}/issues/${number}/labels`, {
    method: "POST",
    body: { labels },
  });
};

export const removeLabels = (
  github: GitHub,
  number: number,
  labels: readonly string[],
): void => {
  for (const label of labels) {
    try {
      github.api(
        `repos/${github.repo}/issues/${number}/labels/${encodeURIComponent(label)}`,
        { method: "DELETE" },
      );
    } catch {
      // Not on the item, which is fine.
    }
  }
};

export const comment = (github: GitHub, number: number, body: string): void => {
  github.api(`repos/${github.repo}/issues/${number}/comments`, {
    method: "POST",
    body: { body },
  });
};

export interface IssueComment {
  readonly id: number;
  readonly body: string;
  readonly created_at: string;
  readonly html_url: string;
  readonly user: { readonly login: string; readonly type: string } | null;
}

export const listComments = (github: GitHub, number: number): IssueComment[] =>
  github.paginate<IssueComment>(
    `repos/${github.repo}/issues/${number}/comments?per_page=100`,
  );

export const dispatchWorkflow = (
  github: GitHub,
  workflow: string,
  inputs: Record<string, string>,
  ref = "main",
): void => {
  const args = ["workflow", "run", workflow, "--repo", github.repo, "--ref", ref];
  for (const [key, value] of Object.entries(inputs)) {
    args.push("-f", `${key}=${value}`);
  }
  github.gh(args);
};

/** Write `key=value` lines for later workflow steps. */
export const setOutputs = (outputs: Record<string, string | number | boolean>) => {
  const file = process.env.GITHUB_OUTPUT;
  const lines = Object.entries(outputs).map(([k, v]) => `${k}=${String(v)}`);
  if (file) fs.appendFileSync(file, `${lines.join("\n")}\n`);
  for (const line of lines) console.log(`output: ${line}`);
};

export const runUrl = (): string =>
  `${process.env.GITHUB_SERVER_URL ?? "https://github.com"}/${
    process.env.GITHUB_REPOSITORY ?? ""
  }/actions/runs/${process.env.GITHUB_RUN_ID ?? ""}`;
