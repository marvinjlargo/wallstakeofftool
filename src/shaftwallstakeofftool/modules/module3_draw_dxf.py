"""Module 3: Draw DXF Elevations"""

from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
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
from ..services.units import format_mm, DimFormat


def build_cumulative_elevations(levels: List[str], steps: List[float]) -> List[float]:
    """Build cumulative elevations from bottom (0) upward"""
    cum = [0.0]
    for delta in steps:
        cum.append(cum[-1] + delta)
    return cum


def total_height_mm(cum_z_list: List[float]) -> float:
    """Get total height from cumulative elevations"""
    return cum_z_list[-1] if cum_z_list else 0.0


def resolve_linear_wall_height(
    wall: Dict[str, Any],
    levels: List[str],
    deltas_mm: List[float],
) -> Tuple[Optional[float], Optional[str], Optional[str], str]:
    """
    Resolve wall height from project levels using a single source-of-truth policy.

    Returns:
        (computed_height_mm, resolved_from_level, resolved_to_level, note)
    """
    if len(levels) < 2 or len(deltas_mm) != len(levels) - 1:
        return None, None, None, "levels_missing"

    cum_z = build_cumulative_elevations(levels, deltas_mm)
    if len(cum_z) != len(levels):
        return None, None, None, "levels_missing"
    elev_map = {levels[i]: float(cum_z[i]) for i in range(len(levels))}

    wall_level_from = wall.get("level_from")
    wall_level_to = wall.get("level_to")
    if (
        wall_level_from
        and wall_level_to
        and wall_level_from in elev_map
        and wall_level_to in elev_map
    ):
        from_level = wall_level_from
        to_level = wall_level_to
        note = "ok"
    else:
        from_level = levels[0]
        to_level = levels[-1]
        note = "default_full_building_span"

    height_mm = abs(elev_map[to_level] - elev_map[from_level])
    return float(height_mm), from_level, to_level, note


def draw_level_schedule(
    msp,
    origin_xy: Tuple[float, float],
    levels: List[str],
    cum_z_list: List[float],
    schedule_width_mm: float,
    total_height_mm: float,
    label_dim_format: DimFormat,
) -> None:
    """
    Draw level schedule column on the LEFT.
    For each level: horizontal tick line + text (level name + elevation in mm).
    Text heights: 150-250mm for readability after PDF export.
    """
    x, base_y = origin_xy
    text_height = 200  # mm - readable after PDF export
    tick_length = 50  # mm
    line_spacing = 250  # mm - spacing between level name and elevation
    
    for i, z in enumerate(cum_z_list):
        y_line = base_y + z
        
        # Draw horizontal tick line (aligns with level lines)
        msp.add_line(
            (x, y_line),
            (x + tick_length, y_line),
            dxfattribs={"layer": LAYER_LEVEL_LINES},
        )
        
        # Add text: level name (above) and elevation (below)
        level_name = levels[i]
        # z is in mm (internal geometry units). Format text per selected label units.
        elevation_str = format_mm(z, label_dim_format)
        
        # Level name (stacked above)
        level_text = msp.add_text(
            level_name,
            height=text_height,
            dxfattribs={"layer": LAYER_TEXT},
        )
        level_text.set_placement((x + tick_length + 20, y_line + line_spacing))
        
        # Elevation value (stacked below)
        elev_text = msp.add_text(
            elevation_str,
            height=text_height * 0.9,
            dxfattribs={"layer": LAYER_TEXT},
        )
        elev_text.set_placement((x + tick_length + 20, y_line - line_spacing))


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
    - Outer rectangle (LWPOLYLINE) on OUTLINE layer
    - Horizontal level lines at each cum_z[i] across full view width
    - Grid bubble at TOP (circle + text)
    - Label under the view
    """
    x, y = origin_xy
    
    # Outer rectangle as LWPOLYLINE
    rect_points = [
        (x, y),
        (x + view_width_mm, y),
        (x + view_width_mm, y + view_height_mm),
        (x, y + view_height_mm),
    ]
    msp.add_lwpolyline(
        rect_points,
        close=True,
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    
    # Horizontal level lines at each cum_z[i] across full view width
    for z in cum_z_list:
        y_line = y + z
        msp.add_line(
            (x, y_line),
            (x + view_width_mm, y_line),
            dxfattribs={"layer": LAYER_LEVEL_LINES},
        )
    
    # Grid bubble at TOP of elevation (above rectangle)
    bubble_radius = 30  # mm
    bubble_center_x = x + view_width_mm / 2
    bubble_center_y = y + view_height_mm + bubble_radius + 20  # offset above
    
    # Draw circle
    msp.add_circle(
        (bubble_center_x, bubble_center_y),
        bubble_radius,
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    
    # Add text inside circle (centered)
    bubble_text_height = 150  # mm - readable
    bubble_text = msp.add_text(
        grid_string,
        height=bubble_text_height,
        dxfattribs={"layer": LAYER_TEXT},
    )
    bubble_text.set_placement((bubble_center_x, bubble_center_y))
    bubble_text.dxf.halign = 1  # Center horizontally
    bubble_text.dxf.valign = 1  # Center vertically
    
    # Label under the view (centered)
    label_text_height = 200  # mm - readable
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
    Uses LWPOLYLINE for rectangle, TEXT for labels.
    """
    x, y = origin_xy
    
    # Draw plan rectangle as LWPOLYLINE
    rect_points = [
        (x, y),
        (x + width_mm, y),
        (x + width_mm, y + height_mm),
        (x, y + height_mm),
    ]
    msp.add_lwpolyline(
        rect_points,
        close=True,
        dxfattribs={"layer": LAYER_OUTLINE},
    )
    
    # Label 4 sides with grid strings (TEXT only, no dimensions)
    text_height = 150  # mm - readable
    label_offset = 30  # mm
    
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
    text_height = 200  # mm - readable
    line_spacing = 250  # mm
    
    # Shaft name
    name_text = msp.add_text(
        f"Shaft {shaft['name']}",
        height=text_height,
        dxfattribs={"layer": LAYER_TEXT},
    )
    name_text.set_placement((x, y))
    
    # Grids
    grid_text = f"Grids: {shaft['grid_left']}-{shaft['grid_right']} / {shaft['grid_bottom']}-{shaft['grid_top']}"
    grids_text = msp.add_text(
        grid_text,
        height=text_height * 0.9,
        dxfattribs={"layer": LAYER_TEXT},
    )
    grids_text.set_placement((x, y - line_spacing))


def draw_wall_level_break_lines(
    msp,
    x0: float,
    y0: float,
    wall_length_mm: float,
    span_bottom: float,
    span_top: float,
    cum_z: List[float],
) -> None:
    """
    Draw intermediate level break lines inside a linear wall rectangle.
    """
    for z in cum_z:
        if span_bottom < z < span_top:
            y_line = y0 + (z - span_bottom)
            msp.add_line(
                (x0, y_line),
                (x0 + wall_length_mm, y_line),
                dxfattribs={"layer": LAYER_LEVEL_LINES},
            )


def draw_linear_wall_page(
    msp,
    wall: Dict[str, Any],
    levels: List[str],
    deltas_mm: List[float],
    page_origin_x: float,
    page_origin_y: float,
    label_dim_format: DimFormat,
) -> float:
    """
    Draw one full sheet page for a linear wall and return the page width.
    """
    margin = PAGE_MARGIN_MM
    gap = VIEW_GAP_MM
    schedule_w = 300.0
    top_band_h = 400.0
    bottom_band_h = 450.0
    label_band_h = 250.0
    text_h = 180.0

    wall_length_mm = float(wall.get("length_mm") or 0.0)
    if wall_length_mm <= 0:
        wall_length_mm = 1.0

    wall_height_mm, resolved_from, resolved_to, height_note = resolve_linear_wall_height(
        wall, levels, deltas_mm
    )
    placeholder_height_mm = 3000.0
    draw_height_mm = wall_height_mm if wall_height_mm is not None else placeholder_height_mm
    levels_ok = len(levels) >= 2 and len(deltas_mm) == len(levels) - 1
    cum_z = build_cumulative_elevations(levels, deltas_mm) if levels_ok else []
    elev_map = (
        {levels[i]: float(cum_z[i]) for i in range(len(levels))}
        if levels_ok and len(cum_z) == len(levels)
        else {}
    )

    schedule_block_w = schedule_w + gap if levels_ok else 0.0
    page_w = 2 * margin + schedule_block_w + wall_length_mm
    page_h = 2 * margin + top_band_h + bottom_band_h + label_band_h + draw_height_mm
    if page_w <= page_h:
        page_w = page_h + 1000.0

    frame_points = [
        (page_origin_x, page_origin_y),
        (page_origin_x + page_w, page_origin_y),
        (page_origin_x + page_w, page_origin_y + page_h),
        (page_origin_x, page_origin_y + page_h),
    ]
    msp.add_lwpolyline(
        frame_points,
        close=True,
        dxfattribs={"layer": LAYER_SHEET_FRAME},
    )

    y_elev_base = page_origin_y + margin + bottom_band_h + label_band_h
    x_schedule = page_origin_x + margin
    x_wall = x_schedule + schedule_block_w

    if levels_ok:
        draw_level_schedule(
            msp,
            (x_schedule, y_elev_base),
            levels,
            cum_z,
            schedule_w,
            total_height_mm(cum_z),
            label_dim_format,
        )

    wall_rect_points = [
        (x_wall, y_elev_base),
        (x_wall + wall_length_mm, y_elev_base),
        (x_wall + wall_length_mm, y_elev_base + draw_height_mm),
        (x_wall, y_elev_base + draw_height_mm),
    ]
    msp.add_lwpolyline(
        wall_rect_points,
        close=True,
        dxfattribs={"layer": LAYER_OUTLINE},
    )

    if (
        height_note != "levels_missing"
        and resolved_from in elev_map
        and resolved_to in elev_map
        and wall_height_mm is not None
    ):
        z0 = elev_map[resolved_from]
        z1 = elev_map[resolved_to]
        draw_wall_level_break_lines(
            msp,
            x0=x_wall,
            y0=y_elev_base,
            wall_length_mm=wall_length_mm,
            span_bottom=min(z0, z1),
            span_top=max(z0, z1),
            cum_z=cum_z,
        )

    wall_name = wall.get("name", "Wall")
    title = msp.add_text(
        f"Linear Wall {wall_name}",
        height=text_h,
        dxfattribs={"layer": LAYER_TEXT},
    )
    title.set_placement((page_origin_x + margin, page_origin_y + page_h - margin - text_h))

    label_line = msp.add_text(
        (
            f"Grid line {wall.get('grid_line', '')}: "
            f"{wall.get('from_grid', '')} -> {wall.get('to_grid', '')}"
        ),
        height=text_h * 0.9,
        dxfattribs={"layer": LAYER_TEXT},
    )
    label_line.set_placement((page_origin_x + margin, page_origin_y + page_h - margin - (text_h * 2.2)))

    height_for_label_mm = wall_height_mm if wall_height_mm is not None else draw_height_mm
    dims = msp.add_text(
        (
            f"L={format_mm(wall_length_mm, label_dim_format)} "
            f"H={format_mm(height_for_label_mm, label_dim_format)}"
        ),
        height=text_h,
        dxfattribs={"layer": LAYER_TEXT},
    )
    dims.set_placement((page_origin_x + margin, page_origin_y + margin + 120.0))

    if height_note == "levels_missing":
        tbd = msp.add_text(
            "HEIGHT TBD (define levels)",
            height=text_h,
            dxfattribs={"layer": LAYER_TEXT},
        )
        tbd.set_placement((page_origin_x + margin, page_origin_y + margin + 360.0))
    elif height_note == "default_full_building_span" and resolved_from and resolved_to:
        note = msp.add_text(
            f"Height defaults to {resolved_from}->{resolved_to} (set wall levels to change)",
            height=text_h * 0.85,
            dxfattribs={"layer": LAYER_TEXT},
        )
        note.set_placement((page_origin_x + margin, page_origin_y + margin + 360.0))

    resolved_levels_text = (
        f"Levels: {resolved_from}->{resolved_to}" if resolved_from and resolved_to else "Levels: TBD"
    )
    lvl = msp.add_text(
        resolved_levels_text,
        height=text_h * 0.9,
        dxfattribs={"layer": LAYER_TEXT},
    )
    lvl.set_placement((page_origin_x + margin, page_origin_y + margin + 600.0))

    return page_w


def module3_draw_dxf(
    shafts: List[Dict[str, Any]],
    levels: List[str],
    deltas_mm: List[float],
    output_dxf_path: Path,
    label_dim_format: DimFormat,
    linear_walls: Optional[List[Dict[str, Any]]] = None,
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
        # Compute side widths from shaft dimensions
        W_left = shaft["height_mm"]   # left side width
        W_right = shaft["height_mm"]  # right side width
        W_bottom = shaft["width_mm"]  # bottom side width
        W_top = shaft["width_mm"]      # top side width
        
        # Define constants (mm)
        margin = PAGE_MARGIN_MM
        gap = VIEW_GAP_MM
        schedule_w = 300  # mm - level schedule width
        top_band_h = 400  # mm - top band for plan inset
        bottom_band_h = 400  # mm - bottom band for title block
        label_band_h = 200  # mm - label band below elevations
        
        # Plan inset size
        inset_w = 200  # mm
        inset_h = 150  # mm
        
        # Title block size
        title_w = 400  # mm
        title_h = 300  # mm
        
        # Compute page dimensions (LANDSCAPE: width > height)
        # Page width = margins + schedule + gap + (4 elevations with gaps)
        page_w = 2 * margin + schedule_w + gap + (W_left + gap + W_right + gap + W_bottom + gap + W_top)
        
        # Page height = margins + top_band + bottom_band + label_band + elevation height H
        page_h = 2 * margin + top_band_h + bottom_band_h + label_band_h + H
        
        # Ensure landscape: if page_w <= page_h, increase page_w
        if page_w <= page_h:
            page_w = page_h + 1000  # Add extra whitespace to force landscape
        
        # Draw SHEET_FRAME (LWPOLYLINE) around full page
        frame_points = [
            (current_page_origin_x, current_page_origin_y),
            (current_page_origin_x + page_w, current_page_origin_y),
            (current_page_origin_x + page_w, current_page_origin_y + page_h),
            (current_page_origin_x, current_page_origin_y + page_h),
        ]
        msp.add_lwpolyline(
            frame_points,
            close=True,
            dxfattribs={"layer": LAYER_SHEET_FRAME},
        )
        
        # Layout coordinates (all inside the frame)
        # y_elev_base = origin_y + margin + bottom_band_h + label_band_h
        y_elev_base = current_page_origin_y + margin + bottom_band_h + label_band_h
        
        # x_schedule = origin_x + margin
        x_schedule = current_page_origin_x + margin
        
        # x_views0 = x_schedule + schedule_w + gap
        x_views0 = x_schedule + schedule_w + gap
        
        # Place 4 elevation view rectangles horizontally
        x_left = x_views0
        x_right = x_left + W_left + gap
        x_bottom = x_right + W_right + gap
        x_top = x_bottom + W_bottom + gap
        
        # Draw level schedule (LEFT column, aligned with level lines)
        draw_level_schedule(
            msp,
            (x_schedule, y_elev_base),
            levels,
            cum_z,
            schedule_w,
            H,
            label_dim_format,
        )
        
        # Draw 4 elevation views in ONE horizontal row
        draw_elevation_view(
            msp,
            (x_left, y_elev_base),
            W_left,
            H,
            shaft['grid_left'],
            "Left",
            levels,
            cum_z,
        )
        draw_elevation_view(
            msp,
            (x_right, y_elev_base),
            W_right,
            H,
            shaft['grid_right'],
            "Right",
            levels,
            cum_z,
        )
        draw_elevation_view(
            msp,
            (x_bottom, y_elev_base),
            W_bottom,
            H,
            shaft['grid_bottom'],
            "Bottom",
            levels,
            cum_z,
        )
        draw_elevation_view(
            msp,
            (x_top, y_elev_base),
            W_top,
            H,
            shaft['grid_top'],
            "Top",
            levels,
            cum_z,
        )
        
        # Plan inset (TOP-RIGHT of the sheet, inside top band area)
        x_inset = current_page_origin_x + page_w - margin - inset_w
        y_inset = current_page_origin_y + page_h - margin - inset_h
        draw_plan_inset(
            msp,
            (x_inset, y_inset),
            inset_w,
            inset_h,
            shaft['grid_left'],
            shaft['grid_right'],
            shaft['grid_bottom'],
            shaft['grid_top'],
        )
        
        # Title block (BOTTOM-RIGHT, inside bottom band)
        x_title = current_page_origin_x + page_w - margin - title_w
        y_title = current_page_origin_y + margin
        draw_title_block(msp, (x_title, y_title), shaft)
        
        # Move origin for next shaft page
        current_page_origin_x += page_w + PAGE_GAP_BETWEEN_SHAFTS_MM
    
    walls = linear_walls or []
    for wall in walls:
        wall_page_w = draw_linear_wall_page(
            msp,
            wall=wall,
            levels=levels,
            deltas_mm=deltas_mm,
            page_origin_x=current_page_origin_x,
            page_origin_y=current_page_origin_y,
            label_dim_format=label_dim_format,
        )
        current_page_origin_x += wall_page_w + PAGE_GAP_BETWEEN_SHAFTS_MM

    # Save DXF
    output_dxf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(output_dxf_path))
