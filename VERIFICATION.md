# Manual Verification Checklist

## Staged Plan Summary

| Stage | Description |
|-------|-------------|
| **Stage 1** | DB CRUD: `list_projects`, `get_project`, `rename_project`, `delete_project`, `list_shafts`, `get_shaft`, `upsert_shaft`, `delete_shaft`, `get_levels`, `save_levels` |
| **Stage 2** | Main menu (Create / Open / Rename / Delete / Exit) and project menu (Summary, Edit shafts, Edit levels, Generate DXF, Export PDF, Export package, Back) |
| **Stage 3** | Edit shafts: load from DB, Add / Edit / Delete / Capture all from scratch |
| **Stage 4** | Edit levels: load from DB when present, reuse module2 editor; else capture from scratch |
| **Stage 5** | DXF/PDF generation runs from DB state (no re-prompting) |

---

## How to Run from Terminal

1. **Install and run**
   ```bash
   cd wallstakeofftool
   pip install -e .
   python -m shaftwallstakeofftool.main
   ```
   Or from `src` with PYTHONPATH:
   ```bash
   cd wallstakeofftool
   pip install -r requirements.txt   # or: pip install -e .
   set PYTHONPATH=src
   python -m shaftwallstakeofftool.main
   ```

2. **Main menu**
   - You should see: **Wall Stakeoff Tool** and options: Create new project, Open existing project, Rename project, Delete project, Exit.

3. **Create new project**
   - Choose "Create new project", enter a project name and dimension format.
   - You should enter the **project menu** with: View summary, Edit shafts, Edit levels & heights, Generate DXF, Export PDF, Export package (DXF+PDF), Back.

4. **Open existing project**
   - From main menu choose "Open existing project".
   - You should see a list: `project_name • shafts_count • levels_count • last_updated`.
   - Select one to open that project’s menu.

5. **Edit shafts**
   - From project menu choose "Edit shafts (add / edit / delete)".
   - With no shafts: options are Add shaft, Capture all from scratch, Back.
   - With shafts: Add shaft, Edit shaft, Delete shaft, Capture all from scratch, Back.
   - Add one shaft, then Edit it (defaults from DB), then Delete (with confirm).

6. **Edit levels & heights**
   - With no levels: full capture flow (Module 2).
   - With existing levels: current levels/deltas shown, then same edit flow (rename, insert, delete, edit step height). Save updates DB.

7. **Generate DXF / Export PDF**
   - With shafts and levels in DB, choose "Generate DXF" then "Export PDF" (or "Export package").
   - No re-prompting for shafts/levels; data comes from DB.
   - Check `output/<project_name>_shafts.dxf` and `output/<project_name>_shafts.pdf`.

8. **Rename / Delete project**
   - From main menu: Rename project → select project, enter new name.
   - Delete project → select project, confirm. State clears if current project was deleted.

---

## How to Run Tests

From project root:

```bash
pip install -e .
set PYTHONPATH=src
python -m unittest discover -s tests -p "test_*.py" -v
```

On Unix/macOS use `export PYTHONPATH=src` instead of `set PYTHONPATH=src`.

Tests cover: `list_projects`, `get_project`, `rename_project`, `delete_project`, `list_shafts`, `get_shaft`, `upsert_shaft`, `delete_shaft`, `get_levels`, `save_levels` using a temporary SQLite file.

---

## DB Location

- Default DB file: `data/shaftwallstakeofftool.sqlite3` (created from project root when the app runs).
- Same DB is used for Create/Open/Rename/Delete and for loading shafts/levels for DXF/PDF.
