"""
Builds a standalone executable using PyInstaller with project-specific settings.
Also handles cleanup, copies runtime files, zips the result, and prints a summary.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from platform import system

from toolkit_build.version import get_version


def get_platform_name() -> str:
    """
    Returns a normalized platform name for use in output paths.
    """
    match system():
        case "Windows":
            return "windows"
        case "Linux":
            return "linux"
        case "Darwin":
            return "macOS"
        case _:
            return "unknown"


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_MAIN = PROJECT_ROOT / "src" / "FactorioPreviewToolkit" / "__main__.py"
BUILD_ROOT = PROJECT_ROOT / "toolkit_build"
DIST_ROOT = BUILD_ROOT / "dist"
DIST_DIR = DIST_ROOT / get_platform_name()
BUILD_DIR = BUILD_ROOT / "__pyinstaller__"
EXECUTABLE_NAME = "factorio-preview-toolkit"


def clean_old_builds() -> None:
    """
    Deletes old build artifacts including dist/, __pyinstaller__/, and .spec files.
    """
    print("Cleaning previous build artifacts...")
    shutil.rmtree(DIST_ROOT, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()


def run_pyinstaller(version: str) -> None:
    """
    Builds the standalone executable using PyInstaller.
    """
    print("Building with PyInstaller...")
    subprocess.run(
        [
            "pyinstaller",
            "--onefile",
            "--name",
            EXECUTABLE_NAME,
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(BUILD_DIR),
            "--log-level",
            "WARN",
            str(SRC_MAIN),
        ],
        check=True,
    )


def copy_runtime_files() -> None:
    """
    Copies runtime assets (e.g. config.ini, assets folder) into the build output directory.
    Also creates an empty previews/ folder.
    """
    print("Copying assets and config files...")

    # Copy config.ini
    config_src = PROJECT_ROOT / "config.ini"
    config_dst = DIST_DIR / "config.ini"
    if config_src.exists():
        shutil.copy2(config_src, config_dst)

    # Copy assets/
    assets_src = PROJECT_ROOT / "assets"
    assets_dst = DIST_DIR / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    # Copy viewer/
    viewer_src = PROJECT_ROOT / "viewer"
    viewer_dst = DIST_DIR / "viewer"
    if viewer_src.exists():
        shutil.copytree(viewer_src, viewer_dst, dirs_exist_ok=True)

    # Create redirect HTML at root → /viewer/
    (DIST_DIR / "factorio-preview-viewer.html").write_text(
        '<!DOCTYPE html><html><head><meta http-equiv="Refresh" content="0; url=viewer/index.html" />'
        "<title>Redirecting to Factorio Map Viewer</title></head><body>"
        '<p>Redirecting... If not redirected, <a href="viewer/index.html">click here</a>.</p>'
        "</body></html>",
        encoding="utf-8",
    )

    # Create previews/ and add default local_planet_names.js
    previews_dir = DIST_DIR / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)

    js_file = previews_dir / "local_planet_names.js"
    js_file.write_text(
        "const planetNames = [\n"
        '  "nauvis",\n'
        '  "vulcanus",\n'
        '  "gleba",\n'
        '  "fulgora",\n'
        '  "aquilo"\n'
        "];\n"
        'const planetNamesUploadTime = "";\n',
        encoding="utf-8",
    )

    # Ensure it's writable by the user (rw-r--r--)
    os.chmod(js_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


def copy_rclone_binary_for_current_platform() -> None:
    """
    Copies the rclone binary for the current OS and architecture into the build output directory.
    """
    platform_dir = get_platform_name()
    source_root = PROJECT_ROOT / "third_party" / "rclone" / platform_dir
    dest_root = DIST_DIR / "third_party" / "rclone" / platform_dir

    if not source_root.exists():
        print(f"Rclone binary folder not found for current platform: {source_root}")
        return

    print(f"Copying rclone binary from {source_root} -> {dest_root}")
    shutil.copytree(source_root, dest_root, dirs_exist_ok=True)

    # Mark all rclone binaries inside as executable
    for path in dest_root.rglob("*"):
        if path.is_file() and path.name.startswith("rclone"):
            print(f"Marking {path} as executable")
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def print_result(version: str) -> None:
    """
    Prints the path of the final built executable for user visibility.
    """
    exe = DIST_DIR / f"{EXECUTABLE_NAME}-v{version}"
    if sys.platform == "win32":
        exe = exe.with_suffix(".exe")
    print(f"Build complete: {exe}")
    print("You can now distribute this executable.")


def zip_build_output(version: str) -> None:
    """
    Zips the entire build output folder into a versioned archive.
    Example: toolkit_build/dist/factorio-preview-toolkit-windows-v0.1.32.zip
    """
    platform_name = get_platform_name()
    zip_name = f"factorio-preview-toolkit-{platform_name}-v{version}"
    zip_target = DIST_ROOT / zip_name
    print(f"Creating ZIP archive: {zip_target}.zip")
    shutil.make_archive(str(zip_target), "zip", root_dir=DIST_DIR)


def main() -> None:
    """
    Runs the complete build process: cleans, builds, copies runtime files and rclone, zips, and prints result.
    """
    clean_old_builds()
    version = get_version()
    run_pyinstaller(version)
    copy_runtime_files()
    copy_rclone_binary_for_current_platform()
    print_result(version)
    zip_build_output(version)


if __name__ == "__main__":
    main()
