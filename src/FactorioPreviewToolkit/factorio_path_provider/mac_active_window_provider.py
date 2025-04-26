import collections
from pathlib import Path

import psutil
from AppKit import NSWorkspace

from src.FactorioPreviewToolkit.factorio_path_provider.base_active_window_provider import (
    BaseActiveWindowProvider,
)
from src.FactorioPreviewToolkit.shared.structured_logger import log


class MacActiveWindowProvider(BaseActiveWindowProvider):
    """
    macOS-specific implementation of ActiveWindowProvider.
    """

    def __init__(self, on_new_factorio_path: collections.abc.Callable[[Path], None]):
        """
        Initializes the macOS-specific active window provider.
        """
        super().__init__(on_new_factorio_path)

    def get_factorio_executable_path(self) -> Path | None:
        """
        Returns the path of the Factorio executable if it is the active window.
        """
        try:
            active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if not active_app:
                return None
            pid = active_app.processIdentifier()
            process = psutil.Process(pid)
            executable_path = process.exe()
            if "factorio" in executable_path.lower():
                return Path(executable_path)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            log.info(f"Error getting Factorio executable path: {e}")
        return None
