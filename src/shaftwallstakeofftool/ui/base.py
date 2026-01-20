"""Base UI interface"""

from abc import ABC, abstractmethod
from typing import Optional, List


class UI(ABC):
    """Abstract UI contract"""

    @abstractmethod
    def banner(self, text: str) -> None:
        """Display a banner message"""
        pass

    @abstractmethod
    def info(self, text: str) -> None:
        """Display an info message"""
        pass

    @abstractmethod
    def warn(self, text: str) -> None:
        """Display a warning message"""
        pass

    @abstractmethod
    def error(self, text: str) -> None:
        """Display an error message"""
        pass

    @abstractmethod
    def prompt_string(self, label: str, default: Optional[str] = None, allow_empty: bool = False) -> str:
        """Prompt for a string input"""
        pass

    @abstractmethod
    def prompt_int(self, label: str, default: Optional[int] = None, min_value: Optional[int] = None) -> int:
        """Prompt for an integer input"""
        pass

    @abstractmethod
    def prompt_choice(self, title: str, options: List[str], default_index: int = 0) -> int:
        """Prompt for a choice from a list"""
        pass

    @abstractmethod
    def prompt_float(self, label: str, default: Optional[float] = None, min_value: Optional[float] = None) -> float:
        """Prompt for a float input"""
        pass

    @abstractmethod
    def confirm(self, label: str, default_yes: bool = True) -> bool:
        """Prompt for yes/no confirmation"""
        pass

    @abstractmethod
    def pause(self, label: str = "Press Enter to continue...") -> None:
        """Pause and wait for user input"""
        pass
