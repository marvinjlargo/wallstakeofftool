"""Module 6: Application UI Orchestrator"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from ..ui.base import UI
from ..ui.terminal_ui import TerminalUI
from ..modules.module5_db import DB, DBConfig
from ..modules.module1_plan_input import module1_plan_input_terminal
from ..modules.module2_levels_height import module2_level_height_definition
from ..modules.module3_draw_dxf import module3_draw_dxf
from ..modules.module4_export_pdf import module4_export_pdf
from ..services.downloads import save_to_downloads
from .state import AppState, AppPaths, DimFormat


class AppController:
    """Orchestrates modules + DB + UI"""

    def __init__(self, ui: UI, db: DB, paths: AppPaths):
        self.ui = ui
        self.db = db
        self.paths = paths
        self.state: Optional[AppState] = None

    def start(self) -> None:
        """Start the application"""
        self.ui.banner("Shaft Walls Takeoff Tool")

        project_name = self.ui.prompt_string("Project name", default="shaftwallstakeofftool")
        dim_format = self._select_dim_format()

        project_id = self.db.get_or_create_project(project_name, dim_format)
        self.state = AppState(project_id=project_id, project_name=project_name, dim_format=dim_format)

        self._main_menu_loop()

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

    def _main_menu_loop(self) -> None:
        assert self.state is not None

        while True:
            self.ui.banner(f"Main Menu -- Project: {self.state.project_name}")

            choice = self.ui.prompt_choice(
                "Select action:",
                [
                    "1) Module 1 -- Input shafts (plan grid-to-grid)",
                    "2) Module 2 -- Input levels + heights",
                    "3) Module 3 -- Generate DXF (elevations)",
                    "4) Module 4 -- Export PDF (from DXF)",
                    "5) View current saved data summary",
                    "6) Download last DXF to Downloads",
                    "7) Download last PDF to Downloads",
                    "8) Exit",
                ],
                default_index=0,
            )

            if choice == 0:
                self.run_module_1()
            elif choice == 1:
                self.run_module_2()
            elif choice == 2:
                self.run_module_3()
            elif choice == 3:
                self.run_module_4()
            elif choice == 4:
                self.show_summary()
            elif choice == 5:
                self.download_last_dxf()
            elif choice == 6:
                self.download_last_pdf()
            else:
                self.ui.info("Goodbye.")
                return

            self.ui.pause()

    def run_module_1(self) -> None:
        assert self.state is not None
        self.ui.banner("Module 1 -- Shaft Plan Input")

        out = module1_plan_input_terminal(self.ui)

        # Update project format if Module 1 selected a different one
        if out["dim_format"] != self.state.dim_format:
            self.state.dim_format = out["dim_format"]
            self.db.get_or_create_project(self.state.project_name, out["dim_format"])

        self.db.replace_shafts(self.state.project_id, out["shafts"])
        self.ui.info(f"Saved {len(out['shafts'])} shaft(s) to database.")

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
            self.ui.error("No shafts found. Run Module 1 first.")
            return
        if len(levels) < 2 or len(deltas_mm) != len(levels) - 1:
            self.ui.error("Levels/heights not complete. Run Module 2 first.")
            return

        run_id = self.db.start_run(self.state.project_id)

        try:
            dxf_path = self.paths.output_dir / f"{self.state.project_name}_shafts.dxf"
            module3_draw_dxf(shafts, levels, deltas_mm, dxf_path)

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

        self.ui.info(f"Shafts saved: {len(shafts)}")
        for s in shafts:
            self.ui.info(
                f"  - {s['name']} | grids: {s['grid_left']}-{s['grid_right']} / "
                f"{s['grid_bottom']}-{s['grid_top']} | W={s['width_mm']:.2f}mm H={s['height_mm']:.2f}mm"
            )

        self.ui.info(f"Levels saved: {len(levels)}")
        for i, lv in enumerate(levels):
            self.ui.info(f"  - {i+1}) {lv}")

        self.ui.info(f"Level-to-level steps: {len(deltas)}")
        for i in range(len(deltas)):
            self.ui.info(f"  - {levels[i]} → {levels[i+1]} : {deltas[i]:.2f} mm")

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
