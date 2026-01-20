"""Application state and shared types"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal

DimFormat = Literal["MM_DECIMAL_2", "FT_DECIMAL_2", "FT_IN_FRAC_QUARTER"]


@dataclass
class AppPaths:
    db_path: Path
    output_dir: Path


@dataclass
class AppState:
    project_id: int
    project_name: str
    dim_format: DimFormat
    last_dxf_path: Optional[Path] = None
    last_pdf_path: Optional[Path] = None
