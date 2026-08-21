from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support.fabric_notebook import load_notebook_functions  # noqa: E402
from support.fake_spark import FakeSparkSession, current_timestamp, lit  # noqa: E402

BRONZE_NOTEBOOK = "Notebook 1.Notebook/notebook-content.py"


@pytest.fixture
def spark() -> FakeSparkSession:
    return FakeSparkSession()


@pytest.fixture
def bronze_notebook(spark: FakeSparkSession) -> dict:
    """The bronze notebook's functions, bound to a recording Spark double."""
    return load_notebook_functions(
        BRONZE_NOTEBOOK,
        {"spark": spark, "lit": lit, "current_timestamp": current_timestamp},
    )


@pytest.fixture
def load_bronze(bronze_notebook: dict):
    return bronze_notebook["load_bronze"]
