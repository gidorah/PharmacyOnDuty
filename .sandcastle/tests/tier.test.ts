import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { describe, it } from "node:test";
import { parse } from "yaml";
import type { Finding } from "../steps/findings.ts";
import {
  type ChangedFile,
  computeTier,
  type DependabotMetadata,
  maxTier,
  parseNumstat,
  proposedTierFrom,
  type RiskMap,
  riskHits,
  type StandingRule,
  type TierInput,
} from "../steps/tier.ts";
import { checkLock, checkPyproject, devDependencies, parseRequirement } from "../steps/version-only.ts";

const ROOT = path.join(import.meta.dirname, "../..");
const RISK_MAP = parse(fs.readFileSync(path.join(ROOT, "factory/risk-map.yml"), "utf8")) as RiskMap;
const RULES = (parse(fs.readFileSync(path.join(ROOT, "factory/standing-rules.yml"), "utf8")) as { rules: StandingRule[] }).rules;

const file = (p: string, added = 5, deleted = 0, oldPath: string | null = null): ChangedFile => ({ path: p, oldPath, added, deleted });

const PYPROJECT = `[project]
name = "pharmacyonduty"
version = "0.1.0"
dependencies = [
    "django>=5.2.16,<6.0",
    "soupsieve>=2.9",
    "celery[redis]>=5.5.3",
]

[dependency-groups]
dev = [
    "ruff>=0.15.11",
    "pytest-django>=4.12.0",
]

[tool.ruff]
line-length = 88
`;

const lock = (soupsieve: string, ruff: string, extra = "") => `version = 1
revision = 3
requires-python = ">=3.13"

[[package]]
name = "pharmacyonduty"
version = "0.1.0"
source = { virtual = "." }
dependencies = [
    { name = "soupsieve" },
]

[package.metadata]
requires-dist = [{ name = "soupsieve", specifier = ">=${soupsieve}" }]

[package.metadata.requires-dev]
dev = [{ name = "ruff", specifier = ">=${ruff}" }]

[[package]]
name = "ruff"
version = "${ruff}"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files/ruff-${ruff}.tar.gz", hash = "sha256:${ruff}" }
wheels = [
    { url = "https://files/ruff-${ruff}-x86_64.whl", hash = "sha256:w${ruff}" },
]

[[package]]
name = "soupsieve"
version = "${soupsieve}"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files/soupsieve-${soupsieve}.tar.gz", hash = "sha256:${soupsieve}" }
wheels = [
    { url = "https://files/soupsieve-${soupsieve}-any.whl", hash = "sha256:w${soupsieve}" },
]
${extra}`;

const dependabot = (...updates: [string, string][]): DependabotMetadata => ({
  ecosystem: "uv",
  updates: updates.map(([dependencyName, updateType]) => ({ dependencyName, updateType })),
});

const soupsieveBump = (): TierInput => ({
  riskMap: RISK_MAP,
  rules: RULES,
  files: [file("pyproject.toml", 1, 1), file("uv.lock", 4, 4)],
  author: "dependabot[bot]",
  dependabot: dependabot(["soupsieve", "version-update:semver-patch"]),
  manifests: {
    pyproject: { base: PYPROJECT, head: PYPROJECT.replace('"soupsieve>=2.9"', '"soupsieve>=2.9.1"') },
    lock: { base: lock("2.9", "0.15.11"), head: lock("2.9.1", "0.15.11") },
    pyprojectLines: { removed: ['    "soupsieve>=2.9",'], added: ['    "soupsieve>=2.9.1",'] },
    projectName: "pharmacyonduty",
  },
  findings: [],
  proposedTier: null,
});

const finding = (category: string): Finding => ({
  id: "R1-1", category, severity: "minor", requested: true, path: null, line: null, title: "t", detail: "d",
});

describe("riskHits with the real risk map", () => {
  const hits = (files: ChangedFile[]) => riskHits(RISK_MAP, files).map((h) => h.area.name);

  it("finds high-risk paths at any depth and under directories", () => {
    assert.deepEqual(hits([file("pharmacies/views.py")]), ["Public endpoints and billing"]);
    assert.deepEqual(hits([file("pharmacies/AGENTS.md")]), ["Agent instructions"]);
    assert.deepEqual(hits([file("docker/dev/Dockerfile")]), ["Deploy and infrastructure"]);
    assert.deepEqual(hits([file(".sandcastle/steps/tier.ts")]), ["The factory itself"]);
    assert.deepEqual(hits([file("theme/CLAUDE.md")]), ["Agent instructions"], "optional_paths count too");
    assert.deepEqual(hits([file("pharmacies/utils/istanbul_saglik_scraper.py")]), []);
  });

  it("counts a renamed file under its old path too", () => {
    assert.deepEqual(hits([file("pharmacies/old_views.py", 0, 0, "pharmacies/views.py")]), ["Public endpoints and billing"]);
  });

  it("raises scraper tests only when existing lines change (S0-3)", () => {
    assert.deepEqual(hits([file("pharmacies/tests/test_ankaraeo_scraper.py", 40, 0)]), []);
    assert.deepEqual(hits([file("pharmacies/tests/test_ankaraeo_scraper.py", 40, 1)]), ["Scraper expected results"]);
  });
});

describe("computeTier", () => {
  it("gives tier A to a Dependabot patch update that changes only versions", () => {
    const result = computeTier(soupsieveBump());
    assert.equal(result.tier, "A");
    assert.equal(result.rule, "dependabot-version-only");
    const risk = result.checks.find((c) => c.check.startsWith("1."));
    assert.match(risk?.why.join(" ") ?? "", /Waived by `dependabot-version-only`: Dependencies and tool settings/);
  });

  it("gives tier A to a minor update of a dev dependency", () => {
    const input = soupsieveBump();
    const result = computeTier({
      ...input,
      dependabot: dependabot(["ruff", "version-update:semver-minor"]),
      manifests: {
        ...input.manifests,
        pyproject: { base: PYPROJECT, head: PYPROJECT.replace('"ruff>=0.15.11"', '"ruff>=0.16.1"') },
        lock: { base: lock("2.9", "0.15.11"), head: lock("2.9", "0.16.1") },
        pyprojectLines: { removed: ['    "ruff>=0.15.11",'], added: ['    "ruff>=0.16.1",'] },
      },
    });
    assert.equal(result.tier, "A");
  });

  it("gives tier C to a minor update of a runtime dependency (S0-6)", () => {
    const result = computeTier({ ...soupsieveBump(), dependabot: dependabot(["soupsieve", "version-update:semver-minor"]) });
    assert.equal(result.tier, "C");
    assert.equal(result.rule, null);
    assert.match(result.checks.find((c) => c.check.startsWith("2."))?.why.join(" ") ?? "", /semver-minor is not allowed/);
  });

  it("treats a package in both the runtime and the dev lists as runtime", () => {
    const both = PYPROJECT.replace('    "ruff>=0.15.11",\n', '    "ruff>=0.15.11",\n    "soupsieve>=2.9",\n');
    const input = soupsieveBump();
    const result = computeTier({
      ...input,
      dependabot: dependabot(["soupsieve", "version-update:semver-minor"]),
      manifests: { ...input.manifests, pyproject: { base: both, head: both } },
    });
    assert.equal(result.tier, "C");
  });

  it("gives tier C to a major update and to a run without Dependabot metadata", () => {
    assert.equal(computeTier({ ...soupsieveBump(), dependabot: dependabot(["soupsieve", "version-update:semver-major"]) }).tier, "C");
    assert.equal(computeTier({ ...soupsieveBump(), dependabot: null }).tier, "C");
  });

  it("gives tier C when someone other than Dependabot makes the same change", () => {
    assert.equal(computeTier({ ...soupsieveBump(), author: "gidorah" }).tier, "C");
  });

  it("gives tier C when the update touches another file", () => {
    const input = soupsieveBump();
    const result = computeTier({ ...input, files: [...input.files, file("README.md", 1, 0)] });
    assert.equal(result.tier, "C");
  });

  it("keeps the factory's own paths at tier C even for Dependabot (GitHub Actions updates)", () => {
    const result = computeTier({
      ...soupsieveBump(),
      files: [file(".github/workflows/factory-gate.yml", 1, 1)],
      dependabot: { ecosystem: "github_actions", updates: [{ dependencyName: "actions/checkout", updateType: "version-update:semver-patch" }] },
    });
    assert.equal(result.tier, "C");
  });

  it("is at least tier B above the size limit", () => {
    const input = soupsieveBump();
    const result = computeTier({ ...input, files: [file("pyproject.toml", 1, 1), file("uv.lock", 150, 150)] });
    assert.equal(result.tier, "B");
    assert.match(result.checks.find((c) => c.check.startsWith("3."))?.why.join(" ") ?? "", /at least tier B/);
  });

  it("raises to tier C on a high-risk reviewer finding, even a minor one", () => {
    assert.equal(computeTier({ ...soupsieveBump(), findings: [finding("security")] }).tier, "C");
    assert.equal(computeTier({ ...soupsieveBump(), findings: [finding("docs")] }).tier, "A");
  });

  it("gives tier B to ordinary work and lets the proposed tier only raise it", () => {
    const work: TierInput = {
      ...soupsieveBump(),
      author: "github-actions[bot]",
      dependabot: null,
      files: [file("pharmacies/utils/istanbul_saglik_scraper.py", 20, 4), file("pharmacies/tests/test_new_thing.py", 30, 0)],
    };
    assert.equal(computeTier(work).tier, "B");
    assert.equal(computeTier({ ...work, proposedTier: "A" }).tier, "B", "a proposal cannot lower the tier");
    assert.equal(computeTier({ ...work, proposedTier: "C" }).tier, "C");
  });

  it("does not match a rule with conditions the tier job does not know", () => {
    const strange: StandingRule = { id: "x", status: "active", tier: "A", match: { author: "dependabot[bot]", sunny: true } as never };
    assert.equal(computeTier({ ...soupsieveBump(), rules: [strange] }).tier, "C");
  });

  it("ignores rules that are not active", () => {
    const rules = RULES.map((r) => ({ ...r, status: "paused" }));
    assert.equal(computeTier({ ...soupsieveBump(), rules }).tier, "C");
  });
});

describe("version-only checks", () => {
  const updated = new Set(["soupsieve"]);

  it("parses requirements with extras and markers", () => {
    assert.deepEqual(parseRequirement("celery[redis]>=5.5.3"), { name: "celery", identity: "celery[redis]", specifier: ">=5.5.3" });
    assert.equal(parseRequirement('Django_Stubs >=6 ; python_version >= "3.13"')?.identity, 'django-stubs; python_version >= "3.13"');
  });

  it("reads the dev dependencies", () => {
    assert.deepEqual([...devDependencies(PYPROJECT)], ["ruff", "pytest-django"]);
  });

  it("pyproject.toml: rejects changes outside the dependency lists", () => {
    const head = PYPROJECT.replace("line-length = 88", "line-length = 120");
    assert.equal(checkPyproject(PYPROJECT, head, { removed: ["line-length = 88"], added: ["line-length = 120"] }, updated).ok, false);
  });

  it("pyproject.toml: rejects a renamed package, changed extras, an added entry, or an unlisted package", () => {
    const swap = (from: string, to: string) => checkPyproject(PYPROJECT, PYPROJECT.replace(from, to), { removed: [from], added: [to] }, updated);
    assert.equal(swap('"soupsieve>=2.9"', '"soupsieve2>=2.9"').ok, false);
    assert.equal(swap('"celery[redis]>=5.5.3"', '"celery[redis,sqs]>=5.5.3"').ok, false);
    assert.equal(swap('"django>=5.2.16,<6.0"', '"django>=5.2.17,<6.0"').ok, false, "django is not in Dependabot's list");
    const added = PYPROJECT.replace('    "soupsieve>=2.9",\n', '    "soupsieve>=2.9",\n    "evil>=1",\n');
    assert.equal(checkPyproject(PYPROJECT, added, { removed: [], added: ['    "evil>=1",'] }, updated).ok, false);
  });

  it("uv.lock: accepts version, sdist and wheels changes of the updated package", () => {
    assert.deepEqual(checkLock(lock("2.9", "0.15.11"), lock("2.9.1", "0.15.11"), updated, "pharmacyonduty").ok, true);
  });

  it("uv.lock: rejects a new package, a change to another package, or other fields", () => {
    const extra = `\n[[package]]\nname = "evil"\nversion = "1.0"\nsource = { registry = "https://pypi.org/simple" }\n`;
    assert.equal(checkLock(lock("2.9", "0.15.11"), lock("2.9.1", "0.15.11", extra), updated, "pharmacyonduty").ok, false);
    assert.equal(checkLock(lock("2.9", "0.15.11"), lock("2.9.1", "0.16.1"), updated, "pharmacyonduty").ok, false);
    const otherSource = lock("2.9.1", "0.15.11").replace(
      'name = "soupsieve"\nversion = "2.9.1"\nsource = { registry = "https://pypi.org/simple" }',
      'name = "soupsieve"\nversion = "2.9.1"\nsource = { registry = "https://evil.example/simple" }',
    );
    assert.equal(checkLock(lock("2.9", "0.15.11"), otherSource, updated, "pharmacyonduty").ok, false);
    const header = lock("2.9.1", "0.15.11").replace("revision = 3", "revision = 4");
    assert.equal(checkLock(lock("2.9", "0.15.11"), header, updated, "pharmacyonduty").ok, false);
  });
});

describe("helpers", () => {
  it("takes the highest tier", () => {
    assert.equal(maxTier("A", "C", "B"), "C");
    assert.equal(maxTier(), "A");
  });

  it("reads the proposed tier from the work order form", () => {
    assert.equal(proposedTierFrom("### Risk\n\nNo high-risk area\n\n### Proposed tier\n\nB (Onur reads a summary)\n"), "B");
    assert.equal(proposedTierFrom("### Proposed tier\n\n_No response_\n"), null);
  });

  it("parses git diff --numstat -z, including renames and binary files", () => {
    const raw = ["3\t1\tpharmacies/views.py", "0\t0\t", "old/name.py", "new/name.py", "-\t-\tstatic/logo.png", ""].join("\0");
    assert.deepEqual(parseNumstat(raw), [
      { oldPath: null, path: "pharmacies/views.py", added: 3, deleted: 1 },
      { oldPath: "old/name.py", path: "new/name.py", added: 0, deleted: 0 },
      { oldPath: null, path: "static/logo.png", added: 1, deleted: 1 },
    ]);
  });
});
