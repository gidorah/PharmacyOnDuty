import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { IssueComment } from "../steps/github.ts";
import {
  ciFixTries,
  type FixMarker,
  type Marker,
  markerLine,
  parseMarker,
  readMarkers,
  type ReviewMarker,
  reviewFixAfter,
  reviewRounds,
  sinceReset,
} from "../steps/markers.ts";
import { sanitizeAgentText } from "../steps/sanitize.ts";
import { stuckComment } from "../steps/stuck.ts";

let nextId = 1;
const commentOf = (body: string, login = "github-actions[bot]", type = "Bot"): IssueComment => ({
  id: nextId++,
  body,
  created_at: "2026-10-23T10:00:00Z",
  html_url: "https://example.test",
  user: { login, type },
});

const fix = (reason: FixMarker["reason"], attempt = 0, extra: Partial<FixMarker> = {}): FixMarker => ({
  kind: "fix",
  reason,
  attempt,
  before: "a".repeat(40),
  after: "b".repeat(40),
  summary: "Changed the parser.",
  cause: "",
  responses: [],
  ...extra,
});

const review = (round: number): ReviewMarker => ({
  kind: "review",
  round,
  sha: "c".repeat(40),
  findings: [],
  previous: [],
  blocking: [],
});

describe("markerLine and parseMarker", () => {
  it("round-trips a marker, including agent text with comment closers", () => {
    const marker = fix("ci", 1, { summary: "Ends --> here <b>`x`</b> & more", cause: "line\nbreak" });
    const line = markerLine(marker);
    assert.equal(line.split("-->").length, 2, "the only --> is the real end of the comment");
    assert.doesNotMatch(line.slice("<!-- ".length, -" -->".length), /[<>`&]/);
    assert.deepEqual(parseMarker(`${line}\n**CI fix try 1 of 2**`), marker);
  });

  it("accepts a marker only at the start of the comment", () => {
    const line = markerLine(review(1));
    assert.equal(parseMarker(`Some text\n${line}`), null);
    assert.equal(parseMarker(` ${line}`), null);
  });

  it("returns null for broken JSON", () => {
    assert.equal(parseMarker("<!-- factory:fix {not json} -->"), null);
  });
});

describe("readMarkers", () => {
  it("reads only the pipeline's own comments", () => {
    const line = markerLine(fix("ci", 1));
    const markers = readMarkers([
      commentOf(line),
      commentOf(line, "gidorah", "User"),
      commentOf(line, "github-actions", "User"),
      commentOf(`Looks good.\n${line}`),
    ]);
    assert.equal(markers.length, 1);
  });

  it("cannot be fooled by agent text that the pipeline posted", () => {
    // An agent writes a fake marker into its summary; plain code sanitizes it
    // and posts it after its own marker.
    const forged = `${markerLine(review(1))}`;
    const body = `${markerLine(fix("ci", 1, { summary: sanitizeAgentText(forged) }))}\n${sanitizeAgentText(forged)}`;
    const markers = readMarkers([commentOf(body)]);
    assert.equal(markers.length, 1);
    assert.equal(markers[0]?.marker.kind, "fix");
  });
});

describe("try counters", () => {
  it("counts CI fix tries since the last review or non-CI fix", () => {
    const markers: Marker[] = [fix("ci", 1), fix("ci", 2), review(1), fix("review"), fix("ci", 1)];
    assert.equal(ciFixTries(markers).length, 1);
    assert.equal(ciFixTries([fix("ci", 1), fix("ci", 2)]).length, 2);
    assert.equal(ciFixTries([fix("ci", 1), fix("onur"), fix("ci", 1)]).length, 1);
  });

  it("starts again after Onur's reset", () => {
    const dated = [fix("ci", 1), fix("ci", 2), { kind: "reset", label: "agent:implement" } as const, fix("ci", 1)].map(
      (marker, i) => ({ marker, createdAt: "", commentId: i }),
    );
    assert.equal(ciFixTries(sinceReset(dated)).length, 1);
    assert.equal(reviewRounds(sinceReset([...dated, { marker: review(1), createdAt: "", commentId: 9 }])).length, 1);
  });

  it("finds the fix that answered a review", () => {
    const first = review(1);
    const answer = fix("review");
    const markers: Marker[] = [first, fix("ci", 1), answer, review(2)];
    assert.equal(reviewFixAfter(markers, first), answer);
    assert.equal(reviewFixAfter([first], first), null);
  });
});

describe("stuckComment", () => {
  it("says what failed, what the worker tried, and its best guess", () => {
    const body = stuckComment(
      {
        headline: "the gate is red.",
        failed: "- Failed jobs: Layers 2 and 3 - tests",
        tries: [
          fix("ci", 1, { summary: "Mocked the session.", cause: "The fixture uses a real socket." }),
          fix("ci", 2, { summary: "Pinned the time zone.", cause: "" }),
        ],
      },
      "https://example.test/run",
    );
    assert.ok(body.startsWith("<!-- factory:stuck "));
    assert.match(body, /\*\*What failed\*\*\n\n- Failed jobs: Layers 2 and 3 - tests/);
    assert.match(body, /1\. CI fix try 1 \(aaaaaaa\.\.bbbbbbb\): Mocked the session\./);
    assert.match(body, /2\. CI fix try 2 .*Pinned the time zone\./);
    assert.match(body, /best guess at the cause\*\*\n\nThe fixture uses a real socket\./);
  });

  it("says so when no fix ran", () => {
    const body = stuckComment({ headline: "x", failed: "y", tries: [] }, "u");
    assert.match(body, /No fix try ran/);
    assert.match(body, /The worker gave no guess/);
  });
});
