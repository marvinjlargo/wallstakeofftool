"""File naming utilities"""

from pathlib import Path


def versioned_name(path: Path) -> Path:
    """
    Return a versioned path if the file exists.
    Examples: file.dxf -> file_v2.dxf -> file_v3.dxf
    
    Args:
        path: Original file path
        
    Returns:
        Path that doesn't exist (original or versioned)
    """
    if not path.exists():
        return path
    
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    
    version = 2
    while True:
        new_name = f"{stem}_v{version}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        version += 1
