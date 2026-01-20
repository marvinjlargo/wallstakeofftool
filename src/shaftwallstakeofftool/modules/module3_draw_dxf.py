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


def draw_level_schedule(
    msp,
    origin_xy: Tuple[float, float],
    levels: List[str],
    cum_z_list: List[float],
    schedule_width_mm: float,
    total_height_mm: float,
) -> None:
    """
    Draw level schedule column on the LEFT.
    For each level: horizontal tick line + text (level name + elevation in mm).
    """
    x, base_y = origin_xy
    text_height = 5  # mm
    tick_length = 20  # mm
    
    for i, z in enumerate(cum_z_list):
        y_line = base_y + z
        
        # Draw horizontal tick line
        msp.add_line(
            (x, y_line),
            (x + tick_length, y_line),
            dxfattribs={"layer": LAYER_LEVEL_LINES},
        )
        
        # Add text: level name (top) and elevation (bottom)
        level_name = levels[i]
        elevation_mm = int(z)
        
        # Level name
        msp.add_text(
            level_name,
            height=text_height,
            dxfattribs={"layer": LAYER_TEXT},
        ).set_placement((x + tick_length + 5, y_line + text_height * 0.5))
        
        # Elevation value
        msp.add_text(
            str(elevation_mm),
            height=text_height * 0.8,
            dxfattribs={"layer": LAYER_TEXT},
        ).set_placement((x + tick_length + 5, y_line - text_height * 0.3))


def draw_elevation_view(
    msp,
    origin_xy: Tuple[float, float],
    view_width_mm: float,
    view_height_mm: float,
    grid_string: str,
    view_label: str,
    levels: List[str],
    cum_z_list: List[float],
) -> None:
    """
    Draw one elevation view with:
    - Outer rectangle (view boundary)
    - Horizontal level lines at each cum_z[i]
    - Grid bubble at TOP (circle + text)
    - Simple label under the view
    """
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
    for z in cum_z_list:
        y_line = y + z
        msp.add_line(
            (x, y_line),
            (x + view_width_mm, y_line),
            dxfattribs={"layer": LAYER_LEVEL_LINES},
        )
    
    # Grid bubble at TOP of elevation
    bubble_radius = 8  # mm
    bubble_center_x = x + view_width_mm / 2
    bubble_center_y = y + view_height_mm + bubble_radius + 5
    
    # Draw circle
    msp.add_circle(
        (bubble_center_x, bubble_center_y),
        bubble_radius,
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    
    # Add text inside circle (centered)
    bubble_text_height = 4  # mm
    bubble_text = msp.add_text(
        grid_string,
        height=bubble_text_height,
        dxfattribs={"layer": LAYER_TEXT},
    )
    bubble_text.set_placement((bubble_center_x, bubble_center_y))
    bubble_text.dxf.halign = 1  # Center horizontally
    bubble_text.dxf.valign = 1  # Center vertically
    
    # Simple label under the view (centered)
    label_text_height = 5  # mm
    label_text = msp.add_text(
        view_label,
        height=label_text_height,
        dxfattribs={"layer": LAYER_TEXT},
    )
    label_text.set_placement((x + view_width_mm / 2, y - label_text_height * 1.5))
    label_text.dxf.halign = 1  # Center horizontally


def draw_plan_inset(
    msp,
    origin_xy: Tuple[float, float],
    width_mm: float,
    height_mm: float,
    grid_left: str,
    grid_right: str,
    grid_bottom: str,
    grid_top: str,
) -> None:
    """
    Draw a small plan rectangle at TOP-RIGHT with grid labels on 4 sides.
    """
    x, y = origin_xy
    
    # Draw plan rectangle
    msp.add_line(
        (x, y),
        (x + width_mm, y),
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    msp.add_line(
        (x + width_mm, y),
        (x + width_mm, y + height_mm),
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    msp.add_line(
        (x + width_mm, y + height_mm),
        (x, y + height_mm),
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    msp.add_line(
        (x, y + height_mm),
        (x, y),
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    
    # Label 4 sides with grid strings
    text_height = 4  # mm
    label_offset = 5  # mm
    
    # Left side (right-aligned, middle vertically)
    left_text = msp.add_text(
        grid_left,
        height=text_height,
        dxfattribs={"layer": LAYER_TEXT},
    )
    left_text.set_placement((x - label_offset, y + height_mm / 2))
    left_text.dxf.halign = 2  # Right
    left_text.dxf.valign = 1  # Middle
    
    # Right side (left-aligned, middle vertically)
    right_text = msp.add_text(
        grid_right,
        height=text_height,
        dxfattribs={"layer": LAYER_TEXT},
    )
    right_text.set_placement((x + width_mm + label_offset, y + height_mm / 2))
    right_text.dxf.halign = 0  # Left
    right_text.dxf.valign = 1  # Middle
    
    # Bottom side (center-aligned, top vertically)
    bottom_text = msp.add_text(
        grid_bottom,
        height=text_height,
        dxfattribs={"layer": LAYER_TEXT},
    )
    bottom_text.set_placement((x + width_mm / 2, y - label_offset))
    bottom_text.dxf.halign = 1  # Center
    bottom_text.dxf.valign = 3  # Top
    
    # Top side (center-aligned, bottom vertically)
    top_text = msp.add_text(
        grid_top,
        height=text_height,
        dxfattribs={"layer": LAYER_TEXT},
    )
    top_text.set_placement((x + width_mm / 2, y + height_mm + label_offset))
    top_text.dxf.halign = 1  # Center
    top_text.dxf.valign = 0  # Bottom


def draw_title_block(msp, origin_xy: Tuple[float, float], shaft: Dict[str, Any]) -> None:
    """
    Draw title block at BOTTOM-RIGHT.
    Text:
      "Shaft {name}"
      "Grids: {grid_left}-{grid_right} / {grid_bottom}-{grid_top}"
    """
    x, y = origin_xy
    text_height = 10  # mm
    
    # Shaft name
    msp.add_text(
        f"Shaft {shaft['name']}",
        height=text_height,
        dxfattribs={"layer": LAYER_TEXT},
    ).set_placement((x, y))
    
    # Grids
    grid_text = f"Grids: {shaft['grid_left']}-{shaft['grid_right']} / {shaft['grid_bottom']}-{shaft['grid_top']}"
    msp.add_text(
        grid_text,
        height=text_height * 0.8,
        dxfattribs={"layer": LAYER_TEXT},
    ).set_placement((x, y - text_height * 1.2))


def module3_draw_dxf(
    shafts: List[Dict[str, Any]],
    levels: List[str],
    deltas_mm: List[float],
    output_dxf_path: Path,
) -> None:
    """
    Draw DXF file with elevation views for each shaft.
    Layout: Landscape sheet with level schedule on LEFT, 4 elevations in horizontal row,
    plan inset at TOP-RIGHT, title block at BOTTOM-RIGHT.
    
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
        
        # Level schedule width
        SCHEDULE_WIDTH = 100  # mm
        
        # Elevation view widths
        W_left = W_lr
        W_right = W_lr
        W_bottom = W_bt
        W_top = W_bt
        
        # Plan inset size
        PLAN_INSET_WIDTH = 80  # mm
        PLAN_INSET_HEIGHT = 60  # mm
        
        # Title block area
        TITLE_WIDTH = 200  # mm
        TITLE_HEIGHT = 40  # mm
        
        # Compute page size (LANDSCAPE: width > height)
        # Horizontal layout: [schedule] [left] [right] [bottom] [top]
        content_width = (
            SCHEDULE_WIDTH + VIEW_GAP_MM +
            W_left + VIEW_GAP_MM +
            W_right + VIEW_GAP_MM +
            W_bottom + VIEW_GAP_MM +
            W_top
        )
        
        # Height: max of (elevation height H, plan inset + title block)
        content_height = max(H, PLAN_INSET_HEIGHT + TITLE_HEIGHT + VIEW_GAP_MM)
        
        page_width = content_width + 2 * PAGE_MARGIN_MM
        page_height = content_height + 2 * PAGE_MARGIN_MM
        
        # Ensure landscape (swap if needed)
        if page_width <= page_height:
            page_width, page_height = page_height, page_width
        
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
        
        # Base Y for elevations (aligned with bottom)
        base_y = current_page_origin_y + PAGE_MARGIN_MM
        
        # X positions for horizontal row
        x_schedule = current_page_origin_x + PAGE_MARGIN_MM
        x_left = x_schedule + SCHEDULE_WIDTH + VIEW_GAP_MM
        x_right = x_left + W_left + VIEW_GAP_MM
        x_bottom = x_right + W_right + VIEW_GAP_MM
        x_top = x_bottom + W_bottom + VIEW_GAP_MM
        
        # Draw level schedule (LEFT column)
        draw_level_schedule(
            msp,
            (x_schedule, base_y),
            levels,
            cum_z,
            SCHEDULE_WIDTH,
            H,
        )
        
        # Draw 4 elevation views in horizontal row
        draw_elevation_view(
            msp,
            (x_left, base_y),
            W_left,
            H,
            shaft['grid_left'],
            "Left",
            levels,
            cum_z,
        )
        draw_elevation_view(
            msp,
            (x_right, base_y),
            W_right,
            H,
            shaft['grid_right'],
            "Right",
            levels,
            cum_z,
        )
        draw_elevation_view(
            msp,
            (x_bottom, base_y),
            W_bottom,
            H,
            shaft['grid_bottom'],
            "Bottom",
            levels,
            cum_z,
        )
        draw_elevation_view(
            msp,
            (x_top, base_y),
            W_top,
            H,
            shaft['grid_top'],
            "Top",
            levels,
            cum_z,
        )
        
        # Plan inset at TOP-RIGHT
        plan_inset_x = current_page_origin_x + page_width - PAGE_MARGIN_MM - PLAN_INSET_WIDTH
        plan_inset_y = current_page_origin_y + page_height - PAGE_MARGIN_MM - PLAN_INSET_HEIGHT
        draw_plan_inset(
            msp,
            (plan_inset_x, plan_inset_y),
            PLAN_INSET_WIDTH,
            PLAN_INSET_HEIGHT,
            shaft['grid_left'],
            shaft['grid_right'],
            shaft['grid_bottom'],
            shaft['grid_top'],
        )
        
        # Title block at BOTTOM-RIGHT
        title_x = current_page_origin_x + page_width - PAGE_MARGIN_MM - TITLE_WIDTH
        title_y = current_page_origin_y + PAGE_MARGIN_MM + TITLE_HEIGHT
        draw_title_block(msp, (title_x, title_y), shaft)
        
        # Move origin for next shaft page
        current_page_origin_x += page_width + PAGE_GAP_BETWEEN_SHAFTS_MM
    
    # Save DXF
    output_dxf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(output_dxf_path))
