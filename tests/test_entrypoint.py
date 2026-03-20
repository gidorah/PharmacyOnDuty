import importlib
from pathlib import Path


def test_entrypoint_runs_wait_script_as_module_from_app() -> None:
    entrypoint = Path("scripts/entrypoint.sh").read_text()

    assert "uv run python -m scripts.wait_for_services" in entrypoint
    assert 'if [ -f "/app/scripts/wait_for_services.py" ]; then' in entrypoint


def test_wait_for_services_is_importable_as_module() -> None:
    module = importlib.import_module("scripts.wait_for_services")

    assert hasattr(module, "wait_for_postgres")
