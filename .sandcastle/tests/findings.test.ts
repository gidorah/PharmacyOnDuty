import assert from "node:assert/strict";
import * as path from "node:path";
import { describe, it } from "node:test";
import {
  assignIds,
  blockingIds,
  type Finding,
  isDeclinable,
  loadHighRiskCategories,
  parseFixOutput,
  parseReviewOutput,
  reconcileResponses,
} from "../steps/findings.ts";

const HIGH_RISK = loadHighRiskCategories(path.join(import.meta.dirname, "../../factory/risk-map.yml"));

const finding = (id: string, overrides: Partial<Finding> = {}): Finding => ({
  id,
  category: "correctness",
  severity: "major",
  requested: true,
  path: "pharmacies/utils/utils.py",
  line: 10,
  title: "Off by one",
  detail: "The loop skips the last district.",
  ...overrides,
});

describe("the risk map's high-risk categories", () => {
  it("are read from factory/risk-map.yml", () => {
    assert.deepEqual(HIGH_RISK, [
      "security", "privacy", "auth", "billing", "data-retention", "migrations", "idempotency", "concurrency",
    ]);
  });
});

describe("parseReviewOutput", () => {
  it("accepts a valid review and drops unknown fields", () => {
    const out = parseReviewOutput(
      {
        summary: "Fine.",
        findings: [{ category: "security", severity: "minor", requested: true, path: "a.py", line: 3, title: "t", detail: "d", extra: 1 }],
        previous: [],
      },
      HIGH_RISK,
    );
    assert.deepEqual(out.findings[0], { category: "security", severity: "minor", requested: true, path: "a.py", line: 3, title: "t", detail: "d" });
  });

  it("rejects an unknown category, a missing `requested`, or a bad severity", () => {
    const base = { category: "correctness", severity: "major", requested: true, title: "t", detail: "d" };
    assert.throws(() => parseReviewOutput({ summary: "s", findings: [{ ...base, category: "vibes" }] }, HIGH_RISK), /category/);
    assert.throws(() => parseReviewOutput({ summary: "s", findings: [{ ...base, requested: "yes" }] }, HIGH_RISK), /requested/);
    assert.throws(() => parseReviewOutput({ summary: "s", findings: [{ ...base, severity: "huge" }] }, HIGH_RISK), /severity/);
    assert.throws(() => parseReviewOutput({ findings: [] }, HIGH_RISK), /summary/);
  });

  it("numbers findings itself", () => {
    const ids = assignIds(2, [finding("x"), finding("x")]).map((f) => f.id);
    assert.deepEqual(ids, ["R2-1", "R2-2"]);
  });
});

describe("declining", () => {
  it("allows declining only requested findings outside the high-risk categories", () => {
    assert.equal(isDeclinable(finding("R1-1"), HIGH_RISK), true);
    assert.equal(isDeclinable(finding("R1-1", { category: "security" }), HIGH_RISK), false);
    assert.equal(isDeclinable(finding("R1-1", { requested: false, category: "scope" }), HIGH_RISK), false);
  });

  it("records a decline the rules do not allow, and a missing answer", () => {
    const findings = [
      finding("R1-1"),
      finding("R1-2", { category: "migrations", severity: "minor" }),
      finding("R1-3", { requested: false, category: "scope", severity: "nit" }),
      finding("R1-4"),
    ];
    const responses = reconcileResponses(
      findings,
      parseFixOutput({
        summary: "s",
        responses: [
          { id: "R1-1", action: "declined", reason: "The work order fixes this later." },
          { id: "R1-2", action: "declined", reason: "Not needed." },
          { id: "R1-3", action: "declined", reason: "Nice to have." },
        ],
      }),
      HIGH_RISK,
    );
    assert.deepEqual(
      responses.map((r) => [r.id, r.action, r.declineRefused ?? false]),
      [
        ["R1-1", "declined", false],
        ["R1-2", "declined", true],
        ["R1-3", "declined", true],
        ["R1-4", "none", false],
      ],
    );
  });
});

describe("blockingIds", () => {
  it("round 1: blockers, majors, high-risk and unrequested work block; minor and nit do not", () => {
    const findings = [
      finding("R1-1", { severity: "blocker" }),
      finding("R1-2", { severity: "minor" }),
      finding("R1-3", { severity: "nit", category: "concurrency" }),
      finding("R1-4", { severity: "nit", requested: false, category: "scope" }),
      finding("R1-5", { severity: "nit" }),
    ];
    assert.deepEqual(blockingIds(1, findings, HIGH_RISK), ["R1-1", "R1-3", "R1-4"]);
  });

  it("round 2: settles fixed findings and accepted declines, keeps the rest and new ones", () => {
    const earlier = [
      finding("R1-1"),
      finding("R1-2"),
      finding("R1-3", { category: "security" }),
      finding("R1-4"),
      finding("R1-5", { severity: "minor" }),
    ];
    const responses = reconcileResponses(
      earlier,
      parseFixOutput({
        summary: "s",
        responses: [
          { id: "R1-1", action: "fixed", reason: "" },
          { id: "R1-2", action: "declined", reason: "Out of scope." },
          { id: "R1-3", action: "declined", reason: "Fine as is." },
          { id: "R1-4", action: "declined", reason: "Disagree." },
          { id: "R1-5", action: "declined", reason: "Style only." },
        ],
      }),
      HIGH_RISK,
    );
    const previous = [
      { id: "R1-1", status: "fixed" as const, note: "" },
      { id: "R1-2", status: "declined_accepted" as const, note: "" },
      // The reviewer accepts a decline the rules do not allow: still blocking.
      { id: "R1-3", status: "declined_accepted" as const, note: "" },
      { id: "R1-4", status: "declined_rejected" as const, note: "" },
      { id: "R1-5", status: "not_fixed" as const, note: "" },
    ];
    const fresh = [finding("R2-1", { severity: "minor" }), finding("R2-2", { severity: "blocker" })];
    assert.deepEqual(blockingIds(2, fresh, HIGH_RISK, { findings: earlier, responses, previous }), [
      "R1-3",
      "R1-4",
      "R2-2",
    ]);
  });

  it("round 2: a finding the reviewer did not check stays open", () => {
    const earlier = [finding("R1-1")];
    const responses = [{ id: "R1-1", action: "fixed" as const, reason: "" }];
    assert.deepEqual(blockingIds(2, [], HIGH_RISK, { findings: earlier, responses, previous: [] }), ["R1-1"]);
  });
});
