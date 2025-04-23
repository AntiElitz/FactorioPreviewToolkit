"""
Handles preview generation setup using a dummy save.

This module injects Lua code into the control.lua of a dummy save file that:
- Decodes a map exchange string at tick 0
- Extracts map-gen-settings
- Lists available planets (based on the loaded game/mod environment)

It then runs Factorio in benchmark mode to trigger the script and collect results.
"""

import json
import textwrap
import zipfile
from pathlib import Path

from src.FactorioPreviewToolkit.preview_generator.factorio_interface import run_factorio_command
from src.FactorioPreviewToolkit.shared.shared_constants import constants
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section


def _build_control_lua(
    exchange_string: str, combined_map_gen_settings_filename: str, planet_names_filename: str
) -> str:
    """
    Generates Lua code that:
    - Extracts combined-map-gen-settings from a map exchange string
    - Collects supported planet names (from game.planets)
    Uses pcall to support both Factorio 2.0+ (helpers.*) and 1.1 (game.*) environments.
    """
    return textwrap.dedent(
        f"""
        script.on_event(defines.events.on_tick, function(event)
            if event.tick == 0 then
                local exchange_string = "{exchange_string}"
                local combined_map_gen_settings_filename = "{combined_map_gen_settings_filename}"
                local supported_planets_filename = "{planet_names_filename}"

                -- Try Factorio 2.0+ (helpers.* and game.planets)
                local success, err = pcall(function()
                    -- Extract and write map-gen-settings
                    local json = helpers.table_to_json(helpers.parse_map_exchange_string(exchange_string))
                    helpers.write_file(combined_map_gen_settings_filename, json)

                    -- Extract and write supported planets
                    local planet_names = {{}}
                    for name, _ in pairs(game.planets or {{}}) do
                        table.insert(planet_names, name)
                    end
                    local json_planets = helpers.table_to_json(planet_names)
                    helpers.write_file(supported_planets_filename, json_planets)
                end)

                -- Fallback for Factorio 1.1 (game.* only)
                if not success then
                    -- Extract and write map-gen-settings
                    local json = game.table_to_json(game.parse_map_exchange_string(exchange_string))
                    game.write_file(combined_map_gen_settings_filename, json)

                    -- Only 'nauvis' is supported
                    local json_planets = game.table_to_json({{"nauvis"}})
                    game.write_file(supported_planets_filename, json_planets)
                end
            end
        end)
        """
    ).strip()


def _create_dummy_save(factorio_path: Path) -> None:
    """
    Creates a dummy save used to execute Lua code to extract preview-relevant data.
    Cleans up any leftover .zip from previous crashes.
    """
    with log_section("🛠️ Creating dummy save..."):
        save_folder = constants.DUMMY_SAVE_TO_EXECUTE_LUA_CODE_PATH
        save_zip = save_folder.with_suffix(".zip")

        if save_zip.exists():
            save_zip.unlink()
            log.info(f"🗑️ Removed leftover dummy save zip: {save_zip}")

        log.info(f"📦 Creating dummy save at: {save_folder}")
        run_factorio_command(factorio_path, ["--create", str(save_zip)])

        log.info("📂 Extracting dummy save zip.")
        with zipfile.ZipFile(save_zip, "r") as zip_ref:
            zip_ref.extractall(save_folder.parent)
        save_zip.unlink()
        log.info("✅ Dummy save created.")


def _inject_preview_setup_script(exchange_string: str) -> None:
    """
    Overwrites control.lua with the Lua script that runs preview setup on tick 0.
    """
    with log_section("🛠️ Injecting preview setup script into control.lua..."):
        control_lua = constants.CONTROL_LUA_FILEPATH

        # Build and write the script directly
        injected_script = _build_control_lua(
            exchange_string,
            constants.COMBINED_MAP_GEN_SETTINGS_FILENAME,
            constants.PLANET_NAMES_REMOTE_FILENAME,
        )

        control_lua.write_text(
            control_lua.read_text(encoding="utf-8").strip() + "\n\n" + injected_script + "\n",
            encoding="utf-8",
        )

        log.info("✅ Lua setup script written.")


def _extract_map_gen_settings_from_json() -> None:
    """
    Extracts map-gen-settings from the combined JSON written by Factorio.
    """
    with log_section("🛠️ Extracting map-gen-settings from exported data..."):
        combined_path = constants.COMBINED_MAP_GEN_SETTINGS_FILEPATH

        with combined_path.open("r", encoding="utf-8") as f:
            combined_data = json.load(f)

        map_gen_settings = combined_data.get("map_gen_settings")
        if not map_gen_settings:
            raise ValueError("❌ 'map_gen_settings' key missing in combined settings JSON.")

        output_path = Path(constants.MAP_GEN_SETTINGS_FILEPATH)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(map_gen_settings, f, indent=2)

        log.info(f"✅ map-gen-settings extracted to {constants.MAP_GEN_SETTINGS_FILEPATH}")


def _run_preview_setup_save(factorio_path: Path) -> None:
    """
    Runs the dummy save to trigger preview setup Lua script.
    """
    save_folder = constants.DUMMY_SAVE_TO_EXECUTE_LUA_CODE_PATH
    with log_section("🛠️ Running dummy save to extract preview setup data..."):
        run_factorio_command(
            factorio_path,
            [
                "--benchmark",
                str(save_folder),
                "-ticks",
                "1",
            ],
        )
        log.info("✅ Lua script executed and output files generated.")


def run_preview_setup_pipeline(factorio_path: Path, map_string: str) -> None:
    """
    Full pipeline: prepares dummy save, injects Lua setup script, runs Factorio, and extracts result.
    """
    with log_section("🔄 Running preview setup pipeline..."):
        _create_dummy_save(factorio_path)
        _inject_preview_setup_script(map_string)
        _run_preview_setup_save(factorio_path)
        _extract_map_gen_settings_from_json()
        log.info("✅ Preview setup complete.")
