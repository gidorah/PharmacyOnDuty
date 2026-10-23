// Starts the CI gate on a branch and waits for its `gate` job (decision S0-7).
//
// Pushes and pull requests made with the built-in token start no workflow, so
// the pipeline starts the gate itself:
//
//   gh workflow run factory-gate.yml --ref <branch> -f base=main
//
// and reads one result: the conclusion of the job named `gate` in that run.
// When it fails, the failed jobs are rerun once with no Claude involved
// (decision 9, sub-decision 4), so a test that fails only sometimes does not
// use up a fix try.

import type { GitHub } from "./github.ts";

export const GATE_WORKFLOW = "factory-gate.yml";
export const GATE_JOB = "gate";

export interface WorkflowRun {
  readonly id: number;
  readonly html_url: string;
  readonly head_sha: string;
  readonly status: string;
  readonly conclusion: string | null;
  readonly run_attempt: number;
  readonly event: string;
  readonly created_at: string;
}

interface Job {
  readonly name: string;
  readonly conclusion: string | null;
}

export interface GateResult {
  readonly runId: number;
  readonly attempt: number;
  readonly url: string;
  readonly sha: string;
  readonly green: boolean;
  /** The `gate` job's conclusion, or "missing" when the run has no such job. */
  readonly conclusion: string;
  /** Names of the jobs that did not succeed, other than `gate` itself. */
  readonly failedJobs: readonly string[];
}

export interface GateOutcome {
  /** The last result, after the rerun if there was one. */
  readonly final: GateResult;
  readonly first: GateResult;
  readonly rerun: boolean;
}

export interface Clock {
  now(): number;
  sleep(seconds: number): Promise<void>;
}

export const realClock: Clock = {
  now: () => Date.now(),
  sleep: (s) => new Promise((resolve) => setTimeout(resolve, s * 1000)),
};

export interface GateOptions {
  readonly pollSeconds: number;
  /** How long to wait for the dispatched run to appear. */
  readonly findTimeoutSeconds: number;
  /** How long to wait for one attempt to finish. */
  readonly runTimeoutSeconds: number;
}

export const DEFAULT_GATE_OPTIONS: GateOptions = {
  pollSeconds: 15,
  findTimeoutSeconds: 300,
  runTimeoutSeconds: 40 * 60,
};

export class Gate {
  constructor(
    private readonly github: GitHub,
    private readonly clock: Clock = realClock,
    private readonly options: GateOptions = DEFAULT_GATE_OPTIONS,
  ) {}

  private runsFor(sha: string): WorkflowRun[] {
    return this.github.api<{ workflow_runs: WorkflowRun[] }>(
      `repos/${this.github.repo}/actions/workflows/${GATE_WORKFLOW}/runs?event=workflow_dispatch&head_sha=${sha}&per_page=50`,
    ).workflow_runs;
  }

  private getRun(id: number): WorkflowRun {
    return this.github.api<WorkflowRun>(`repos/${this.github.repo}/actions/runs/${id}`);
  }

  /** Dispatch the gate on `ref` and return the new run for `sha`. */
  async dispatch(ref: string, sha: string, base: string): Promise<WorkflowRun> {
    // Runs that already exist for this commit are not ours. Comparing ids
    // avoids trusting the runner's clock against GitHub's.
    const known = new Set(this.runsFor(sha).map((r) => r.id));
    this.github.gh([
      "workflow",
      "run",
      GATE_WORKFLOW,
      "--repo",
      this.github.repo,
      "--ref",
      ref,
      "-f",
      `base=${base}`,
    ]);
    const deadline = this.clock.now() + this.options.findTimeoutSeconds * 1000;
    while (this.clock.now() < deadline) {
      await this.clock.sleep(this.options.pollSeconds);
      const fresh = this.runsFor(sha)
        .filter((r) => !known.has(r.id))
        .sort((a, b) => a.id - b.id);
      const run = fresh.at(-1);
      if (run) return run;
    }
    throw new Error(
      `The gate run for ${sha} did not appear within ${this.options.findTimeoutSeconds}s. Did ${ref} move?`,
    );
  }

  /** Wait until attempt `attempt` (or later) of the run has finished. */
  async wait(runId: number, attempt: number): Promise<WorkflowRun> {
    const deadline = this.clock.now() + this.options.runTimeoutSeconds * 1000;
    for (;;) {
      const run = this.getRun(runId);
      if (run.run_attempt >= attempt && run.status === "completed") return run;
      if (this.clock.now() >= deadline) {
        throw new Error(`Gate run ${run.html_url} did not finish in time.`);
      }
      await this.clock.sleep(this.options.pollSeconds);
    }
  }

  result(run: WorkflowRun): GateResult {
    const jobs = this.github.api<{ jobs: Job[] }>(
      `repos/${this.github.repo}/actions/runs/${run.id}/attempts/${run.run_attempt}/jobs?per_page=100`,
    ).jobs;
    return summarize(run, jobs);
  }

  async rerunFailed(run: WorkflowRun): Promise<WorkflowRun> {
    this.github.api(`repos/${this.github.repo}/actions/runs/${run.id}/rerun-failed-jobs`, {
      method: "POST",
    });
    return this.wait(run.id, run.run_attempt + 1);
  }

  /** Dispatch, wait, and rerun the failed jobs once if the gate is red. */
  async check(ref: string, sha: string, base = "main"): Promise<GateOutcome> {
    const started = await this.dispatch(ref, sha, base);
    console.log(`Gate run: ${started.html_url}`);
    const done = await this.wait(started.id, started.run_attempt);
    const first = this.result(done);
    if (first.green) return { first, final: first, rerun: false };
    console.log(
      `Gate is red (${first.conclusion}; failed: ${first.failedJobs.join(", ") || "none listed"}). Rerunning the failed jobs once.`,
    );
    const rerun = await this.rerunFailed(done);
    return { first, final: this.result(rerun), rerun: true };
  }
}

export const summarize = (run: WorkflowRun, jobs: readonly Job[]): GateResult => {
  const gate = jobs.find((j) => j.name === GATE_JOB);
  const conclusion = gate?.conclusion ?? "missing";
  return {
    runId: run.id,
    attempt: run.run_attempt,
    url: run.html_url,
    sha: run.head_sha,
    green: conclusion === "success",
    conclusion,
    failedJobs: jobs
      .filter((j) => j.name !== GATE_JOB && j.conclusion !== "success" && j.conclusion !== "skipped")
      .map((j) => j.name),
  };
};

/**
 * The latest gate run on a commit, from any event (push, pull request or
 * dispatch). `pending` when that run has not finished.
 */
export const latestGateOnCommit = (
  github: GitHub,
  sha: string,
): { readonly pending: true; readonly run: WorkflowRun } | ({ readonly pending: false } & GateResult) | null => {
  const runs = github
    .api<{ workflow_runs: WorkflowRun[] }>(
      `repos/${github.repo}/actions/workflows/${GATE_WORKFLOW}/runs?head_sha=${sha}&per_page=50`,
    )
    .workflow_runs.sort((a, b) => a.id - b.id);
  const latest = runs.at(-1);
  if (!latest) return null;
  if (latest.status !== "completed") return { pending: true, run: latest };
  const jobs = github.api<{ jobs: Job[] }>(
    `repos/${github.repo}/actions/runs/${latest.id}/attempts/${latest.run_attempt}/jobs?per_page=100`,
  ).jobs;
  return { pending: false, ...summarize(latest, jobs) };
};

/** The log lines of the failed jobs in a run, cut to the last `maxChars`. */
export const failedLogs = (github: GitHub, runId: number, maxChars = 60_000): string => {
  let log: string;
  try {
    log = github.gh(["run", "view", String(runId), "--repo", github.repo, "--log-failed"]);
  } catch (error) {
    return `(Could not read the logs: ${String(error).slice(0, 300)})`;
  }
  return log.length > maxChars ? `[... cut to the last ${maxChars} characters ...]\n${log.slice(-maxChars)}` : log;
};
