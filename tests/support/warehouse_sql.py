"""Helpers for parsing the warehouse T-SQL artifacts with sqlglot."""

from __future__ import annotations

from pathlib import Path

import sqlglot
from sqlglot import exp

REPO_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE_ROOT = REPO_ROOT / "cust360_warehouse.Warehouse"

DIALECT = "tsql"


def read_sql(relative_path: str) -> str:
    return (WAREHOUSE_ROOT / relative_path).read_text(encoding="utf-8")


def parse_sql(relative_path: str) -> list[exp.Expression]:
    statements = sqlglot.parse(read_sql(relative_path), read=DIALECT)
    return [statement for statement in statements if statement is not None]


def table_columns(relative_path: str) -> list[str]:
    """Column names of the single ``CREATE TABLE`` in a table definition file."""
    (statement,) = parse_sql(relative_path)
    schema = statement.this
    assert isinstance(schema, exp.Schema), f"{relative_path} is not a CREATE TABLE"
    return [column.name for column in schema.expressions if isinstance(column, exp.ColumnDef)]
