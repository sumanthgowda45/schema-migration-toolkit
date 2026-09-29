"""Load schema snapshots from JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from schema_model import Column, SchemaSnapshot, Table


def load_schema(path: str | Path) -> SchemaSnapshot:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    tables: list[Table] = []
    for item in raw.get("tables", raw if isinstance(raw, list) else []):
        columns = [
            Column(
                name=c["name"],
                data_type=c.get("data_type", "VARCHAR(255)"),
                nullable=bool(c.get("nullable", True)),
                primary_key=bool(c.get("primary_key", False)),
                default=c.get("default"),
            )
            for c in item.get("columns", [])
        ]
        tables.append(
            Table(
                name=item["name"],
                schema=item.get("schema", "public"),
                columns=columns,
            )
        )
    return SchemaSnapshot(tables=tables)
