import subprocess
import time
from pathlib import Path
from typing import Literal, Any

from pydantic import BaseModel, model_validator, field_validator
from pydantic_core.core_schema import FieldValidationInfo, ValidationInfo
from typing_extensions import Self

from src.FactorioPreviewToolkit.shared.structured_logger import log
from src.FactorioPreviewToolkit.shared.utils import (
    resolve_relative_to_project_root,
    detect_os,
    get_supported_architecture,
)


def _is_rclone_remote_configured(remote_name: str, rclone_path: Path) -> bool:
    """
    Checks if a given rclone remote is configured.
    """
    result = subprocess.run(
        [str(rclone_path), "listremotes"],
        capture_output=True,
        text=True,
    )
    return f"{remote_name}:" in result.stdout


def _run_dropbox_auto_setup(rclone_path: Path) -> None:
    """
    Runs `rclone config create` to set up a Dropbox remote called FactorioPreviewToolkitDropbox.
    """
    subprocess.run(
        [str(rclone_path), "config", "create", "FactorioPreviewToolkitDropbox", "dropbox"]
    )


class Settings(BaseModel):
    """
    Validates and normalizes all config values loaded from config.ini.
    Resolves project-relative paths and applies computed fields.
    """

    # === Factorio Path Detection ===
    factorio_locator_method: Literal["fixed_path", "active_window_monitor"]
    fixed_path_factorio_executable: Path = Path("not-used")
    factorio_locator_poll_interval_in_seconds: float = 2

    # === Map Exchange Input ===
    map_exchange_input_method: Literal["clipboard_monitor", "file_monitor"]
    file_monitor_filepath: Path = Path("not-used")
    map_exchange_input_poll_interval_in_seconds: float = 0.5

    # === Preview Generation ===
    map_preview_size: int

    # === Sound Settings ===
    sound_start_filepath: Path
    start_sound_volume: float
    sound_success_filepath: Path
    success_sound_volume: float
    sound_failure_filepath: Path
    failure_sound_volume: float

    # === Upload Settings ===
    upload_method: Literal["rclone", "local_sync", "skip"]
    rclone_remote_service: str = ""
    rclone_remote_upload_dir: Path = Path("not-used")
    rclone_executable: Path = Path("not-used")
    local_sync_target_dir: Path = Path("not-used")

    class Config:
        frozen = True

    @model_validator(mode="before")
    def normalize_config_values(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Expands .app paths, resolves relative paths, and computes derived fields before validation.
        """
        cls._expand_mac_app_path(values)
        cls._resolve_auto_rclone_path(values)
        cls._resolve_paths_relative_to_root(values)
        cls._resolve_rclone_remote_aliases(values)
        return values

    @staticmethod
    def _expand_mac_app_path(values: dict[str, Any]) -> None:
        """
        Expands macOS .app bundles to the actual Factorio executable path if needed.
        Example: /Applications/factorio.app → /Applications/factorio.app/Contents/MacOS/factorio
        """
        path = values.get("fixed_path_factorio_executable")
        if (
            path
            and detect_os() == "mac"
            and isinstance(path, (str, Path))
            and str(path).endswith(".app")
            and "factorio" in str(path).lower()
        ):
            values["fixed_path_factorio_executable"] = (
                Path(path) / "Contents" / "MacOS" / "factorio"
            )

    @staticmethod
    def _resolve_auto_rclone_path(values: dict[str, Any]) -> None:
        """
        Replaces 'auto' in rclone_executable with the appropriate bundled binary path.
        Throws if the current OS/architecture is unsupported.
        """
        if values.get("rclone_executable") == "auto":
            arch = get_supported_architecture()
            if arch == "unsupported":
                raise RuntimeError(
                    f"❌ Unsupported architecture for bundled rclone.\n"
                    f"You must manually download and install rclone and configure the full path via 'rclone_executable' in your config file.\n"
                )

            os_name = detect_os()
            binary_name = "rclone.exe" if os_name == "windows" else "rclone"
            values["rclone_executable"] = (
                Path("third_party") / "rclone" / f"{os_name}" / f"{arch}" / binary_name
            )

    @staticmethod
    def _resolve_paths_relative_to_root(values: dict[str, Any]) -> None:
        """
        Resolves relevant paths relative to the project root directory.
        """
        for name in [
            "fixed_path_factorio_executable",
            "sound_start_filepath",
            "sound_success_filepath",
            "sound_failure_filepath",
            "file_monitor_filepath",
            "rclone_executable",
            "local_sync_target_dir",
        ]:
            if values.get(name) is not None:
                values[name] = resolve_relative_to_project_root(values[name])

    @staticmethod
    def _resolve_rclone_remote_aliases(values: dict[str, Any]) -> None:
        """
        Replaces shorthand or special values like 'dropbox_auto' with the actual remote name.
        """
        if values.get("rclone_remote_service") == "dropbox_auto":
            values["rclone_remote_service"] = "FactorioPreviewToolkitDropbox"

    @model_validator(mode="after")
    def validate_rclone_remote_setup(values: Self, info: ValidationInfo) -> Self:
        """
        Verifies rclone remote setup after all fields are available.
        """
        if values.upload_method != "rclone":
            return values

        remote_service = values.rclone_remote_service.strip()
        if not remote_service:
            raise ValueError("'rclone_remote_service' must be set when using rclone upload.")

        if remote_service == "FactorioPreviewToolkitDropbox":
            if remote_service == "FactorioPreviewToolkitDropbox":
                for attempt in range(5):
                    if _is_rclone_remote_configured(
                        "FactorioPreviewToolkitDropbox", values.rclone_executable
                    ):
                        break
                    log.info(f"🕒 Waiting for Dropbox setup to complete (retry {attempt}/5)...")
                    _run_dropbox_auto_setup(values.rclone_executable)
                    time.sleep(1)
        else:
            if not _is_rclone_remote_configured(remote_service, values.rclone_executable):
                raise ValueError(
                    f"❌ The rclone remote '{remote_service}' is not configured.\n"
                    "Please run `rclone config` manually to add it, or use 'dropbox_auto'."
                )

        return values

    # === Validators ===

    @field_validator("map_preview_size")
    def must_be_positive(cls, v: int) -> int:
        """
        Ensures preview size is a positive integer.
        """
        if v <= 0:
            raise ValueError(f"'map_preview_size' must be a positive integer. You entered: {v}")
        return v

    @field_validator("start_sound_volume", "success_sound_volume", "failure_sound_volume")
    def volumes_between_0_and_1(cls, v: float, info: FieldValidationInfo) -> float:
        """
        Ensures volume is between 0.0 and 1.0.
        """
        if not (0.0 <= v <= 1.0):
            raise ValueError(
                f"The volume for '{info.field_name}' must be between 0.0 and 1.0. You entered: {v}"
            )
        return v

    @field_validator(
        "sound_start_filepath",
        "sound_success_filepath",
        "sound_failure_filepath",
    )
    def path_must_exist(cls, v: Path, info: FieldValidationInfo) -> Path:
        """
        Ensures the given path exists on disk.
        """
        if not v.exists():
            raise ValueError(
                f"The path specified for '{info.field_name}' does not exist:\n  {v}\n"
                f"Please double-check the path in your configuration."
            )
        return v.resolve()

    @field_validator("rclone_executable")
    def rclone_executable_must_exist_if_needed(cls, v: Path, info: FieldValidationInfo) -> Path:
        """
        Ensures rclone executable exists if rclone upload method is selected.
        """
        if info.data.get("upload_method") == "rclone":
            if not v.exists():
                raise ValueError(
                    f"The rclone executable was not found at the expected location:\n  {v}\n"
                    f"Make sure 'rclone_executable' is correct and points to the binary."
                )
        return v.resolve()

    @field_validator("rclone_remote_upload_dir")
    def rclone_remote_upload_dir_must_be_valid_path(
        cls, v: Path, info: FieldValidationInfo
    ) -> Path:
        """
        Ensures remote upload dir is a syntactically valid path when using rclone.
        Does NOT check if the path exists (since it's a remote target).
        """
        if info.data.get("upload_method") == "rclone":
            try:
                _ = str(v)  # forces path parsing
            except Exception:
                raise ValueError(f"'rclone_remote_upload_dir' is not a valid path string: {v}")
        return v

    @field_validator("rclone_remote_service")
    def check_rclone_remote_service_if_needed(cls, v: str, info: FieldValidationInfo) -> str:
        """
        Ensures the rclone remote service name is set if rclone is used.
        """
        if info.data.get("upload_method") == "rclone" and not v.strip():
            raise ValueError("'rclone_remote_service' must be set when using rclone upload.")
        return v

    @field_validator("file_monitor_filepath")
    def check_file_monitor_filepath_if_used(cls, v: Path, info: FieldValidationInfo) -> Path:
        """
        Validates file path only when using file monitor as input method.
        """
        if info.data.get("map_exchange_input_method") == "file_monitor":
            if not v.exists():
                raise ValueError(
                    f"The path specified for 'file_monitor_filepath' does not exist:\n  {v}\n"
                    f"Check your 'file_monitor_filepath' setting."
                )
        return v

    @field_validator("map_exchange_input_poll_interval_in_seconds")
    def check_map_exchange_input_poll_interval(cls, v: float, info: FieldValidationInfo) -> float:
        """
        Ensures polling interval is valid only when clipboard monitor is used.
        """
        if info.data.get("map_exchange_input_method") == "clipboard_monitor" and v <= 0:
            raise ValueError(
                f"'map_exchange_input_poll_interval_in_seconds' must be greater than 0 "
                f"when using 'clipboard_monitor'. You entered: {v}"
            )
        return v

    @field_validator("factorio_locator_poll_interval_in_seconds")
    def check_factorio_locator_poll_interval(cls, v: float, info: FieldValidationInfo) -> float:
        """
        Ensures polling interval is valid only when using the active window monitor.
        """
        if info.data.get("factorio_locator_method") == "active_window_monitor" and v <= 0:
            raise ValueError(
                f"'factorio_locator_poll_interval_in_seconds' must be greater than 0 "
                f"when using 'active_window_monitor'. You entered: {v}"
            )
        return v

    @field_validator("fixed_path_factorio_executable")
    def check_factorio_executable_exists(cls, v: Path, info: FieldValidationInfo) -> Path:
        """
        Checks that the Factorio executable path is valid if fixed path mode is used.
        """
        if info.data.get("factorio_locator_method") == "fixed_path" and not v.exists():
            raise ValueError(
                f"The Factorio executable specified does not exist:\n  {v}\n"
                f"Check your 'fixed_path_factorio_executable' setting."
            )
        return v

    @field_validator("local_sync_target_dir")
    def check_local_sync_target_dir(cls, v: Path, info: FieldValidationInfo) -> Path:
        """
        Ensures local sync directory is valid if 'local_sync' is selected.
        """
        if info.data.get("upload_method") == "local_sync":
            if not v.exists():
                raise ValueError(
                    f"The local sync target directory does not exist:\n  {v}\n"
                    f"Please create it or adjust your 'local_sync_target_dir' setting."
                )
        return v.resolve()
