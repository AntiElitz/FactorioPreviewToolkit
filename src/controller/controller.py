import queue
from pathlib import Path
from queue import Queue

from src.controller.map_processing_pipeline import MapProcessingPipeline
from src.factorio_path_provider.base import FactorioPathProvider
from src.factorio_path_provider.factory import get_factorio_path_provider
from src.map_string_provider.base import MapStringProvider
from src.map_string_provider.factory import get_map_string_provider
from src.shared.structured_logger import log


class PreviewController:
    """
    A controller for managing map processing pipeline for Factorio map previews.

    This controller listens for map strings and Factorio paths asynchronously and processes them
    by running the map preview generation and upload tasks. Only one task is executed at a time,
    and if a new task starts, the old task is aborted.
    """

    def __init__(self) -> None:
        """
        Initializes the PreviewController with required resources.
        """
        self._running: bool = False
        self._factorio_path_provider: FactorioPathProvider | None = None
        self._map_string_provider: MapStringProvider | None = None

        self._latest_factorio_path: Path | None = None
        self._latest_map_string: str | None = None
        self._map_string_analysed: bool = False

        self._event_queue: Queue[tuple[str, str | Path]] = Queue()
        self._map_processing_pipeline = MapProcessingPipeline()

    def _process_events(self) -> None:
        """
        Processes events from the event queue. This method listens for new map strings and Factorio paths,
        and triggers the map processing pipeline when both are available.
        """
        while self._running:
            try:
                event_type, data = self._event_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if event_type == "map_string":
                assert isinstance(data, str)
                self._latest_map_string = data
                self._map_string_analysed = False

            elif event_type == "factorio_path":
                assert isinstance(data, Path)
                self._latest_factorio_path = data

            if (
                self._latest_map_string
                and self._latest_factorio_path
                and not self._map_string_analysed
            ):
                self._start_map_processing()

    def _start_map_processing(self) -> None:
        """
        Starts the map processing pipeline with the latest map string and Factorio path.
        """
        self._map_string_analysed = True

        assert self._latest_map_string is not None
        assert self._latest_factorio_path is not None

        self._map_processing_pipeline.run_async(self._latest_factorio_path, self._latest_map_string)

    def stop(self) -> None:
        """
        Stops the map processing pipeline and cleans up resources.
        """
        if self._map_string_provider is not None:
            self._map_string_provider.stop()
        if self._factorio_path_provider is not None:
            self._factorio_path_provider.stop()
        log.info("👋 Controller stopped successfully.")
        self._running = False

    def start(self) -> None:
        """
        Starts the PreviewController to process map strings and Factorio paths asynchronously.
        """

        def on_new_map_string(map_string: str) -> None:
            log.info(f"📥 Received new map string: {map_string}")
            self._event_queue.put(("map_string", map_string))

        def on_new_factorio_path(factorio_path: Path) -> None:
            log.info(f"📍 Detected new Factorio path: {factorio_path}")
            self._event_queue.put(("factorio_path", factorio_path))

        self._map_string_provider = get_map_string_provider(on_new_map_string)
        self._factorio_path_provider = get_factorio_path_provider(on_new_factorio_path)

        self._map_string_provider.start()
        self._factorio_path_provider.start()

        self._running = True
        self._process_events()
