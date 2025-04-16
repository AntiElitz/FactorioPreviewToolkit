# src/map_string_provider/factory.py
import collections

from src.FactorioPreviewToolkit.map_string_provider.base import MapStringProvider
from src.FactorioPreviewToolkit.map_string_provider.clipboard_provider import (
    ClipboardMapStringProvider,
)
from src.FactorioPreviewToolkit.shared.config import Config
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section


def get_map_string_provider(
    on_new_map_string: collections.abc.Callable[[str], None],
) -> MapStringProvider:
    """
    Selects and returns a map string provider based on config.
    """
    config = Config.get()
    map_exchange_input_method = config.map_exchange_input_method
    with log_section("🔌 Selecting map string provider..."):
        if map_exchange_input_method == "clipboard_auto":
            log.info("✅ Using ClipboardMapStringProvider (auto mode).")
            return ClipboardMapStringProvider(on_new_map_string)
        # elif map_exchange_input_method == "file_watch":  # TODO: AntiElitz: Implement a file watcher
        #     # Watch a file for changes and read map string
        #     return FileWatchMapStringProvider(on_new_map_string)
        else:
            raise ValueError(f"Unsupported map_exchange_input_method: {map_exchange_input_method}")
