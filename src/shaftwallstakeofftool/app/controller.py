"""Module 6: Application UI Orchestrator"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import csv

from ..ui.base import UI
from ..ui.terminal_ui import TerminalUI
from ..modules.module5_db import DB, DBConfig
from ..modules.module1_plan_input import module1_plan_input_terminal
from ..modules.module2_levels_height import module2_level_height_definition, module2_edit_existing
from ..modules.module3_draw_dxf import module3_draw_dxf, build_cumulative_elevations
from ..modules.module4_export_pdf import module4_export_pdf
from ..services.downloads import save_to_downloads
from ..services.units import parse_dimension_to_mm, format_mm
from .state import AppState, AppPaths, DimFormat


def _format_updated(updated_at) -> str:
    """Format updated_at for display (e.g. 2025-01-15 12:30)."""
    if updated_at is None:
        return "—"
    try:
        return updated_at.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(updated_at)


class AppController:
    """Orchestrates modules + DB + UI"""

    def __init__(self, ui: UI, db: DB, paths: AppPaths):
        self.ui = ui
        self.db = db
        self.paths = paths
        self.state: Optional[AppState] = None

    def start(self) -> None:
        """Start the application: top-level menu then project menu when a project is open."""
        self.ui.banner("Wall Stakeoff Tool")

        while True:
            choice = self.ui.prompt_choice(
                "Main menu",
                [
                    "Create new project",
                    "Open existing project",
                    "Rename project",
                    "Delete project",
                    "Exit",
                ],
                default_index=0,
            )
            if choice == 0:
                self._do_create_project()
                if self.state is not None:
                    self._project_menu_loop()
            elif choice == 1:
                self._do_open_project()
                if self.state is not None:
                    self._project_menu_loop()
            elif choice == 2:
                self._do_rename_project()
            elif choice == 3:
                self._do_delete_project()
            else:
                self.ui.info("Goodbye.")
                return
            if self.state is None:
                self.ui.pause()

    def _do_create_project(self) -> None:
        """Create new project and set state."""
        project_name = self.ui.prompt_string("Project name", default="shaftwallstakeofftool")
        dim_format = self._select_dim_format()
        try:
            project_id = self.db.get_or_create_project(project_name, dim_format)
            self.state = AppState(project_id=project_id, project_name=project_name, dim_format=dim_format)
            self.ui.info(f"Project '{project_name}' created/opened.")
        except Exception as e:
            self.ui.error(str(e))
            self.state = None

    def _do_open_project(self) -> None:
        """Show project list, select one, set state."""
        projects = self.db.list_projects()
        if not projects:
            self.ui.warn("No projects found. Create one from the main menu.")
            self.state = None
            return
        options = [
            f"{p['name']} • {p['shafts_count']} shafts • {p['levels_count']} levels • {_format_updated(p['updated_at'])}"
            for p in projects
        ]
        idx = self.ui.prompt_choice("Open existing project:", options, default_index=0)
        project_name = projects[idx]["name"]
        proj = self.db.get_project(project_name)
        if proj is None:
            self.ui.error("Project not found.")
            self.state = None
            return
        self.state = AppState(
            project_id=proj["id"],
            project_name=proj["name"],
            dim_format=proj["dim_format"],
        )
        self.ui.info(f"Opened project '{project_name}'.")

    def _do_rename_project(self) -> None:
        """Rename a project (list, select, prompt new name)."""
        projects = self.db.list_projects()
        if not projects:
            self.ui.warn("No projects to rename.")
            return
        options = [p["name"] for p in projects]
        idx = self.ui.prompt_choice("Select project to rename:", options, default_index=0)
        old_name = projects[idx]["name"]
        new_name = self.ui.prompt_string("New project name", default=old_name)
        if new_name.strip() == old_name:
            self.ui.info("Unchanged.")
            return
        try:
            self.db.rename_project(old_name, new_name.strip())
            self.ui.info(f"Renamed '{old_name}' to '{new_name}'.")
            if self.state and self.state.project_name == old_name:
                self.state.project_name = new_name
        except ValueError as e:
            self.ui.error(str(e))

    def _do_delete_project(self) -> None:
        """Delete a project (list, select, confirm)."""
        projects = self.db.list_projects()
        if not projects:
            self.ui.warn("No projects to delete.")
            return
        options = [p["name"] for p in projects]
        idx = self.ui.prompt_choice("Select project to delete:", options, default_index=0)
        name = projects[idx]["name"]
        if not self.ui.confirm(f"Delete project '{name}' and all its data?", default_yes=False):
            self.ui.info("Cancelled.")
            return
        try:
            self.db.delete_project(name)
            self.ui.info(f"Project '{name}' deleted.")
            if self.state and self.state.project_name == name:
                self.state = None
        except ValueError as e:
            self.ui.error(str(e))

    def _select_dim_format(self) -> DimFormat:
        idx = self.ui.prompt_choice(
            "Choose dimension format (input/display):",
            [
                "mm (decimal, 2 decimals)",
                "feet (decimal, 2 decimals)",
                "feet-inches (fractions to 1/4\")",
            ],
            default_index=0,
        )
        if idx == 0:
            return "MM_DECIMAL_2"
        if idx == 1:
            return "FT_DECIMAL_2"
        return "FT_IN_FRAC_QUARTER"

    def _select_dim_format_with_default(self, current: DimFormat, prompt: str) -> DimFormat:
        options = [
            "mm (decimal, 2 decimals)",
            "feet (decimal, 2 decimals)",
            "feet-inches (fractions to 1/4\")",
        ]
        if current == "MM_DECIMAL_2":
            default_index = 0
        elif current == "FT_DECIMAL_2":
            default_index = 1
        else:
            default_index = 2
        idx = self.ui.prompt_choice(prompt, options, default_index=default_index)
        if idx == 0:
            return "MM_DECIMAL_2"
        if idx == 1:
            return "FT_DECIMAL_2"
        return "FT_IN_FRAC_QUARTER"

    def _dim_format_label(self, dim_format: DimFormat) -> str:
        if dim_format == "MM_DECIMAL_2":
            return "mm (decimal, 2 decimals)"
        if dim_format == "FT_DECIMAL_2":
            return "feet (decimal, 2 decimals)"
        return "feet-inches (fractions to 1/4\")"

    def _choose_session_dim_format(self, context: str) -> DimFormat:
        """
        Let the user optionally change units for a single editing/view session.
        Returns the dim_format to use for this session.
        May also update the project default dim_format if the user chooses so.
        """
        assert self.state is not None
        current = self.state.dim_format
        self.ui.info(
            f"Current project units for {context}: {self._dim_format_label(current)} "
            "(stored internally in mm)."
        )
        session_dim = self._select_dim_format_with_default(
            current,
            f"View/Edit units for this {context} session:",
        )
        if session_dim != current:
            if self.ui.confirm(
                f"Save '{self._dim_format_label(session_dim)}' as the new default units "
                "for this project?", default_yes=False
            ):
                self.db.update_project_dim_format(self.state.project_id, session_dim)
                self.state.dim_format = session_dim
                self.ui.info(
                    f"Project default units updated to {self._dim_format_label(session_dim)} "
                    "(values still stored internally in mm)."
                )
        return session_dim

    def _project_menu_loop(self) -> None:
        """Project-level menu: summary, edit shafts/levels, generate DXF/PDF, back."""
        assert self.state is not None

        while True:
            self.ui.banner(f"Project: {self.state.project_name}")

            choice = self.ui.prompt_choice(
                "Select action:",
                [
                    "View summary",
                    "Edit shafts (add / edit / delete)",
                    "Edit levels & heights",
                    "Edit linear walls (add / edit / delete)",
                    "Generate DXF",
                    "Export PDF",
                    "Export package (DXF+PDF)",
                    "Export linear walls CSV",
                    "Units settings",
                    "Back",
                ],
                default_index=0,
            )

            if choice == 0:
                self.show_summary()
            elif choice == 1:
                self.run_edit_shafts()
            elif choice == 2:
                self.run_edit_levels()
            elif choice == 3:
                self.run_edit_linear_walls()
            elif choice == 4:
                self.run_module_3()
            elif choice == 5:
                self.run_module_4()
            elif choice == 6:
                self.run_export_package()
            elif choice == 7:
                self.run_export_linear_walls_csv()
            elif choice == 8:
                self._units_settings()
            else:
                return

            self.ui.pause()

    def _units_settings(self) -> None:
        """Show and optionally change the project's default dim_format."""
        assert self.state is not None
        current = self.state.dim_format
        self.ui.banner("Units settings")
        self.ui.info(
            f"Current project dimension format: {self._dim_format_label(current)} "
            "(stored internally in mm; displayed as chosen format)."
        )
        if not self.ui.confirm("Change default units for this project?", default_yes=False):
            return
        new_dim = self._select_dim_format_with_default(
            current,
            "New default dimension format for this project:",
        )
        if new_dim == current:
            self.ui.info("Units unchanged.")
            return
        self.db.update_project_dim_format(self.state.project_id, new_dim)
        self.state.dim_format = new_dim
        self.ui.info(
            f"Project default units set to {self._dim_format_label(new_dim)} "
            "(all numeric values remain stored internally in mm)."
        )

    def run_edit_shafts(self) -> None:
        """Edit shafts: list from DB, then Add / Edit / Delete."""
        assert self.state is not None
        project_name = self.state.project_name
        session_dim_format = self._choose_session_dim_format("shafts")

        while True:
            shafts = self.db.list_shafts(project_name)
            self.ui.banner("Edit shafts")

            if shafts:
                self.ui.info(f"Current shafts ({len(shafts)}):")
                for s in shafts:
                    self.ui.info(
                        f"  • {s['name']} | {s['grid_left']}-{s['grid_right']} / "
                        f"{s['grid_bottom']}-{s['grid_top']} | "
                        f"W={format_mm(s['width_mm'], session_dim_format)} "
                        f"H={format_mm(s['height_mm'], session_dim_format)} "
                        "(stored internally in mm)"
                    )
            else:
                self.ui.info("No shafts yet.")

            actions = ["Add shaft", "Edit shaft", "Delete shaft", "Capture all from scratch (replace)", "Back"]
            if not shafts:
                # Omit Edit/Delete when empty
                actions = ["Add shaft", "Capture all from scratch (replace)", "Back"]
            choice = self.ui.prompt_choice("Action:", actions, default_index=len(actions) - 1)

            if "Back" in actions[choice]:
                return
            if "Capture all" in actions[choice]:
                out = module1_plan_input_terminal(self.ui)
                if out["dim_format"] != self.state.dim_format:
                    self.ui.info(
                        f"Module 1 used units: {self._dim_format_label(out['dim_format'])} "
                        "(values stored internally in mm)."
                    )
                    if self.ui.confirm(
                        "Save this as the new default units for this project?",
                        default_yes=True,
                    ):
                        self.db.update_project_dim_format(self.state.project_id, out["dim_format"])
                        self.state.dim_format = out["dim_format"]
                        session_dim_format = out["dim_format"]
                self.db.replace_shafts(self.state.project_id, out["shafts"])
                self.ui.info(f"Saved {len(out['shafts'])} shaft(s).")
                continue
            if "Add shaft" in actions[choice]:
                self._shaft_add_one(project_name, session_dim_format)
                continue
            if "Edit shaft" in actions[choice]:
                if not shafts:
                    continue
                self._shaft_edit_one(project_name, shafts, session_dim_format)
                continue
            if "Delete shaft" in actions[choice]:
                if not shafts:
                    continue
                self._shaft_delete_one(project_name, shafts)
                continue

    def _shaft_add_one(self, project_name: str, dim_format: DimFormat) -> None:
        """Prompt for one shaft and upsert."""
        self.ui.info("Add new shaft")
        name = self.ui.prompt_string("Shaft name", allow_empty=False)
        grid_left = self.ui.prompt_string("Left gridline", allow_empty=False)
        grid_right = self.ui.prompt_string("Right gridline", allow_empty=False)
        grid_bottom = self.ui.prompt_string("Bottom gridline", allow_empty=False)
        grid_top = self.ui.prompt_string("Top gridline", allow_empty=False)
        width_text = self.ui.prompt_string(
            f"Width (left→right) [{self._dim_format_label(dim_format)}]", allow_empty=False
        )
        height_text = self.ui.prompt_string(
            f"Height (bottom→top) [{self._dim_format_label(dim_format)}]", allow_empty=False
        )
        try:
            width_mm = parse_dimension_to_mm(width_text, dim_format)
            height_mm = parse_dimension_to_mm(height_text, dim_format)
        except ValueError as e:
            self.ui.error(str(e))
            return
        if width_mm <= 0 or height_mm <= 0:
            self.ui.error("Width and height must be > 0.")
            return
        shaft = {
            "name": name,
            "grid_left": grid_left,
            "grid_right": grid_right,
            "grid_bottom": grid_bottom,
            "grid_top": grid_top,
            "width_mm": width_mm,
            "height_mm": height_mm,
        }
        try:
            self.db.upsert_shaft(project_name, shaft)
            self.ui.info(f"Shaft '{name}' saved.")
        except ValueError as e:
            self.ui.error(str(e))

    def _shaft_edit_one(self, project_name: str, shafts: List[Dict[str, Any]], dim_format: DimFormat) -> None:
        """Select a shaft, prompt with defaults, upsert."""
        names = [s["name"] for s in shafts]
        idx = self.ui.prompt_choice("Select shaft to edit:", names, default_index=0)
        name = names[idx]
        current = self.db.get_shaft(project_name, name)
        if not current:
            self.ui.error("Shaft not found.")
            return
        self.ui.info(f"Editing '{name}' (press Enter to keep current value)")
        new_name = self.ui.prompt_string("Shaft name", default=current["name"])
        grid_left = self.ui.prompt_string("Left gridline", default=current["grid_left"])
        grid_right = self.ui.prompt_string("Right gridline", default=current["grid_right"])
        grid_bottom = self.ui.prompt_string("Bottom gridline", default=current["grid_bottom"])
        grid_top = self.ui.prompt_string("Top gridline", default=current["grid_top"])
        width_default = format_mm(current["width_mm"], dim_format)
        height_default = format_mm(current["height_mm"], dim_format)
        width_text = self.ui.prompt_string(
            f"Width [{self._dim_format_label(dim_format)}]",
            default=width_default,
        )
        height_text = self.ui.prompt_string(
            f"Height [{self._dim_format_label(dim_format)}]",
            default=height_default,
        )
        try:
            width_mm = parse_dimension_to_mm(width_text, dim_format)
            height_mm = parse_dimension_to_mm(height_text, dim_format)
        except ValueError as e:
            self.ui.error(str(e))
            return
        if width_mm <= 0 or height_mm <= 0:
            self.ui.error("Width and height must be > 0.")
            return
        shaft = {
            "name": new_name.strip() or current["name"],
            "grid_left": grid_left,
            "grid_right": grid_right,
            "grid_bottom": grid_bottom,
            "grid_top": grid_top,
            "width_mm": width_mm,
            "height_mm": height_mm,
        }
        try:
            if new_name.strip() and new_name.strip() != name:
                self.db.delete_shaft(project_name, name)
            self.db.upsert_shaft(project_name, shaft)
            self.ui.info("Shaft updated.")
        except ValueError as e:
            self.ui.error(str(e))

    def _shaft_delete_one(self, project_name: str, shafts: List[Dict[str, Any]]) -> None:
        """Select a shaft, confirm, delete."""
        names = [s["name"] for s in shafts]
        idx = self.ui.prompt_choice("Select shaft to delete:", names, default_index=0)
        name = names[idx]
        if not self.ui.confirm(f"Delete shaft '{name}'?", default_yes=False):
            self.ui.info("Cancelled.")
            return
        try:
            self.db.delete_shaft(project_name, name)
            self.ui.info(f"Shaft '{name}' deleted.")
        except ValueError as e:
            self.ui.error(str(e))

    def run_edit_levels(self) -> None:
        """Edit levels & heights: load from DB if present, else capture from scratch."""
        assert self.state is not None
        project_name = self.state.project_name
        dim_format = self._choose_session_dim_format("levels & heights")
        levels, deltas_mm = self.db.get_levels(project_name)

        if len(levels) >= 2 and len(deltas_mm) == len(levels) - 1:
            out = module2_edit_existing(self.ui, levels, deltas_mm, dim_format)
            if not out["levels"]:
                return
            try:
                self.db.save_levels(project_name, out["levels"], out["deltas_mm"])
                self.ui.info(f"Saved {len(out['levels'])} level(s) and {len(out['deltas_mm'])} step(s).")
            except ValueError as e:
                self.ui.error(str(e))
        else:
            self.ui.banner("Edit levels & heights (no existing data)")
            out = module2_level_height_definition(self.ui, dim_format)
            if not out["levels"]:
                return
            try:
                self.db.replace_levels_and_steps(
                    self.state.project_id,
                    level_names_in_order=out["levels"],
                    deltas_mm_between_consecutive=out["deltas_mm"],
                )
                self.ui.info(f"Saved {len(out['levels'])} level(s) and {len(out['deltas_mm'])} step(s) to database.")
            except ValueError as e:
                self.ui.error(str(e))
                self.ui.warn("Returning to project menu.")

    def run_export_package(self) -> None:
        """Generate DXF then Export PDF (from DB state)."""
        assert self.state is not None
        self.run_module_3()
        if self.state.last_dxf_path and self.state.last_dxf_path.exists():
            self.ui.pause("Press Enter to continue to PDF export...")
            self.run_module_4()

    def run_module_1(self) -> None:
        """Legacy: full Module 1 shaft input (replaced by run_edit_shafts in menu)."""
        self.run_edit_shafts()

    def run_module_2(self) -> None:
        assert self.state is not None
        self.ui.banner("Module 2 -- Levels + Height Input")

        out = module2_level_height_definition(self.ui, self.state.dim_format)

        try:
            self.db.replace_levels_and_steps(
                self.state.project_id,
                level_names_in_order=out["levels"],
                deltas_mm_between_consecutive=out["deltas_mm"],
            )
            self.ui.info(f"Saved {len(out['levels'])} level(s) and {len(out['deltas_mm'])} step(s) to database.")
        except ValueError as e:
            self.ui.error(f"Failed to save levels/heights: {e}")
            self.ui.warn("Returning to main menu.")
            return

    def run_module_3(self) -> None:
        assert self.state is not None
        self.ui.banner("Module 3 -- Generate DXF")

        shafts = self._load_shafts_as_dicts()
        levels, deltas_mm = self._load_levels_and_deltas()

        if not shafts:
            self.ui.error("No shafts found. Edit shafts first.")
            return
        if len(levels) < 2 or len(deltas_mm) != len(levels) - 1:
            self.ui.error("Levels/heights not complete. Edit levels & heights first.")
            return

        # Choose label units for this DXF export (geometry remains in mm)
        label_dim_format = self._select_dim_format_with_default(
            self.state.dim_format,
            "Label units for DXF export (geometry is always in mm):",
        )

        run_id = self.db.start_run(self.state.project_id)

        try:
            dxf_path = self.paths.output_dir / f"{self.state.project_name}_shafts.dxf"
            module3_draw_dxf(shafts, levels, deltas_mm, dxf_path, label_dim_format)

            self.state.last_dxf_path = dxf_path
            self.db.finish_run_ok(
                run_id,
                dxf_path=str(dxf_path),
                pdf_path=str(self.state.last_pdf_path) if self.state.last_pdf_path else None,
            )
            self.db.add_export_record(self.state.project_id, "DXF", str(dxf_path), meta={"module": 3})

            self.ui.info(f"DXF generated: {dxf_path}")

        except Exception as e:
            self.db.finish_run_error(run_id, notes=str(e))
            self.ui.error(f"DXF generation failed: {e}")

    def run_module_4(self) -> None:
        assert self.state is not None
        self.ui.banner("Module 4 -- Export PDF")

        dxf_path = self.state.last_dxf_path
        if dxf_path is None or not dxf_path.exists():
            self.ui.error("No DXF available. Run Module 3 first.")
            return

        run_id = self.db.start_run(self.state.project_id)

        try:
            pdf_path = self.paths.output_dir / f"{self.state.project_name}_shafts.pdf"
            module4_export_pdf(dxf_path, pdf_path)

            self.state.last_pdf_path = pdf_path
            self.db.finish_run_ok(run_id, dxf_path=str(dxf_path), pdf_path=str(pdf_path))
            self.db.add_export_record(
                self.state.project_id,
                "PDF",
                str(pdf_path),
                meta={"module": 4, "source_dxf": str(dxf_path)},
            )

            self.ui.info(f"PDF exported: {pdf_path}")

        except Exception as e:
            self.db.finish_run_error(run_id, notes=str(e))
            self.ui.error(f"PDF export failed: {e}")

    def download_last_dxf(self) -> None:
        assert self.state is not None
        if self.state.last_dxf_path is None or not self.state.last_dxf_path.exists():
            self.ui.error("No DXF file available to download.")
            return

        try:
            dest_path = save_to_downloads(self.state.last_dxf_path)
            self.ui.info(f"DXF copied to Downloads: {dest_path}")
        except Exception as e:
            self.ui.error(f"Failed to copy DXF: {e}")

    def download_last_pdf(self) -> None:
        assert self.state is not None
        if self.state.last_pdf_path is None or not self.state.last_pdf_path.exists():
            self.ui.error("No PDF file available to download.")
            return

        try:
            dest_path = save_to_downloads(self.state.last_pdf_path)
            self.ui.info(f"PDF copied to Downloads: {dest_path}")
        except Exception as e:
            self.ui.error(f"Failed to copy PDF: {e}")

    def show_summary(self) -> None:
        assert self.state is not None
        self.ui.banner("Current Saved Data Summary")

        shafts = self._load_shafts_as_dicts()
        levels, deltas = self._load_levels_and_deltas()
        dim_format = self.state.dim_format

        self.ui.info(f"Shafts saved: {len(shafts)}")
        for s in shafts:
            self.ui.info(
                f"  - {s['name']} | grids: {s['grid_left']}-{s['grid_right']} / "
                f"{s['grid_bottom']}-{s['grid_top']} | "
                f"W={format_mm(s['width_mm'], dim_format)} "
                f"H={format_mm(s['height_mm'], dim_format)} "
                "(stored internally in mm)"
            )

        linear_walls = self.db.get_linear_walls(self.state.project_id)
        elevation_by_level = self._build_level_elevation_map(levels, deltas)
        self.ui.info(f"Linear walls saved: {len(linear_walls)}")
        for w in linear_walls:
            level_range = (
                f"{w.get('level_from')}->{w.get('level_to')}"
                if w.get("level_from") and w.get("level_to")
                else "(levels not set)"
            )
            self.ui.info(
                f"  - {w['name']} | grid line {w['grid_line']} from {w['from_grid']} to {w['to_grid']} | "
                f"L={format_mm(w['length_mm'], dim_format)} "
                f"H={self._linear_wall_height_display(w, elevation_by_level, dim_format)} "
                f"| levels {level_range}"
            )

        self.ui.info(f"Levels saved: {len(levels)}")
        for i, lv in enumerate(levels):
            self.ui.info(f"  - {i+1}) {lv}")

        self.ui.info(f"Level-to-level steps: {len(deltas)}")
        for i in range(len(deltas)):
            self.ui.info(
                f"  - {levels[i]} → {levels[i+1]} : "
                f"{format_mm(deltas[i], dim_format)} "
                "(stored internally in mm)"
            )

        if self.state.last_dxf_path:
            self.ui.info(f"Last DXF: {self.state.last_dxf_path}")
        if self.state.last_pdf_path:
            self.ui.info(f"Last PDF: {self.state.last_pdf_path}")

    def _load_shafts_as_dicts(self) -> List[Dict[str, Any]]:
        assert self.state is not None
        rows = self.db.load_shafts(self.state.project_id)
        shafts: List[Dict[str, Any]] = []
        for r in rows:
            shafts.append({
                "name": r.name,
                "grid_left": r.grid_left,
                "grid_right": r.grid_right,
                "grid_bottom": r.grid_bottom,
                "grid_top": r.grid_top,
                "width_mm": float(r.width_mm),
                "height_mm": float(r.height_mm),
            })
        return shafts

    def _load_levels_and_deltas(self) -> Tuple[List[str], List[float]]:
        assert self.state is not None
        levels_rows, step_rows = self.db.load_levels_and_steps(self.state.project_id)

        levels = [lv.name for lv in sorted(levels_rows, key=lambda x: x.order_index)]

        step_map = {(st.from_level_id, st.to_level_id): float(st.delta_mm) for st in step_rows}

        level_ids_in_order = [lv.id for lv in sorted(levels_rows, key=lambda x: x.order_index)]
        deltas: List[float] = []
        for i in range(len(level_ids_in_order) - 1):
            key = (level_ids_in_order[i], level_ids_in_order[i+1])
            deltas.append(step_map.get(key, 0.0))
        return levels, deltas

    def _build_level_elevation_map(
        self,
        levels: List[str],
        deltas_mm: List[float],
    ) -> Dict[str, float]:
        if len(levels) < 2 or len(deltas_mm) != len(levels) - 1:
            return {}
        cum_z = build_cumulative_elevations(levels, deltas_mm)
        if len(cum_z) != len(levels):
            return {}
        return {levels[i]: float(cum_z[i]) for i in range(len(levels))}

    def _linear_wall_levels_available(self, levels: List[str], deltas_mm: List[float]) -> bool:
        """Linear-wall level assignment is available only when level data is complete."""
        return len(levels) >= 2 and len(deltas_mm) == len(levels) - 1

    def _compute_linear_wall_height_mm(
        self,
        wall: Dict[str, Any],
        elevation_by_level: Dict[str, float],
    ) -> Optional[float]:
        level_from = wall.get("level_from")
        level_to = wall.get("level_to")
        if not level_from or not level_to:
            return None
        if level_from not in elevation_by_level or level_to not in elevation_by_level:
            return None
        return abs(elevation_by_level[level_to] - elevation_by_level[level_from])

    def _linear_wall_height_display(
        self,
        wall: Dict[str, Any],
        elevation_by_level: Dict[str, float],
        dim_format: DimFormat,
    ) -> str:
        height_mm = self._compute_linear_wall_height_mm(wall, elevation_by_level)
        if height_mm is None:
            return "(set levels to compute height)"
        return format_mm(height_mm, dim_format)

    # ---------------------------
    # LINEAR WALLS UI
    # ---------------------------

    def run_edit_linear_walls(self) -> None:
        """Edit linear walls: list from DB, then Add / Edit / Delete."""
        assert self.state is not None
        session_dim_format = self._choose_session_dim_format("linear walls")

        while True:
            walls = self.db.get_linear_walls(self.state.project_id)
            levels, deltas_mm = self.db.get_levels(self.state.project_name)
            elevation_by_level = self._build_level_elevation_map(levels, deltas_mm)
            self.ui.banner("Edit linear walls")

            if walls:
                self.ui.info(f"Current linear walls ({len(walls)}):")
                for w in walls:
                    level_range = (
                        f"{w.get('level_from')}->{w.get('level_to')}"
                        if w.get("level_from") and w.get("level_to")
                        else "(levels not set)"
                    )
                    self.ui.info(
                        f"  • {w['name']} | grid line {w['grid_line']} from {w['from_grid']} to {w['to_grid']} | "
                        f"L={format_mm(w['length_mm'], session_dim_format)} "
                        f"H={self._linear_wall_height_display(w, elevation_by_level, session_dim_format)} "
                        f"| levels {level_range}"
                    )
            else:
                self.ui.info("No linear walls yet.")

            actions = ["Add wall", "Edit wall", "Delete wall", "Back"]
            if not walls:
                actions = ["Add wall", "Back"]

            choice = self.ui.prompt_choice("Action:", actions, default_index=len(actions) - 1)

            if "Back" in actions[choice]:
                return
            if "Add wall" in actions[choice]:
                self._linear_wall_add_one(session_dim_format)
                continue
            if "Edit wall" in actions[choice]:
                if not walls:
                    continue
                self._linear_wall_edit_one(walls, session_dim_format)
                continue
            if "Delete wall" in actions[choice]:
                if not walls:
                    continue
                self._linear_wall_delete_one(walls)
                continue

    def _linear_wall_add_one(self, dim_format: DimFormat) -> None:
        """Prompt for one linear wall and insert."""
        assert self.state is not None
        self.ui.info("Add new linear wall")
        name = self.ui.prompt_string("Wall name", allow_empty=False)
        grid_line = self.ui.prompt_string("Grid line (e.g. 'F')", allow_empty=False)
        from_grid = self.ui.prompt_string("From grid (e.g. '1' or 'F/1')", allow_empty=False)
        to_grid = self.ui.prompt_string("To grid", allow_empty=False)
        length_text = self.ui.prompt_string(
            f"Length along grid line [{self._dim_format_label(dim_format)}]", allow_empty=False
        )
        notes = self.ui.prompt_string("Notes (optional)", allow_empty=True)

        try:
            length_mm = parse_dimension_to_mm(length_text, dim_format)
        except ValueError as e:
            self.ui.error(str(e))
            return

        if length_mm <= 0:
            self.ui.error("Length must be > 0.")
            return

        levels, deltas_mm = self.db.get_levels(self.state.project_name)
        level_from: Optional[str] = None
        level_to: Optional[str] = None
        elevation_by_level = self._build_level_elevation_map(levels, deltas_mm)
        if self._linear_wall_levels_available(levels, deltas_mm):
            from_idx = self.ui.prompt_choice("From level:", levels, default_index=0)
            to_default = 1 if len(levels) > 1 else 0
            to_idx = self.ui.prompt_choice("To level:", levels, default_index=to_default)
            level_from = levels[from_idx]
            level_to = levels[to_idx]
        else:
            self.ui.info(
                "Levels are not defined yet; saving without from/to levels. "
                "Height will be computed after levels are configured."
            )

        computed_height_mm = self._compute_linear_wall_height_mm(
            {"level_from": level_from, "level_to": level_to},
            elevation_by_level,
        )

        payload: Dict[str, Any] = {
            "name": name,
            "grid_line": grid_line,
            "from_grid": from_grid,
            "to_grid": to_grid,
            "length_mm": length_mm,
            "level_from": level_from,
            "level_to": level_to,
            "height_mm": computed_height_mm if computed_height_mm is not None else 0.0,
            "notes": notes or None,
        }

        try:
            self.db.add_linear_wall(self.state.project_id, payload)
            self.ui.info(f"Linear wall '{name}' saved.")
        except ValueError as e:
            self.ui.error(str(e))

    def _linear_wall_edit_one(self, walls: List[Dict[str, Any]], dim_format: DimFormat) -> None:
        """Select a linear wall, prompt with defaults, then update."""
        assert self.state is not None
        names = [w["name"] for w in walls]
        idx = self.ui.prompt_choice("Select wall to edit:", names, default_index=0)
        wall = walls[idx]

        self.ui.info(f"Editing '{wall['name']}' (press Enter to keep current value)")
        new_name = self.ui.prompt_string("Wall name", default=wall["name"])
        grid_line = self.ui.prompt_string("Grid line", default=wall["grid_line"])
        from_grid = self.ui.prompt_string("From grid", default=wall["from_grid"])
        to_grid = self.ui.prompt_string("To grid", default=wall["to_grid"])

        length_default = format_mm(wall["length_mm"], dim_format)
        length_text = self.ui.prompt_string(
            f"Length along grid line [{self._dim_format_label(dim_format)}]",
            default=length_default,
        )
        notes_default = wall["notes"] or ""
        notes = self.ui.prompt_string("Notes (optional)", default=notes_default, allow_empty=True)

        try:
            length_mm = parse_dimension_to_mm(length_text, dim_format)
        except ValueError as e:
            self.ui.error(str(e))
            return

        if length_mm <= 0:
            self.ui.error("Length must be > 0.")
            return

        levels, deltas_mm = self.db.get_levels(self.state.project_name)
        level_from: Optional[str] = None
        level_to: Optional[str] = None
        elevation_by_level = self._build_level_elevation_map(levels, deltas_mm)
        if self._linear_wall_levels_available(levels, deltas_mm):
            from_default = 0
            to_default = 1 if len(levels) > 1 else 0
            if wall.get("level_from") in levels:
                from_default = levels.index(wall["level_from"])
            if wall.get("level_to") in levels:
                to_default = levels.index(wall["level_to"])
            from_idx = self.ui.prompt_choice("From level:", levels, default_index=from_default)
            to_idx = self.ui.prompt_choice("To level:", levels, default_index=to_default)
            level_from = levels[from_idx]
            level_to = levels[to_idx]
        else:
            self.ui.info(
                "Levels are missing/incomplete; saving without from/to levels. "
                "Height will be computed after levels are configured."
            )

        computed_height_mm = self._compute_linear_wall_height_mm(
            {"level_from": level_from, "level_to": level_to},
            elevation_by_level,
        )

        payload: Dict[str, Any] = {
            "name": new_name.strip() or wall["name"],
            "grid_line": grid_line,
            "from_grid": from_grid,
            "to_grid": to_grid,
            "length_mm": length_mm,
            "level_from": level_from,
            "level_to": level_to,
            "height_mm": computed_height_mm if computed_height_mm is not None else 0.0,
            "notes": notes or None,
        }

        try:
            self.db.update_linear_wall(wall["id"], payload)
            self.ui.info("Linear wall updated.")
        except ValueError as e:
            self.ui.error(str(e))

    def _linear_wall_delete_one(self, walls: List[Dict[str, Any]]) -> None:
        """Select a linear wall, confirm, then delete."""
        assert self.state is not None
        names = [w["name"] for w in walls]
        idx = self.ui.prompt_choice("Select wall to delete:", names, default_index=0)
        wall = walls[idx]
        if not self.ui.confirm(f"Delete linear wall '{wall['name']}'?", default_yes=False):
            self.ui.info("Cancelled.")
            return
        try:
            self.db.delete_linear_wall(wall["id"])
            self.ui.info(f"Linear wall '{wall['name']}' deleted.")
        except ValueError as e:
            self.ui.error(str(e))

    def run_export_linear_walls_csv(self) -> None:
        """Export linear walls for the current project to a CSV file."""
        assert self.state is not None
        walls = self.db.get_linear_walls(self.state.project_id)
        if not walls:
            self.ui.warn("No linear walls to export.")
            return

        dim_format = self.state.dim_format
        csv_path = self.paths.output_dir / f"{self.state.project_name}_linear_walls.csv"
        levels, deltas_mm = self.db.get_levels(self.state.project_name)
        elevation_by_level = self._build_level_elevation_map(levels, deltas_mm)

        try:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "name",
                        "grid_line",
                        "from_grid",
                        "to_grid",
                        "from_level",
                        "to_level",
                        "length_display",
                        "height_display",
                        "length_mm",
                        "height_mm_computed",
                        "height_note",
                    ]
                )
                for w in walls:
                    computed_height_mm = self._compute_linear_wall_height_mm(w, elevation_by_level)
                    height_display = (
                        format_mm(computed_height_mm, dim_format)
                        if computed_height_mm is not None
                        else "(set levels to compute height)"
                    )
                    height_note = "" if computed_height_mm is not None else "needs levels"
                    writer.writerow(
                        [
                            w["name"],
                            w["grid_line"],
                            w["from_grid"],
                            w["to_grid"],
                            w.get("level_from") or "",
                            w.get("level_to") or "",
                            format_mm(w["length_mm"], dim_format),
                            height_display,
                            w["length_mm"],
                            computed_height_mm if computed_height_mm is not None else "",
                            height_note,
                        ]
                    )
            self.ui.info(f"Linear walls CSV exported: {csv_path}")
        except Exception as e:
            self.ui.error(f"Failed to export linear walls CSV: {e}")
