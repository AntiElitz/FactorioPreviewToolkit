import json
import platform
import re
import sys
from pathlib import Path
from typing import Literal, Any


def is_valid_map_string(s: str) -> bool:
    """
    Checks if the string matches the map exchange format: >>>eN...<<<
    """
    return bool(re.match(r"^>>>eN[\sA-Za-z0-9+/=]+<<<$", s.strip()))


def sanitize_map_string(raw: str) -> str | None:
    """
    Strips all whitespace from the raw input and returns the cleaned map string
    if it's a valid Factorio map exchange string.
    """
    cleaned = re.sub(r"\s+", "", raw)
    return cleaned if is_valid_map_string(cleaned) else None


def get_project_root() -> Path:
    """
    Detects the root directory of the project, whether running from source or from a frozen executable.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[3]  # adjust if needed based on actual file depth


def resolve_relative_to_project_root(path: str | Path) -> Path:
    """
    Resolves the given path relative to the project root, unless it's already absolute.
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return (get_project_root() / path).resolve()


def get_script_base() -> Path:
    """
    Returns the root directory where assets and config files are located.
    Supports both development and PyInstaller bundle modes.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


def detect_os() -> Literal["windows", "linux", "mac"]:
    """
    Detects and returns the current OS name used in bundled rclone folder names.
    Raises an exception if the OS is unsupported.
    """
    os_name = platform.system().lower()
    match os_name:
        case "windows":
            return "windows"
        case "linux":
            return "linux"
        case "darwin":
            return "mac"
        case _:
            raise RuntimeError(f"❌ Unsupported OS {os_name}")


def get_supported_architecture() -> Literal["intel_amd64", "arm64", "unsupported"]:
    """
    Returns the normalized architecture name used in bundled rclone folder names.
    Returns "unsupported" if the architecture is not recognized.
    """
    arch_raw = platform.machine().lower()
    if arch_raw in ("x86_64", "amd64", "amd"):
        return "intel_amd64"
    if arch_raw in ("arm64", "aarch64"):
        return "arm64"
    return "unsupported"


def write_js_variable(filepath: Path, variable_name: str, value: Any) -> None:
    """
    Writes a JS file with a single variable assignment.
    Example output: const variable_name = <json-encoded value>;
    """
    with filepath.open("w", encoding="utf-8") as f:
        f.write(f"const {variable_name} = ")
        json.dump(value, f, indent=2)
        f.write(";\n")


def read_js_variable(filepath: Path, variable_name: str) -> Any:
    """
    Reads a JS file that declares a variable and returns its value.
    Expects format: const <variable_name> = <value>;
    """
    prefix = f"const {variable_name} = "
    with filepath.open("r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content.startswith(prefix):
            raise ValueError(f"JS file does not start with expected prefix: {prefix}")
        json_part = content[len(prefix) :]
        if json_part.endswith(";"):
            json_part = json_part[:-1]
        return json.loads(json_part)
