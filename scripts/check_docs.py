"""Check that the Markdown docs still match the repo.

Scans every ``*.md`` file (except the ADRs ``docs/decisions/0*.md``, which are
records of their time) and prints each failure as ``file:line: what is wrong``.
It exits non-zero when there is any. The checks:

1. a backticked repo path exists, from the file's folder or the repo root; a
   bare file name (``models.py``) may be anywhere in the tree;
2. every ``just <recipe>`` is a ``justfile`` recipe;
3. every ``manage.py <command>`` / ``just manage <command>`` is a Django command;
4. every relative Markdown link resolves, ``#anchor`` included;
5. root ``AGENTS.md`` is at most 100 lines, an area ``AGENTS.md`` at most 50.

Standard library only, and it walks the tree rather than asking git, so it runs
in CI's lint job where there is no ``.git``. Run: ``python scripts/check_docs.py``.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "staticfiles",
    "htmlcov",
}
AGENT_FILES = {"AGENTS.md", "CLAUDE.md"}
ROOT_LINE_LIMIT = 100
AREA_LINE_LIMIT = 50
FILE_EXTENSIONS = {
    ".py",
    ".md",
    ".yml",
    ".yaml",
    ".sh",
    ".toml",
    ".json",
    ".js",
    ".css",
    ".html",
    ".txt",
    ".conf",
    ".cfg",
    ".ini",
    ".env",
    ".lock",
    ".crt",
    ".sql",
}

# Deliberate non-paths that no general rule skips: token -> reason.
ALLOWED: dict[str, str] = {
    "flower.prod.eczanerede.onur.sh": "a host name, not a file",
}

_SHELL_COMMENT = re.compile(r"(^|\s)#.*$")
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_PATH_CHARS = re.compile(r"^[A-Za-z0-9._/~<>*:@-]+$")
_SYMBOL_SUFFIX = re.compile(r":\w+$")
_NODE_ID = re.compile(r"::.*$")
_RATE = re.compile(r"^\d+/[smhd]$")
_TIME_ZONE = re.compile(r"^[A-Z][a-z]+/[A-Z][A-Za-z_]+$")
_CODE_LIST = re.compile(r"^[A-Z0-9]+(/[A-Z0-9]+)+$")
_JUST_USE = re.compile(r"(?<![\w./-])just\s+([A-Za-z_][\w-]*)")
_MANAGE_USE = re.compile(r"manage\.py\s+([a-z][\w-]*)")
_JUST_MANAGE_USE = re.compile(r"(?<![\w./-])just\s+manage\s+[\"']?([a-z][\w-]*)")
_LINK = re.compile(r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
_REF_DEF = re.compile(r"^ {0,3}\[[^\]]+\]:\s*<?([^\s>]+)>?")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
_RECIPE = re.compile(r"""^@?([A-Za-z_][\w-]*)\b(?:[^:\n"']|"[^"]*"|'[^']*')*:(?!=)""")
_ALIAS = re.compile(r"^alias\s+([A-Za-z_][\w-]*)\s*:=")


class Tree:
    """The walked repo: Markdown files to check and every file/dir name."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.markdown: list[Path] = []
        self.names: set[str] = set()
        for folder, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            self.names.update(dirs)
            self.names.update(files)
            for name in sorted(files):
                path = Path(folder) / name
                if name.endswith(".md") and not self._is_adr(path):
                    self.markdown.append(path)

    def _is_adr(self, path: Path) -> bool:
        rel = path.relative_to(self.root)
        return rel.parent.as_posix() == "docs/decisions" and rel.name.startswith("0")


def parse_recipes(justfile: str) -> set[str]:
    """Recipe and alias names defined at column 0 of a justfile."""
    names: set[str] = set()
    for line in justfile.splitlines():
        if match := _RECIPE.match(line) or _ALIAS.match(line):
            names.add(match.group(1))
    return names


def heading_slugs(text: str) -> set[str]:
    """GitHub anchors for the headings of a Markdown text."""
    slugs: set[str] = set()
    seen: dict[str, int] = {}
    for line, in_fence in _lines(text):
        if in_fence:
            continue
        if match := _HEADING.match(line):
            slug = re.sub(r"[^\w\s-]", "", match.group(1).lower()).replace(" ", "-")
            count = seen.get(slug, 0)
            seen[slug] = count + 1
            slugs.add(slug if count == 0 else f"{slug}-{count}")
    return slugs


def _lines(text: str) -> list[tuple[str, bool]]:
    """Each line with whether it is inside (or is a marker of) a code fence."""
    out: list[tuple[str, bool]] = []
    fence = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = stripped[:3]
        if fence:
            out.append((line, True))
            if marker == fence:
                fence = ""
        elif marker in ("```", "~~~"):
            fence = marker
            out.append((line, True))
        else:
            out.append((line, False))
    return out


def _path_candidate(token: str) -> str | None:
    """The repo path a code span names, or None when it is not a path."""
    if token in ALLOWED or not _PATH_CHARS.match(token) or "://" in token:
        return None
    if token.startswith(("/", "~")) or any(c in token for c in "<>*"):
        return None
    if "NNNN" in token or _RATE.match(token) or _CODE_LIST.match(token):
        return None
    if _TIME_ZONE.match(token):
        return None
    token = _SYMBOL_SUFFIX.sub("", _NODE_ID.sub("", token))
    if "/" in token or Path(token).suffix in FILE_EXTENSIONS:
        return token
    return None


def _path_exists(tree: Tree, md_file: Path, token: str) -> bool:
    if "/" not in token:
        return token in tree.names
    return (md_file.parent / token).exists() or (tree.root / token).exists()


def _check_link(
    tree: Tree, md_file: Path, target: str, slug_cache: dict[Path, set[str]]
) -> str | None:
    if _SCHEME.match(target) or target.startswith("/"):
        return None
    path_part, _, anchor = unquote(target).partition("#")
    dest = (md_file.parent / path_part) if path_part else md_file
    if not dest.exists():
        return f"link target `{path_part}` does not exist"
    if anchor and dest.is_file() and dest.suffix == ".md":
        if dest not in slug_cache:
            slug_cache[dest] = heading_slugs(dest.read_text(encoding="utf-8"))
        if anchor.lower() not in slug_cache[dest]:
            where = path_part or dest.name
            return f"link anchor `#{anchor}` not found in {where}"
    return None


def _check_file(
    tree: Tree,
    md_file: Path,
    recipes: set[str],
    commands: set[str],
    slug_cache: dict[Path, set[str]],
) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    text = md_file.read_text(encoding="utf-8")
    for number, (line, in_fence) in enumerate(_lines(text), start=1):
        spans = [_SHELL_COMMENT.sub("", line)] if in_fence else _CODE_SPAN.findall(line)
        if not in_fence:
            for token in spans:
                path = _path_candidate(token)
                if path and not _path_exists(tree, md_file, path):
                    found.append((number, f"path `{token}` does not exist"))
        for chunk in spans:
            for name in _JUST_USE.findall(chunk):
                if name not in recipes:
                    found.append((number, f"`just {name}` is not a justfile recipe"))
            names = _MANAGE_USE.findall(chunk) + _JUST_MANAGE_USE.findall(chunk)
            for name in names:
                if name not in commands:
                    found.append((number, f"`{name}` is not a manage.py command"))
        if not in_fence:
            bare = _CODE_SPAN.sub(lambda m: " " * len(m.group()), line)
            targets = _LINK.findall(bare)
            if ref := _REF_DEF.match(line):
                targets.append(ref.group(1))
            for target in targets:
                problem = _check_link(tree, md_file, target, slug_cache)
                if problem:
                    found.append((number, problem))
    return found


def _check_length(rel: Path, text: str) -> list[tuple[int, str]]:
    if rel.name not in AGENT_FILES:
        return []
    limit = ROOT_LINE_LIMIT if len(rel.parts) == 1 else AREA_LINE_LIMIT
    count = len(text.splitlines())
    if count > limit:
        return [(limit + 1, f"{count} lines, over the limit of {limit}")]
    return []


def missing_own_commands(root: Path, listed: set[str]) -> list[str]:
    """The repo's own management commands that ``listed`` lacks."""
    own: set[str] = set()
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        here = Path(folder)
        if here.name == "commands" and here.parent.name == "management":
            own.update(
                f[:-3] for f in files if f.endswith(".py") and not f.startswith("_")
            )
    return sorted(own - listed)


def check_repo(root: Path, django_commands: set[str]) -> list[str]:
    """All doc failures under ``root`` as ``file:line: message`` strings."""
    tree = Tree(root)
    justfile = root / "justfile"
    recipes = (
        parse_recipes(justfile.read_text(encoding="utf-8"))
        if justfile.exists()
        else set()
    )
    slug_cache: dict[Path, set[str]] = {}
    failures: list[str] = []
    for md_file in tree.markdown:
        rel = md_file.relative_to(root)
        found = _check_file(tree, md_file, recipes, django_commands, slug_cache)
        found += _check_length(rel, md_file.read_text(encoding="utf-8"))
        found.sort(key=lambda item: item[0])
        failures += [f"{rel.as_posix()}:{n}: {msg}" for n, msg in found]
    return failures


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "manage.py", "help", "--commands"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1:] or ["no output"]
        print(f"check_docs: could not list Django commands: {detail[0]}")
        return 1
    listed = set(result.stdout.split())
    missing = missing_own_commands(root, listed)
    if missing:
        print(
            "check_docs: could not list Django commands: the project's own "
            f"commands ({', '.join(missing)}) are missing; did the settings load?"
        )
        return 1
    failures = check_repo(root, listed | {"help", "version"})
    for failure in failures:
        print(failure)
    if failures:
        return 1
    print("check_docs: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
