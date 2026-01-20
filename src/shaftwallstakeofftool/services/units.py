"""Dimension parsing and formatting utilities"""

import re
from typing import Literal

DimFormat = Literal["MM_DECIMAL_2", "FT_DECIMAL_2", "FT_IN_FRAC_QUARTER"]

# Conversion constants
MM_PER_FT = 304.8
MM_PER_IN = 25.4


def parse_dimension_to_mm(text: str, dim_format: DimFormat) -> float:
    """
    Parse user input text to millimeters based on dimension format.
    
    Args:
        text: User input string
        dim_format: Format to interpret the text
        
    Returns:
        Value in millimeters as float
    """
    text = text.strip()
    
    if dim_format == "MM_DECIMAL_2":
        # Simple numeric millimeters
        try:
            return float(text)
        except ValueError:
            raise ValueError(f"Invalid mm value: {text}")
    
    elif dim_format == "FT_DECIMAL_2":
        # Numeric feet -> mm
        try:
            feet = float(text)
            return feet * MM_PER_FT
        except ValueError:
            raise ValueError(f"Invalid feet value: {text}")
    
    elif dim_format == "FT_IN_FRAC_QUARTER":
        # Feet-inches with fractions to 1/4"
        return _parse_feet_inches_to_mm(text)
    
    else:
        raise ValueError(f"Unknown dimension format: {dim_format}")


def _parse_feet_inches_to_mm(text: str) -> float:
    """
    Parse feet-inches format like: 10'-3 1/4", 10' 3 1/4", 10-3 1/4, etc.
    Supports:
    - Just feet: "10'", "10"
    - Just inches: "3 1/4\"", "3.25"
    - Feet + inches: "10'-3 1/4\"", "10' 3 1/4\""
    """
    text = text.strip().replace("'", "'").replace('"', '"')
    
    feet = 0.0
    inches = 0.0
    
    # Pattern for feet: number followed by ' or just number at start
    feet_match = re.search(r'^(\d+(?:\.\d+)?)\s*\'?', text)
    if feet_match:
        feet = float(feet_match.group(1))
        text = text[feet_match.end():].strip()
    
    # Pattern for inches: number, optional fraction, optional "
    # Handle fraction like "3 1/4" or "3.25"
    if text:
        # Try fraction pattern first: "3 1/4" or "1/4"
        frac_match = re.search(r'(\d+)\s+(\d+)/(\d+)', text)
        if frac_match:
            whole_inches = float(frac_match.group(1))
            num = float(frac_match.group(2))
            den = float(frac_match.group(3))
            inches = whole_inches + (num / den)
        else:
            # Try decimal inches
            inch_match = re.search(r'(\d+(?:\.\d+)?)', text)
            if inch_match:
                inches = float(inch_match.group(1))
    
    total_inches = (feet * 12) + inches
    
    # Round to nearest 1/4 inch (MVP simplification)
    total_inches = round(total_inches * 4) / 4
    
    return total_inches * MM_PER_IN


def format_mm(mm_value: float, dim_format: DimFormat) -> str:
    """
    Format a millimeter value to display string.
    
    Args:
        mm_value: Value in millimeters
        dim_format: Target format
        
    Returns:
        Formatted string
    """
    if dim_format == "MM_DECIMAL_2":
        return f"{mm_value:.2f} mm"
    
    elif dim_format == "FT_DECIMAL_2":
        feet = mm_value / MM_PER_FT
        return f"{feet:.2f} ft"
    
    elif dim_format == "FT_IN_FRAC_QUARTER":
        total_inches = mm_value / MM_PER_IN
        feet = int(total_inches // 12)
        inches = total_inches % 12
        
        # Round to nearest 1/4"
        quarter_inches = round(inches * 4)
        whole_inches = quarter_inches // 4
        frac_num = quarter_inches % 4
        
        parts = []
        if feet > 0:
            parts.append(f"{feet}'")
        
        if whole_inches > 0 or frac_num > 0:
            if frac_num == 0:
                parts.append(f"{whole_inches}\"")
            elif frac_num == 1:
                parts.append(f"{whole_inches} 1/4\"")
            elif frac_num == 2:
                parts.append(f"{whole_inches} 1/2\"")
            elif frac_num == 3:
                parts.append(f"{whole_inches} 3/4\"")
        
        if not parts:
            return "0\""
        
        return "-".join(parts)
    
    else:
        return f"{mm_value:.2f} mm"
