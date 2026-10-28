"""Keep docs/reference/environment.md in sync with the code that reads the env.

The code side is a static scan (no imports), so a new ``os.environ`` read, a new
shell variable or a new compose interpolation fails here until the reference
lists it. Commented ``# KEY=value`` lines in ``.env.example`` count as listed.
"""

import ast
import re
import unittest
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_PATH = REPO_ROOT / "docs" / "reference" / "environment.md"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"
READ_BY_CODE = "Read by the code"
READ_BY_COMPOSE = "Read by Docker Compose"
FIX_HINT = "Update docs/reference/environment.md in the same change."

PYTHON_SOURCES = [
    REPO_ROOT / "PharmacyOnDuty" / "settings.py",
    REPO_ROOT / "PharmacyOnDuty" / "database_config.py",
    *sorted((REPO_ROOT / "scripts").rglob("*.py")),
]
SHELL_SOURCES = sorted((REPO_ROOT / "scripts").rglob("*.sh"))
COMPOSE_SOURCES = [
    REPO_ROOT / "docker" / "dev" / "docker-compose.yml",
    REPO_ROOT / "docker" / "prod" / "services" / "docker-compose.yml",
    REPO_ROOT / "docker" / "prod" / "workers" / "docker-compose.yml",
]

# Helpers that take the variable name as a parameter. Their callers are resolved
# instead: ``_env_bool("X")`` by its first argument, ``_get_first_env_value``
# through the DATABASE_ENV_ALIASES constants.
ENV_HELPERS = {"_env_bool", "_get_first_env_value"}
ALIASES_CONSTANT = "DATABASE_ENV_ALIASES"
SHELL_BUILTINS = {"EUID", "UID", "HOME", "PATH", "PWD"}

_SHELL_VAR = re.compile(r"\$\{?([A-Z_][A-Z0-9_]*)")
_COMPOSE_VAR = re.compile(r"(?<!\$)\$\{([A-Z_][A-Z0-9_]*)")
_TABLE_FIRST_CELL = re.compile(r"^\|([^|]*)\|")
_BACKTICKED_NAME = re.compile(r"`([A-Z_][A-Z0-9_]*)`")
_ENV_EXAMPLE_KEY = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)=")


class DynamicEnvReadError(Exception):
    """An env read whose name is not a string constant, outside a known helper."""


def _is_os_environ(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _is_env_read(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id == "_env_bool"
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr == "getenv":
        return isinstance(func.value, ast.Name) and func.value.id == "os"
    return func.attr in {"get", "setdefault", "pop"} and _is_os_environ(func.value)


class _EnvScanner(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.names: set[str] = set()
        self._function_stack: list[str] = []

    def _record(self, name_node: ast.expr | None, line: int) -> None:
        if isinstance(name_node, ast.Constant) and isinstance(name_node.value, str):
            self.names.add(name_node.value)
        elif not set(self._function_stack) & ENV_HELPERS:
            raise DynamicEnvReadError(
                f"{self.filename}:{line}: env read with a non-constant name; "
                "use a string literal or teach this test about the helper."
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if _is_env_read(node):
            self._record(node.args[0] if node.args else None, node.lineno)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if _is_os_environ(node.value):
            self._record(node.slice, node.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._collect_aliases(node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._collect_aliases([node.target], node.value)
        self.generic_visit(node)

    def _collect_aliases(
        self, targets: Iterable[ast.expr], value: ast.expr | None
    ) -> None:
        if value is None or self._function_stack:
            return
        if any(isinstance(t, ast.Name) and t.id == ALIASES_CONSTANT for t in targets):
            # Only the dict values are env names; the keys are Django fields.
            nodes = value.values if isinstance(value, ast.Dict) else [value]
            self.names.update(
                n.value
                for node in nodes
                for n in ast.walk(node)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            )


def python_env_vars(source: str, filename: str = "<source>") -> set[str]:
    scanner = _EnvScanner(filename)
    scanner.visit(ast.parse(source, filename=filename))
    return scanner.names


def code_env_vars(paths: Iterable[Path]) -> set[str]:
    names: set[str] = set()
    for path in paths:
        text = path.read_text()
        if path.suffix == ".py":
            names |= python_env_vars(text, str(path.relative_to(REPO_ROOT)))
        else:
            names |= set(_SHELL_VAR.findall(text)) - SHELL_BUILTINS
    return names


def compose_env_vars(paths: Iterable[Path]) -> set[str]:
    names: set[str] = set()
    for path in paths:
        names |= set(_COMPOSE_VAR.findall(path.read_text()))
    return names


def reference_env_vars(markdown_text: str, section_heading: str) -> set[str]:
    names: set[str] = set()
    in_section = False
    for line in markdown_text.splitlines():
        if line.startswith("## "):
            in_section = line[3:].strip() == section_heading
        elif in_section and (cell := _TABLE_FIRST_CELL.match(line)):
            names.update(_BACKTICKED_NAME.findall(cell.group(1)))
    return names


def env_example_vars(text: str) -> set[str]:
    return {
        m.group(1) for line in text.splitlines() if (m := _ENV_EXAMPLE_KEY.match(line))
    }


def _drift_message(missing: set[str], stale: set[str], what: str) -> str:
    return (
        f"{what}. Not in the reference: {sorted(missing)}. "
        f"In the reference but not read: {sorted(stale)}. {FIX_HINT}"
    )


class TestEnvironmentReference(unittest.TestCase):
    @property
    def reference(self) -> str:
        return REFERENCE_PATH.read_text()

    def test_code_and_reference_list_the_same_variables(self) -> None:
        read = code_env_vars(PYTHON_SOURCES + SHELL_SOURCES)
        listed = reference_env_vars(self.reference, READ_BY_CODE)
        self.assertEqual(
            (read - listed, listed - read),
            (set(), set()),
            _drift_message(read - listed, listed - read, "Code and reference disagree"),
        )

    def test_compose_and_reference_list_the_same_variables(self) -> None:
        interpolated = compose_env_vars(COMPOSE_SOURCES)
        in_compose_section = reference_env_vars(self.reference, READ_BY_COMPOSE)
        in_code_section = reference_env_vars(self.reference, READ_BY_CODE)
        missing = interpolated - in_compose_section - in_code_section
        stale = in_compose_section - interpolated
        self.assertEqual(
            (missing, stale),
            (set(), set()),
            _drift_message(missing, stale, "Compose files and reference disagree"),
        )

    def test_env_example_keys_are_in_the_reference(self) -> None:
        keys = env_example_vars(ENV_EXAMPLE_PATH.read_text())
        listed = reference_env_vars(self.reference, READ_BY_CODE)
        listed |= reference_env_vars(self.reference, READ_BY_COMPOSE)
        self.assertEqual(
            keys - listed,
            set(),
            f".env.example has keys the reference lacks. {FIX_HINT}",
        )


class TestScanHelpers(unittest.TestCase):
    def test_python_scan_finds_every_read_form(self) -> None:
        source = (
            "import os\n"
            "a = os.environ.get('A')\n"
            "b = os.getenv('B', 'x')\n"
            "c = os.environ['C']\n"
            "os.environ.setdefault('D', 'x')\n"
            "os.environ.pop('E')\n"
            "f = _env_bool('F', default=True)\n"
        )
        self.assertEqual(python_env_vars(source), set("ABCDEF"))

    def test_helper_bodies_may_read_dynamic_names(self) -> None:
        source = (
            "import os\n"
            "DATABASE_ENV_ALIASES = {'NAME': ('DB_NAME', 'PGDATABASE')}\n"
            "def _get_first_env_value(*names):\n"
            "    return os.environ.get(names[0])\n"
            "def _env_bool(name, default):\n"
            "    return os.environ.get(name)\n"
        )
        self.assertEqual(python_env_vars(source), {"DB_NAME", "PGDATABASE"})

    def test_dynamic_read_outside_a_helper_raises(self) -> None:
        source = "import os\nname = 'X'\nvalue = os.environ.get(name)\n"
        with self.assertRaisesRegex(DynamicEnvReadError, r"<source>:3"):
            python_env_vars(source)

    def test_shell_scan_skips_builtins_and_lowercase_locals(self) -> None:
        path = Path(__file__).parent / "_shell_fixture.sh"
        path.write_text('x=$HOME\nif [ "$EUID" ]; then echo "${RUN_X:-1} $local"; fi\n')
        try:
            self.assertEqual(code_env_vars([path]), {"RUN_X"})
        finally:
            path.unlink()

    def test_compose_scan_ignores_escaped_dollars(self) -> None:
        path = Path(__file__).parent / "_compose_fixture.yml"
        path.write_text("a: ${PORT:-80}\nb: $${NOT_ME}\n")
        try:
            self.assertEqual(compose_env_vars([path]), {"PORT"})
        finally:
            path.unlink()

    def test_reference_parser_reads_only_the_named_section(self) -> None:
        text = (
            "## One\n| Variable | Default |\n|---|---|\n| `A` | x |\n"
            "## Two\n| `B` | y |\nprose with `C`\n"
        )
        self.assertEqual(reference_env_vars(text, "One"), {"A"})
        self.assertEqual(reference_env_vars(text, "Two"), {"B"})

    def test_reference_parser_reads_several_names_in_one_cell(self) -> None:
        text = "## One\n| `DB_NAME`, `PGDATABASE` | x |\n"
        self.assertEqual(reference_env_vars(text, "One"), {"DB_NAME", "PGDATABASE"})

    def test_a_variable_removed_from_the_reference_is_reported(self) -> None:
        read = python_env_vars("import os\nos.environ.get('A')\nos.getenv('B')\n")
        listed = reference_env_vars("## S\n| `A` | x |\n", "S")
        self.assertEqual(read - listed, {"B"})

    def test_env_example_parser_counts_commented_examples(self) -> None:
        text = "# Notes here\nA=1\n# B=2\n# Optional\nlower=3\n"
        self.assertEqual(env_example_vars(text), {"A", "B"})
