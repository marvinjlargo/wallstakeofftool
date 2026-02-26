"""Module 2: Levels + Height Definition"""

from typing import Dict, Any, List, Literal, Tuple
from ..ui.base import UI
from ..services.units import parse_dimension_to_mm, format_mm, DimFormat


def module2_level_height_definition(ui: UI, dim_format: DimFormat) -> Dict[str, Any]:
    """
    Collect levels and heights between consecutive levels.
    
    Returns:
        {
            "levels": [level_name, ...],
            "deltas_mm": [delta1, delta2, ...]  # len = N-1
        }
    """
    ui.banner("Module 2 - Levels + Height Definition")

    # Collect levels in order (bottom -> top)
    levels: List[str] = []
    ui.info("Enter levels in order from bottom to top:")

    level_num = 1
    while True:
        level_name = ui.prompt_string(f"Level {level_num} name", allow_empty=False)
        levels.append(level_name)

        if level_num == 1:
            ui.info(f"Bottom level: {level_name}")
        else:
            ui.info(f"Level {level_num}: {level_name}")

        if not ui.confirm("Add more levels?", default_yes=True):
            break
        level_num += 1

    if len(levels) < 2:
        ui.error("Need at least 2 levels.")
        return {"levels": [], "deltas_mm": []}

    ui.info("")
    ui.info(f"Levels entered ({len(levels)} total):")
    for i, lv in enumerate(levels, start=1):
        ui.info(f"  {i}) {lv}")

    # Collect heights between consecutive levels
    ui.info("")
    ui.info("Enter height between each consecutive level pair:")
    deltas_mm: List[float] = []

    for i in range(len(levels) - 1):
        while True:  # Loop until valid height is entered
            ui.info("")
            ui.info(f"Height from '{levels[i]}' to '{levels[i+1]}':")
            height_text = ui.prompt_string("  Height", allow_empty=False)

            try:
                delta_mm = parse_dimension_to_mm(height_text, dim_format)
                if delta_mm <= 0:
                    ui.error("Height must be > 0. Please re-enter.")
                    continue  # Stay in loop for same pair
                deltas_mm.append(delta_mm)
                break  # Valid height entered, move to next pair
            except ValueError as e:
                ui.error(f"Invalid dimension: {e}")
                ui.warn("Please re-enter this height.")
                # Stay in loop for same pair

    # Simple editing options
    ui.info("")
    if ui.confirm("Edit levels or heights?", default_yes=False):
        levels, deltas_mm = _edit_levels_and_heights(ui, levels, deltas_mm, dim_format)
    
    # Final validation
    if len(deltas_mm) != len(levels) - 1:
        ui.error(f"Internal error: deltas count ({len(deltas_mm)}) doesn't match levels count ({len(levels)}).")
        ui.error("Please re-run Module 2.")
        return {"levels": [], "deltas_mm": []}

    # Final summary
    ui.info("")
    ui.info("Module 2 complete.")
    ui.info(f"Levels: {len(levels)}")
    ui.info(f"Level-to-level steps: {len(deltas_mm)}")
    for i in range(len(deltas_mm)):
        ui.info(
            f"  {levels[i]} → {levels[i+1]}: "
            f"{format_mm(deltas_mm[i], dim_format)} "
            "(stored internally in mm)"
        )

    return {
        "levels": levels,
        "deltas_mm": deltas_mm,
    }


def module2_edit_existing(
    ui: UI,
    levels: List[str],
    deltas_mm: List[float],
    dim_format: DimFormat,
) -> Dict[str, Any]:
    """
    Edit existing levels and heights (e.g. loaded from DB).
    Shows current data and runs the same edit flow (rename, insert, delete, edit step).
    Returns {"levels": [...], "deltas_mm": [...]}.
    """
    if len(levels) < 2 or len(deltas_mm) != len(levels) - 1:
        return {"levels": [], "deltas_mm": []}
    ui.banner("Edit levels & heights (existing data)")
    ui.info(f"Current levels ({len(levels)}):")
    for i, lv in enumerate(levels, start=1):
        ui.info(f"  {i}) {lv}")
    ui.info("Level-to-level steps:")
    for i in range(len(deltas_mm)):
        ui.info(
            f"  {levels[i]} → {levels[i+1]}: "
            f"{format_mm(deltas_mm[i], dim_format)} "
            "(stored internally in mm)"
        )
    ui.info("")
    levels, deltas_mm = _edit_levels_and_heights(ui, levels, deltas_mm, dim_format)
    if len(deltas_mm) != len(levels) - 1:
        ui.error("Edit left data inconsistent; not saving.")
        return {"levels": [], "deltas_mm": []}
    return {"levels": levels, "deltas_mm": deltas_mm}


def _edit_levels_and_heights(ui: UI, levels: List[str], deltas_mm: List[float], dim_format: DimFormat) -> Tuple[List[str], List[float]]:
    """Simple editing interface for levels and heights"""
    while True:
        # Validate before each edit operation
        if len(deltas_mm) != len(levels) - 1:
            ui.error(f"Error: deltas count ({len(deltas_mm)}) doesn't match levels count ({len(levels)}).")
            ui.error("Editing cancelled. Please re-run Module 2.")
            return levels, deltas_mm
        ui.info("")
        ui.info("Edit options:")
        choice = ui.prompt_choice(
            "What would you like to edit?",
            [
                "Rename a level",
                "Insert a level",
                "Delete a level",
                "Edit a step height",
                "Done editing",
            ],
            default_index=4,
        )

        if choice == 4:  # Done
            break

        elif choice == 0:  # Rename level
            ui.info("Select level to rename:")
            idx = ui.prompt_choice("Level:", levels, default_index=0)
            new_name = ui.prompt_string("New name", default=levels[idx], allow_empty=False)
            levels[idx] = new_name

        elif choice == 1:  # Insert level
            ui.info("Select position to insert after:")
            idx = ui.prompt_choice("After level:", levels, default_index=0)
            new_name = ui.prompt_string("New level name", allow_empty=False)
            levels.insert(idx + 1, new_name)
            
            # Need TWO new heights: from previous to new, and from new to next
            # First height: from levels[idx] to new_name
            height1_valid = False
            while not height1_valid:
                height_text1 = ui.prompt_string(f"Height from '{levels[idx]}' to '{new_name}'", allow_empty=False)
                try:
                    delta1 = parse_dimension_to_mm(height_text1, dim_format)
                    if delta1 > 0:
                        height1_valid = True
                    else:
                        ui.error("Height must be > 0. Please re-enter.")
                except ValueError as e:
                    ui.error(f"Invalid dimension: {e}")
            
            # Second height: from new_name to levels[idx+2] (which was originally levels[idx+1])
            height2_valid = False
            while not height2_valid:
                height_text2 = ui.prompt_string(f"Height from '{new_name}' to '{levels[idx+2]}'", allow_empty=False)
                try:
                    delta2 = parse_dimension_to_mm(height_text2, dim_format)
                    if delta2 > 0:
                        height2_valid = True
                    else:
                        ui.error("Height must be > 0. Please re-enter.")
                except ValueError as e:
                    ui.error(f"Invalid dimension: {e}")
            
            # Replace the old single height with two new heights
            deltas_mm[idx] = delta1
            deltas_mm.insert(idx + 1, delta2)

        elif choice == 2:  # Delete level
            if len(levels) <= 2:
                ui.error("Cannot delete - need at least 2 levels.")
                continue
            ui.info("Select level to delete:")
            idx = ui.prompt_choice("Level:", levels, default_index=0)
            if idx == 0:
                # Delete bottom level - remove first step
                deltas_mm.pop(0)
                levels.pop(idx)
            elif idx == len(levels) - 1:
                # Delete top level - remove last step
                deltas_mm.pop(-1)
                levels.pop(idx)
            else:
                # Delete middle level - ask user for new height between remaining neighbors
                ui.info(f"Deleting '{levels[idx]}' will merge steps from '{levels[idx-1]}' to '{levels[idx+1]}'.")
                while True:
                    height_text = ui.prompt_string(
                        f"Enter new height from '{levels[idx-1]}' to '{levels[idx+1]}'",
                        allow_empty=False
                    )
                    try:
                        new_delta = parse_dimension_to_mm(height_text, dim_format)
                        if new_delta > 0:
                            # Replace the two old steps with one new step
                            deltas_mm[idx - 1] = new_delta
                            deltas_mm.pop(idx)
                            levels.pop(idx)
                            break
                        else:
                            ui.error("Height must be > 0. Please re-enter.")
                    except ValueError as e:
                        ui.error(f"Invalid dimension: {e}")

        elif choice == 3:  # Edit step height
            if len(deltas_mm) == 0:
                ui.error("No steps to edit.")
                continue
            ui.info("Select step to edit:")
            step_options = [f"{levels[i]} → {levels[i+1]}" for i in range(len(deltas_mm))]
            step_idx = ui.prompt_choice("Step:", step_options, default_index=0)
            
            while True:  # Loop until valid height is entered
                height_text = ui.prompt_string("New height", allow_empty=False)
                try:
                    delta = parse_dimension_to_mm(height_text, dim_format)
                    if delta > 0:
                        deltas_mm[step_idx] = delta
                        break  # Valid height entered
                    else:
                        ui.error("Height must be > 0. Please re-enter.")
                except ValueError as e:
                    ui.error(f"Invalid dimension: {e}")

    return levels, deltas_mm
