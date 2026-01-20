"""Module 3: Draw DXF Elevations"""

from pathlib import Path
from typing import List, Dict, Any, Tuple
import ezdxf
from ezdxf import units
from ..app.config import (
    PAGE_MARGIN_MM,
    VIEW_GAP_MM,
    TITLE_AREA_HEIGHT_MM,
    PAGE_GAP_BETWEEN_SHAFTS_MM,
    LAYER_SHEET_FRAME,
    LAYER_OUTLINE,
    LAYER_LEVEL_LINES,
    LAYER_TEXT,
    TEXT_LABEL_OFFSET_X,
    TEXT_GAP_ABOVE_VIEW,
)


def build_cumulative_elevations(levels: List[str], steps: List[float]) -> List[float]:
    """Build cumulative elevations from bottom (0) upward"""
    cum = [0.0]
    for delta in steps:
        cum.append(cum[-1] + delta)
    return cum


def total_height_mm(cum_z_list: List[float]) -> float:
    """Get total height from cumulative elevations"""
    return cum_z_list[-1] if cum_z_list else 0.0


def draw_title_block(msp, origin_xy: Tuple[float, float], shaft: Dict[str, Any], levels: List[str]) -> None:
    """Draw minimal title block"""
    x, y = origin_xy
    text_height = 200  # mm
    
    # Shaft name
    msp.add_text(
        f"SHAFT: {shaft['name']}",
        height=text_height,
        dxfattribs={"layer": LAYER_TEXT},
    ).set_placement((x, y))
    
    # Grids
    grid_text = f"GRIDS: {shaft['grid_left']}-{shaft['grid_right']} / {shaft['grid_bottom']}-{shaft['grid_top']}"
    msp.add_text(
        grid_text,
        height=text_height * 0.8,
        dxfattribs={"layer": LAYER_TEXT},
    ).set_placement((x, y - text_height * 1.2))
    
    # Levels
    levels_text = f"LEVELS: {' .. '.join(levels)}"
    msp.add_text(
        levels_text,
        height=text_height * 0.8,
        dxfattribs={"layer": LAYER_TEXT},
    ).set_placement((x, y - text_height * 2.4))


def draw_elevation_view(
    msp,
    origin_xy: Tuple[float, float],
    view_width_mm: float,
    view_height_mm: float,
    side_label: str,
    levels: List[str],
    cum_z_list: List[float],
) -> None:
    """Draw one elevation view with outer rectangle, level lines, and labels"""
    x, y = origin_xy
    
    # Outer rectangle
    msp.add_line(
        (x, y),
        (x + view_width_mm, y),
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    msp.add_line(
        (x + view_width_mm, y),
        (x + view_width_mm, y + view_height_mm),
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    msp.add_line(
        (x + view_width_mm, y + view_height_mm),
        (x, y + view_height_mm),
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    msp.add_line(
        (x, y + view_height_mm),
        (x, y),
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    
    # Horizontal level lines
    text_height = 100  # mm
    for i, z in enumerate(cum_z_list):
        if i == 0 or i == len(cum_z_list) - 1:
            # Skip bottom (0) and top (optional)
            continue
        y_line = y + z
        msp.add_line(
            (x, y_line),
            (x + view_width_mm, y_line),
            dxfattribs={"layer": LAYER_LEVEL_LINES},
        )
        
        # Level name text near left
        msp.add_text(
            levels[i],
            height=text_height,
            dxfattribs={"layer": LAYER_TEXT},
        ).set_placement((x - TEXT_LABEL_OFFSET_X, y_line))
    
    # Side label above view
    msp.add_text(
        side_label,
        height=text_height,
        dxfattribs={"layer": LAYER_TEXT},
    ).set_placement((x, y + view_height_mm + TEXT_GAP_ABOVE_VIEW))


def module3_draw_dxf(
    shafts: List[Dict[str, Any]],
    levels: List[str],
    deltas_mm: List[float],
    output_dxf_path: Path,
) -> None:
    """
    Draw DXF file with elevation views for each shaft.
    
    Args:
        shafts: List of shaft dicts with name, grid_*, width_mm, height_mm
        levels: List of level names (bottom to top)
        deltas_mm: List of heights between consecutive levels (len = N-1)
        output_dxf_path: Path to save DXF file
    """
    # Create DXF document
    doc = ezdxf.new("R2010", units=units.MM)
    
    # Setup layers
    doc.layers.add(LAYER_SHEET_FRAME, color=1)
    doc.layers.add(LAYER_OUTLINE, color=2)
    doc.layers.add(LAYER_LEVEL_LINES, color=3)
    doc.layers.add(LAYER_TEXT, color=7)
    
    msp = doc.modelspace()
    
    # Build cumulative elevations
    cum_z = build_cumulative_elevations(levels, deltas_mm)
    H = total_height_mm(cum_z)
    
    # Page positioning
    current_page_origin_x = 0.0
    current_page_origin_y = 0.0
    
    for shaft in shafts:
        # Compute side widths
        W_lr = shaft["height_mm"]  # left/right side width (plan depth)
        W_bt = shaft["width_mm"]   # bottom/top side width (plan width)
        
        # Compute page size
        page_width = (W_lr + VIEW_GAP_MM + W_lr) + 2 * PAGE_MARGIN_MM
        page_height = TITLE_AREA_HEIGHT_MM + (H + VIEW_GAP_MM + H) + 2 * PAGE_MARGIN_MM
        
        # Draw page frame rectangle
        frame_points = [
            (current_page_origin_x, current_page_origin_y),
            (current_page_origin_x + page_width, current_page_origin_y),
            (current_page_origin_x + page_width, current_page_origin_y + page_height),
            (current_page_origin_x, current_page_origin_y + page_height),
        ]
        msp.add_lwpolyline(
            frame_points,
            close=True,
            dxfattribs={"layer": LAYER_SHEET_FRAME},
        )
        
        # Title block origin
        title_origin = (
            current_page_origin_x + PAGE_MARGIN_MM,
            current_page_origin_y + page_height - PAGE_MARGIN_MM - TITLE_AREA_HEIGHT_MM,
        )
        draw_title_block(msp, title_origin, shaft, levels)
        
        # View origins (2x2 grid)
        top_row_y = current_page_origin_y + PAGE_MARGIN_MM + H + VIEW_GAP_MM
        bot_row_y = current_page_origin_y + PAGE_MARGIN_MM
        
        left_col_x = current_page_origin_x + PAGE_MARGIN_MM
        right_col_x = current_page_origin_x + PAGE_MARGIN_MM + W_lr + VIEW_GAP_MM
        
        # Side labels
        side_left_label = f"ELEV - GRID {shaft['grid_left']}"
        side_right_label = f"ELEV - GRID {shaft['grid_right']}"
        side_bottom_label = f"ELEV - GRID {shaft['grid_bottom']}"
        side_top_label = f"ELEV - GRID {shaft['grid_top']}"
        
        # Draw 4 elevation views
        draw_elevation_view(msp, (left_col_x, top_row_y), W_lr, H, side_left_label, levels, cum_z)
        draw_elevation_view(msp, (right_col_x, top_row_y), W_lr, H, side_right_label, levels, cum_z)
        draw_elevation_view(msp, (left_col_x, bot_row_y), W_bt, H, side_bottom_label, levels, cum_z)
        draw_elevation_view(msp, (right_col_x, bot_row_y), W_bt, H, side_top_label, levels, cum_z)
        
        # Move origin for next shaft page
        current_page_origin_x += page_width + PAGE_GAP_BETWEEN_SHAFTS_MM
    
    # Save DXF
    output_dxf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(output_dxf_path))
