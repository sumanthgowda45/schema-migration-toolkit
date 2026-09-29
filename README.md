# Schema Migration Toolkit

Python toolkit that **diffs table metadata** between two schema snapshots and generates **forward + rollback SQL migration scripts**.

Designed for platform/schema automation workflows (CREATE/ALTER/DROP tables & columns).

## Features

- Load schema snapshots from JSON
- Detect:
  - new / dropped tables
  - added / dropped columns
  - altered column type / nullability / default
- Generate:
  - forward migration (`V1__*.sql`)
  - rollback migration (`U1__*.sql`)
- MySQL and PostgreSQL dialects
- Transaction-wrapped scripts
- Unit test for sample schema upgrade

## Usage

```bash
python migrate.py \
  --source samples/schema_v1.json \
  --target samples/schema_v2.json \
  --dialect mysql \
  --name ticket_platform_upgrade \
  --print-plan
```

Outputs:

```text
migrations/V1__ticket_platform_upgrade.sql
migrations/U1__ticket_platform_upgrade.sql
```

## Schema JSON format

```json
{
  "tables": [
    {
      "name": "ticket",
      "schema": "platform",
      "columns": [
        {"name": "id", "data_type": "BIGINT", "nullable": false, "primary_key": true}
      ]
    }
  ]
}
```

## Tests

```bash
python -m unittest tests/test_diff.py
```

## Author

Sumanth D Gowda
