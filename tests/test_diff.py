import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from diff_engine import diff_schemas
from schema_loader import load_schema


class DiffTests(unittest.TestCase):
    def test_sample_diff(self):
        source = load_schema(ROOT / "samples" / "schema_v1.json")
        target = load_schema(ROOT / "samples" / "schema_v2.json")
        changes = diff_schemas(source, target)
        types = {c.change_type for c in changes}
        self.assertIn("CREATE_TABLE", types)
        self.assertIn("ADD_COLUMN", types)
        self.assertIn("ALTER_COLUMN", types)
        self.assertTrue(any(c.table_name == "audit_log" for c in changes))


if __name__ == "__main__":
    unittest.main()
