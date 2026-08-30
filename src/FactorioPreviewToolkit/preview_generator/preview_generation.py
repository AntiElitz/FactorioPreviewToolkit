import json
from datetime import datetime, timezone
from pathlib import Path

from src.FactorioPreviewToolkit.preview_generator.factorio_interface import run_factorio_command
from src.FactorioPreviewToolkit.shared.config import Config
from src.FactorioPreviewToolkit.shared.shared_constants import constants
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section
from src.FactorioPreviewToolkit.uploader.base_uploader import BaseUploader
from src.FactorioPreviewToolkit.uploader.factory import get_uploader


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


# Vanilla planets in their in-game order. Everything else comes from mods.
_VANILLA_PLANET_ORDER = ("nauvis", "vulcanus", "gleba", "fulgora", "aquilo")


def _sort_planets(planets: list[str]) -> list[str]:
    """
    Sorts planets deterministically: vanilla planets in their known order first,
    then mod planets alphabetically. Lua's pairs() returns them in arbitrary order,
    which would otherwise shuffle the viewer tabs on every run.
    """

    def sort_key(planet: str) -> tuple[int, str]:
        if planet in _VANILLA_PLANET_ORDER:
            return (_VANILLA_PLANET_ORDER.index(planet), "")
        return (len(_VANILLA_PLANET_ORDER), planet)

    return sorted(planets, key=sort_key)


def _select_planets(available: list[str]) -> list[str]:
    """
    Narrows the planets found in the game down to the ones configured via 'planets'.
    Every planet costs a full Factorio startup, so this is the main way to save time
    when a modpack adds dozens of them.
    Understands 'all', 'vanilla', explicit names and '!name' exclusions, in that order.
    """
    tokens = [token.strip().lower() for token in Config.get().planets.split(",")]
    by_lowercase_name = {planet.lower(): planet for planet in available}

    selected: list[str] = []
    excluded: set[str] = set()
    unknown: list[str] = []

    def select(planet: str) -> None:
        if planet not in selected:
            selected.append(planet)

    for token in tokens:
        if not token:
            continue
        if token.startswith("!"):
            name = token[1:].strip()
            if name in by_lowercase_name:
                excluded.add(by_lowercase_name[name])
            else:
                unknown.append(token)
        elif token == "all":
            for planet in available:
                select(planet)
        elif token == "vanilla":
            for planet in available:
                if planet in _VANILLA_PLANET_ORDER:
                    select(planet)
        elif token in by_lowercase_name:
            select(by_lowercase_name[token])
        else:
            unknown.append(token)

    chosen = [planet for planet in selected if planet not in excluded]

    if unknown:
        log.warning(f"⚠️ Ignoring unknown entries in the 'planets' config: {', '.join(unknown)}")
    if not chosen:
        raise ValueError(
            f"The 'planets' config selected none of the available planets.\n"
            f"Available: {', '.join(available)}"
        )
    if len(chosen) < len(available):
        skipped = [planet for planet in available if planet not in chosen]
        log.info(f"🎯 Generating {len(chosen)} of {len(available)} planets (config 'planets').")
        log.info(f"⏭️ Skipping: {', '.join(skipped)}")

    return chosen


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


def write_planet_names_list_to_output(planets: list[str], map_string: str = "") -> None:
    """
    Writes the list of supported planets in both JSON and JS format to the preview output directory.
    The map exchange string travels along with it, so the viewer can offer it for copying -
    that is what lets an audience generate the very same map.
    Adds a UTC '' field to the JSON file to ensure Dropbox sees the file as updated.
    """
    # Wrap with metadata for the JSON version
    json_payload = {
        "planets": planets,
        "map_string": map_string,
        "time": datetime.now(timezone.utc).isoformat(),
    }

    # Write JSON version
    with constants.PLANET_NAMES_REMOTE_VIEWER_FILEPATH.open("w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2)
    log.info(f"📋 Planet list written to JSON: {constants.PLANET_NAMES_REMOTE_VIEWER_FILEPATH}")

    # Write JS version (list + upload time).
    # Assignments to window rather than 'const' declarations: the viewer reloads this
    # file periodically to notice a new run, and re-declaring a const would throw.
    with constants.PLANET_NAMES_LOCAL_VIEWER_FILEPATH.open("w", encoding="utf-8") as f:
        f.write("window.planetNames = ")
        json.dump(planets, f, indent=2)
        f.write(";\n")

        f.write("window.planetNamesUploadTime = ")
        f.write(json.dumps(json_payload["time"]))
        f.write(";\n")

        f.write("window.mapExchangeString = ")
        f.write(json.dumps(map_string))
        f.write(";\n")

    log.info(f"📄 Planet list written to JS: {constants.PLANET_NAMES_LOCAL_VIEWER_FILEPATH}")


def generate_all_planet_previews(
    factorio_base_path: Path,
    settings_path: Path,
    preview_width: int,
    planet_names: list[str],
    map_string: str = "",
) -> list[str]:
    """
    Generates preview images for all supported planets and returns the ones that succeeded.
    A planet that cannot be rendered (happens with some modded planets) is skipped instead
    of aborting the whole run, so the remaining planets still get their previews.

    Each planet is uploaded as soon as it is rendered, together with a planet list holding
    exactly the planets uploaded so far. That way an audience watching the hosted viewer
    sees planets appear one by one during a run that can take half an hour - and never a
    tab whose image is still the previous map's.
    """
    generated: list[str] = []
    failed: list[str] = []
    uploader = get_uploader_for_run()
    uploaded_links: dict[str, str] = {}
    planet_names_link = ""

    if uploader is not None:
        # Clears the previous run's images and publishes the full planet list, so the
        # hosted viewer shows every tab right away with a placeholder.
        planet_names_link = uploader.prepare_remote(planet_names)

    for planet in planet_names:
        with log_section(f"🪐 Generating preview for {planet}..."):
            try:
                _generate_preview_image(factorio_base_path, planet, settings_path, preview_width)
                generated.append(planet)
            except Exception:
                log.error(f"❌ Failed to generate preview for {planet} - skipping this planet.")
                failed.append(planet)
                continue

        if uploader is None:
            continue

        # Only the image: the planet list was published up front, and re-publishing it per
        # planet would make every viewer reload every image it already has.
        url = uploader.upload_planet_image(planet)
        if url is not None:
            uploaded_links[planet] = url

    if uploader is not None:
        if failed:
            # Drop the planets that never rendered, so no tab waits forever.
            write_planet_names_list_to_output(generated, map_string)
            planet_names_link = uploader.upload_planet_names_file()
        if uploaded_links:
            uploader.write_viewer_config(uploaded_links, planet_names_link)

    if failed:
        log.warning(f"⚠️ No preview generated for: {', '.join(failed)}")
    if not generated:
        raise RuntimeError("❌ Preview generation failed for every planet.")

    return generated


def get_uploader_for_run() -> BaseUploader | None:
    """
    Returns the uploader to use during generation, or None when uploading is turned off.
    """
    if Config.get().upload_method == "skip":
        log.info("⏩ Uploading is disabled ('upload_method = skip').")
        return None

    uploader = get_uploader()
    log.info(f"📤 Uploading each planet as it is rendered ('{Config.get().upload_method}').")
    return uploader


def _summarize(names: list[str], limit: int = 8) -> str:
    """
    Joins names for a log line, keeping it readable when a modpack drops dozens at once.
    """
    if len(names) <= limit:
        return ", ".join(names)
    return f"{', '.join(names[:limit])} ... and {len(names) - limit} more"


def _load_previously_generated_planets() -> list[str]:
    """
    Reads the planet list the previous run wrote, so its images can be cleaned up.
    Returns an empty list on the first run, or if the file is gone or unreadable.
    """
    try:
        with constants.PLANET_NAMES_REMOTE_VIEWER_FILEPATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return [planet for planet in data.get("planets", []) if isinstance(planet, str)]
    except Exception:
        return []


def _delete_outdated_previews(planet_names: list[str], previous_planets: list[str]) -> None:
    """
    Deletes the preview images of this run's planets and of planets the previous run
    generated but this one does not.

    The first part matters because the planet list is written before the images exist,
    so the viewer shows a tab per planet right away - a leftover image from an earlier
    map string would otherwise be served under the new one, the wrong map with nothing
    saying so. The viewer now shows "no preview available yet" until the real image lands.

    The second part keeps the folder from filling up when a run covers fewer planets
    than the one before it - a 41 planet modpack followed by a vanilla run leaves 36
    obsolete images behind.

    Only images this tool generated are touched. Anything else in the output folder is
    left alone, since it may be a user's own image referenced from 'planetPreviewSources'.
    """
    dropped = [planet for planet in previous_planets if planet not in planet_names]

    deleted = 0
    for planet in list(planet_names) + dropped:
        image_path = constants.PREVIEWS_OUTPUT_DIR / f"{planet}.png"
        try:
            if image_path.is_file():
                image_path.unlink()
                deleted += 1
        except OSError as e:
            log.warning(f"⚠️ Could not delete the old preview '{image_path}': {e}")

    if deleted:
        log.info(f"🗑️ Removed {deleted} preview image(s) from the previous run.")
    if dropped:
        log.info(
            f"🧹 Cleaned up {len(dropped)} planet(s) no longer generated: {_summarize(dropped)}"
        )


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


def run_full_preview_generation(factorio_base_path: Path, map_string: str = "") -> None:
    """
    Main entry point: prepares inputs and triggers map preview generation for all supported planets.
    """
    with log_section("🌍 Starting map preview generation..."):
        settings_path = Path(constants.MAP_GEN_SETTINGS_FILEPATH)
        _log_seed_from_map_gen_settings(settings_path)

        available_planets = _sort_planets(
            _load_supported_planets(constants.PLANET_NAMES_GENERATION_FILEPATH)
        )
        planet_names = _select_planets(available_planets)

        # Read before the list is overwritten: it tells us which images this tool
        # generated last time, and therefore which ones it may clean up.
        previous_planets = _load_previously_generated_planets()

        # Written up front, so the viewer already shows all planet tabs while the
        # much slower image rendering is still running.
        write_planet_names_list_to_output(planet_names, map_string)
        _delete_outdated_previews(planet_names, previous_planets)

        preview_width = Config.get().map_preview_size
        generated_planets = generate_all_planet_previews(
            factorio_base_path, settings_path, preview_width, planet_names, map_string
        )

        if generated_planets != planet_names:
            # Rewritten so the viewer stops offering planets that could not be rendered.
            log.info("📝 Updating planet list to the planets that were actually rendered...")
            write_planet_names_list_to_output(generated_planets, map_string)

        log.info(f"✅ Previews generated for {len(generated_planets)} planet(s).")
