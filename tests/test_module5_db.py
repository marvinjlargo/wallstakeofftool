"""Simple tests for module5_db CRUD (list/get/rename/delete projects, shafts, levels)."""

import tempfile
import unittest
from pathlib import Path

# Allow importing package from repo root when running: python -m unittest discover -s tests
import sys
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from shaftwallstakeofftool.modules.module5_db import DB, DBConfig


class TestModule5DB(unittest.TestCase):
    """Test DB CRUD using a temporary SQLite file."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "test.sqlite3"
        self.db = DB(DBConfig(db_path=self.db_path))

    def tearDown(self) -> None:
        self.db.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()
        Path(self.tmpdir).rmdir()

    def test_list_projects_empty(self) -> None:
        self.assertEqual(self.db.list_projects(), [])

    def test_get_project_missing(self) -> None:
        self.assertIsNone(self.db.get_project("nonexistent"))

    def test_create_and_list_projects(self) -> None:
        pid1 = self.db.get_or_create_project("ProjA", "MM_DECIMAL_2")
        pid2 = self.db.get_or_create_project("ProjB", "FT_DECIMAL_2")
        self.assertIsNotNone(pid1)
        self.assertIsNotNone(pid2)
        listed = self.db.list_projects()
        self.assertEqual(len(listed), 2)
        names = {p["name"] for p in listed}
        self.assertEqual(names, {"ProjA", "ProjB"})
        for p in listed:
            self.assertIn("shafts_count", p)
            self.assertIn("levels_count", p)
            self.assertIn("updated_at", p)

    def test_get_project(self) -> None:
        self.db.get_or_create_project("ProjA", "MM_DECIMAL_2")
        proj = self.db.get_project("ProjA")
        self.assertIsNotNone(proj)
        self.assertEqual(proj["name"], "ProjA")
        self.assertEqual(proj["dim_format"], "MM_DECIMAL_2")
        self.assertIn("id", proj)

    def test_rename_project(self) -> None:
        self.db.get_or_create_project("Old", "MM_DECIMAL_2")
        self.db.rename_project("Old", "New")
        self.assertIsNone(self.db.get_project("Old"))
        self.assertIsNotNone(self.db.get_project("New"))

    def test_rename_project_missing(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.db.rename_project("NoSuch", "New")
        self.assertIn("not found", str(ctx.exception))

    def test_delete_project(self) -> None:
        self.db.get_or_create_project("ToDelete", "MM_DECIMAL_2")
        self.db.delete_project("ToDelete")
        self.assertIsNone(self.db.get_project("ToDelete"))
        self.assertEqual(len(self.db.list_projects()), 0)

    def test_list_shafts_empty(self) -> None:
        self.db.get_or_create_project("P", "MM_DECIMAL_2")
        self.assertEqual(self.db.list_shafts("P"), [])

    def test_upsert_and_list_shafts(self) -> None:
        self.db.get_or_create_project("P", "MM_DECIMAL_2")
        shaft = {
            "name": "S1",
            "grid_left": "A", "grid_right": "B", "grid_bottom": "C", "grid_top": "D",
            "width_mm": 100.0, "height_mm": 200.0,
        }
        self.db.upsert_shaft("P", shaft)
        listed = self.db.list_shafts("P")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["name"], "S1")
        self.assertEqual(listed[0]["width_mm"], 100.0)
        got = self.db.get_shaft("P", "S1")
        self.assertIsNotNone(got)
        self.assertEqual(got["name"], "S1")

    def test_delete_shaft(self) -> None:
        self.db.get_or_create_project("P", "MM_DECIMAL_2")
        self.db.upsert_shaft("P", {
            "name": "S1", "grid_left": "A", "grid_right": "B",
            "grid_bottom": "C", "grid_top": "D", "width_mm": 100.0, "height_mm": 200.0,
        })
        self.db.delete_shaft("P", "S1")
        self.assertEqual(len(self.db.list_shafts("P")), 0)
        self.assertIsNone(self.db.get_shaft("P", "S1"))

    def test_get_levels_empty(self) -> None:
        self.db.get_or_create_project("P", "MM_DECIMAL_2")
        levels, deltas = self.db.get_levels("P")
        self.assertEqual(levels, [])
        self.assertEqual(deltas, [])

    def test_save_and_get_levels(self) -> None:
        self.db.get_or_create_project("P", "MM_DECIMAL_2")
        pid = self.db.get_project("P")["id"]
        self.db.replace_levels_and_steps(
            pid,
            level_names_in_order=["L1", "L2", "L3"],
            deltas_mm_between_consecutive=[100.0, 150.0],
        )
        levels, deltas = self.db.get_levels("P")
        self.assertEqual(levels, ["L1", "L2", "L3"])
        self.assertEqual(deltas, [100.0, 150.0])

    def test_save_levels_by_name(self) -> None:
        self.db.get_or_create_project("P", "MM_DECIMAL_2")
        self.db.save_levels("P", ["Bottom", "Top"], [200.0])
        levels, deltas = self.db.get_levels("P")
        self.assertEqual(levels, ["Bottom", "Top"])
        self.assertEqual(deltas, [200.0])


if __name__ == "__main__":
    unittest.main()
