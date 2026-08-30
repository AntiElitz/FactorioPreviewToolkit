import json
import os
import re
import subprocess
import sys
import textwrap
import time
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.FactorioPreviewToolkit.shared.config import Config
from src.FactorioPreviewToolkit.shared.shared_constants import constants
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section
from src.FactorioPreviewToolkit.shared.utils import detect_os, resolve_relative_to_project_root

_factorio_version_cache: dict[Path, tuple[int, int]] = {}


def get_factorio_version(factorio_path: Path) -> tuple[int, int]:
    """
    Detects the major and minor Factorio version from CLI output.
    Returns (major, minor) as integers.
    Successful lookups are cached, because this launches Factorio and runs before every
    command - otherwise every single planet pays for an extra Factorio startup.
    """
    cached_version = _factorio_version_cache.get(factorio_path)
    if cached_version is not None:
        return cached_version

    try:
        result = subprocess.run(
            [str(factorio_path), "--version"], capture_output=True, text=True, check=True
        )
        match = re.search(r"Version:\s+(\d+)\.(\d+)", result.stdout)
        if match:
            version = (int(match.group(1)), int(match.group(2)))
            _factorio_version_cache[factorio_path] = version
            return version
    except Exception as e:
        log.error(f"⚠️ Failed to detect Factorio version: {e}")

    # Deliberately not cached, so a failed detection is retried instead of sticking.
    return (0, 0)  # Default fallback


def wait_for_factorio_lock_to_release(timeout_in_sec: int = 30) -> bool:
    """
    Waits for the Factorio lock file to be released, up to a timeout.
    """
    start_time = time.time()
    lock_file = constants.FACTORIO_LOCK_FILEPATH

    while lock_file.exists():
        log.info(f"📋 Waiting for '{lock_file}' release.")
        if time.time() - start_time > timeout_in_sec:
            log.error(f"❌ Timeout: Lock file still exists after {timeout_in_sec}s.")
            raise TimeoutError(f"Lock file '{lock_file}' still exists.")
        time.sleep(1)

    return True


def remove_map_preview_planet_arg(args: list[str]) -> None:
    """
    Removes '--map-preview-planet=...' in-place if Factorio version is 1.x.
    """
    for idx, arg in enumerate(args):
        if arg.startswith("--map-preview-planet="):
            log.info("⛔ Stripping '--map-preview-planet=...' (unsupported in Factorio 1.1)")
            del args[idx]


def _get_factorio_install_root(factorio_executable_path: Path) -> Path | None:
    """
    Returns the installation root of a Factorio executable.
    Windows/Linux: <root>/bin/x64/factorio[.exe]   macOS: <root>/Contents/MacOS/factorio
    """
    depth = 1 if detect_os() == "macOS" else 2
    parents = factorio_executable_path.resolve().parents
    return parents[depth] if len(parents) > depth else None


def _get_system_factorio_data_dir() -> Path | None:
    """
    Returns the OS specific Factorio user data folder, which holds 'mods' for
    regular (installer/Steam) installations.
    """
    os_name = detect_os()
    if os_name == "windows":
        appdata = os.environ.get("APPDATA")
        return Path(appdata) / "Factorio" if appdata else None
    if os_name == "linux":
        return Path.home() / ".factorio"
    return Path.home() / "Library" / "Application Support" / "factorio"


def _prefers_system_data_paths(install_root: Path) -> bool:
    """
    Standalone (zip/tar) installs ship a 'config-path.cfg' that disables the system
    data paths, which means their mods live inside the installation folder instead.
    """
    config_path_file = install_root / "config-path.cfg"
    try:
        content = config_path_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return True

    # Read the setting's value rather than looking for a fixed string: the key is
    # 'use-system-read-write-data-directories', and matching anything shorter means
    # never recognising a standalone install - which sends Factorio to the system
    # mod folder, where a mod built for another version refuses to load.
    for line in content.splitlines():
        line = line.split("#", 1)[0].strip().replace(" ", "")
        key, separator, value = line.partition("=")
        if separator and key.lower() == "use-system-read-write-data-directories":
            return value.strip().lower() != "false"
    return True


def _auto_detect_mod_directory(factorio_executable_path: Path) -> Path | None:
    """
    Finds the mod folder belonging to the given Factorio executable.
    Returns None if no mod folder exists, in which case Factorio loads vanilla only.
    """
    install_root = _get_factorio_install_root(factorio_executable_path)
    system_data_dir = _get_system_factorio_data_dir()

    portable_mods = install_root / "mods" if install_root else None
    system_mods = system_data_dir / "mods" if system_data_dir else None

    if install_root and not _prefers_system_data_paths(install_root):
        candidates = [portable_mods, system_mods]
    else:
        candidates = [system_mods, portable_mods]

    for candidate in candidates:
        if candidate and candidate.is_dir():
            return candidate
    return None


@lru_cache(maxsize=None)
def resolve_mod_directory(factorio_executable_path: Path) -> Path | None:
    """
    Resolves the mod folder to hand to Factorio, based on the 'factorio_mod_directory' config.
    Without it Factorio would use the toolkit's own (empty) write-data folder,
    so planets added by mods would never show up.
    """
    setting = str(Config.get().factorio_mod_directory).strip()

    if setting.lower() in ("none", ""):
        log.info("⛔ Mod loading disabled - only vanilla planets will be detected.")
        return None

    if setting.lower() == "auto":
        mod_dir = _auto_detect_mod_directory(factorio_executable_path)
        if mod_dir is None:
            log.warning(
                "⚠️ Could not auto-detect a Factorio mod folder - continuing without mods. "
                "Set 'factorio_mod_directory' in config.ini to the folder containing "
                "'mod-list.json' if you use mods."
            )
            return None
        log.info(f"🧩 Auto-detected mod folder: {mod_dir}")
        return mod_dir

    mod_dir = resolve_relative_to_project_root(setting)
    if not mod_dir.is_dir():
        raise ValueError(
            f"❌ The configured 'factorio_mod_directory' does not exist: {mod_dir}\n"
            f"Use 'auto', 'none' or a path to the folder containing 'mod-list.json'."
        )
    log.info(f"🧩 Using configured mod folder: {mod_dir}")
    return mod_dir


def _parse_mod_selection(raw: bytes) -> dict[str, bool] | None:
    """
    Parses a mod-list.json into a name -> enabled mapping, or None if it cannot be read.
    """
    try:
        data = json.loads(raw.decode("utf-8"))
        return {
            str(entry["name"]): bool(entry.get("enabled"))
            for entry in data["mods"]
            if isinstance(entry, dict) and "name" in entry
        }
    except Exception:
        return None


def _describe_mod_selection_changes(original: bytes, current: bytes) -> str:
    """
    Summarizes what Factorio changed about which mods are enabled.
    Returns an empty string when only the file's formatting changed, which Factorio
    does on any normal run and which is not worth warning about.
    """
    before = _parse_mod_selection(original)
    after = _parse_mod_selection(current)
    if before is None or after is None:
        return "could not compare the mod lists"

    disabled = sorted(name for name, on in before.items() if on and not after.get(name, False))
    enabled = sorted(name for name, on in after.items() if on and not before.get(name, False))
    removed = sorted(set(before) - set(after))

    parts = []
    if disabled:
        parts.append(f"disabled: {', '.join(disabled)}")
    if enabled:
        parts.append(f"enabled: {', '.join(enabled)}")
    if removed:
        parts.append(f"removed: {', '.join(removed)}")
    return "; ".join(parts)


@contextmanager
def preserved_mod_list(factorio_executable_path: Path) -> Iterator[None]:
    """
    Keeps the user's mod selection intact for the duration of the run.
    Factorio rewrites 'mod-list.json' in the mod folder when it decides to disable mods,
    for example after a Factorio update made some of them incompatible. Since the toolkit
    points Factorio at the user's real mod folder, that would silently change the setup
    they play with, so the file is put back the way it was.
    """
    mod_dir = resolve_mod_directory(factorio_executable_path)
    mod_list_path = mod_dir / "mod-list.json" if mod_dir else None
    original: bytes | None = None

    if mod_list_path is not None and mod_list_path.is_file():
        try:
            original = mod_list_path.read_bytes()
        except OSError as e:
            log.warning(f"⚠️ Could not read '{mod_list_path}', cannot protect it: {e}")

    try:
        yield
    finally:
        if original is not None and mod_list_path is not None:
            try:
                if mod_list_path.read_bytes() != original:
                    changes = _describe_mod_selection_changes(original, mod_list_path.read_bytes())
                    mod_list_path.write_bytes(original)
                    if changes:
                        log.warning(
                            f"⚠️ Factorio changed your mod selection ({changes}) - "
                            f"restored '{mod_list_path}'. Those mods are most likely "
                            f"incompatible with this Factorio version."
                        )
                    else:
                        # Factorio rewrites the file in its own formatting on a normal run.
                        log.info(f"📋 Restored the original formatting of '{mod_list_path}'.")
            except OSError as e:
                log.error(f"❌ Failed to restore '{mod_list_path}': {e}")


def _build_mod_directory_args(factorio_executable_path: Path) -> list[str]:
    """
    Builds the '--mod-directory' CLI args, or none if mods should not be loaded.
    """
    mod_dir = resolve_mod_directory(factorio_executable_path)
    return ["--mod-directory", str(mod_dir)] if mod_dir else []


def _build_factorio_command(executable_path: Path, args: list[str], config_path: Path) -> list[str]:
    """
    Builds the full Factorio CLI command with resolved paths, config file and mod folder.
    """
    # Remove unsupported CLI args if needed
    if get_factorio_version(executable_path)[0] <= 1:
        remove_map_preview_planet_arg(args)

    resolved_args = [str(Path(arg).resolve()) if not arg.startswith("--") else arg for arg in args]
    return (
        [str(executable_path), "--config", str(config_path)]
        + _build_mod_directory_args(executable_path)
        + resolved_args
    )


def _build_subprocess_kwargs() -> dict[str, Any]:
    """
    Builds default subprocess.run kwargs with logging and priority settings.
    """
    return {
        "check": True,
        "capture_output": True,
        "text": True,
        **_get_priority_settings(),
    }


def _get_priority_settings() -> dict[str, Any]:
    """
    Returns platform-specific CPU priority settings for subprocess.run.
    """
    if sys.platform == "win32":
        return {"creationflags": subprocess.IDLE_PRIORITY_CLASS}
    elif sys.platform in ("linux", "darwin"):
        return {"preexec_fn": lambda: os.nice(19)}
    return {}


def update_config_file(config_path: Path) -> None:
    """
    Updates the Factorio config file if the content has to change.
    If the file doesn't exist, it will be created with the default content.
    """
    existing_content = ""
    default_content = _generate_default_config_content()
    if config_path.exists():
        with open(config_path, "r") as config_file:
            existing_content = config_file.read()
    if existing_content != default_content:
        with log_section(f"📄 Creating/Updating Factorio config at {config_path}..."):
            with open(config_path, "w") as config_file:
                config_file.write(default_content)
            log.info("✅ Factorio config created/updated.")


def _generate_default_config_content() -> str:
    """
    Generates the default content for the config file.
    Enables Factorio's data stage cache, which is what makes repeated launches cheap:
    every planet needs its own launch, and with a large modpack loading the prototypes
    is nearly all of that time. The cache is written into the toolkit's own write-data
    folder, so the user's Factorio installation is not touched.
    """
    if detect_os() == "macOS":
        read_data = "__PATH__executable__/../data"
    else:
        read_data = "__PATH__executable__/../../data"
    cache_prototype_data = "true" if Config.get().use_factorio_prototype_cache else "false"
    return textwrap.dedent(f"""
        ; version=12
        [path]
        read-data={read_data}
        write-data={constants.FACTORIO_WRITE_DATA_DIR}
        [other]
        cache-prototype-data={cache_prototype_data}
        """)


def _is_write_data_lock_conflict(error: subprocess.CalledProcessError) -> bool:
    """
    Tells whether Factorio failed because another Factorio held the write-data lock.
    """
    output = f"{error.stdout or ''}\n{error.stderr or ''}".lower()
    return "couldn't create lock file" in output


def run_factorio_command(
    factorio_executable_path: Path, args: list[str], attempts: int = 3
) -> None:
    """
    Runs Factorio with the given args and config, with low-priority CPU settings.

    A busy write-data lock is retried instead of failing the whole run: the lock is held
    for the lifetime of a Factorio process, and 'wait_for_factorio_lock_to_release' can
    only wait for a lock file that is already there - it loses the race when the previous
    Factorio is still shutting down.
    """
    config_path = constants.FACTORIO_CONFIG_FILEPATH
    update_config_file(config_path)
    log.info(f"⚙️ Using config file: {config_path}")

    for attempt in range(1, attempts + 1):
        try:
            wait_for_factorio_lock_to_release()
            cmd = _build_factorio_command(factorio_executable_path, args, config_path)
            kwargs = _build_subprocess_kwargs()
            subprocess.run(cmd, **kwargs)
            return

        except FileNotFoundError:
            log.error("❌ Factorio executable not found.")
            raise
        except subprocess.CalledProcessError as e:
            if _is_write_data_lock_conflict(e) and attempt < attempts:
                log.warning(
                    f"⚠️ Factorio's data lock is still held (attempt {attempt}/{attempts}). "
                    f"Retrying in 5s - is another Factorio using this toolkit's temp folder?"
                )
                time.sleep(5)
                continue
            log.error("❌ Factorio execution failed.")
            log.error(f"stdout:\n{e.stdout}")
            log.error(f"stderr:\n{e.stderr}")
            raise
