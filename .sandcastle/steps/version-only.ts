// The `version_only_check` of the Dependabot standing rule
// (factory/standing-rules.yml): did a change touch only version numbers in
// pyproject.toml and uv.lock? Plain code, and strict: anything it does not
// recognise fails the check, and pyproject.toml and uv.lock then make the
// change tier C through the risk map.

import { parse } from "smol-toml";

/** PEP 503 name normalisation: lowercase, runs of `-_.` become `-`. */
export const normalizeName = (name: string): string => name.toLowerCase().replace(/[-_.]+/g, "-");

export interface Requirement {
  readonly name: string;
  /** Extras and markers: everything that must stay the same. */
  readonly identity: string;
  readonly specifier: string;
}

const PEP508 = /^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*([^;]*?)\s*(;.*)?$/;

export const parseRequirement = (text: string): Requirement | null => {
  const m = PEP508.exec(text);
  if (!m || !m[1]) return null;
  const name = normalizeName(m[1]);
  const extras = (m[2] ?? "").replace(/\s+/g, "");
  const markers = (m[4] ?? "").replace(/\s+/g, " ").trim();
  return { name, identity: `${name}${extras}${markers}`, specifier: (m[3] ?? "").replace(/\s+/g, "") };
};

type Toml = Record<string, unknown>;

const sameJson = (a: unknown, b: unknown): boolean => JSON.stringify(a) === JSON.stringify(b);

const requirementNames = (list: unknown): Set<string> => {
  const names = new Set<string>();
  if (Array.isArray(list)) {
    for (const entry of list) {
      const req = typeof entry === "string" ? parseRequirement(entry) : null;
      if (req) names.add(req.name);
    }
  }
  return names;
};

/** Names in `[dependency-groups].dev`, read from pyproject.toml on the base commit. */
export const devDependencies = (pyproject: string): Set<string> =>
  requirementNames(((parse(pyproject) as Toml)["dependency-groups"] as Toml | undefined)?.dev);

/** Names in `[project].dependencies`: what runs in production. */
export const runtimeDependencies = (pyproject: string): Set<string> =>
  requirementNames(((parse(pyproject) as Toml).project as Toml | undefined)?.dependencies);

export interface VersionCheck {
  readonly ok: boolean;
  readonly why: string;
}

const pass = (why: string): VersionCheck => ({ ok: true, why });
const failCheck = (why: string): VersionCheck => ({ ok: false, why });

/** The dependency lists that may change: `[project].dependencies` and every `[dependency-groups]` list. */
const dependencyLists = (data: Toml): Map<string, unknown[]> => {
  const lists = new Map<string, unknown[]>();
  const project = data.project as Toml | undefined;
  if (Array.isArray(project?.dependencies)) lists.set("project.dependencies", project.dependencies);
  const groups = data["dependency-groups"] as Toml | undefined;
  for (const [name, list] of Object.entries(groups ?? {})) {
    if (Array.isArray(list)) lists.set(`dependency-groups.${name}`, list);
  }
  return lists;
};

const withoutDependencyLists = (data: Toml): Toml => {
  const copy = structuredClone(data);
  const project = copy.project as Toml | undefined;
  if (project) delete project.dependencies;
  delete copy["dependency-groups"];
  return copy;
};

const DEPENDENCY_LINE = /^\s*"[^"]+",?\s*$/;

/**
 * pyproject.toml: every changed line is a dependency line in
 * `[project].dependencies` or `[dependency-groups]`; the removed and added
 * entries name the same packages, and only the version specifiers differ.
 */
export const checkPyproject = (
  base: string,
  head: string,
  changedLines: { readonly removed: readonly string[]; readonly added: readonly string[] },
  updated: ReadonlySet<string>,
): VersionCheck => {
  if (changedLines.removed.length !== changedLines.added.length) {
    return failCheck("pyproject.toml: lines were added or removed, not only changed.");
  }
  const odd = [...changedLines.removed, ...changedLines.added].find((l) => !DEPENDENCY_LINE.test(l));
  if (odd !== undefined) return failCheck(`pyproject.toml: a changed line is not a dependency entry: \`${odd.trim()}\``);
  let b: Toml;
  let h: Toml;
  try {
    b = parse(base) as Toml;
    h = parse(head) as Toml;
  } catch (error) {
    return failCheck(`pyproject.toml does not parse: ${String(error).slice(0, 200)}`);
  }
  if (!sameJson(withoutDependencyLists(b), withoutDependencyLists(h))) {
    return failCheck("pyproject.toml: something outside the dependency lists changed.");
  }
  const baseLists = dependencyLists(b);
  const headLists = dependencyLists(h);
  if (!sameJson([...baseLists.keys()], [...headLists.keys()])) {
    return failCheck("pyproject.toml: a dependency list was added or removed.");
  }
  const changed: string[] = [];
  for (const [key, baseList] of baseLists) {
    const headList = headLists.get(key) ?? [];
    if (baseList.length !== headList.length) return failCheck(`pyproject.toml: ${key} gained or lost an entry.`);
    for (let i = 0; i < baseList.length; i++) {
      const before = typeof baseList[i] === "string" ? parseRequirement(baseList[i] as string) : null;
      const after = typeof headList[i] === "string" ? parseRequirement(headList[i] as string) : null;
      if (!before || !after) return failCheck(`pyproject.toml: ${key} has an entry that is not a plain requirement.`);
      if (before.identity !== after.identity) {
        return failCheck(`pyproject.toml: ${key} entry ${i + 1} changed package, extras or markers.`);
      }
      if (before.specifier !== after.specifier) changed.push(before.name);
    }
  }
  const unexpected = changed.filter((n) => !updated.has(n));
  if (unexpected.length > 0) {
    return failCheck(`pyproject.toml: versions changed for packages Dependabot did not list: ${unexpected.join(", ")}.`);
  }
  return pass(changed.length > 0 ? `pyproject.toml: only the version specifiers of ${changed.join(", ")} changed.` : "pyproject.toml: unchanged.");
};

interface LockPackage extends Toml {
  readonly name: string;
}

const lockPackages = (data: Toml): LockPackage[] =>
  (Array.isArray(data.package) ? data.package : []) as LockPackage[];

/** The fields a version update may change in an updated package's entry. */
const VERSION_FIELDS = ["version", "sdist", "wheels"];

const strip = (pkg: Toml, fields: readonly string[]): Toml => {
  const copy = structuredClone(pkg);
  for (const field of fields) delete copy[field];
  return copy;
};

/** In the root package, blank the specifiers of the updated dependencies. */
const normalizeRoot = (pkg: Toml, updated: ReadonlySet<string>): Toml => {
  const copy = structuredClone(pkg);
  const blank = (list: unknown) => {
    if (!Array.isArray(list)) return;
    for (const entry of list as Toml[]) {
      if (typeof entry?.name === "string" && updated.has(normalizeName(entry.name)) && "specifier" in entry) {
        entry.specifier = "(updated)";
      }
    }
  };
  const metadata = copy.metadata as Toml | undefined;
  blank(metadata?.["requires-dist"]);
  for (const group of Object.values((metadata?.["requires-dev"] as Toml | undefined) ?? {})) blank(group);
  return copy;
};

/**
 * uv.lock: no `[[package]]` entry is added or removed; only the entries of
 * the updated dependencies change, and in them only `version`, `sdist` and
 * `wheels`. In the project's own entry only the updated dependencies'
 * specifiers change.
 */
export const checkLock = (
  base: string,
  head: string,
  updated: ReadonlySet<string>,
  projectName: string,
): VersionCheck => {
  let b: Toml;
  let h: Toml;
  try {
    b = parse(base) as Toml;
    h = parse(head) as Toml;
  } catch (error) {
    return failCheck(`uv.lock does not parse: ${String(error).slice(0, 200)}`);
  }
  if (!sameJson(strip(b, ["package"]), strip(h, ["package"]))) {
    return failCheck("uv.lock: the lock file's header (version, revision, markers or options) changed.");
  }
  const group = (data: Toml) => {
    const map = new Map<string, LockPackage[]>();
    for (const p of lockPackages(data)) {
      const key = normalizeName(String(p.name));
      map.set(key, [...(map.get(key) ?? []), p]);
    }
    return map;
  };
  const before = group(b);
  const after = group(h);
  const added = [...after.keys()].filter((k) => !before.has(k));
  const removed = [...before.keys()].filter((k) => !after.has(k));
  if (added.length || removed.length) {
    return failCheck(`uv.lock: packages added (${added.join(", ") || "none"}) or removed (${removed.join(", ") || "none"}).`);
  }
  const root = normalizeName(projectName);
  const changed: string[] = [];
  for (const [name, olds] of before) {
    const news = after.get(name) ?? [];
    if (olds.length !== news.length) return failCheck(`uv.lock: the number of entries for ${name} changed.`);
    for (let i = 0; i < olds.length; i++) {
      const o = olds[i] as LockPackage;
      const n = news[i] as LockPackage;
      if (sameJson(o, n)) continue;
      changed.push(name);
      if (name === root) {
        if (!sameJson(normalizeRoot(o, updated), normalizeRoot(n, updated))) {
          return failCheck(`uv.lock: the project's own entry changed beyond the updated dependencies' specifiers.`);
        }
      } else if (!updated.has(name)) {
        return failCheck(`uv.lock: ${name} changed, but Dependabot did not list it as updated.`);
      } else if (!sameJson(strip(o, VERSION_FIELDS), strip(n, VERSION_FIELDS))) {
        return failCheck(`uv.lock: ${name} changed in more than its version, sdist and wheels.`);
      }
    }
  }
  return pass(`uv.lock: only the version, sdist and wheels of ${changed.filter((n) => n !== root).join(", ") || "no package"} changed.`);
};
