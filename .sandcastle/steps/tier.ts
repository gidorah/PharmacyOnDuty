// The tier rule from factory-design.md: plain code, no Claude.
//
// The final tier is the highest tier any of five checks gives. A check can
// only raise the tier, never lower it.
//   1. Risk map: a change touching a path in factory/risk-map.yml is tier C.
//   2. Kind of work: tier A exists only through an active standing rule in
//      factory/standing-rules.yml; otherwise the risk map's default tier.
//   3. Size: a diff above the size limit is at least tier B.
//   4. Reviewer findings: a finding in a `reviewer_findings` category raises
//      the change to tier C.
//   5. The work order's proposed tier.

import ignore from "ignore";
import type { Finding } from "./findings.ts";
import { checkLock, checkPyproject, devDependencies, normalizeName, runtimeDependencies } from "./version-only.ts";

export type Tier = "A" | "B" | "C";
const ORDER: Record<Tier, number> = { A: 0, B: 1, C: 2 };
export const maxTier = (...tiers: Tier[]): Tier => tiers.reduce((a, b) => (ORDER[b] > ORDER[a] ? b : a), "A");

export interface RiskArea {
  readonly name: string;
  readonly tier: Tier;
  readonly why: string;
  readonly when?: "any_change" | "existing_lines_changed";
  readonly waived_by_standing_rule?: string;
  readonly paths?: readonly string[];
  readonly planned_paths?: readonly string[];
  readonly optional_paths?: readonly string[];
}

export interface RiskMap {
  readonly default_tier: Tier;
  readonly areas: readonly RiskArea[];
  readonly reviewer_findings: { readonly raise_to: Tier; readonly categories: readonly string[] };
  readonly size_limit: { readonly max_changed_lines: number; readonly max_files: number };
}

export interface StandingRule {
  readonly id: string;
  readonly status: string;
  readonly tier: Tier;
  readonly match: {
    readonly author?: string;
    readonly ecosystem?: string;
    readonly allowed_updates?: readonly { readonly update_type: string; readonly dependencies: string }[];
    readonly files_only?: readonly string[];
    readonly version_only?: boolean;
  };
}

export interface ChangedFile {
  readonly path: string;
  /** The old path of a renamed file. */
  readonly oldPath: string | null;
  readonly added: number;
  readonly deleted: number;
}

export interface DependabotUpdate {
  readonly dependencyName: string;
  readonly updateType: string | null;
}

export interface DependabotMetadata {
  readonly ecosystem: string;
  readonly updates: readonly DependabotUpdate[];
}

export interface TierInput {
  readonly riskMap: RiskMap;
  readonly rules: readonly StandingRule[];
  readonly files: readonly ChangedFile[];
  readonly author: string;
  /** Null when the job had no Dependabot metadata (not a Dependabot event). */
  readonly dependabot: DependabotMetadata | null;
  /** Base and head contents of pyproject.toml and uv.lock, and pyproject's changed lines. */
  readonly manifests: {
    readonly pyproject: { readonly base: string; readonly head: string } | null;
    readonly lock: { readonly base: string; readonly head: string } | null;
    readonly pyprojectLines: { readonly removed: readonly string[]; readonly added: readonly string[] };
    readonly projectName: string;
  };
  /** Every review finding since Onur's last restart. */
  readonly findings: readonly Finding[];
  /** The work order's proposed tier, if it has one. */
  readonly proposedTier: Tier | null;
}

export interface CheckResult {
  readonly check: string;
  readonly tier: Tier;
  readonly why: readonly string[];
}

export interface TierResult {
  readonly tier: Tier;
  /** The standing rule that applied, when the result is tier A. */
  readonly rule: string | null;
  readonly checks: readonly CheckResult[];
  readonly changedLines: number;
}

const patternsOf = (area: RiskArea): string[] => [
  ...(area.paths ?? []),
  ...(area.planned_paths ?? []),
  ...(area.optional_paths ?? []),
];

export const touchedPaths = (files: readonly ChangedFile[]): string[] =>
  files.flatMap((f) => (f.oldPath && f.oldPath !== f.path ? [f.oldPath, f.path] : [f.path]));

/** Areas a change touches, and the files that touch each. */
export const riskHits = (
  map: RiskMap,
  files: readonly ChangedFile[],
): { area: RiskArea; files: string[] }[] =>
  map.areas.flatMap((area) => {
    const matcher = ignore().add(patternsOf(area));
    const hits = files
      .filter((f) => (area.when === "existing_lines_changed" ? f.deleted > 0 : true))
      .flatMap((f) => (f.oldPath && f.oldPath !== f.path ? [f.oldPath, f.path] : [f.path]))
      .filter((p) => matcher.ignores(p));
    return hits.length > 0 ? [{ area, files: [...new Set(hits)] }] : [];
  });

export interface RuleMatch {
  readonly id: string;
  readonly matched: boolean;
  readonly why: readonly string[];
}

/** Check one standing rule. Fields this code does not know make it fail. */
export const matchRule = (rule: StandingRule, input: TierInput): RuleMatch => {
  const misses: string[] = [];
  const evidence: string[] = [];
  const known = new Set(["author", "ecosystem", "allowed_updates", "files_only", "version_only"]);
  const unknown = Object.keys(rule.match).filter((k) => !known.has(k));
  if (unknown.length > 0) misses.push(`the tier job does not know the conditions ${unknown.join(", ")}`);
  const m = rule.match;

  if (m.author !== undefined) {
    if (input.author === m.author) evidence.push(`author is ${m.author}`);
    else misses.push(`author is ${input.author}, not ${m.author}`);
  }

  const dependabot = input.dependabot;
  if (m.ecosystem !== undefined || m.allowed_updates !== undefined) {
    if (!dependabot) misses.push("no Dependabot metadata for this run");
    else if (m.ecosystem !== undefined && dependabot.ecosystem !== m.ecosystem) {
      misses.push(`ecosystem is ${dependabot.ecosystem}, not ${m.ecosystem}`);
    }
  }

  const updated = new Set((dependabot?.updates ?? []).map((u) => normalizeName(u.dependencyName)));
  if (m.allowed_updates !== undefined && dependabot) {
    if (dependabot.updates.length === 0) misses.push("Dependabot listed no updated dependencies");
    const pyprojectBase = input.manifests.pyproject?.base;
    const dev = pyprojectBase ? devDependencies(pyprojectBase) : new Set<string>();
    // A package in both lists also runs in production, so it counts as a
    // runtime dependency: S0-6 keeps minor updates of those at tier C.
    const runtime = pyprojectBase ? runtimeDependencies(pyprojectBase) : new Set<string>();
    for (const u of dependabot.updates) {
      const name = normalizeName(u.dependencyName);
      const fits = m.allowed_updates.some((allowed) => {
        if (allowed.update_type !== u.updateType) return false;
        if (allowed.dependencies === "any") return true;
        if (allowed.dependencies === "[dependency-groups].dev in pyproject.toml") return dev.has(name) && !runtime.has(name);
        return false;
      });
      if (fits) evidence.push(`${u.dependencyName}: ${u.updateType}${u.updateType?.endsWith("minor") ? " of a dev dependency" : ""}`);
      else misses.push(`${u.dependencyName}: ${u.updateType ?? "unknown update type"} is not allowed by the rule`);
    }
  }

  if (m.files_only !== undefined) {
    const others = touchedPaths(input.files).filter((p) => !m.files_only?.includes(p));
    if (others.length > 0) misses.push(`it changes other files: ${others.slice(0, 5).join(", ")}`);
    else evidence.push(`only ${m.files_only.join(" and ")} changed`);
  }

  if (m.version_only) {
    const { pyproject, lock, pyprojectLines, projectName } = input.manifests;
    const touched = new Set(touchedPaths(input.files));
    const checks = [
      touched.has("pyproject.toml")
        ? pyproject
          ? checkPyproject(pyproject.base, pyproject.head, pyprojectLines, updated)
          : { ok: false, why: "pyproject.toml changed but could not be read" }
        : null,
      touched.has("uv.lock")
        ? lock
          ? checkLock(lock.base, lock.head, updated, projectName)
          : { ok: false, why: "uv.lock changed but could not be read" }
        : null,
    ].filter((c) => c !== null);
    for (const c of checks) (c.ok ? evidence : misses).push(c.why);
  }

  return { id: rule.id, matched: misses.length === 0, why: misses.length === 0 ? evidence : misses };
};

export const computeTier = (input: TierInput): TierResult => {
  const { riskMap } = input;
  const active = input.rules.filter((r) => r.status === "active");
  const matches = active.map((r) => matchRule(r, input));
  const rule = matches.find((m) => m.matched) ?? null;
  const ruleTier = rule ? (active.find((r) => r.id === rule.id)?.tier ?? riskMap.default_tier) : riskMap.default_tier;

  // Check 2 first: it sets the starting point.
  const kind: CheckResult = {
    check: "2. Kind of work",
    tier: ruleTier,
    why: rule
      ? [`Standing rule \`${rule.id}\` matches: ${rule.why.join("; ")}.`]
      : matches.length > 0
        ? matches.map((m) => `Standing rule \`${m.id}\` does not match: ${m.why.join("; ")}.`)
        : ["No active standing rule."],
  };

  const hits = riskHits(riskMap, input.files).filter(
    (h) => !(rule && h.area.waived_by_standing_rule === rule.id),
  );
  const waived = rule
    ? riskMap.areas.filter((a) => a.waived_by_standing_rule === rule.id).map((a) => a.name)
    : [];
  const risk: CheckResult = {
    check: "1. Risk map",
    tier: maxTier("A", ...hits.map((h) => h.area.tier)),
    why: [
      ...(hits.length === 0 ? ["No high-risk path."] : hits.map((h) => `${h.area.name} (${h.area.tier}): ${h.files.join(", ")}`)),
      ...(waived.length > 0 ? [`Waived by \`${rule?.id}\`: ${waived.join(", ")}.`] : []),
    ],
  };

  const changedLines = input.files.reduce((n, f) => n + f.added + f.deleted, 0);
  const limit = riskMap.size_limit;
  const tooBig = changedLines > limit.max_changed_lines || input.files.length > limit.max_files;
  const size: CheckResult = {
    check: "3. Size",
    tier: tooBig ? "B" : "A",
    why: [
      `${input.files.length} file(s), ${changedLines} changed line(s); the limit is ${limit.max_files} files and ${limit.max_changed_lines} lines${tooBig ? ", so at least tier B" : ""}.`,
    ],
  };

  const highRisk = input.findings.filter((f) => riskMap.reviewer_findings.categories.includes(f.category));
  const findings: CheckResult = {
    check: "4. Reviewer findings",
    tier: highRisk.length > 0 ? riskMap.reviewer_findings.raise_to : "A",
    why:
      highRisk.length > 0
        ? highRisk.map((f) => `${f.id} is a ${f.category} finding.`)
        : [`No finding in a high-risk category (${input.findings.length} finding(s) in all).`],
  };

  const proposal: CheckResult = {
    check: "5. Proposed tier",
    tier: input.proposedTier ?? "A",
    why: [input.proposedTier ? `The work order proposes tier ${input.proposedTier}.` : "No proposed tier."],
  };

  const checks = [risk, kind, size, findings, proposal];
  const tier = maxTier(...checks.map((c) => c.tier));
  return { tier, rule: tier === "A" && rule ? rule.id : null, checks, changedLines };
};

/** The tier the work order's "Proposed tier" field names. */
export const proposedTierFrom = (issueBody: string): Tier | null => {
  const m = /^###\s+Proposed tier\s*\n+\s*([ABC])\b/m.exec(issueBody);
  return m ? (m[1] as Tier) : null;
};

/** `git diff --numstat -z -M` entries. Binary files count as one line. */
export const parseNumstat = (raw: string): ChangedFile[] => {
  const parts = raw.split("\0");
  const files: ChangedFile[] = [];
  for (let i = 0; i < parts.length; i++) {
    const head = parts[i];
    if (!head) continue;
    const [a, d, p] = head.split("\t");
    const count = (x: string | undefined) => (x === "-" || x === undefined ? 1 : Number(x));
    if (p === "") {
      files.push({ oldPath: parts[i + 1] ?? null, path: parts[i + 2] ?? "", added: count(a), deleted: count(d) });
      i += 2;
    } else {
      files.push({ oldPath: null, path: p ?? "", added: count(a), deleted: count(d) });
    }
  }
  return files;
};
