import assert from "node:assert/strict";
import { describe, it } from "node:test";
import * as sandcastle from "@ai-hero/sandcastle";
import { instructionFileLines, STATIONS, withExtraFlags } from "../agent-workflows/shared/agent.ts";
import { sanitizeAgentText } from "../steps/sanitize.ts";

describe("withExtraFlags", () => {
  it("adds the flags to Sandcastle's print command and keeps the rest", () => {
    const base = sandcastle.claudeCode("claude-sonnet-5-5");
    const wrapped = withExtraFlags(base, () => ["--max-turns", "150", "--debug-file", "'/tmp/x.log'"]);
    const original = base.buildPrintCommand({ prompt: "hi", dangerouslySkipPermissions: true });
    const command = wrapped.buildPrintCommand({ prompt: "hi", dangerouslySkipPermissions: true });
    assert.equal(
      command.command,
      original.command.replace(
        "claude --print",
        "claude --print --max-turns 150 --debug-file '/tmp/x.log'",
      ),
    );
    assert.match(command.command, /--print .*--model 'claude-sonnet-5-5'/);
    assert.equal(command.stdin, "hi");
  });

  it("keeps resume flags for the extraction run", () => {
    const wrapped = withExtraFlags(sandcastle.claudeCode("claude-opus-5-5"), () => ["--max-turns", "5"]);
    const command = wrapped.buildPrintCommand({
      prompt: "extract",
      dangerouslySkipPermissions: true,
      resumeSession: "abc",
    });
    assert.match(command.command, /--max-turns 5 .*--resume 'abc'/);
  });
});

describe("STATIONS", () => {
  it("uses Sonnet to build and fix and Opus to review (decision 8)", () => {
    assert.equal(STATIONS.build.model, "claude-sonnet-5-5");
    assert.equal(STATIONS.fix.model, "claude-sonnet-5-5");
    assert.equal(STATIONS.review.model, "claude-opus-5-5");
  });
});

describe("instructionFileLines", () => {
  it("keeps the AGENTS.md lines from a debug log and drops the rest", () => {
    // Lines as Claude Code 2.1.304 wrote them in a local run.
    const log = [
      "2026-10-23T17:52:53.900Z [DEBUG] Starting session",
      "2026-10-23T17:52:53.916Z [DEBUG] $.fs.ancestors (cc-plugin-agents-md): CLAUDE.md, .claude/CLAUDE.md, CLAUDE.local.md found 0 of 6 directories",
      "2026-10-23T17:52:53.928Z [DEBUG] [cc-plugin-agents-md] $.ui.log (to debug): no CLAUDE.md found; AGENTS.md loaded: /home/runner/work/PharmacyOnDuty/work/AGENTS.md",
      "2026-10-23T17:52:54.000Z [DEBUG] API request",
    ].join("\n");
    assert.deepEqual(instructionFileLines(log), [
      "$.fs.ancestors (cc-plugin-agents-md): CLAUDE.md, .claude/CLAUDE.md, CLAUDE.local.md found 0 of 6 directories",
      "[cc-plugin-agents-md] $.ui.log (to debug): no CLAUDE.md found; AGENTS.md loaded: /home/runner/work/PharmacyOnDuty/work/AGENTS.md",
    ]);
  });
});

describe("sanitizeAgentText", () => {
  it("breaks HTML comment openers, so agent text cannot carry a marker", () => {
    assert.equal(
      sanitizeAgentText('<!-- factory:fix {"try":0} -->'),
      '&lt;!-- factory:fix {"try":0} -->',
    );
  });

  it("breaks @-mentions but leaves e-mail addresses and code alone", () => {
    assert.equal(sanitizeAgentText("ping @gidorah"), "ping @​gidorah");
    assert.equal(sanitizeAgentText("a@b.example"), "a@b.example");
    assert.equal(sanitizeAgentText("`@pytest.fixture`"), "`@pytest.fixture`");
  });
});
