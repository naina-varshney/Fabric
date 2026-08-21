"""Contract tests for the ``cust360_warehouse`` T-SQL artifacts.

These guard the couplings the SQL project itself cannot check: the shape of the
``INSERT ... SELECT`` in ``usp_build_customer_360`` against the target table,
the aggregation it depends on, and the row level security predicate.
"""

from __future__ import annotations

import pytest
from sqlglot import exp
from support.warehouse_sql import parse_sql, read_sql, table_columns

DIM_TABLE = "c360/Tables/dim_customer_360.sql"
RM_MAP_TABLE = "c360/Tables/rm_region_map.sql"
BUILD_PROC = "c360/StoredProcedures/usp_build_customer_360.sql"
RLS_FUNCTION = "c360/Functions/fn_rls_region.sql"


@pytest.fixture(scope="module")
def build_proc() -> exp.Expression:
    (statement,) = parse_sql(BUILD_PROC)
    return statement


@pytest.fixture(scope="module")
def insert(build_proc: exp.Expression) -> exp.Insert:
    inserts = list(build_proc.find_all(exp.Insert))
    assert len(inserts) == 1, "expected exactly one INSERT in the build procedure"
    return inserts[0]


@pytest.fixture(scope="module")
def select(insert: exp.Insert) -> exp.Select:
    select = insert.expression
    assert isinstance(select, exp.Select)
    return select


def test_dim_table_columns_are_unique() -> None:
    columns = table_columns(DIM_TABLE)
    assert len(set(columns)) == len(columns)


def test_insert_projection_matches_dim_table_column_count(select: exp.Select) -> None:
    # The INSERT has no explicit column list, so the projection is positional:
    # any column added to the table must also be added to the SELECT.
    assert len(select.expressions) == len(table_columns(DIM_TABLE))


def test_insert_targets_the_dim_table(insert: exp.Insert) -> None:
    target = insert.this
    if isinstance(target, exp.Schema):
        target = target.this
    assert isinstance(target, exp.Table)
    assert target.name == "dim_customer_360"
    assert target.db == "c360"


def test_target_table_is_truncated_before_the_insert(build_proc: exp.Expression) -> None:
    sql = read_sql(BUILD_PROC).lower()
    assert "truncate table c360.dim_customer_360" in sql
    assert sql.index("truncate table") < sql.index("insert into")


def test_transaction_metrics_are_aggregated_and_null_safe(select: exp.Select) -> None:
    projections = select.expressions
    count_expr = next(e for e in projections if isinstance(e, exp.Count))
    sum_expr = next(e for e in projections if isinstance(e, exp.Sum))

    # COUNT ignores the NULL of the unmatched CASE branch; SUM needs an ELSE 0
    # so customers without successful transactions report 0 instead of NULL.
    assert count_expr.this.find(exp.Case).args.get("default") is None
    sum_default = sum_expr.this.find(exp.Case).args.get("default")
    assert isinstance(sum_default, exp.Literal)
    assert sum_default.this == "0"


def test_only_successful_transactions_feed_the_metrics(select: exp.Select) -> None:
    statuses = {
        literal.this
        for aggregate in (exp.Count, exp.Sum)
        for node in select.find_all(aggregate)
        for case in node.find_all(exp.Case)
        for literal in case.find_all(exp.Literal)
        if literal.is_string
    }
    assert statuses == {"Success"}


def test_customer_table_is_the_driving_table_and_joins_are_left(select: exp.Select) -> None:
    driving = select.find(exp.From).this
    assert driving.name == "bronze_crm_customers"

    joins = list(select.find_all(exp.Join))
    assert [join.side.upper() for join in joins] == ["LEFT", "LEFT"]
    assert [join.this.name for join in joins] == [
        "bronze_transactions",
        "bronze_kyc_records",
    ]


def test_every_join_matches_on_customer_id(select: exp.Select) -> None:
    for join in select.find_all(exp.Join):
        columns = {column.name for column in join.args["on"].find_all(exp.Column)}
        assert columns == {"customer_id"}


def test_non_aggregated_projections_are_all_grouped(select: exp.Select) -> None:
    grouped = {column.sql() for column in select.find(exp.Group).expressions}

    for projection in select.expressions:
        if projection.find(exp.AggFunc):
            continue
        assert projection.sql() in grouped, f"{projection.sql()} is not in the GROUP BY"


def test_grouping_keys_do_not_come_from_the_transactions_table(select: exp.Select) -> None:
    aliases = {
        join.this.alias
        for join in select.find_all(exp.Join)
        if join.this.name == "bronze_transactions"
    }
    for column in select.find(exp.Group).expressions:
        assert column.table not in aliases, "grouping by a transaction column fans out rows"


def test_rls_function_filters_by_current_user_and_region() -> None:
    (statement,) = parse_sql(RLS_FUNCTION)
    sql = statement.sql(dialect="tsql").lower()

    assert "user_name()" in sql
    referenced = {column.name for column in statement.find_all(exp.Column)}
    assert {"rm_login", "region"} <= referenced
    assert {"rm_login", "region"} <= set(table_columns(RM_MAP_TABLE))


def test_rls_function_is_schemabound_and_returns_a_table() -> None:
    sql = read_sql(RLS_FUNCTION).lower()
    assert "returns table" in sql
    assert "with schemabinding" in sql


def test_rls_region_parameter_is_compared_against_the_mapped_region() -> None:
    (statement,) = parse_sql(RLS_FUNCTION)
    comparisons = [
        eq
        for eq in statement.find_all(exp.EQ)
        if any(isinstance(side, exp.Parameter) for side in (eq.left, eq.right))
    ]
    assert comparisons, "the @region parameter is never used"
    for eq in comparisons:
        column = eq.left if isinstance(eq.right, exp.Parameter) else eq.right
        assert isinstance(column, exp.Column)
        assert column.name == "region"


def test_dim_table_and_rls_map_agree_on_the_region_type() -> None:
    def region_type(path: str) -> str:
        (statement,) = parse_sql(path)
        column = next(
            c
            for c in statement.this.expressions
            if isinstance(c, exp.ColumnDef) and c.name == "region"
        )
        return column.args["kind"].sql().lower()

    assert region_type(DIM_TABLE) == region_type(RM_MAP_TABLE)
