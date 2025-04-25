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
            log.info("🔍 Checking frontmost application via NSWorkspace...")
            active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if not active_app:
                log.info("⚠️ No frontmost application detected.")
                return None
            pid = active_app.processIdentifier()
            process = psutil.Process(pid)
            executable_path = process.exe()
            log.info(f"🛠️  Resolved executable path: {executable_path}")
            if "factorio" in executable_path.lower():
                log.info("🎯 Factorio executable detected.")
                return Path(executable_path)
            else:
                log.info("ℹ️ Active application is not Factorio.")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            log.error(f"Error getting Factorio executable path: {e}")
        return None
