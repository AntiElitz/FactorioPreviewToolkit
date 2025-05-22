import os
import re
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

from src.FactorioPreviewToolkit.shared.shared_constants import constants
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section
from src.FactorioPreviewToolkit.shared.utils import detect_os


def get_factorio_version(factorio_path: Path) -> tuple[int, int]:
    """
    Detects the major and minor Factorio version from CLI output.
    Returns (major, minor) as integers.
    """
    try:
        result = subprocess.run(
            [str(factorio_path), "--version"], capture_output=True, text=True, check=True
        )
        match = re.search(r"Version:\s+(\d+)\.(\d+)", result.stdout)
        if match:
            return int(match.group(1)), int(match.group(2))
    except Exception as e:
        log.error(f"⚠️ Failed to detect Factorio version: {e}")
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


def _build_factorio_command(executable_path: Path, args: list[str], config_path: Path) -> list[str]:
    """
    Builds the full Factorio CLI command with resolved paths and config file.
    """
    # Remove unsupported CLI args if needed
    if get_factorio_version(executable_path)[0] <= 1:
        remove_map_preview_planet_arg(args)

    resolved_args = [str(Path(arg).resolve()) if not arg.startswith("--") else arg for arg in args]
    return [str(executable_path), "--config", str(config_path)] + resolved_args


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
    """
    if detect_os() == "macOS":
        read_data = "__PATH__executable__/../data"
    else:
        read_data = "__PATH__executable__/../../data"
    return textwrap.dedent(
        f"""
        ; version=12
        [path]
        read-data={read_data}
        write-data={constants.FACTORIO_WRITE_DATA_DIR}
        """
    )


def run_factorio_command(factorio_executable_path: Path, args: list[str]) -> None:
    """
    Runs Factorio with the given args and config, with low-priority CPU settings.
    """
    config_path = constants.FACTORIO_CONFIG_FILEPATH
    update_config_file(config_path)
    log.info(f"⚙️ Using config file: {config_path}")

    try:
        wait_for_factorio_lock_to_release()
        cmd = _build_factorio_command(factorio_executable_path, args, config_path)
        kwargs = _build_subprocess_kwargs()
        subprocess.run(cmd, **kwargs)

    except FileNotFoundError:
        log.error("❌ Factorio executable not found.")
        raise
    except subprocess.CalledProcessError as e:
        log.error("❌ Factorio execution failed.")
        log.error(f"stdout:\n{e.stdout}")
        log.error(f"stderr:\n{e.stderr}")
        raise
