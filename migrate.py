#!/usr/bin/env python3
"""CLI: generate DB migration scripts by diffing schema snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from diff_engine import diff_schemas
from migration_generator import generate_forward_sql, generate_rollback_sql
from schema_loader import load_schema


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate SQL migration scripts from schema metadata diffs"
    )
    parser.add_argument("--source", required=True, type=Path, help="Current schema JSON")
    parser.add_argument("--target", required=True, type=Path, help="Desired schema JSON")
    parser.add_argument("--dialect", choices=["mysql", "postgres"], default="mysql")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("migrations"),
        help="Directory for generated scripts",
    )
    parser.add_argument("--name", default="schema_update", help="Migration name prefix")
    parser.add_argument("--print-plan", action="store_true", help="Print change plan as JSON")
    args = parser.parse_args()

    source = load_schema(args.source)
    target = load_schema(args.target)
    changes = diff_schemas(source, target)

    if args.print_plan:
        plan = [
            {
                "change_type": c.change_type,
                "table": c.table_name,
                "column": c.column_name,
                "details": c.details,
            }
            for c in changes
        ]
        print(json.dumps(plan, indent=2))

    if not changes:
        print("No schema differences found. Nothing to migrate.")
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    forward_path = args.out_dir / f"V1__{args.name}.sql"
    rollback_path = args.out_dir / f"U1__{args.name}.sql"

    forward_path.write_text(generate_forward_sql(changes, args.dialect), encoding="utf-8")
    rollback_path.write_text(generate_rollback_sql(changes, args.dialect), encoding="utf-8")

    print(f"Detected {len(changes)} change(s)")
    print(f"Forward : {forward_path}")
    print(f"Rollback: {rollback_path}")


if __name__ == "__main__":
    main()
