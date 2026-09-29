"""Generate forward/rollback SQL migration scripts from schema diffs."""

from __future__ import annotations

from datetime import datetime, timezone

from diff_engine import SchemaChange
from schema_model import Column, Table


def _qi(name: str, dialect: str) -> str:
    return f'"{name}"' if dialect == "postgres" else f"`{name}`"


def _full(schema: str, table: str, dialect: str) -> str:
    if schema and schema not in {"public", ""}:
        return f"{_qi(schema, dialect)}.{_qi(table, dialect)}"
    return _qi(table, dialect)


def _null_sql(col: Column) -> str:
    return "NULL" if col.nullable and not col.primary_key else "NOT NULL"


def _default_sql(col: Column) -> str:
    if col.default in (None, ""):
        return ""
    upper = str(col.default).upper()
    if upper in {"CURRENT_TIMESTAMP", "NOW()", "NULL"}:
        return f" DEFAULT {col.default if upper != 'NOW()' else 'CURRENT_TIMESTAMP'}"
    if str(col.default).replace(".", "", 1).isdigit():
        return f" DEFAULT {col.default}"
    return f" DEFAULT '{str(col.default).replace(chr(39), chr(39) * 2)}'"


def _create_table_sql(table: Table, dialect: str) -> str:
    lines = [f"CREATE TABLE {_full(table.schema, table.name, dialect)} ("]
    parts: list[str] = []
    for col in table.columns:
        parts.append(
            f"  {_qi(col.name, dialect)} {col.data_type} {_null_sql(col)}{_default_sql(col)}"
        )
    pk = [c.name for c in table.columns if c.primary_key]
    if pk:
        parts.append("  PRIMARY KEY (" + ", ".join(_qi(c, dialect) for c in pk) + ")")
    lines.append(",\n".join(parts))
    lines.append(");")
    return "\n".join(lines)


def _add_column_sql(change: SchemaChange, dialect: str) -> str:
    assert isinstance(change.after, Column)
    col = change.after
    table = _full(change.schema_name, change.table_name, dialect)
    return (
        f"ALTER TABLE {table} ADD COLUMN {_qi(col.name, dialect)} "
        f"{col.data_type} {_null_sql(col)}{_default_sql(col)};"
    )


def _drop_column_sql(change: SchemaChange, dialect: str) -> str:
    table = _full(change.schema_name, change.table_name, dialect)
    return f"ALTER TABLE {table} DROP COLUMN {_qi(change.column_name or '', dialect)};"


def _alter_column_sql(change: SchemaChange, dialect: str) -> str:
    assert isinstance(change.after, Column)
    col = change.after
    table = _full(change.schema_name, change.table_name, dialect)
    if dialect == "postgres":
        stmts = [
            f"ALTER TABLE {table} ALTER COLUMN {_qi(col.name, dialect)} TYPE {col.data_type};",
            (
                f"ALTER TABLE {table} ALTER COLUMN {_qi(col.name, dialect)} "
                f"{'DROP NOT NULL' if col.nullable and not col.primary_key else 'SET NOT NULL'};"
            ),
        ]
        if col.default in (None, ""):
            stmts.append(f"ALTER TABLE {table} ALTER COLUMN {_qi(col.name, dialect)} DROP DEFAULT;")
        else:
            default = _default_sql(col).replace(" DEFAULT ", "", 1)
            stmts.append(
                f"ALTER TABLE {table} ALTER COLUMN {_qi(col.name, dialect)} SET DEFAULT {default};"
            )
        return "\n".join(stmts)

    # MySQL / MariaDB style
    return (
        f"ALTER TABLE {table} MODIFY COLUMN {_qi(col.name, dialect)} "
        f"{col.data_type} {_null_sql(col)}{_default_sql(col)};"
    )


def generate_forward_sql(changes: list[SchemaChange], dialect: str = "mysql") -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "-- Forward migration script",
        f"-- Generated at: {now}",
        f"-- Dialect: {dialect}",
        f"-- Changes: {len(changes)}",
        "START TRANSACTION;",
        "",
    ]

    ordered = sorted(
        changes,
        key=lambda c: {
            "CREATE_TABLE": 0,
            "ADD_COLUMN": 1,
            "ALTER_COLUMN": 2,
            "DROP_COLUMN": 3,
            "DROP_TABLE": 4,
        }[c.change_type],
    )

    for change in ordered:
        lines.append(f"-- {change.details}")
        if change.change_type == "CREATE_TABLE":
            assert isinstance(change.after, Table)
            lines.append(_create_table_sql(change.after, dialect))
        elif change.change_type == "DROP_TABLE":
            lines.append(
                f"DROP TABLE IF EXISTS {_full(change.schema_name, change.table_name, dialect)};"
            )
        elif change.change_type == "ADD_COLUMN":
            lines.append(_add_column_sql(change, dialect))
        elif change.change_type == "DROP_COLUMN":
            lines.append(_drop_column_sql(change, dialect))
        elif change.change_type == "ALTER_COLUMN":
            lines.append(_alter_column_sql(change, dialect))
        lines.append("")

    lines.append("COMMIT;")
    lines.append("")
    return "\n".join(lines)


def generate_rollback_sql(changes: list[SchemaChange], dialect: str = "mysql") -> str:
    """Best-effort rollback: invert changes where possible."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "-- Rollback migration script",
        f"-- Generated at: {now}",
        f"-- Dialect: {dialect}",
        "START TRANSACTION;",
        "",
    ]

    # Reverse order of destructive-safe inversion
    for change in reversed(changes):
        lines.append(f"-- Rollback: {change.details}")
        if change.change_type == "CREATE_TABLE":
            lines.append(
                f"DROP TABLE IF EXISTS {_full(change.schema_name, change.table_name, dialect)};"
            )
        elif change.change_type == "DROP_TABLE":
            assert isinstance(change.before, Table)
            lines.append(_create_table_sql(change.before, dialect))
        elif change.change_type == "ADD_COLUMN":
            lines.append(
                f"ALTER TABLE {_full(change.schema_name, change.table_name, dialect)} "
                f"DROP COLUMN {_qi(change.column_name or '', dialect)};"
            )
        elif change.change_type == "DROP_COLUMN":
            assert isinstance(change.before, Column)
            inverse = SchemaChange(
                change_type="ADD_COLUMN",
                table_name=change.table_name,
                schema_name=change.schema_name,
                column_name=change.column_name,
                after=change.before,
            )
            lines.append(_add_column_sql(inverse, dialect))
        elif change.change_type == "ALTER_COLUMN":
            inverse = SchemaChange(
                change_type="ALTER_COLUMN",
                table_name=change.table_name,
                schema_name=change.schema_name,
                column_name=change.column_name,
                after=change.before,
                before=change.after,
            )
            lines.append(_alter_column_sql(inverse, dialect))
        lines.append("")

    lines.append("COMMIT;")
    lines.append("")
    return "\n".join(lines)
