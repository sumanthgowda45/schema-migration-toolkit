"""Compute schema differences between two snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from schema_model import Column, SchemaSnapshot, Table

ChangeType = Literal[
    "CREATE_TABLE",
    "DROP_TABLE",
    "ADD_COLUMN",
    "DROP_COLUMN",
    "ALTER_COLUMN",
]


@dataclass
class SchemaChange:
    change_type: ChangeType
    table_name: str
    schema_name: str = "public"
    column_name: str | None = None
    before: Column | Table | None = None
    after: Column | Table | None = None
    details: str = ""


def diff_schemas(source: SchemaSnapshot, target: SchemaSnapshot) -> list[SchemaChange]:
    """
    Produce changes required to transform *source* into *target*.

    source = currently deployed schema
    target = desired schema
    """
    changes: list[SchemaChange] = []
    source_tables = source.table_map()
    target_tables = target.table_map()

    for name, table in target_tables.items():
        if name not in source_tables:
            changes.append(
                SchemaChange(
                    change_type="CREATE_TABLE",
                    table_name=name,
                    schema_name=table.schema,
                    after=table,
                    details=f"Create table {table.schema}.{name}",
                )
            )

    for name, table in source_tables.items():
        if name not in target_tables:
            changes.append(
                SchemaChange(
                    change_type="DROP_TABLE",
                    table_name=name,
                    schema_name=table.schema,
                    before=table,
                    details=f"Drop table {table.schema}.{name}",
                )
            )

    for name, target_table in target_tables.items():
        if name not in source_tables:
            continue
        source_table = source_tables[name]
        source_cols = source_table.column_map()
        target_cols = target_table.column_map()

        for col_name, col in target_cols.items():
            if col_name not in source_cols:
                changes.append(
                    SchemaChange(
                        change_type="ADD_COLUMN",
                        table_name=name,
                        schema_name=target_table.schema,
                        column_name=col_name,
                        after=col,
                        details=f"Add column {name}.{col_name}",
                    )
                )

        for col_name, col in source_cols.items():
            if col_name not in target_cols:
                changes.append(
                    SchemaChange(
                        change_type="DROP_COLUMN",
                        table_name=name,
                        schema_name=source_table.schema,
                        column_name=col_name,
                        before=col,
                        details=f"Drop column {name}.{col_name}",
                    )
                )

        for col_name, target_col in target_cols.items():
            if col_name not in source_cols:
                continue
            source_col = source_cols[col_name]
            if _column_changed(source_col, target_col):
                changes.append(
                    SchemaChange(
                        change_type="ALTER_COLUMN",
                        table_name=name,
                        schema_name=target_table.schema,
                        column_name=col_name,
                        before=source_col,
                        after=target_col,
                        details=f"Alter column {name}.{col_name}",
                    )
                )

    return changes


def _column_changed(before: Column, after: Column) -> bool:
    return (
        before.data_type.upper() != after.data_type.upper()
        or before.nullable != after.nullable
        or (before.default or "") != (after.default or "")
        or before.primary_key != after.primary_key
    )
