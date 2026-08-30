# src/map_string_provider/clipboard_provider.py
import collections
import ctypes
import sys
import threading

import pyperclip

from src.FactorioPreviewToolkit.map_string_provider.base import MapStringProvider
from src.FactorioPreviewToolkit.shared.config import Config
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section
from src.FactorioPreviewToolkit.shared.utils import is_valid_map_string

# After this many failed polls in a row, try once to unstick the clipboard.
_HEAL_ATTEMPT_AFTER_FAILURES = 10


class ClipboardMapStringProvider(MapStringProvider):
    """
    Watches the system clipboard for valid map exchange strings.
    Calls the callback when a new one is detected.
    """

    def __init__(
        self,
        on_new_map_string: collections.abc.Callable[[str], None],
    ):
        """
        Sets up the clipboard monitor and polling interval.
        """
        super().__init__(on_new_map_string)
        self._poll_interval = Config.get().map_exchange_input_poll_interval_in_seconds
        self._last_map_string = ""
        self._failures = 0
        self._stop_flag = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="ClipboardMonitor",
            daemon=True,
        )

    def start(self) -> None:
        """
        Starts the clipboard monitoring thread.
        """
        log.info("🟢 Starting Clipboard Monitor...")
        self._stop_flag.clear()
        self._thread.start()

    def stop(self) -> None:
        """
        Stops the monitoring thread and waits for it to finish.
        """
        with log_section("🛑 Stopping Clipboard Monitor..."):
            self._stop_flag.set()
            self._thread.join()
            log.info("✅ Clipboard Monitor stopped.")

    def _run(self) -> None:
        """
        Loop that checks the clipboard for new map exchange strings.
        """
        with log_section("📋 Monitoring clipboard for new map exchange strings..."):
            while not self._stop_flag.is_set():
                try:
                    clipboard_text = pyperclip.paste().strip()
                    self._note_clipboard_worked()
                    if clipboard_text != self._last_map_string and is_valid_map_string(
                        clipboard_text
                    ):
                        log.info("🎯 New map exchange string detected in clipboard.")
                        self._last_map_string = clipboard_text
                        self._on_new_map_string(clipboard_text)
                except Exception as e:
                    self._note_clipboard_failed(e)
                self._stop_flag.wait(timeout=self._poll_interval)

    def _note_clipboard_worked(self) -> None:
        """
        Reports that the clipboard came back, and for how long it was gone.
        """
        if not self._failures:
            return

        minutes = (self._failures * self._poll_interval) / 60
        log.info(
            f"✅ Clipboard readable again after {self._failures} failed attempts "
            f"({minutes:.0f} min)."
        )
        self._failures = 0

    def _note_clipboard_failed(self, error: Exception) -> None:
        """
        Logs the start of a clipboard problem, once.

        The clipboard can stay unreadable for hours - a machine waking from sleep is enough.
        Polling twice a second, logging every attempt wrote tens of thousands of identical
        lines overnight and buried everything else. One line here and one when it recovers
        says everything: no recovery line yet means it is still broken.
        """
        self._failures += 1

        if self._failures == 1:
            log.warning(
                f"⚠️ Failed to read the clipboard: {error}\n"
                f"Another program may be holding it. Copied map strings will not be noticed "
                f"until this clears up - restarting the toolkit fixes it. This is logged "
                f"once, plus one line when the clipboard works again."
            )
        elif self._failures == _HEAL_ATTEMPT_AFTER_FAILURES:
            self._try_release_stuck_clipboard()

    @staticmethod
    def _try_release_stuck_clipboard() -> None:
        """
        Best effort attempt to unstick the clipboard.

        If this process ever left the clipboard open, every later OpenClipboard from it
        fails - which looks exactly like this. Closing it is harmless when we do not hold
        it, and worth trying when nothing else can be done from inside the process.
        """
        if sys.platform != "win32":
            return
        try:
            ctypes.windll.user32.CloseClipboard()
        except Exception:
            pass
