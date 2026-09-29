"""Schema model objects used by the migration toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Column:
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    default: str | None = None


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)
    schema: str = "public"

    def column_map(self) -> dict[str, Column]:
        return {c.name: c for c in self.columns}


@dataclass
class SchemaSnapshot:
    tables: list[Table] = field(default_factory=list)

    def table_map(self) -> dict[str, Table]:
        return {t.name: t for t in self.tables}
