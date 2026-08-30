import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from PIL import PngImagePlugin, Image
from PIL.Image import ADAPTIVE

from src.FactorioPreviewToolkit.shared.shared_constants import constants
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section


def _write_viewer_config_js(planet_image_links: dict[str, str], planet_names_link: str) -> None:
    """
    Writes a JavaScript file that defines the viewerConfig object.
    This includes preview image URLs and a reference to the planet names JS file.
    """
    from src.FactorioPreviewToolkit.shared.shared_constants import constants

    output_path = constants.PREVIEW_LINKS_FILEPATH
    with log_section("📝 Writing viewerConfig.js..."):
        try:
            with output_path.open("w", encoding="utf-8") as f:
                f.write("const viewerConfig = {\n")
                f.write("  planetPreviewSources: {\n")
                for planet, url in planet_image_links.items():
                    f.write(f'    {planet}: "{url}",\n')
                f.write("  },\n")
                f.write(f'  planetNamesSource: "{planet_names_link}"\n')
                f.write("};\n")
            log.info(f"✅ viewerConfig.js written to: {output_path}")
        except Exception:
            log.error(f"❌ Failed to write viewerConfig.js to: {output_path}")
            raise


def _load_planet_names() -> list[str]:
    """
    Loads the list of planet names from the JSON file generated during preview setup.
    """
    planet_file = constants.PLANET_NAMES_REMOTE_VIEWER_FILEPATH
    with log_section("📄 Loading planet names..."):
        try:
            with planet_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            planets = data.get("planets", [])
            log.info(f"✅ Loaded {len(planets)} planets: {', '.join(planets)}")
            return cast(list[str], planets)
        except Exception:
            log.error("❌ Failed to load or parse planet names JSON file.")
            raise


def _inject_upload_timestamp_into_planet_names_file() -> None:
    """
    Adds or updates an '' field in the planet names JSON file.
    """
    path = constants.PLANET_NAMES_REMOTE_VIEWER_FILEPATH
    with path.open("r+", encoding="utf-8") as f:
        data = json.load(f)
        data["time"] = datetime.now(timezone.utc).isoformat()
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()


def _add_upload_timestamp_to_png(path: Path) -> None:
    """
    Adds or updates a timestamp in the metadata of a PNG file.
    """
    image = Image.open(path)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("", datetime.now(timezone.utc).isoformat())

    image.save(path, "PNG", pnginfo=metadata)


def _optimize_png(path: Path) -> None:
    """
    Re-encodes a PNG image with maximum lossless compression.
    """
    with Image.open(path) as img:
        if img.mode != "P":
            img = img.convert("P", palette=ADAPTIVE, colors=256)
        img.save(path, optimize=True, compress_level=9)


class BaseUploader(ABC):
    """
    Abstract uploader class. Uploads the planet names file and all planet preview images.
    Subclasses must implement upload_single().

    Two ways to use it:
    - upload_planet_image() / upload_planet_names_file() / write_viewer_config() are driven
      by the generator, one planet at a time, so an audience sees each planet as soon as it
      is rendered instead of waiting for the whole run.
    - upload_all() uploads everything that is already on disk, for a manual re-upload.
    """

    def prepare_remote(self, planet_names: list[str]) -> str:
        """
        Runs once before the first planet of a run.

        Deletes the previews about to be replaced and publishes the full planet list, so a
        hosted viewer immediately shows a tab per planet with a "waiting" placeholder -
        exactly like the local viewer - instead of serving the previous map's images under
        the new map's tabs. The images then appear one by one as they are rendered; the
        viewer picks each one up on its own.

        Returns the public URL of the planet list.
        """
        for planet in planet_names:
            self.delete_remote_preview(planet)
        return self.upload_planet_names_file()

    def delete_remote_preview(self, planet: str) -> None:
        """
        Deletes one planet's uploaded preview. Uploaders that cannot delete do nothing,
        which only means the old image lingers until it is overwritten.
        """

    def upload_planet_image(self, planet: str) -> str | None:
        """
        Optimizes, stamps and uploads one planet's preview. Returns its public URL, or
        None if there is no image for that planet.
        """
        image_path = constants.PREVIEWS_OUTPUT_DIR / f"{planet}.png"
        if not image_path.exists():
            log.warning(f"⚠️ No preview image for {planet} - skipping upload.")
            return None

        with log_section(f"🌍 Uploading {planet} preview..."):
            try:
                _optimize_png(image_path)
                _add_upload_timestamp_to_png(image_path)
                url = self.upload_single(image_path, f"{planet}.png")
                log.info(f"✅ {planet} uploaded.")
                return url
            except Exception:
                log.error(f"❌ Failed to upload {planet}.png")
                raise

    def write_viewer_config(self, planet_image_links: dict[str, str], names_link: str) -> None:
        """
        Writes the config file that a hosted viewer needs, with the public links.
        """
        _write_viewer_config_js(planet_image_links, names_link)

    def upload_all(self) -> None:
        """
        Uploads the planet names file and all preview images listed in it.
        Saves resulting download links to a JavaScript config file.
        """
        with log_section("🚀 Uploading preview assets..."):
            planet_names = _load_planet_names()
            planet_names_link = self.upload_planet_names_file()
            planet_image_links = self._upload_planet_images(planet_names)
            _write_viewer_config_js(planet_image_links, planet_names_link)
            log.info("✅ All assets uploaded successfully.")

    def upload_planet_names_file(self) -> str:
        """
        Uploads the planet names JS file and returns its public URL.
        """
        with log_section("📤 Uploading planet names file..."):
            try:
                # Add a timestamp to ensure the file appears changed to Dropbox,
                # even if its actual content hasn't changed. This helps preserve
                # a stable shareable link when using rclone.
                _inject_upload_timestamp_into_planet_names_file()
                url = self.upload_single(
                    constants.PLANET_NAMES_REMOTE_VIEWER_FILEPATH,
                    constants.PLANET_NAMES_REMOTE_FILENAME,
                )
                log.info("✅ Planet names uploaded.")
                return url
            except Exception:
                log.error("❌ Failed to upload planet names.")
                raise

    def _upload_planet_images(self, planet_names: list[str]) -> dict[str, str]:
        """
        Uploads all preview images and returns a dict of download links.
        """
        links: dict[str, str] = {}
        for planet in planet_names:
            url = self.upload_planet_image(planet)
            if url is not None:
                links[planet] = url
        return links

    @abstractmethod
    def upload_single(self, local_path: Path, remote_filename: str) -> str:
        """
        Uploads a single file and returns a public URL.
        """
        ...
