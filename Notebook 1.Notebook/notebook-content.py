# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "3cf24b0d-234e-439b-9090-b10204ecd5fc",
# META       "default_lakehouse_name": "cust360_lakehouse",
# META       "default_lakehouse_workspace_id": "7b173a49-4de9-4c8d-b703-1584ec15bdc0",
# META       "known_lakehouses": [
# META         {
# META           "id": "3cf24b0d-234e-439b-9090-b10204ecd5fc"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# Welcome to your new notebook
# Type here in the cell editor to add code!


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import DataFrame
from pyspark.sql.functions import current_timestamp, lit
from pyspark.sql.utils import AnalysisException

FILES_ROOT = "Files"


class BronzeLoadError(Exception):
    """Raised when a bronze table cannot be loaded from its source file."""


def read_csv(path: str) -> DataFrame:
    return (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "true")
        .option("mode", "FAILFAST")
        .load(path)
    )


def add_audit_columns(
    df: DataFrame,
    source_system: str,
    file_name: str,
    pipeline_run_id: str,
) -> DataFrame:
    return (
        df.withColumn("source_system", lit(source_system))
        .withColumn("source_file_name", lit(file_name))
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("pipeline_run_id", lit(pipeline_run_id))
    )


def write_delta(df: DataFrame, table_name: str, mode: str = "overwrite") -> None:
    df.write.format("delta").mode(mode).saveAsTable(table_name)


def load_bronze(file_name, table_name, source_system, pipeline_run_id):

    path = f"{FILES_ROOT}/{file_name}"

    try:
        df = read_csv(path)
    except AnalysisException as exc:
        raise BronzeLoadError(
            f"Cannot read source file {path} for table {table_name}: {exc}"
        ) from exc

    if not df.columns:
        raise BronzeLoadError(f"Source file {path} has no columns; refusing to overwrite {table_name}")

    df = add_audit_columns(df, source_system, file_name, pipeline_run_id)

    try:
        write_delta(df, table_name)
    except Exception as exc:
        raise BronzeLoadError(f"Failed to write table {table_name} from {path}: {exc}") from exc

    row_count = spark.table(table_name).count()
    if row_count == 0:
        raise BronzeLoadError(f"Table {table_name} was written from {path} but contains no rows")

    print(f"{table_name} loaded successfully ({row_count} rows)")
    return row_count


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import uuid

BRONZE_SOURCES = [
    # ("crm_customers.csv", "bronze_crm_customers", "CRM"),
    ("crm_interactions.csv", "bronze_crm_interactions", "CRM"),
    ("transactions.csv", "bronze_transactions", "Transactions"),
    ("kyc_records.csv", "bronze_kyc_records", "KYC"),
    ("relationship_managers.csv", "bronze_relationship_managers", "Reference"),
]

pipeline_run_id = str(uuid.uuid4())
print(f"pipeline_run_id={pipeline_run_id}")

failures = {}
for file_name, table_name, source_system in BRONZE_SOURCES:
    try:
        load_bronze(file_name, table_name, source_system, pipeline_run_id)
    except BronzeLoadError as exc:
        failures[table_name] = str(exc)
        print(f"{table_name} failed: {exc}")

if failures:
    details = "; ".join(f"{table}: {message}" for table, message in failures.items())
    raise BronzeLoadError(f"{len(failures)} of {len(BRONZE_SOURCES)} bronze loads failed -> {details}")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
