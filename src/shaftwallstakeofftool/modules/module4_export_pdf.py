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
        # Get bounding box
        bbox = entity.bbox()
        if bbox:
            min_x, min_y = bbox.extmin
            max_x, max_y = bbox.extmax
            frames.append({
                "entity": entity,
                "bbox": (min_x, min_y, max_x, max_y),
                "width": max_x - min_x,
                "height": max_y - min_y,
            })
    
    return frames


def choose_sheet_size(width_mm: float, height_mm: float) -> Tuple[str, Tuple[float, float], bool]:
    """
    Choose smallest Arch sheet size that fits the bbox.
    Returns: (sheet_name, (width, height), landscape)
    """
    # Try both orientations
    for landscape in [False, True]:
        if landscape:
            w, h = height_mm, width_mm
        else:
            w, h = width_mm, height_mm
        
        # Find smallest sheet that fits
        best_sheet = None
        best_area = float('inf')
        
        for sheet_name, (sw, sh) in ARCH_SHEET_SIZES.items():
            if w <= sw and h <= sh:
                area = sw * sh
                if area < best_area:
                    best_area = area
                    best_sheet = (sheet_name, (sw, sh), landscape)
        
        if best_sheet:
            return best_sheet
    
    # Fallback to largest sheet
    return ("ARCH_E", ARCH_SHEET_SIZES["ARCH_E"], False)


def render_frame_to_matplotlib(doc, frame_info: dict, sheet_size: Tuple[float, float], landscape: bool) -> plt.Figure:
    """Render entities within frame bbox to matplotlib figure"""
    min_x, min_y, max_x, max_y = frame_info["bbox"]
    width = max_x - min_x
    height = max_y - min_y
    
    sheet_w, sheet_h = sheet_size
    
    # Create figure with sheet size
    fig = plt.figure(figsize=(sheet_w / 25.4, sheet_h / 25.4), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, sheet_w)
    ax.set_ylim(0, sheet_h)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Center the frame content on the sheet
    content_center_x = (min_x + max_x) / 2
    content_center_y = (min_y + max_y) / 2
    sheet_center_x = sheet_w / 2
    sheet_center_y = sheet_h / 2
    
    offset_x = sheet_center_x - content_center_x
    offset_y = sheet_center_y - content_center_y
    
    # Render entities from modelspace that are within or intersect the frame
    msp = doc.modelspace()
    
    for entity in msp:
        if entity.dxf.layer == LAYER_SHEET_FRAME:
            continue
        
        # Get entity bbox
        try:
            entity_bbox = entity.bbox()
            if not entity_bbox:
                continue
            
            e_min_x, e_min_y = entity_bbox.extmin
            e_max_x, e_max_y = entity_bbox.extmax
            
            # Check if entity intersects frame
            if e_max_x < min_x or e_min_x > max_x or e_max_y < min_y or e_min_y > max_y:
                continue
            
            # Draw entity based on type
            if entity.dxftype() == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                ax.plot(
                    [start.x + offset_x, end.x + offset_x],
                    [start.y + offset_y, end.y + offset_y],
                    color='black',
                    linewidth=0.5,
                )
            
            elif entity.dxftype() == "LWPOLYLINE":
                points = list(entity.vertices())
                if points:
                    xs = [p[0] + offset_x for p in points]
                    ys = [p[1] + offset_y for p in points]
                    if entity.is_closed:
                        xs.append(xs[0])
                        ys.append(ys[0])
                    ax.plot(xs, ys, color='black', linewidth=0.5)
            
            elif entity.dxftype() == "TEXT":
                pos = entity.dxf.insert
                text = entity.dxf.text
                height = entity.dxf.height
                ax.text(
                    pos.x + offset_x,
                    pos.y + offset_y,
                    text,
                    fontsize=height * 0.7,  # Approximate scaling
                    ha='left',
                    va='bottom',
                )
        
        except Exception:
            # Skip entities that can't be rendered
            continue
    
    return fig


def module4_export_pdf(dxf_path: Path, output_pdf_path: Path) -> None:
    """
    Convert DXF to multi-page PDF.
    
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
            
            # Choose sheet size
            sheet_name, sheet_size, landscape = choose_sheet_size(width, height)
            
            # Render frame to matplotlib
            fig = render_frame_to_matplotlib(doc, frame_info, sheet_size, landscape)
            
            # Add to PDF
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
