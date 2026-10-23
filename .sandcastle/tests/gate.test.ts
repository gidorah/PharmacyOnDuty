import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { type Clock, Gate, type WorkflowRun } from "../steps/gate.ts";
import { decideAfterGate } from "../steps/route.ts";
import { FakeGitHub } from "./fake-github.ts";

const SHA = "a".repeat(40);
const RUNS = `actions/workflows/factory-gate.yml/runs?event=workflow_dispatch&head_sha=${SHA}&per_page=50`;

const fakeClock = (): Clock & { slept: number } => {
  let t = 0;
  return {
    slept: 0,
    now: () => t,
    async sleep(seconds: number) {
      t += seconds * 1000;
      this.slept += seconds;
    },
  };
};

const run = (overrides: Partial<WorkflowRun> = {}): WorkflowRun => ({
  id: 7,
  html_url: "https://github.com/gidorah/PharmacyOnDuty/actions/runs/7",
  head_sha: SHA,
  status: "completed",
  conclusion: "success",
  run_attempt: 1,
  event: "workflow_dispatch",
  created_at: "2026-10-23T10:00:00Z",
  ...overrides,
});

const jobs = (gate: string, failed: string[] = []) => ({
  jobs: [
    { name: "Layer 1 - static checks", conclusion: failed.includes("static") ? "failure" : "success" },
    { name: "Layers 2 and 3 - tests", conclusion: failed.includes("tests") ? "failure" : "success" },
    { name: "gate", conclusion: gate },
  ],
});

const options = { pollSeconds: 10, findTimeoutSeconds: 60, runTimeoutSeconds: 600 };

describe("Gate.check", () => {
  it("dispatches the gate on the branch and reads the gate job", async () => {
    const github = new FakeGitHub();
    let listed = 0;
    github
      .on("GET", RUNS, () => ({ workflow_runs: listed++ === 0 ? [run({ id: 3 })] : [run({ id: 3 }), run()] }))
      .on("GET", "actions/runs/7", run())
      .on("GET", "actions/runs/7/attempts/1/jobs?per_page=100", jobs("success"));
    const outcome = await new Gate(github, fakeClock(), options).check("factory/issue-45", SHA);
    assert.deepEqual(github.ghCalls[0], [
      "workflow", "run", "factory-gate.yml", "--repo", "gidorah/PharmacyOnDuty",
      "--ref", "factory/issue-45", "-f", "base=main",
    ]);
    assert.equal(outcome.final.runId, 7, "ignores the run that existed before the dispatch");
    assert.equal(outcome.final.green, true);
    assert.equal(outcome.rerun, false);
  });

  it("reruns the failed jobs once when the gate is red", async () => {
    const github = new FakeGitHub();
    let listed = 0;
    let attempt = 1;
    github
      .on("GET", RUNS, () => ({ workflow_runs: listed++ === 0 ? [] : [run()] }))
      .on("GET", "actions/runs/7", () => run({ run_attempt: attempt }))
      .on("GET", "actions/runs/7/attempts/1/jobs?per_page=100", jobs("failure", ["tests"]))
      .on("GET", "actions/runs/7/attempts/2/jobs?per_page=100", jobs("success"))
      .on("POST", "actions/runs/7/rerun-failed-jobs", () => {
        attempt = 2;
        return null;
      });
    const outcome = await new Gate(github, fakeClock(), options).check("factory/issue-45", SHA);
    assert.equal(outcome.rerun, true);
    assert.deepEqual(outcome.first.failedJobs, ["Layers 2 and 3 - tests"]);
    assert.equal(outcome.final.green, true, "a flaky failure passes on the rerun");
  });

  it("treats a run without a gate job as red", async () => {
    const github = new FakeGitHub();
    let listed = 0;
    github
      .on("GET", RUNS, () => ({ workflow_runs: listed++ === 0 ? [] : [run({ conclusion: "failure" })] }))
      .on("GET", "actions/runs/7", run({ conclusion: "failure" }))
      .on("GET", "actions/runs/7/attempts/1/jobs?per_page=100", { jobs: [] })
      .on("POST", "actions/runs/7/rerun-failed-jobs", null);
    const gate = new Gate(github, fakeClock(), options);
    const done = gate.result(run({ conclusion: "failure" }));
    assert.equal(done.green, false);
    assert.equal(done.conclusion, "missing");
  });

  it("gives up when the dispatched run never appears", async () => {
    const github = new FakeGitHub();
    github.on("GET", RUNS, { workflow_runs: [] });
    await assert.rejects(
      new Gate(github, fakeClock(), options).check("factory/issue-45", SHA),
      /did not appear/,
    );
  });

  it("gives up when the run does not finish in time", async () => {
    const github = new FakeGitHub();
    let listed = 0;
    github
      .on("GET", RUNS, () => ({ workflow_runs: listed++ === 0 ? [] : [run({ status: "in_progress" })] }))
      .on("GET", "actions/runs/7", run({ status: "in_progress", conclusion: null }));
    await assert.rejects(
      new Gate(github, fakeClock(), options).check("factory/issue-45", SHA),
      /did not finish in time/,
    );
  });
});

describe("decideAfterGate", () => {
  const green = { runId: 1, attempt: 1, url: "u", sha: SHA, green: true, conclusion: "success", failedJobs: [] };
  const red = { ...green, green: false, conclusion: "failure", failedJobs: ["tests"] };

  it("sends a green gate to review", () => {
    assert.deepEqual(decideAfterGate({ first: green, final: green, rerun: false }, 0), {
      action: "review",
    });
  });

  it("sends a red gate to a fix while tries are left", () => {
    const outcome = { first: red, final: red, rerun: true };
    assert.deepEqual(decideAfterGate(outcome, 0, 2), { action: "fix", attempt: 1 });
    assert.deepEqual(decideAfterGate(outcome, 1, 2), { action: "fix", attempt: 2 });
    assert.equal(decideAfterGate(outcome, 2, 2).action, "stuck");
  });

  it("waits for Onur when only the test-removal check failed", () => {
    const removal = { ...red, failedJobs: ["Test-removal check"] };
    const next = decideAfterGate({ first: removal, final: removal, rerun: true }, 0);
    assert.equal(next.action, "stuck");
    assert.match(next.action === "stuck" ? next.why : "", /allow-test-removal/);
  });
});
