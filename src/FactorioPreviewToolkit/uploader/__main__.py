from src.FactorioPreviewToolkit.shared.error_popup import show_error_popup
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section
from src.FactorioPreviewToolkit.uploader.factory import get_uploader


def main() -> None:
    """
    Entry point for running the uploader standalone. Selects the uploader and starts the upload.
    Handles errors and ensures clean logging exit.
    """
    try:
        with log_section("🚀 Uploader started."):
            uploader = get_uploader()
            uploader.upload_all()
            log.info("✅ Uploader finished successfully.")
    except Exception as e:
        log.exception("❌ Uploader failed with an exception.")
        show_error_popup("Factorio Toolkit Error", str(e))
        raise
    finally:
        log.info("👋 Uploader exited.")


if __name__ == "__main__":
    main()
