from src.FactorioPreviewToolkit.shared.utils import get_project_root


class _Constants:
    """
    Central definition of constants like directory and file paths used by the toolkit.
    Some directories are created on import to ensure availability.
    """

    # === Project & Config ===
    BASE_PROJECT_DIR = get_project_root()
    PREVIEW_TOOLKIT_CONFIG_FILEPATH = BASE_PROJECT_DIR / "config.ini"

    # === Logging & Assets ===
    LOGS_DIR = BASE_PROJECT_DIR / "logs"
    BASE_ASSETS_DIR = BASE_PROJECT_DIR / "assets"

    # === Output Folder for Generated Previews ===
    PREVIEWS_OUTPUT_DIR = BASE_PROJECT_DIR / "previews"
    PREVIEW_LINKS_FILEPATH = PREVIEWS_OUTPUT_DIR / "remote_viewer_config.txt"

    # === Temporary / Working Directories ===
    BASE_TEMP_DIR = BASE_PROJECT_DIR / "temp_files"
    FACTORIO_WRITE_DATA_DIR = BASE_TEMP_DIR / "data"
    SCRIPT_OUTPUT_DIR = FACTORIO_WRITE_DATA_DIR / "script-output"
    MAP_GEN_SETTINGS_FILEPATH = BASE_TEMP_DIR / "map-gen-settings.json"

    # === Dummy Save for Settings Generation ===
    DUMMY_SAVE_TO_EXECUTE_LUA_CODE_PATH = BASE_TEMP_DIR / "dummy-save-to-create-map-gen-settings"
    CONTROL_LUA_FILEPATH = DUMMY_SAVE_TO_EXECUTE_LUA_CODE_PATH / "control.lua"

    # === File Naming & Generated Outputs ===
    COMBINED_MAP_GEN_SETTINGS_FILENAME = "combined-map-gen-settings.json"
    COMBINED_MAP_GEN_SETTINGS_FILEPATH = SCRIPT_OUTPUT_DIR / COMBINED_MAP_GEN_SETTINGS_FILENAME
    PLANET_NAMES_REMOTE_FILENAME = "remote_planet_names.json"
    PLANET_NAMES_LOCAL_FILENAME = "local_planet_names.js"
    PLANET_NAMES_GENERATION_FILEPATH = SCRIPT_OUTPUT_DIR / PLANET_NAMES_REMOTE_FILENAME
    PLANET_NAMES_REMOTE_VIEWER_FILEPATH = PREVIEWS_OUTPUT_DIR / PLANET_NAMES_REMOTE_FILENAME
    PLANET_NAMES_LOCAL_VIEWER_FILEPATH = PREVIEWS_OUTPUT_DIR / PLANET_NAMES_LOCAL_FILENAME
    FACTORIO_CONFIG_FILEPATH = BASE_TEMP_DIR / "factorio_config.ini"
    FACTORIO_LOCK_FILEPATH = FACTORIO_WRITE_DATA_DIR / ".lock"

    # === Ensure required directories exist ===
    BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEWS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


constants = _Constants()
