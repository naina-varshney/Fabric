"""A tiny recording double for the subset of the Spark API the notebooks use.

The doubles record every builder call (``format``/``option``/``mode``/...) so
tests can assert on the read path, the columns that get added, the order of
operations and the write path without a JVM or a Spark session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Literal:
    """Stand-in for ``pyspark.sql.functions.lit``."""

    value: Any


@dataclass(frozen=True)
class FunctionCall:
    """Stand-in for a zero argument column function such as ``current_timestamp``."""

    name: str


def lit(value: Any) -> Literal:
    return Literal(value)


def current_timestamp() -> FunctionCall:
    return FunctionCall("current_timestamp")


@dataclass
class ReadRecord:
    format: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    load_path: str | None = None


@dataclass
class WriteRecord:
    format: str | None = None
    mode: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    saved_table: str | None = None
    saved_path: str | None = None


@dataclass
class LoadRecord:
    """Everything one DataFrame lineage did, from read to write."""

    read: ReadRecord
    columns: dict[str, Any] = field(default_factory=dict)
    write: WriteRecord = field(default_factory=WriteRecord)
    events: list[str] = field(default_factory=list)


class FakeDataFrameWriter:
    def __init__(self, load: LoadRecord) -> None:
        self._load = load

    def format(self, source: str) -> "FakeDataFrameWriter":
        self._load.write.format = source
        return self

    def mode(self, save_mode: str) -> "FakeDataFrameWriter":
        self._load.write.mode = save_mode
        return self

    def option(self, key: str, value: Any) -> "FakeDataFrameWriter":
        self._load.write.options[key] = value
        return self

    def saveAsTable(self, name: str) -> None:  # noqa: N802 - Spark API name
        self._load.write.saved_table = name
        self._load.events.append(f"saveAsTable:{name}")

    def save(self, path: str) -> None:
        self._load.write.saved_path = path
        self._load.events.append(f"save:{path}")


class FakeDataFrame:
    def __init__(self, load: LoadRecord) -> None:
        self.load = load

    def withColumn(self, name: str, column: Any) -> "FakeDataFrame":  # noqa: N802
        self.load.columns[name] = column
        self.load.events.append(f"withColumn:{name}")
        return FakeDataFrame(self.load)

    @property
    def write(self) -> FakeDataFrameWriter:
        return FakeDataFrameWriter(self.load)


class FakeDataFrameReader:
    def __init__(self, session: "FakeSparkSession") -> None:
        self._session = session
        self._read = ReadRecord()

    def format(self, source: str) -> "FakeDataFrameReader":
        self._read.format = source
        return self

    def option(self, key: str, value: Any) -> "FakeDataFrameReader":
        self._read.options[key] = value
        return self

    def load(self, path: str) -> FakeDataFrame:
        self._read.load_path = path
        record = LoadRecord(read=self._read)
        record.events.append(f"read:{path}")
        self._session.loads.append(record)
        return FakeDataFrame(record)


class FakeSparkSession:
    def __init__(self) -> None:
        self.loads: list[LoadRecord] = []

    @property
    def read(self) -> FakeDataFrameReader:
        return FakeDataFrameReader(self)

    @property
    def reads(self) -> list[ReadRecord]:
        return [load.read for load in self.loads]

    @property
    def last_load(self) -> LoadRecord:
        if not self.loads:
            raise AssertionError("no DataFrame was created")
        return self.loads[-1]
