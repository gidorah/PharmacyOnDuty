import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { DatedMarker, Marker } from "../steps/markers.ts";
import { checkMerge, type MergeState } from "../steps/merge-check.ts";
import { tierComment } from "../steps/tier-report.ts";
import type { TierResult } from "../steps/tier.ts";

const SHA = "a".repeat(40);
const dated = (...markers: Marker[]): DatedMarker[] => markers.map((marker, i) => ({ marker, createdAt: "", commentId: i + 1 }));
const tierA = (sha = SHA): Marker => ({ kind: "tier", tier: "A", sha, rule: "dependabot-version-only" });

const state = (overrides: Partial<MergeState> = {}): MergeState => ({
  open: true,
  sameRepo: true,
  headSha: SHA,
  requestedSha: SHA,
  labels: ["tier:A", "dependencies"],
  markers: dated(tierA()),
  gate: { pending: false, green: true, url: "https://example.test/gate" },
  ...overrides,
});

const reasons = (s: MergeState) => {
  const d = checkMerge(s);
  return d.ok ? [] : d.reasons;
};

describe("checkMerge", () => {
  it("merges a tier A pull request with a green gate on the checked commit", () => {
    assert.deepEqual(checkMerge(state()), { ok: true });
  });

  it("refuses without the tier:A label, or with a stop label", () => {
    assert.match(reasons(state({ labels: [] })).join(), /not labeled `tier:A`/);
    assert.match(reasons(state({ labels: ["tier:A", "agent:stuck"] })).join(), /agent:stuck/);
    assert.match(reasons(state({ labels: ["tier:A", "tier:C"] })).join(), /tier:C/);
  });

  it("refuses when the head is not the commit the tier job checked", () => {
    assert.match(reasons(state({ headSha: "b".repeat(40) })).join(), /head moved/);
    assert.match(reasons(state({ markers: dated(tierA("c".repeat(40))) })).join(), /tier job checked ccccccc/);
  });

  it("uses the tier job's latest result", () => {
    const markers = dated(tierA(), { kind: "tier", tier: "B", sha: SHA, rule: null });
    assert.match(reasons(state({ markers })).join(), /latest result is tier B/);
    assert.match(reasons(state({ markers: [] })).join(), /has not checked it/);
  });

  it("refuses unless the gate is green on the head", () => {
    assert.match(reasons(state({ gate: null })).join(), /has not run/);
    assert.match(reasons(state({ gate: { pending: true, green: false, url: "u" } })).join(), /still running/);
    assert.match(reasons(state({ gate: { pending: false, green: false, url: "u" } })).join(), /red/);
  });

  it("refuses while the latest review has blocking findings", () => {
    const review: Marker = { kind: "review", round: 2, sha: SHA, findings: [], previous: [], blocking: ["R1-2"] };
    assert.match(reasons(state({ markers: dated(review, tierA()) })).join(), /blocking findings are open: R1-2/);
    const reset: Marker = { kind: "reset", label: "agent:review" };
    assert.deepEqual(checkMerge(state({ markers: dated(review, reset, tierA()) })), { ok: true });
  });

  it("refuses closed pull requests and forks", () => {
    assert.ok(reasons(state({ open: false })).length > 0);
    assert.ok(reasons(state({ sameRepo: false })).length > 0);
  });
});

describe("tierComment", () => {
  const result: TierResult = {
    tier: "B",
    rule: null,
    changedLines: 24,
    checks: [
      { check: "1. Risk map", tier: "A", why: ["No high-risk path."] },
      { check: "2. Kind of work", tier: "B", why: ["No active standing rule."] },
    ],
  };
  const evidence = {
    sha: SHA,
    gate: "green (u).",
    review: "1 round(s), 0 finding(s), blocking: none.",
    commits: ["🐛 fix: retry one district @someone"],
    files: [{ path: "pharmacies/utils/istanbul_saglik_scraper.py", oldPath: null, added: 20, deleted: 4 }],
    workOrder: "#45 Retry one district",
  };

  it("starts with the tier marker and explains every check", () => {
    const body = tierComment(result, evidence, "https://example.test/run");
    assert.ok(body.startsWith("<!-- factory:tier "));
    assert.match(body, /read this summary, then press Merge/);
    assert.match(body, /- 1\. Risk map: \*\*A\*\*\. No high-risk path\./);
    assert.match(body, /Work order: #45 Retry one district/);
    assert.match(body, /istanbul_saglik_scraper\.py` \+20 −4/);
    assert.match(body, /@​someone/, "commit subjects are sanitized");
  });

  it("is short for tier A", () => {
    const body = tierComment({ ...result, tier: "A", rule: "dependabot-version-only" }, evidence, "u");
    assert.doesNotMatch(body, /What changed/);
    assert.match(body, /merge step merges it/);
  });
});
