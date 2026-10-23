"""Checks for the factory files in factory/ and .github/ISSUE_TEMPLATE/.

The tier job and the label pipeline read these files. These tests keep them in
step with the repository, so a renamed path or a stray label fails CI instead
of silently changing how changes are routed.
"""

import os
import re
from pathlib import Path
from typing import Any

import pathspec
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
RISK_MAP = ROOT / "factory" / "risk-map.yml"
STANDING_RULES = ROOT / "factory" / "standing-rules.yml"
LABELS = ROOT / "factory" / "labels.yml"
ISSUE_TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"

# Generated or local directories, not repository content. `.claude` holds local
# Claude Code state, including worktrees that copy the whole repository.
SKIPPED_DIRS = {
    ".git",
    ".claude",
    ".venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    "staticfiles",
}
TIERS = {"A", "B", "C"}
AREA_CONDITIONS = {"any_change", "existing_lines_changed"}
WORK_ORDER_FIELDS = {
    "goal",
    "out_of_scope",
    "test_points",
    "done_check",
    "size",
    "risk",
    "decision_log",
}


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"{path} must hold a mapping"
    return data


def _repo_files() -> list[str]:
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIPPED_DIRS]
        rel = Path(dirpath).relative_to(ROOT)
        files.extend((rel / name).as_posix() for name in filenames)
    return files


def _matches(pattern: str, files: list[str]) -> bool:
    spec = pathspec.PathSpec.from_lines("gitignore", [pattern])
    return any(spec.match_file(f) for f in files)


RISK_AREAS: list[dict[str, Any]] = _load(RISK_MAP)["areas"]
RISK_PATHS = [p for area in RISK_AREAS for p in area["paths"]]
PLANNED_PATHS = [p for area in RISK_AREAS for p in area.get("planned_paths", [])]
OPTIONAL_PATHS = [p for area in RISK_AREAS for p in area.get("optional_paths", [])]


@pytest.fixture(scope="module")
def repo_files() -> list[str]:
    return _repo_files()


def test_risk_map_shape() -> None:
    risk_map = _load(RISK_MAP)
    assert risk_map["version"] == 1
    assert risk_map["default_tier"] == "B"
    names = [area["name"] for area in RISK_AREAS]
    assert len(names) == len(set(names)), "area names must be unique"
    for area in RISK_AREAS:
        assert area["tier"] in TIERS, area["name"]
        assert area["why"], area["name"]
        assert area["paths"], f"{area['name']} lists no paths"
        assert area.get("when", "any_change") in AREA_CONDITIONS, area["name"]
    all_patterns = RISK_PATHS + PLANNED_PATHS + OPTIONAL_PATHS
    assert all(isinstance(p, str) and p for p in all_patterns)
    assert len(all_patterns) == len(set(all_patterns)), "patterns must be unique"
    findings = risk_map["reviewer_findings"]
    assert findings["raise_to"] == "C"
    assert findings["categories"]


@pytest.mark.parametrize("pattern", RISK_PATHS)
def test_risk_map_path_exists(pattern: str, repo_files: list[str]) -> None:
    assert _matches(pattern, repo_files), (
        f"risk map pattern {pattern!r} matches no file. Update factory/risk-map.yml "
        "to the new path instead of deleting the entry."
    )


@pytest.mark.parametrize("pattern", PLANNED_PATHS)
def test_planned_path_not_created_yet(pattern: str, repo_files: list[str]) -> None:
    assert not _matches(pattern, repo_files), (
        f"{pattern!r} exists now. Move it from planned_paths to paths in "
        "factory/risk-map.yml."
    )


def test_waivers_name_active_standing_rules() -> None:
    active = {
        rule["id"]
        for rule in _load(STANDING_RULES)["rules"]
        if rule["status"] == "active"
    }
    for area in RISK_AREAS:
        waiver = area.get("waived_by_standing_rule")
        if waiver is not None:
            assert waiver in active, f"{area['name']} names unknown rule {waiver!r}"


def test_standing_rules_shape() -> None:
    standing = _load(STANDING_RULES)
    assert standing["version"] == 1
    ids = [
        entry["id"]
        for key in ("rules", "proposals", "declined")
        for entry in standing.get(key) or []
    ]
    assert len(ids) == len(set(ids)), "rule, proposal and declined ids must be unique"
    for rule in standing["rules"]:
        assert rule["status"] in {"active", "paused"}, rule["id"]
        assert rule["tier"] == "A", "standing rules exist only to reach tier A"
        assert rule["match"], rule["id"]


def test_labels() -> None:
    data = _load(LABELS)
    labels: list[dict[str, Any]] = data["labels"]
    names = [label["name"].lower() for label in labels]
    assert len(names) == len(set(names)), "label names must be unique"
    for label in labels:
        name = label["name"]
        assert re.fullmatch(r"[0-9a-f]{6}", label["color"]), name
        assert 0 < len(label["description"]) <= 100, name
        assert label["applies_to"] in {"issue", "pr", "both"}, name
        for key in ("state", "added_by", "starts"):
            assert label[key], f"{name} has no {key}"
    deleted = {entry["name"].lower() for entry in data.get("delete", [])}
    assert not deleted & set(names), "a label can't be both kept and deleted"


def test_work_order_form_applies_no_agent_label() -> None:
    # Only labels Onur adds may start a factory job, and anyone can open an
    # issue on this public repository.
    form = _load(ISSUE_TEMPLATES / "work-order.yml")
    labels = form.get("labels") or []
    assert not [label for label in labels if str(label).startswith("agent:")]
    ids = {field.get("id") for field in form["body"]}
    assert WORK_ORDER_FIELDS <= ids


def test_blank_issues_allowed() -> None:
    config = _load(ISSUE_TEMPLATES / "config.yml")
    assert config["blank_issues_enabled"] is True
