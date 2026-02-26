#!/usr/bin/env python3
"""Test script to verify linear wall behavior without manual height prompts."""

import tempfile
from pathlib import Path
import sys
from io import StringIO

from shaftwallstakeofftool.modules.module5_db import DB, DBConfig
from shaftwallstakeofftool.app.controller import AppController
from shaftwallstakeofftool.app.state import AppPaths
from shaftwallstakeofftool.ui.base import UI

def test_linear_wall_with_levels():
    """Test linear wall addition when levels exist."""
    print("\n=== Test 1: Linear Wall with Levels ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = DB(DBConfig(db_path=tmp_path / "test.db"))
        
        # Create project with levels
        project_id = db.get_or_create_project("TestProject", "MM_DECIMAL_2")
        db.save_levels("TestProject", ["L1", "L2", "L3"], [3000.0, 3500.0])
        
        # Simulate user inputs for adding a linear wall
        inputs = [
            "TestProject",  # Select project
            "2",  # Edit linear walls
            "1",  # Add wall
            "Wall-A",  # Wall name
            "F",  # Grid line
            "1",  # From grid
            "5",  # To grid
            "4500",  # Length in mm
            "",  # Notes (empty)
            "0",  # From level: L1
            "2",  # To level: L3
            "4",  # Back
            "6",  # Exit
        ]
        
        ui = MockUI(inputs)
        paths = AppPaths(output_dir=tmp_path, exports_dir=tmp_path)
        config = AppConfig(db_cfg=DBConfig(db_path=tmp_path / "test.db"))
        controller = AppController(config=config, ui=ui, paths=paths)
        
        # Run controller to add linear wall
        controller.run()
        
        # Verify the wall was created correctly
        walls = db.get_linear_walls(project_id)
        assert len(walls) == 1, f"Expected 1 wall, got {len(walls)}"
        
        wall = walls[0]
        print(f"Wall created: {wall}")
        
        assert wall["name"] == "Wall-A"
        assert wall["grid_line"] == "F"
        assert wall["from_grid"] == "1"
        assert wall["to_grid"] == "5"
        assert wall["length_mm"] == 4500.0
        assert wall["level_from"] == "L1"
        assert wall["level_to"] == "L3"
        
        # Check computed height (L1->L3 = 3000 + 3500 = 6500mm)
        assert wall["height_mm"] == 6500.0, f"Expected height 6500.0, got {wall['height_mm']}"
        
        print("✓ Wall created with levels L1->L3")
        print(f"✓ Height computed correctly: {wall['height_mm']}mm")


def test_linear_wall_without_levels():
    """Test linear wall addition when no levels exist."""
    print("\n=== Test 2: Linear Wall without Levels ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = DB(DBConfig(db_path=tmp_path / "test.db"))
        
        # Create project without levels
        project_id = db.get_or_create_project("TestProject2", "MM_DECIMAL_2")
        
        # Simulate user inputs for adding a linear wall
        inputs = [
            "TestProject2",  # Select project
            "2",  # Edit linear walls
            "1",  # Add wall
            "Wall-B",  # Wall name
            "G",  # Grid line
            "2",  # From grid
            "6",  # To grid
            "5000",  # Length in mm
            "No levels test",  # Notes
            "4",  # Back
            "6",  # Exit
        ]
        
        ui = MockUI(inputs)
        paths = AppPaths(output_dir=tmp_path, exports_dir=tmp_path)
        config = AppConfig(db_cfg=DBConfig(db_path=tmp_path / "test.db"))
        controller = AppController(config=config, ui=ui, paths=paths)
        
        # Run controller to add linear wall
        controller.run()
        
        # Verify the wall was created correctly
        walls = db.get_linear_walls(project_id)
        assert len(walls) == 1, f"Expected 1 wall, got {len(walls)}"
        
        wall = walls[0]
        print(f"Wall created: {wall}")
        
        assert wall["name"] == "Wall-B"
        assert wall["grid_line"] == "G"
        assert wall["from_grid"] == "2"
        assert wall["to_grid"] == "6"
        assert wall["length_mm"] == 5000.0
        assert wall["level_from"] is None
        assert wall["level_to"] is None
        assert wall["height_mm"] == 0.0
        assert wall["notes"] == "No levels test"
        
        print("✓ Wall created without level references")
        print("✓ Height defaulted to 0.0 as expected")


if __name__ == "__main__":
    try:
        test_linear_wall_with_levels()
        test_linear_wall_without_levels()
        print("\n✅ All tests passed! Linear walls work correctly without manual height prompts.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)