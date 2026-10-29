"""scripts/check_docs.py catches doc drift: dead paths, recipes, commands, links.

The temp-repo cases build a tiny repo and call ``check_repo`` directly with an
injected Django command set, so they never shell out. The last case runs the
real check over the real docs, so ``testenv.sh check`` catches drift too.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_docs import check_repo, missing_own_commands, parse_recipes

REPO_ROOT = Path(__file__).resolve().parent.parent
JUSTFILE = "test:\n    echo hi\n\nmanage command:\n    echo {{command}}\n"
COMMANDS = {"migrate", "check"}


class CheckDocsCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.write("justfile", JUSTFILE)

    def write(self, name: str, text: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def failures(self) -> list[str]:
        return check_repo(self.root, COMMANDS)


class TestFailures(CheckDocsCase):
    def test_missing_path_fails(self) -> None:
        self.write("a.md", "# A\n\nSee `docs/nope.md` here.\n")
        self.assertEqual(
            self.failures(), ["a.md:3: path `docs/nope.md` does not exist"]
        )

    def test_unknown_recipe_fails(self) -> None:
        self.write("a.md", "# A\n\nRun `just frobnicate`.\n")
        out = self.failures()
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("a.md:3: "))
        self.assertIn("frobnicate", out[0])

    def test_unknown_manage_command_fails(self) -> None:
        self.write("a.md", "# A\n\nRun `manage.py bogus` or `just manage bogus2`.\n")
        out = self.failures()
        self.assertEqual(len(out), 2)
        self.assertIn("bogus", out[0])
        self.assertIn("bogus2", out[1])

    def test_broken_link_fails(self) -> None:
        self.write("a.md", "# A\n\n[x](missing.md)\n")
        out = self.failures()
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("a.md:3: "))

    def test_broken_anchor_fails(self) -> None:
        self.write("a.md", "# A\n\n[x](b.md#nope)\n")
        self.write("b.md", "# Real heading\n")
        out = self.failures()
        self.assertEqual(len(out), 1)
        self.assertIn("#nope", out[0])

    def test_root_agents_over_100_lines_fails(self) -> None:
        self.write("AGENTS.md", "x\n" * 101)
        self.assertEqual(
            self.failures(), ["AGENTS.md:101: 101 lines, over the limit of 100"]
        )

    def test_area_agents_over_50_lines_fails(self) -> None:
        self.write("pharmacies/AGENTS.md", "x\n" * 51)
        self.assertEqual(
            self.failures(),
            ["pharmacies/AGENTS.md:51: 51 lines, over the limit of 50"],
        )

    def test_agent_files_at_the_limit_pass(self) -> None:
        self.write("AGENTS.md", "x\n" * 100)
        self.write("pharmacies/AGENTS.md", "x\n" * 50)
        self.assertEqual(self.failures(), [])

    def test_adr_is_not_checked(self) -> None:
        self.write("docs/decisions/0001-x.md", "See `gone/away.md`.\n")
        self.write("docs/decisions/README.md", "See `gone/away.md`.\n")
        out = self.failures()
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("docs/decisions/README.md:1: "))


class TestNewFindings(CheckDocsCase):
    def test_recipe_with_default_parameters_is_parsed(self) -> None:
        names = parse_recipes(
            'build target="x":\n    echo\n'
            "deploy env='prod' *args:\n    echo\n"
            "version := '1'\n"
            "other := 'a: b'\n"
        )
        self.assertEqual(names, {"build", "deploy"})

    def test_node_id_in_code_span_checks_only_the_file(self) -> None:
        self.write("pharmacies/tests/test_views.py", "")
        self.write("a.md", "`pharmacies/tests/test_views.py::TestNearest::test_x`\n")
        self.assertEqual(self.failures(), [])
        self.write("b.md", "`pharmacies/tests/gone.py::TestNearest::test_x`\n")
        out = self.failures()
        self.assertEqual(len(out), 1)
        self.assertIn("gone.py", out[0])

    def test_single_quoted_title_link_is_checked(self) -> None:
        self.write("a.md", "# A\n\n[q](missing.md 'title')\n")
        out = self.failures()
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("a.md:3: "))

    def test_broken_reference_definition_fails(self) -> None:
        self.write("a.md", "# A\n\nSee [x][ref] and [ref][].\n\n[ref]: missing.md\n")
        out = self.failures()
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("a.md:5: "))

    def test_good_reference_definition_and_fenced_one_pass(self) -> None:
        self.write("b.md", "# B\n")
        self.write(
            "a.md",
            "[ref]: b.md\n[web]: https://example.com\n\n```\n[r]: nope.md\n```\n",
        )
        self.assertEqual(self.failures(), [])


class TestOwnCommands(CheckDocsCase):
    def test_missing_own_commands_reported(self) -> None:
        self.write("app/management/commands/seed_cities.py", "")
        self.write("app/management/commands/__init__.py", "")
        self.write("app/management/commands/_helper.py", "")
        self.write("node_modules/x/management/commands/skipped.py", "")
        self.assertEqual(missing_own_commands(self.root, {"migrate"}), ["seed_cities"])
        self.assertEqual(missing_own_commands(self.root, {"seed_cities"}), [])


class TestPasses(CheckDocsCase):
    def test_clean_doc_passes(self) -> None:
        self.write("pharmacies/models.py", "")
        self.write("docs/other.md", "# Other\n\n## Some Heading!\n")
        self.write(
            "docs/a.md",
            "# A\n\n"
            "Path `pharmacies/models.py`, recipe `just test`, "
            "command `manage.py migrate`, `just manage check`.\n"
            "Link [o](other.md#some-heading) and [self](#a) and "
            "[web](https://example.com/x).\n"
            "Skipped: `/health/data/` `30/m` `Europe/Istanbul` `<city>` "
            "`E4/E7/F/I/UP` `https://example.com/a/b` `*.py` `NNNN/x.md`.\n",
        )
        self.assertEqual(self.failures(), [])

    def test_bare_name_found_anywhere_in_tree(self) -> None:
        self.write("deep/er/models.py", "")
        self.write("a.md", "See `models.py` and `models.py:get_city_data`.\n")
        self.assertEqual(self.failures(), [])

    def test_path_resolves_from_file_folder_or_root(self) -> None:
        self.write("docs/x/sibling.md", "# S\n")
        self.write("top/leaf.py", "")
        self.write("docs/x/a.md", "`sibling.md` `./sibling.md` `top/leaf.py`\n")
        self.assertEqual(self.failures(), [])

    def test_fenced_block_is_not_path_checked_but_just_lines_are(self) -> None:
        self.write(
            "a.md",
            "# A\n\n```bash\ncat gone/file.md\njust test\njust nothing\n```\n",
        )
        out = self.failures()
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("a.md:6: "))
        self.assertIn("nothing", out[0])

    def test_duplicate_heading_anchors(self) -> None:
        self.write("a.md", "# T\n\n# T\n\n[a](#t) [b](#t-1) [c](#t-2)\n")
        out = self.failures()
        self.assertEqual(len(out), 1)
        self.assertIn("#t-2", out[0])


class TestRealRepo(unittest.TestCase):
    def test_repo_docs_pass(self) -> None:
        result = subprocess.run(
            [sys.executable, "manage.py", "help", "--commands"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        commands = set(result.stdout.split()) | {"help", "version"}
        failures = check_repo(REPO_ROOT, commands)
        self.assertEqual(failures, [], "\n" + "\n".join(failures))
