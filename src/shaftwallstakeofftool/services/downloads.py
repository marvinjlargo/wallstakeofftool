"""Downloads folder utilities"""

from pathlib import Path
import shutil


def get_downloads_dir() -> Path:
    """
    Get the Downloads directory path.
    Falls back to home directory if Downloads doesn't exist.
    
    Returns:
        Path to Downloads directory (or home if Downloads missing)
    """
    home = Path.home()
    downloads = home / "Downloads"
    
    if downloads.exists() and downloads.is_dir():
        return downloads
    
    return home


def save_to_downloads(source_path: Path) -> Path:
    """
    Copy a file to the Downloads directory with versioning if needed.
    
    Args:
        source_path: Source file to copy
        
    Returns:
        Path to the copied file in Downloads
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    downloads_dir = get_downloads_dir()
    dest_path = downloads_dir / source_path.name
    
    # Use versioned name if file exists
    from .file_naming import versioned_name
    dest_path = versioned_name(dest_path)
    
    # Copy file
    shutil.copy2(source_path, dest_path)
    
    return dest_path
