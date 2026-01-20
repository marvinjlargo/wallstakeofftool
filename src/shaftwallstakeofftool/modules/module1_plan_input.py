"""Module 1: Plan Input (Grid-to-Grid + Dimension Format)"""

from typing import Dict, Any, List, Literal
from ..ui.base import UI
from ..services.units import parse_dimension_to_mm, format_mm, DimFormat


def module1_plan_input_terminal(ui: UI) -> Dict[str, Any]:
    """
    Collect shaft plan inputs via terminal UI.
    Selects dimension format at the beginning.
    
    Returns:
        {
            "dim_format": DimFormat,
            "shafts": [
                {
                    "name": str,
                    "grid_left": str,
                    "grid_right": str,
                    "grid_bottom": str,
                    "grid_top": str,
                    "width_mm": float,
                    "height_mm": float
                },
                ...
            ]
        }
    """
    ui.banner("Shaft Walls Takeoff Tool\nModule 1 - Plan Input (Grid-to-Grid)")

    # Choose dimension format
    dim_choice_idx = ui.prompt_choice(
        "Choose dimension format:",
        [
            "mm (decimal, 2 decimals)",
            "feet (decimal, 2 decimals)",
            "feet-inches (fractions to 1/4\")",
        ],
        default_index=0,
    )

    if dim_choice_idx == 0:
        selected_format: DimFormat = "MM_DECIMAL_2"
    elif dim_choice_idx == 1:
        selected_format = "FT_DECIMAL_2"
    else:
        selected_format = "FT_IN_FRAC_QUARTER"

    format_display = ["mm (decimal, 2 decimals)", "feet (decimal, 2 decimals)", "feet-inches (fractions to 1/4\")"][dim_choice_idx]
    ui.info(f"All dimensions will be interpreted as: {format_display}")
    ui.info("Internally, values will be stored in millimeters.")

    # Number of shafts
    n = ui.prompt_int("How many shaft walls?", min_value=1)

    shafts: List[Dict[str, Any]] = []

    # Loop through each shaft
    for i in range(1, n + 1):
        ui.info("")
        ui.info("-----------------------------------")
        ui.info(f"Shaft {i} of {n}")

        # Name
        name = ui.prompt_string("Shaft name", default=str(i), allow_empty=False)

        # Gridline references
        ui.info("Gridline references (enter as text):")
        grid_left = ui.prompt_string("  Left gridline", allow_empty=False)
        grid_right = ui.prompt_string("  Right gridline", allow_empty=False)
        grid_bottom = ui.prompt_string("  Bottom gridline", allow_empty=False)
        grid_top = ui.prompt_string("  Top gridline", allow_empty=False)

        # Plan dimensions
        ui.info(f"Plan dimensions in {format_display}:")
        width_text = ui.prompt_string("  Width (left -> right)", allow_empty=False)
        height_text = ui.prompt_string("  Height (bottom -> top)", allow_empty=False)

        try:
            width_mm = parse_dimension_to_mm(width_text, selected_format)
            height_mm = parse_dimension_to_mm(height_text, selected_format)
        except ValueError as e:
            ui.error(f"Invalid dimension: {e}")
            ui.warn("Re-enter this shaft.")
            continue

        # Validate dimensions
        if width_mm <= 0:
            ui.error("ERROR: Width must be > 0. Re-enter this shaft.")
            continue
        if height_mm <= 0:
            ui.error("ERROR: Height must be > 0. Re-enter this shaft.")
            continue

        # Create shaft dict
        shaft = {
            "name": name,
            "grid_left": grid_left,
            "grid_right": grid_right,
            "grid_bottom": grid_bottom,
            "grid_top": grid_top,
            "width_mm": width_mm,
            "height_mm": height_mm,
        }

        shafts.append(shaft)

        # Confirmation summary
        ui.info(f"Saved: {name}")
        ui.info(f"   Width  = {format_mm(width_mm, selected_format)}")
        ui.info(f"   Height = {format_mm(height_mm, selected_format)}")
        ui.info(f"   Grids  = {grid_left} to {grid_right}, {grid_bottom} to {grid_top}")

    # End summary
    ui.info("")
    ui.info("Module 1 complete.")
    ui.info(f"Captured {len(shafts)} shaft wall(s).")

    return {
        "dim_format": selected_format,
        "shafts": shafts,
    }
