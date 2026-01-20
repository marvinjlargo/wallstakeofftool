"""Tkinter UI placeholder (not used by default)"""

from typing import Optional, List
from .base import UI


class TkinterUI(UI):
    """
    Placeholder Tkinter UI implementation.
    This file exists but is not used by default - TerminalUI is the MVP.
    """

    def banner(self, text: str) -> None:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")

    def info(self, text: str) -> None:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")

    def warn(self, text: str) -> None:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")

    def error(self, text: str) -> None:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")

    def prompt_string(self, label: str, default: Optional[str] = None, allow_empty: bool = False) -> str:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")

    def prompt_int(self, label: str, default: Optional[int] = None, min_value: Optional[int] = None) -> int:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")

    def prompt_float(self, label: str, default: Optional[float] = None, min_value: Optional[float] = None) -> float:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")

    def prompt_choice(self, title: str, options: List[str], default_index: int = 0) -> int:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")

    def confirm(self, label: str, default_yes: bool = True) -> bool:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")

    def pause(self, label: str = "Press Enter to continue...") -> None:
        raise NotImplementedError("TkinterUI not implemented - use TerminalUI")
