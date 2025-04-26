import collections
import os
import subprocess
from pathlib import Path

import psutil

from src.FactorioPreviewToolkit.factorio_path_provider.base_active_window_provider import (
    BaseActiveWindowProvider,
)
from src.FactorioPreviewToolkit.shared.structured_logger import log


class LinuxActiveWindowProvider(BaseActiveWindowProvider):
    """
    Linux-specific implementation of ActiveWindowProvider.
    Uses `xdotool` to find the active window and get the associated PID.
    """

    def __init__(self, on_new_factorio_path: collections.abc.Callable[[Path], None]):
        super().__init__(on_new_factorio_path)
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            raise RuntimeError(
                "❌ Active window detection is not supported on Wayland.\n"
                "Please edit your config.ini and use a different locator method like:\n\n"
                "    factorio_locator_method = fixed_path\n\n"
                "Then provide the executable path manually via fixed_path_factorio_executable."
            )

    def get_factorio_executable_path(self) -> Path | None:
        try:
            # Use xdotool to get the window ID of the currently focused window
            window_id = subprocess.check_output(["xdotool", "getwindowfocus"]).strip()
            if not window_id:
                return None

            # Use xdotool to get the PID of that window
            pid = subprocess.check_output(["xdotool", "getwindowpid", window_id]).strip()
            if not pid:
                return None

            process = psutil.Process(int(pid))
            executable_path = process.exe()
            if "factorio" in executable_path.lower():
                return Path(executable_path)

        except (subprocess.CalledProcessError, psutil.NoSuchProcess, psutil.AccessDenied) as e:
            log.error(f"Error getting Factorio executable path (Linux): {e}")
        return None
