"""The engine must stay independent of the web framework."""

import ast
from pathlib import Path

ENGINE_SOURCE = Path(__file__).parents[1] / "src" / "piscope_engine"
FORBIDDEN_ROOTS = {"fastapi", "starlette", "pydantic", "uvicorn", "piscope_api"}


def test_engine_does_not_import_web_stack() -> None:
    offenders: list[str] = []
    for path in ENGINE_SOURCE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] in FORBIDDEN_ROOTS:
                    offenders.append(f"{path.name}: {name}")
    assert offenders == []
