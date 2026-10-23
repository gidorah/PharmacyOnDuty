"""Fail a change that removes or skips tests, compared with a base commit.

The factory gate runs this script on every pull request. It reads both commits
with git and compares them statically, without running any test code. It fails
when the change does any of the following:

1. Deletes a test file, or renames it to a name pytest no longer collects.
2. Removes a test function or method, or renames it.
3. Adds a skip or xfail: a marker, a decorator, a ``pytestmark`` assignment, or
   a call such as ``pytest.skip()`` in a test file or ``conftest.py``.
4. Changes what pytest collects: the ``[tool.pytest.ini_options]`` table in
   ``pyproject.toml``, a new pytest config file, or new collection hooks such as
   ``collect_ignore`` in a ``conftest.py``.
5. Adds a test to ``.github/factory-gate-known-failures.txt``, which the gate
   runs as an expected failure. The change that creates the file is exempt.

Usage:
    python .github/scripts/check_test_removal.py --base <ref> [--head <ref>]

The script compares the head with the merge base of the two refs, so changes
that landed on the base branch after the head branched off are not counted.
It exits with 1 when it finds a problem, and with 2 when git fails.

With ``--approved REASON`` it reports the same findings as accepted and exits
with 0. The gate passes it only when override_label.py found Onur's approval.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import subprocess
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import PurePosixPath

# Kept in step with `python_files` in pyproject.toml. The script uses its own
# copy so that changing the pytest config cannot hide a deleted test file.
TEST_FILE_PATTERNS = ("test_*.py", "*_tests.py", "tests.py")
TEST_FUNCTION_PREFIX = "test"
TEST_CLASS_PREFIX = "Test"

# Names that skip a test or expect it to fail, in pytest and unittest.
SKIP_NAMES = frozenset(
    {
        "skip",
        "skipif",
        "xfail",
        "importorskip",
        "skipTest",
        "skipIf",
        "skipUnless",
        "expectedFailure",
        "SkipTest",
    }
)

# Names in conftest.py that change which tests pytest collects or runs.
COLLECTION_HOOK_NAMES = frozenset(
    {
        "collect_ignore",
        "collect_ignore_glob",
        "pytest_collection_modifyitems",
        "pytest_ignore_collect",
        "pytest_collect_file",
        "pytest_deselected",
        "pytest_pycollect_makeitem",
    }
)

# pytest reads these before pyproject.toml, so adding one can replace the
# project's pytest settings.
PYTEST_CONFIG_FILES = ("pytest.ini", ".pytest.ini", "tox.ini", "setup.cfg")

# The gate runs tests listed here as expected failures.
KNOWN_FAILURES_FILE = ".github/factory-gate-known-failures.txt"


@dataclass
class Finding:
    path: str
    line: int
    message: str


@dataclass
class FileScan:
    """What the script found in one Python file at one commit."""

    tests: dict[str, int] = field(default_factory=dict)
    skips: Counter[tuple[str, str]] = field(default_factory=Counter)
    skip_lines: dict[tuple[str, str], int] = field(default_factory=dict)
    hooks: Counter[str] = field(default_factory=Counter)
    hook_lines: dict[str, int] = field(default_factory=dict)
    syntax_error: str | None = None


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"git {' '.join(args)} failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(2)
    return result.stdout


def is_test_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return any(fnmatch.fnmatch(name, pattern) for pattern in TEST_FILE_PATTERNS)


def is_conftest(path: str) -> bool:
    return PurePosixPath(path).name == "conftest.py"


def list_files(commit: str) -> set[str]:
    return set(git("ls-tree", "-r", "--name-only", commit).splitlines())


def read_file(commit: str, path: str) -> str:
    return git("show", f"{commit}:{path}")


def names_in(node: ast.AST) -> set[str]:
    """Return every bare name and attribute name used inside a node."""
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            found.add(child.id)
        elif isinstance(child, ast.Attribute):
            found.add(child.attr)
    return found


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


class Scanner(ast.NodeVisitor):
    """Collect test names, skip markers and collection hooks in one module."""

    def __init__(self, scan: FileScan, collect_tests: bool) -> None:
        self.scan = scan
        self.collect_tests = collect_tests
        self.scope: list[str] = []

    def qualname(self) -> str:
        return "::".join(self.scope) or "<module>"

    def add_skip(self, kind: str, line: int) -> None:
        key = (self.qualname(), kind)
        self.scan.skips[key] += 1
        self.scan.skip_lines.setdefault(key, line)

    def check_decorators(self, decorators: list[ast.expr]) -> None:
        for decorator in decorators:
            for name in sorted(names_in(decorator) & SKIP_NAMES):
                self.add_skip(f"decorator {name}", decorator.lineno)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.check_decorators(node.decorator_list)
        self.visit_without_decorators(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_function(node)

    def visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not self.scope and node.name in COLLECTION_HOOK_NAMES:
            self.add_hook(node.name, node.lineno)
        self.scope.append(node.name)
        if self.collect_tests and self.is_test(node.name):
            self.scan.tests[self.qualname()] = node.lineno
        self.check_decorators(node.decorator_list)
        self.visit_without_decorators(node)
        self.scope.pop()

    def visit_without_decorators(
        self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        # check_decorators already counted the decorators. Visiting them again
        # would count `@pytest.mark.skipif(...)` a second time, as a call.
        for name, value in ast.iter_fields(node):
            if name == "decorator_list":
                continue
            children = value if isinstance(value, list) else [value]
            for child in children:
                if isinstance(child, ast.AST):
                    self.visit(child)

    def is_test(self, function_name: str) -> bool:
        if not function_name.startswith(TEST_FUNCTION_PREFIX):
            return False
        # Module-level test functions, and methods of classes whose name pytest
        # collects. unittest.TestCase subclasses with other names are rare
        # here; they are still caught by the file and skip checks.
        return len(self.scope) == 1 or self.scope[-2].startswith(TEST_CLASS_PREFIX)

    def visit_Call(self, node: ast.Call) -> None:
        name = call_name(node)
        if name in SKIP_NAMES:
            self.add_skip(f"call {name}()", node.lineno)
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        if node.exc is not None and names_in(node.exc) & SKIP_NAMES:
            # Count `raise SkipTest(...)` once, not again as a call.
            self.add_skip("raise SkipTest", node.lineno)
            return
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if not self.check_assignment(node.targets, node.value, node.lineno):
            self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is None or not self.check_assignment(
            [node.target], node.value, node.lineno
        ):
            self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if not self.check_assignment([node.target], node.value, node.lineno):
            self.generic_visit(node)

    def check_assignment(
        self, targets: list[ast.expr], value: ast.expr, line: int
    ) -> bool:
        """Count skip marks and hooks in an assignment.

        Returns True for a ``pytestmark`` assignment, whose value the caller
        must not visit again.
        """
        target_names = {t.id for t in targets if isinstance(t, ast.Name)}
        if not self.scope:
            for name in sorted(target_names & COLLECTION_HOOK_NAMES):
                self.add_hook(name, line)
        if "pytestmark" not in target_names:
            return False
        for name in sorted(names_in(value) & SKIP_NAMES):
            self.add_skip(f"pytestmark {name}", line)
        return True

    def add_hook(self, name: str, line: int) -> None:
        self.scan.hooks[name] += 1
        self.scan.hook_lines.setdefault(name, line)


def scan_source(source: str, path: str) -> FileScan:
    scan = FileScan()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        scan.syntax_error = f"{error.msg} (line {error.lineno})"
        return scan
    Scanner(scan, collect_tests=is_test_file(path)).visit(tree)
    return scan


def renamed_paths(base: str, head: str) -> dict[str, str]:
    """Map each renamed file's old path to its new path."""
    renames: dict[str, str] = {}
    output = git("diff", "--name-status", "-M", base, head)
    for line in output.splitlines():
        parts = line.split("\t")
        if parts[0].startswith("R") and len(parts) == 3:
            renames[parts[1]] = parts[2]
    return renames


def known_failures(commit: str, files: set[str]) -> set[str]:
    if KNOWN_FAILURES_FILE not in files:
        return set()
    node_ids: set[str] = set()
    for line in read_file(commit, KNOWN_FAILURES_FILE).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            node_ids.add(line.partition("|")[0].strip())
    return node_ids


def pytest_table(commit: str, files: set[str]) -> object:
    if "pyproject.toml" not in files:
        return None
    try:
        data = tomllib.loads(read_file(commit, "pyproject.toml"))
    except tomllib.TOMLDecodeError as error:
        return f"<invalid TOML: {error}>"
    tool = data.get("tool", {})
    pytest_config = tool.get("pytest", {}) if isinstance(tool, dict) else {}
    if isinstance(pytest_config, dict):
        return pytest_config.get("ini_options")
    return pytest_config


def compare(base: str, head: str) -> list[Finding]:
    findings: list[Finding] = []
    base_files = list_files(base)
    head_files = list_files(head)
    renames = renamed_paths(base, head)

    def watched(path: str) -> bool:
        return is_test_file(path) or is_conftest(path)

    for base_path in sorted(p for p in base_files if watched(p)):
        head_path = renames.get(base_path, base_path)
        base_scan = scan_source(read_file(base, base_path), base_path)

        if head_path not in head_files:
            if is_test_file(base_path):
                findings.append(Finding(base_path, 1, "Test file deleted."))
            continue
        if is_test_file(base_path) and not is_test_file(head_path):
            findings.append(
                Finding(
                    head_path,
                    1,
                    f"Test file renamed from {base_path} to a name pytest "
                    "does not collect.",
                )
            )
            continue

        head_scan = scan_source(read_file(head, head_path), head_path)
        if head_scan.syntax_error is not None:
            findings.append(
                Finding(
                    head_path,
                    1,
                    "Cannot parse the file, so its tests cannot be checked: "
                    f"{head_scan.syntax_error}.",
                )
            )
            continue
        findings.extend(compare_scans(head_path, base_scan, head_scan))

    for head_path in sorted(p for p in head_files if watched(p)):
        if head_path in base_files or head_path in renames.values():
            continue
        head_scan = scan_source(read_file(head, head_path), head_path)
        if head_scan.syntax_error is not None:
            continue
        findings.extend(compare_scans(head_path, FileScan(), head_scan))

    for config_file in PYTEST_CONFIG_FILES:
        if config_file in head_files and (
            config_file not in base_files
            or read_file(base, config_file) != read_file(head, config_file)
        ):
            findings.append(
                Finding(
                    config_file,
                    1,
                    "Pytest config file added or changed. pytest may read it "
                    "instead of pyproject.toml.",
                )
            )

    # The change that creates the list is the one exception: it records the
    # failures found when the gate was added, and Onur reviews it as tier C.
    base_known = known_failures(base, base_files)
    if KNOWN_FAILURES_FILE not in base_files:
        base_known = known_failures(head, head_files)
    for node_id in sorted(known_failures(head, head_files) - base_known):
        findings.append(
            Finding(
                KNOWN_FAILURES_FILE,
                1,
                f"Test added to the known-failures list: {node_id}.",
            )
        )

    if pytest_table(base, base_files) != pytest_table(head, head_files):
        findings.append(
            Finding(
                "pyproject.toml",
                1,
                "[tool.pytest.ini_options] changed, which can change which "
                "tests pytest collects or runs.",
            )
        )

    return findings


def compare_scans(path: str, base: FileScan, head: FileScan) -> list[Finding]:
    findings: list[Finding] = []
    for name, line in sorted(base.tests.items(), key=lambda item: item[1]):
        if name not in head.tests:
            findings.append(
                Finding(
                    path,
                    line,
                    f"Test removed or renamed: {name} (line {line} in the base).",
                )
            )
    for key, count in sorted((head.skips - base.skips).items()):
        where, kind = key
        findings.append(
            Finding(
                path,
                head.skip_lines[key],
                f"Skip or xfail added ({kind}, {count}x) in {where}.",
            )
        )
    for name, count in sorted((head.hooks - base.hooks).items()):
        findings.append(
            Finding(
                path,
                head.hook_lines[name],
                f"Collection hook added: {name} ({count}x). It can change "
                "which tests run.",
            )
        )
    return findings


def write_summary(
    findings: list[Finding], base: str, head: str, approval: str | None
) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        "## Test-removal check",
        "",
        f"Compared `{head[:12]}` with merge base `{base[:12]}`.",
        "",
    ]
    if findings and approval:
        lines += [f"**Accepted removals.** {approval}", ""]
    elif findings:
        lines += [f"**Failed.** {approval_hint()}", ""]
    if findings:
        lines.append("| File | Line | Change |")
        lines.append("|---|---|---|")
        for finding in findings:
            message = finding.message.replace("|", "\\|")
            lines.append(f"| `{finding.path}` | {finding.line} | {message} |")
    else:
        lines.append("No tests removed or skipped.")
    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.write("\n".join(lines) + "\n")


def approval_hint() -> str:
    return (
        "To accept these changes, Onur (gidorah) adds the allow-test-removal "
        "label to the pull request after the last commit. New commits need the "
        "label added again."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail a change that removes or skips tests."
    )
    parser.add_argument("--base", required=True, help="Base branch or commit.")
    parser.add_argument("--head", default="HEAD", help="Head commit.")
    parser.add_argument(
        "--approved",
        metavar="REASON",
        help="Accept the findings, citing this approval from override_label.py.",
    )
    args = parser.parse_args()

    head = git("rev-parse", args.head).strip()
    base = git("merge-base", args.base, head).strip()
    findings = compare(base, head)
    level = "notice" if args.approved else "error"

    for finding in findings:
        print(f"::{level} file={finding.path},line={finding.line}::{finding.message}")
    write_summary(findings, base, head, args.approved)

    if findings and args.approved:
        print(f"\n{len(findings)} change(s) accepted: {args.approved}")
        return 0
    if findings:
        print(
            f"\n{len(findings)} problem(s) found. This check fails any change "
            f"that removes or skips tests. {approval_hint()}"
        )
        return 1
    print(f"No tests removed or skipped between {base[:12]} and {head[:12]}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
