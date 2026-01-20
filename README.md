# Shaft Walls Takeoff Tool

A terminal-based tool for creating shaft wall elevation drawings from plan inputs.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install as a package:
```bash
pip install -e .
```

## Running

Run the application:
```bash
python -m shaftwallstakeofftool.main
```

Or if installed as a package:
```bash
shaftwallstakeofftool
```

## Terminal Workflow

1. **Module 1 - Input Shafts**: Define shaft walls by gridline references and plan dimensions
2. **Module 2 - Input Levels + Heights**: Define building levels and heights between consecutive levels
3. **Module 3 - Generate DXF**: Create DXF file with elevation views for each shaft
4. **Module 4 - Export PDF**: Convert DXF to multi-page PDF with automatic sheet sizing
5. **Download Options**: Copy last generated DXF or PDF to Downloads folder

## Output Locations

- Database: `./data/shaftwallstakeofftool.sqlite3`
- DXF files: `./output/{project_name}_shafts.dxf`
- PDF files: `./output/{project_name}_shafts.pdf`

## Dimension Formats

The tool supports three dimension formats:
- **MM_DECIMAL_2**: Millimeters with 2 decimal places
- **FT_DECIMAL_2**: Feet with 2 decimal places
- **FT_IN_FRAC_QUARTER**: Feet-inches with fractions to 1/4"

All values are stored internally in millimeters.
