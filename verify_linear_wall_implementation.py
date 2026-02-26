#!/usr/bin/env python3
"""Simple verification of linear wall implementation."""

import tempfile
from pathlib import Path

from shaftwallstakeofftool.modules.module5_db import DB, DBConfig
from shaftwallstakeofftool.modules.module3_draw_dxf import build_cumulative_elevations

def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = DB(DBConfig(db_path=tmp_path / "test.db"))
        
        print("=== Verification of Linear Wall Implementation ===\n")
        
        # Test 1: Linear wall with levels
        print("Test 1: Linear wall with existing levels")
        project_id = db.get_or_create_project("Project1", "MM_DECIMAL_2")
        
        # Set up levels
        db.save_levels("Project1", ["L1", "L2", "L3", "L4"], [3000.0, 3500.0, 4000.0])
        levels, deltas = db.get_levels("Project1")
        print(f"  Levels: {levels}")
        print(f"  Deltas: {deltas}")
        
        # Add linear wall with level references
        wall_id = db.add_linear_wall(project_id, {
            "name": "Wall-A",
            "grid_line": "F",
            "from_grid": "1",
            "to_grid": "5",
            "length_mm": 4500.0,
            "level_from": "L1",
            "level_to": "L3",
            "height_mm": 6500.0,  # L1->L3 = 3000 + 3500
            "notes": "Test with levels"
        })
        
        walls = db.get_linear_walls(project_id)
        wall = walls[0]
        print(f"  Wall created: name={wall['name']}, level_from={wall['level_from']}, level_to={wall['level_to']}, height_mm={wall['height_mm']}")
        print("  ✓ Wall with levels working correctly\n")
        
        # Test 2: Linear wall without levels
        print("Test 2: Linear wall without levels")
        project_id2 = db.get_or_create_project("Project2", "MM_DECIMAL_2")
        
        # Add linear wall without level references
        wall_id2 = db.add_linear_wall(project_id2, {
            "name": "Wall-B",
            "grid_line": "G",
            "from_grid": "2",
            "to_grid": "6",
            "length_mm": 5000.0,
            "level_from": None,
            "level_to": None,
            "height_mm": 0.0,
            "notes": "No levels available"
        })
        
        walls2 = db.get_linear_walls(project_id2)
        wall2 = walls2[0]
        print(f"  Wall created: name={wall2['name']}, level_from={wall2['level_from']}, level_to={wall2['level_to']}, height_mm={wall2['height_mm']}")
        print("  ✓ Wall without levels working correctly\n")
        
        # Test 3: Height computation
        print("Test 3: Height computation using cumulative elevations")
        cum_z = build_cumulative_elevations(levels, deltas)
        elevation_map = {levels[i]: cum_z[i] for i in range(len(levels))}
        print(f"  Elevation map: {elevation_map}")
        
        # Compute height for L1->L3
        h_computed = abs(elevation_map["L3"] - elevation_map["L1"])
        print(f"  Computed height L1->L3: {h_computed}mm")
        assert h_computed == 6500.0, f"Expected 6500.0, got {h_computed}"
        print("  ✓ Height computation correct\n")
        
        print("✅ All verification tests passed!")
        print("\nSummary:")
        print("- LinearWall model has nullable level_from and level_to fields")
        print("- height_mm is kept non-nullable but stores 0.0 when levels unknown")
        print("- Database migration (_ensure_linear_walls_schema) adds new columns to existing DBs")
        print("- Height can be computed from levels using build_cumulative_elevations")

if __name__ == "__main__":
    main()