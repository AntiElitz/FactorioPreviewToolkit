import collections
import platform
from pathlib import Path

from src.FactorioPreviewToolkit.factorio_path_provider.base import FactorioPathProvider
from src.FactorioPreviewToolkit.factorio_path_provider.fixed_path_provider import FixedPathProvider
from src.FactorioPreviewToolkit.shared.config import Config
from src.FactorioPreviewToolkit.shared.structured_logger import log
from src.FactorioPreviewToolkit.shared.structured_logger import log_section


def get_factorio_path_provider(
    on_new_factorio_path: collections.abc.Callable[[Path], None],
) -> FactorioPathProvider:
    """
    Factory function that returns a FactorioPathProvider implementation
    based on the configured locator method and operating system.
    """
    config = Config.get()
    factorio_locator_method = config.factorio_locator_method

    with log_section("🔀 Selecting Factorio path provider..."):
        match factorio_locator_method:
            case "fixed_path":
                log.info("✅ Using FixedPathProvider.")
                return FixedPathProvider(on_new_factorio_path)

            case "active_window_monitor":
                log.info("✅ Using ActiveWindowProvider.")
                system = platform.system()
                if system == "Windows":
                    from src.FactorioPreviewToolkit.factorio_path_provider.windows_active_window_provider import (
                        WindowsActiveWindowProvider,
                    )

                    return WindowsActiveWindowProvider(on_new_factorio_path)
                elif system == "Darwin":
                    from src.FactorioPreviewToolkit.factorio_path_provider.mac_active_window_provider import (
                        MacActiveWindowProvider,
                    )

                    return MacActiveWindowProvider(on_new_factorio_path)
                elif system == "Linux":
                    from src.FactorioPreviewToolkit.factorio_path_provider.linux_active_window_provider import (
                        LinuxActiveWindowProvider,
                    )

                    return LinuxActiveWindowProvider(on_new_factorio_path)
                else:
                    raise ValueError(f"❌ Unsupported platform: {system}")

            case _:
                raise ValueError(
                    f"❌ Unsupported map_exchange_input_method: {factorio_locator_method}. This can only occur if config schema validation fails"
                )
