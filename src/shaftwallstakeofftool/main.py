"""Module 7: Application Entry Point"""

from pathlib import Path
import sys

from .app.controller import AppController
from .app.state import AppPaths
from .modules.module5_db import DB, DBConfig
from .ui.terminal_ui import TerminalUI


def main():
    """Main entry point"""
    try:
        # Resolve working directories
        base_dir = Path.cwd()
        data_dir = base_dir / "data"
        output_dir = base_dir / "output"

        # Ensure directories exist
        data_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Database path
        db_path = data_dir / "shaftwallstakeofftool.sqlite3"

        # Initialize core services
        ui = TerminalUI()
        db_config = DBConfig(db_path=db_path)
        db = DB(db_config)

        # Build application paths
        paths = AppPaths(db_path=db_path, output_dir=output_dir)

        # Create controller
        controller = AppController(ui=ui, db=db, paths=paths)

        # Start application loop
        controller.start()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
