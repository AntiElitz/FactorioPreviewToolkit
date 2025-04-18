from abc import ABC, abstractmethod
from pathlib import Path

from src.FactorioPreviewToolkit.shared.config import Config
from src.FactorioPreviewToolkit.shared.shared_constants import Constants
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section


def _write_links_file(planet_links: dict[str, str]) -> None:
    """
    Writes a JavaScript config object with links to each uploaded image, one per planet.
    """
    with log_section("📝 Saving download links to file..."):
        preview_links_filepath = Constants.PREVIEW_LINKS_FILEPATH
        try:
            with preview_links_filepath.open("w", encoding="utf-8") as f:
                f.write("const planetConfig = {\n")
                for planet, url in planet_links.items():
                    f.write(f'  {planet}: "{url}",\n')
                f.write("};\n")
            log.info(f"✅ Download links saved to: {preview_links_filepath}")
        except Exception:
            log.error(f"❌ Failed to write output file: {preview_links_filepath}")
            raise


class BaseUploader(ABC):
    """
    Abstract uploader class. Handles upload of all planet preview images.
    Subclasses must implement upload_single().
    """

    def upload_all(self) -> None:
        """
        Uploads all planet preview images and saves the resulting download links to a file.
        """
        with log_section("🖼️ Starting image upload..."):
            planet_links: dict[str, str] = {}

            for planet in Config.get().planet_names:
                with log_section(f"🌍 Uploading {planet.capitalize()}..."):
                    image_path = Constants.PREVIEWS_OUTPUT_DIR / f"{planet}.png"
                    try:
                        link = self.upload_single(image_path, f"{planet}.png")
                        planet_links[planet] = link
                        log.info(f"✅ {planet.capitalize()} done.")
                    except Exception:
                        log.error(f"❌ Failed to upload {planet}.png")
                        raise

            _write_links_file(planet_links)
            log.info("✅ All uploads complete.")

    @abstractmethod
    def upload_single(self, local_path: Path, remote_filename: str) -> str:
        """
        Uploads a single image file and returns a public URL.
        """
        ...
