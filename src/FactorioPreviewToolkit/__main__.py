"""Entry point for the Factorio Preview Toolkit.

This tool detects map exchange strings (e.g. from clipboard), generates
preview images for all configured planets using the Factorio CLI, and optionally
uploads them to a remote service like Dropbox.
"""

import sys

from src.FactorioPreviewToolkit.shared.error_popup import show_error_popup
from src.FactorioPreviewToolkit.shared.shared_constants import constants
from src.FactorioPreviewToolkit.shared.tee_logger import enable_tee_logging

# Check CLI flags for subprocess modes early.
# This is crucial in PyInstaller one-file builds:
# when sys.executable is used to launch a subprocess,
# it re-launches the full bundled EXE, which would otherwise start
# the full controller + monitor again (causing infinite loops).
# By checking for mode flags like --preview-generator-mode or --uploader-mode
# and exiting early, we only start the desired module.
if "--preview-generator-mode" in sys.argv:
    from src.FactorioPreviewToolkit.preview_generator.__main__ import main as generator_main

    generator_main()
    sys.exit()
if "--uploader-mode" in sys.argv:
    from src.FactorioPreviewToolkit.uploader.__main__ import main as uploader_main

    uploader_main()
    sys.exit()


enable_tee_logging(constants.LOGS_DIR, keep_last_n=20)

from src.FactorioPreviewToolkit.controller.controller import PreviewController
from src.FactorioPreviewToolkit.shared.single_instance import (
    AlreadyRunningError,
    single_instance_guard,
)
from src.FactorioPreviewToolkit.shared.structured_logger import log

if __name__ == "__main__":
    log.info("🚀 Factorio preview toolkit started.")
    controller = None
    try:
        with single_instance_guard():
            controller = PreviewController()
            controller.start()
    except AlreadyRunningError as e:
        # Expected situation, not a crash - no stack trace.
        log.error(f"❌ {e}")
        show_error_popup("Factorio Toolkit already running", str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("⚠️ Interrupted by user. Shutting down...")
    except Exception as e:
        log.exception("❌ Unhandled exception occurred.")
        show_error_popup("Factorio Toolkit Error", str(e))
        raise
    finally:
        if controller is not None:
            controller.stop()
        log.info("👋 Factorio preview Toolkit exited.")
