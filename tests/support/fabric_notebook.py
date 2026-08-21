"""Helpers for unit testing Microsoft Fabric notebook sources.

Fabric stores notebooks as ``notebook-content.py`` files that mix executable
code with ``# META`` / ``# CELL`` marker comments, and whose top level calls
into the Spark runtime.  The helpers here extract the notebook's function
definitions so they can be exercised in isolation, without a Spark session.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

_MARKER_PREFIXES = ("# META", "# CELL", "# MARKDOWN", "# Fabric notebook source")


def read_notebook_source(notebook_path: str | Path) -> str:
    """Return the notebook source with Fabric marker comments removed."""
    path = Path(notebook_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not line.startswith(_MARKER_PREFIXES)]
    return "\n".join(kept)


def load_notebook_functions(
    notebook_path: str | Path, injected_globals: dict[str, Any]
) -> dict[str, Any]:
    """Execute only the function definitions of a notebook.

    Top level statements (the cells that actually trigger Spark jobs) are
    skipped, so importing a notebook never touches the data platform.
    ``injected_globals`` stands in for the names the Fabric runtime provides
    implicitly, such as ``spark`` and the ``pyspark.sql.functions`` helpers.
    """
    module = ast.parse(read_notebook_source(notebook_path))
    module.body = [
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    namespace: dict[str, Any] = dict(injected_globals)
    exec(compile(module, filename=str(notebook_path), mode="exec"), namespace)
    return namespace


def notebook_top_level_calls(notebook_path: str | Path, func_name: str) -> list[ast.Call]:
    """Return the top level calls to ``func_name`` made by the notebook."""
    module = ast.parse(read_notebook_source(notebook_path))
    calls = []
    for node in module.body:
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == func_name
        ):
            calls.append(node.value)
    return calls
