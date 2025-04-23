import json
from pathlib import Path

from src.FactorioPreviewToolkit.preview_generator.factorio_interface import run_factorio_command
from src.FactorioPreviewToolkit.shared.config import Config
from src.FactorioPreviewToolkit.shared.shared_constants import constants
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section


def _log_seed_from_map_gen_settings(settings_path: Path) -> int:
    """
    Extracts the seed from the given map-gen-settings file and validates it.
    """
    with log_section("🌱 Extracting seed from map-gen-settings..."):
        try:
            with settings_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                seed = data["seed"]
                if not isinstance(seed, int):
                    raise ValueError
        except Exception:
            log.error("❌ Invalid or missing seed in map-gen-settings.")
            raise

        log.info(f"✅ Seed extracted: {seed}")
        return seed


def _load_supported_planets(path: Path) -> list[str]:
    """
    Loads the list of supported planet names from the generated JSON file.
    """
    with log_section("📄 Loading supported planets list..."):
        try:
            with path.open("r", encoding="utf-8") as f:
                planets = json.load(f)
                if not isinstance(planets, list) or not all(isinstance(p, str) for p in planets):
                    raise ValueError
        except Exception:
            log.error("❌ Failed to load or parse planet names.")
            raise

        log.info(f"✅ Found {len(planets)} planets: {', '.join(planets)}")
        return planets


def write_planet_names_list_to_output(planets: list[str]) -> None:
    """
    Writes the list of supported planets in both JSON and JS format to the preview output directory.
    """
    # Write JSON version
    with constants.PLANET_NAMES_REMOTE_VIEWER_FILEPATH.open("w", encoding="utf-8") as f:
        json.dump(planets, f, indent=2)
    log.info(f"📋 Planet list written to JSON: {constants.PLANET_NAMES_REMOTE_VIEWER_FILEPATH}")

    # Write JS version
    with constants.PLANET_NAMES_LOCAL_VIEWER_FILEPATH.open("w", encoding="utf-8") as f:
        f.write("const planetNames = ")
        json.dump(planets, f, indent=2)
        f.write(";\n")
    log.info(f"📄 Planet list written to JS: {constants.PLANET_NAMES_LOCAL_VIEWER_FILEPATH}")


def generate_all_planet_previews(
    factorio_base_path: Path, settings_path: Path, preview_width: int, planet_names: list[str]
) -> None:
    """
    Generates preview images for all supported planets.
    """
    for planet in planet_names:
        with log_section(f"🪐 Generating preview for {planet}..."):
            try:
                _generate_preview_image(factorio_base_path, planet, settings_path, preview_width)
            except Exception:
                log.error(f"❌ Failed to generate preview for {planet}")
                raise


def _generate_preview_image(
    factorio_base_path: Path, planet: str, settings_path: Path, preview_width: int
) -> None:
    """
    Generates a single map preview image for the given planet using the Factorio CLI.
    """
    output = constants.PREVIEWS_OUTPUT_DIR / f"{planet}.png"

    args = [
        f"--generate-map-preview={output}",
        f"--map-gen-settings={settings_path}",
        f"--map-preview-size={preview_width}",
        f"--map-preview-planet={planet}",
    ]

    run_factorio_command(factorio_base_path, args)
    log.info(f"✅ Preview generated at {output}")


def run_full_preview_generation(factorio_base_path: Path) -> None:
    """
    Main entry point: prepares inputs and triggers map preview generation for all supported planets.
    """
    with log_section("🌍 Starting map preview generation..."):
        settings_path = Path(constants.MAP_GEN_SETTINGS_FILEPATH)
        _log_seed_from_map_gen_settings(settings_path)

        planet_names = _load_supported_planets(constants.PLANET_NAMES_GENERATION_FILEPATH)
        write_planet_names_list_to_output(planet_names)

        preview_width = Config.get().map_preview_size
        generate_all_planet_previews(factorio_base_path, settings_path, preview_width, planet_names)

        log.info("✅ All planet previews generated successfully.")
