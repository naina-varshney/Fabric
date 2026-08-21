"""Unit tests for ``load_bronze`` in ``Notebook 1.Notebook``."""

from __future__ import annotations

import ast

import pytest
from support.fabric_notebook import notebook_top_level_calls
from support.fake_spark import FakeSparkSession, FunctionCall, Literal

from conftest import BRONZE_NOTEBOOK

AUDIT_COLUMNS = (
    "source_system",
    "source_file_name",
    "ingestion_timestamp",
    "pipeline_run_id",
)


def test_reads_csv_from_files_area_with_header_and_schema_inference(
    load_bronze, spark: FakeSparkSession
) -> None:
    load_bronze("crm_interactions.csv", "bronze_crm_interactions", "CRM")

    assert len(spark.reads) == 1
    read = spark.reads[0]
    assert read.format == "csv"
    assert read.load_path == "Files/crm_interactions.csv"
    assert read.options == {"header": "true", "inferSchema": "true"}


def test_adds_the_expected_audit_columns(load_bronze, spark: FakeSparkSession) -> None:
    load_bronze("transactions.csv", "bronze_transactions", "Transactions")

    added = spark.last_load.columns
    assert tuple(added) == AUDIT_COLUMNS
    assert added["source_system"] == Literal("Transactions")
    assert added["source_file_name"] == Literal("transactions.csv")
    assert added["ingestion_timestamp"] == FunctionCall("current_timestamp")
    assert added["pipeline_run_id"] == Literal("run_001")


def test_writes_delta_table_by_overwrite(load_bronze, spark: FakeSparkSession) -> None:
    load_bronze("kyc_records.csv", "bronze_kyc_records", "KYC")

    write = spark.last_load.write
    assert write.format == "delta"
    assert write.mode == "overwrite"
    assert write.saved_table == "bronze_kyc_records"
    assert write.saved_path is None, "bronze loads are managed tables, not paths"


def test_reports_success_for_the_written_table(
    load_bronze, spark: FakeSparkSession, capsys: pytest.CaptureFixture[str]
) -> None:
    load_bronze("relationship_managers.csv", "bronze_relationship_managers", "Reference")

    assert "bronze_relationship_managers" in capsys.readouterr().out


def test_each_invocation_is_independent(load_bronze, spark: FakeSparkSession) -> None:
    load_bronze("a.csv", "bronze_a", "CRM")
    load_bronze("b.csv", "bronze_b", "KYC")

    assert [read.load_path for read in spark.reads] == ["Files/a.csv", "Files/b.csv"]
    assert [load.write.saved_table for load in spark.loads] == ["bronze_a", "bronze_b"]
    assert spark.loads[0].columns["source_system"] == Literal("CRM")
    assert spark.loads[1].columns["source_system"] == Literal("KYC")


def test_file_name_is_not_interpreted_as_an_absolute_or_relative_path(
    load_bronze, spark: FakeSparkSession
) -> None:
    load_bronze("nested/dir/file.csv", "bronze_nested", "CRM")

    assert spark.reads[0].load_path == "Files/nested/dir/file.csv"


def test_audit_columns_are_added_before_the_table_is_written(
    load_bronze, spark: FakeSparkSession
) -> None:
    load_bronze("crm_customers.csv", "bronze_crm_customers", "CRM")

    assert spark.last_load.events == [
        "read:Files/crm_customers.csv",
        *(f"withColumn:{column}" for column in AUDIT_COLUMNS),
        "saveAsTable:bronze_crm_customers",
    ]


def _string_args(call: ast.Call) -> list[str]:
    return [arg.value for arg in call.args if isinstance(arg, ast.Constant)]


def test_notebook_invocations_target_distinct_bronze_tables() -> None:
    calls = notebook_top_level_calls(BRONZE_NOTEBOOK, "load_bronze")
    assert calls, "the notebook no longer calls load_bronze"

    arg_sets = [_string_args(call) for call in calls]
    assert all(len(args) == 3 for args in arg_sets)

    files = [args[0] for args in arg_sets]
    tables = [args[1] for args in arg_sets]
    assert len(set(files)) == len(files), "the same file is ingested twice"
    assert len(set(tables)) == len(tables), "two loads would overwrite the same table"
    assert all(table.startswith("bronze_") for table in tables)
    assert all(file.endswith(".csv") for file in files)
