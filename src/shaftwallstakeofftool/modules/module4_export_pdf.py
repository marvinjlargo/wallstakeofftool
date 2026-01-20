"""Module 4: DXF to PDF Export"""

from pathlib import Path
from typing import Tuple
import ezdxf
from ezdxf import units
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from ..app.config import LAYER_SHEET_FRAME


# Arch sheet sizes in mm (width, height)
ARCH_SHEET_SIZES = {
    "ARCH_A": (228.6, 304.8),      # 9" x 12"
    "ARCH_B": (304.8, 457.2),      # 12" x 18"
    "ARCH_C": (457.2, 609.6),      # 18" x 24"
    "ARCH_D": (609.6, 914.4),      # 24" x 36"
    "ARCH_E": (914.4, 1219.2),     # 36" x 48"
}


def find_sheet_frames(doc) -> list:
    """Find all SHEET_FRAME polylines in modelspace"""
    msp = doc.modelspace()
    frames = []
    
    for entity in msp.query(f"LWPOLYLINE[layer=='{LAYER_SHEET_FRAME}']"):
        # Compute bounding box manually from vertices
        # LWPOLYLINE doesn't have bbox() method, so we compute from points
        try:
            vertices = list(entity.vertices())
            if not vertices:
                continue
            
            # Extract x and y coordinates
            x_coords = [v[0] for v in vertices]
            y_coords = [v[1] for v in vertices]
            
            # Compute bounding box
            min_x = min(x_coords)
            max_x = max(x_coords)
            min_y = min(y_coords)
            max_y = max(y_coords)
            
            frames.append({
                "entity": entity,
                "bbox": (min_x, min_y, max_x, max_y),
                "width": max_x - min_x,
                "height": max_y - min_y,
            })
        except Exception:
            # Skip entities that can't be processed
            continue
    
    return frames


def choose_sheet_size_landscape(width_mm: float, height_mm: float) -> Tuple[str, Tuple[float, float]]:
    """
    Choose smallest Arch sheet size that fits the bbox in LANDSCAPE orientation.
    Always returns landscape sheet (width >= height).
    Returns: (sheet_name, (width, height))
    """
    # Ensure landscape: if content is portrait, swap dimensions
    if width_mm < height_mm:
        content_w, content_h = height_mm, width_mm
    else:
        content_w, content_h = width_mm, height_mm
    
    # Find smallest landscape sheet that fits
    best_sheet = None
    best_area = float('inf')
    
    for sheet_name, (sw, sh) in ARCH_SHEET_SIZES.items():
        # Ensure sheet is landscape (swap if needed)
        if sw < sh:
            sw, sh = sh, sw
        
        if content_w <= sw and content_h <= sh:
            area = sw * sh
            if area < best_area:
                best_area = area
                best_sheet = (sheet_name, (sw, sh))
    
    if best_sheet:
        return best_sheet
    
    # Fallback to largest sheet in landscape
    sw, sh = ARCH_SHEET_SIZES["ARCH_E"]
    if sw < sh:
        sw, sh = sh, sw
    return ("ARCH_E", (sw, sh))


def render_frame_to_matplotlib(doc, frame_info: dict, sheet_size: Tuple[float, float]) -> plt.Figure:
    """
    Render entities within frame bbox to matplotlib figure.
    Scale-to-fit rendering with coordinate transformation.
    Always renders in LANDSCAPE orientation (sheet width >= height).
    Renders SHEET_FRAME as the page border.
    """
    min_x, min_y, max_x, max_y = frame_info["bbox"]
    content_width = max_x - min_x
    content_height = max_y - min_y
    
    sheet_w, sheet_h = sheet_size
    
    # FORCE LANDSCAPE: swap if needed so sheet_w > sheet_h
    if sheet_w < sheet_h:
        sheet_w, sheet_h = sheet_h, sheet_w
    
    # Margin for scale-to-fit
    margin_mm = 20
    
    # Compute scale factor to fit content within sheet with margins
    scale = min((sheet_w - 2 * margin_mm) / content_width, (sheet_h - 2 * margin_mm) / content_height)
    
    # Create figure with sheet size (in inches) - LANDSCAPE
    fig = plt.figure(figsize=(sheet_w / 25.4, sheet_h / 25.4), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, sheet_w)
    ax.set_ylim(0, sheet_h)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Helper function to transform coordinates (scale-to-fit)
    def transform_x(x):
        return (x - min_x) * scale + margin_mm
    
    def transform_y(y):
        return (y - min_y) * scale + margin_mm
    
    # Helper function to check if point is inside frame bbox
    def point_inside(x, y):
        return min_x <= x <= max_x and min_y <= y <= max_y
    
    # Render entities from modelspace
    msp = doc.modelspace()
    
    for entity in msp:
        try:
            # Draw entity based on type with simple inside-frame checks
            if entity.dxftype() == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                # Draw if either endpoint is inside frame
                if point_inside(start.x, start.y) or point_inside(end.x, end.y):
                    ax.plot(
                        [transform_x(start.x), transform_x(end.x)],
                        [transform_y(start.y), transform_y(end.y)],
                        color='black',
                        linewidth=0.3,
                    )
            
            elif entity.dxftype() == "LWPOLYLINE":
                # IMPORTANT: Render SHEET_FRAME as the page border
                # Do NOT skip SHEET_FRAME - draw it as the page border
                points = list(entity.vertices())
                if points:
                    # Draw if any vertex is inside frame (or if it's the SHEET_FRAME itself)
                    if entity.dxf.layer == LAYER_SHEET_FRAME or any(point_inside(p[0], p[1]) for p in points):
                        xs = [transform_x(p[0]) for p in points]
                        ys = [transform_y(p[1]) for p in points]
                        if entity.is_closed:
                            xs.append(xs[0])
                            ys.append(ys[0])
                        ax.plot(xs, ys, color='black', linewidth=0.3)
            
            elif entity.dxftype() == "TEXT":
                pos = entity.dxf.insert
                # Draw if insert point is inside frame
                if point_inside(pos.x, pos.y):
                    text = entity.dxf.text
                    entity_height_mm = entity.dxf.height
                    # Fontsize calculation based on scaled height
                    fontsize = max(6, entity_height_mm * scale * 0.35)
                    ax.text(
                        transform_x(pos.x),
                        transform_y(pos.y),
                        text,
                        fontsize=fontsize,
                        ha='left',
                        va='bottom',
                    )
            
            elif entity.dxftype() == "MTEXT":
                # Optional: handle MTEXT if present
                try:
                    pos = entity.dxf.insert
                    if point_inside(pos.x, pos.y):
                        text = entity.text
                        entity_height_mm = entity.dxf.char_height
                        fontsize = max(6, entity_height_mm * scale * 0.35)
                        ax.text(
                            transform_x(pos.x),
                            transform_y(pos.y),
                            text,
                            fontsize=fontsize,
                            ha='left',
                            va='bottom',
                        )
                except Exception:
                    # Skip if MTEXT can't be processed
                    pass
            
            elif entity.dxftype() == "CIRCLE":
                # Handle circles (for grid bubbles)
                try:
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    # Draw if center is inside frame
                    if point_inside(center.x, center.y):
                        circle = plt.Circle(
                            (transform_x(center.x), transform_y(center.y)),
                            radius * scale,
                            fill=False,
                            color='black',
                            linewidth=0.3,
                        )
                        ax.add_patch(circle)
                except Exception:
                    pass
        
        except Exception:
            # Skip entities that can't be rendered
            continue
    
    return fig


def module4_export_pdf(dxf_path: Path, output_pdf_path: Path) -> None:
    """
    Convert DXF to multi-page PDF.
    All pages are rendered in LANDSCAPE orientation (width >= height).
    
    Args:
        dxf_path: Path to input DXF file
        output_pdf_path: Path to save PDF file
    """
    if not dxf_path.exists():
        raise FileNotFoundError(f"DXF file not found: {dxf_path}")
    
    # Load DXF
    doc = ezdxf.readfile(str(dxf_path))
    
    # Find all sheet frames
    frames = find_sheet_frames(doc)
    
    if not frames:
        raise ValueError("No SHEET_FRAME entities found in DXF")
    
    # Create PDF
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    
    with PdfPages(str(output_pdf_path)) as pdf:
        for frame_info in frames:
            width = frame_info["width"]
            height = frame_info["height"]
            
            # Choose sheet size (always landscape)
            sheet_name, sheet_size = choose_sheet_size_landscape(width, height)
            
            # Render frame to matplotlib (always landscape)
            fig = render_frame_to_matplotlib(doc, frame_info, sheet_size)
            
            # Add to PDF WITHOUT bbox_inches="tight" (tight cropping breaks sheet look)
            pdf.savefig(fig)
            plt.close(fig)
