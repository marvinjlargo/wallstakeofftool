"""Terminal UI implementation"""

from typing import Optional, List
from .base import UI


class TerminalUI(UI):
    """MVP Terminal UI implementation"""

    def banner(self, text: str) -> None:
        print("\n" + "=" * 60)
        print(text)
        print("=" * 60 + "\n")

    def info(self, text: str) -> None:
        print(f"[INFO] {text}")

    def warn(self, text: str) -> None:
        print(f"[WARN] {text}")

    def error(self, text: str) -> None:
        print(f"[ERROR] {text}")

    def prompt_string(self, label: str, default: Optional[str] = None, allow_empty: bool = False) -> str:
        while True:
            suffix = f" [{default}]" if default is not None else ""
            val = input(f"{label}{suffix}: ").strip()
            if not val and default is not None:
                return default
            if not val and not allow_empty:
                self.warn("Value required.")
                continue
            return val

    def prompt_int(self, label: str, default: Optional[int] = None, min_value: Optional[int] = None) -> int:
        while True:
            suffix = f" [{default}]" if default is not None else ""
            raw = input(f"{label}{suffix}: ").strip()
            if not raw and default is not None:
                n = default
            else:
                try:
                    n = int(raw)
                except ValueError:
                    self.warn("Enter an integer.")
                    continue
            if min_value is not None and n < min_value:
                self.warn(f"Must be >= {min_value}.")
                continue
            return n

    def prompt_float(self, label: str, default: Optional[float] = None, min_value: Optional[float] = None) -> float:
        while True:
            suffix = f" [{default}]" if default is not None else ""
            raw = input(f"{label}{suffix}: ").strip()
            if not raw and default is not None:
                return default
            try:
                val = float(raw)
            except ValueError:
                self.warn("Enter a number.")
                continue
            if min_value is not None and val < min_value:
                self.warn(f"Must be >= {min_value}.")
                continue
            return val

    def prompt_choice(self, title: str, options: List[str], default_index: int = 0) -> int:
        print(title)
        for i, opt in enumerate(options, start=1):
            d = " (default)" if (i - 1) == default_index else ""
            print(f"  {i}) {opt}{d}")
        while True:
            raw = input("Select option number: ").strip()
            if not raw:
                return default_index
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(options):
                    return idx
            except ValueError:
                pass
            self.warn("Invalid choice.")

    def confirm(self, label: str, default_yes: bool = True) -> bool:
        default = "Y" if default_yes else "N"
        while True:
            raw = input(f"{label} (Y/N) [{default}]: ").strip().lower()
            if not raw:
                return default_yes
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
            self.warn("Please enter Y or N.")

    def pause(self, label: str = "Press Enter to continue...") -> None:
        input(label)
