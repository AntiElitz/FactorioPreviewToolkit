"""
Builds a standalone executable using PyInstaller with project-specific settings.
Also handles cleanup, copies runtime files, zips the result, and prints a summary.
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
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


# What belongs to whoever runs the built toolkit, not to the build: an edited config with
# real credentials in it, the generated previews, and the logs. A rebuild must not wipe them.
USER_DATA_IN_DIST = ("config.ini", "previews", "logs", "temp_files")


def clean_old_builds() -> Path | None:
    """
    Deletes old build artifacts, but first moves the user's own files out of the way.
    Returns the folder they were parked in, for restore_user_data().
    """
    print("Cleaning previous build artifacts...")

    parked: Path | None = None
    if DIST_DIR.exists():
        parked = Path(tempfile.mkdtemp(prefix="factorio-preview-toolkit-userdata-"))
        for name in USER_DATA_IN_DIST:
            source = DIST_DIR / name
            if source.exists():
                print(f"  Keeping your {name}")
                shutil.move(str(source), str(parked / name))

    shutil.rmtree(DIST_ROOT, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
    return parked


def restore_user_data(parked: Path | None) -> None:
    """
    Puts the user's config, previews and logs back into the fresh build output.
    """
    if parked is None:
        return
    for name in USER_DATA_IN_DIST:
        source = parked / name
        if not source.exists():
            continue
        target = DIST_DIR / name
        if target.exists():
            shutil.rmtree(target) if target.is_dir() else target.unlink()
        shutil.move(str(source), str(target))
    shutil.rmtree(parked, ignore_errors=True)


def run_pyinstaller(version: str) -> None:
    """
    Builds the executable with its libraries in an '_internal' folder beside it.

    Not --onefile: that packs every DLL into the exe and unpacks them to a temp folder on
    every single launch, which measured ~4.2s versus ~0.75s here - paid three times per
    map string, because the generator and the uploader are the same executable. The
    release is a ZIP with config.ini, assets/ and viewer/ anyway, so one more folder next
    to the exe costs the user nothing. Unpacking to temp also trips up application control
    policies such as Windows Smart App Control.
    """
    print("Building with PyInstaller...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onedir",
            "--name",
            EXECUTABLE_NAME,
            "--distpath",
            str(BUILD_DIR / "onedir"),
            "--workpath",
            str(BUILD_DIR),
            "--log-level",
            "WARN",
            str(SRC_MAIN),
        ],
        check=True,
    )
    _flatten_onedir_output()


def _flatten_onedir_output() -> None:
    """
    Moves the exe and its '_internal' folder up into the bundle root.

    PyInstaller puts a --onedir build in '<distpath>/<name>/', but the bundle has the exe
    at the top next to config.ini and viewer/, so users see one obvious thing to start.
    """
    built = BUILD_DIR / "onedir" / EXECUTABLE_NAME
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    for item in built.iterdir():
        target = DIST_DIR / item.name
        if target.exists():
            shutil.rmtree(target) if target.is_dir() else target.unlink()
        shutil.move(str(item), str(target))
    shutil.rmtree(BUILD_DIR / "onedir", ignore_errors=True)


def copy_runtime_files() -> None:
    """
    Copies runtime assets (e.g. config.ini, assets folder) into the build output directory.
    Also creates an empty previews/ folder.
    """
    print("Copying assets and config files...")

    # Copy config.ini, but never over one that is already there: it may hold the user's
    # own settings and credentials.
    config_src = PROJECT_ROOT / "config.ini"
    config_dst = DIST_DIR / "config.ini"
    if config_src.exists() and not config_dst.exists():
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

    write_default_planet_list(previews_dir, overwrite=False)


def write_default_planet_list(previews_dir: Path, overwrite: bool) -> None:
    """
    Writes the placeholder planet list a fresh bundle needs, so the viewer has something
    to show before the first run. Never touches an existing list unless asked to.
    """
    js_file = previews_dir / "local_planet_names.js"
    if js_file.exists() and not overwrite:
        return

    js_file.write_text(
        "window.planetNames = [\n"
        '  "nauvis",\n'
        '  "vulcanus",\n'
        '  "gleba",\n'
        '  "fulgora",\n'
        '  "aquilo"\n'
        "];\n"
        'window.planetNamesUploadTime = "";\n',
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
    exe = DIST_DIR / EXECUTABLE_NAME
    if sys.platform == "win32":
        exe = exe.with_suffix(".exe")
    print(f"Build complete (v{version}): {exe}")
    print("You can now distribute the folder it sits in.")


def zip_build_output(version: str) -> None:
    """
    Zips a clean copy of the build output into a versioned archive.

    A copy rather than the folder itself, because the build output doubles as a working
    install: it can hold an edited config.ini with real credentials, generated previews and
    logs. None of that belongs in a release.
    """
    platform_name = get_platform_name()
    zip_name = f"factorio-preview-toolkit-{platform_name}-v{version}"
    zip_target = DIST_ROOT / zip_name
    print(f"Creating ZIP archive: {zip_target}.zip")

    with tempfile.TemporaryDirectory() as staging_root:
        staging = Path(staging_root) / "bundle"
        shutil.copytree(DIST_DIR, staging)

        shutil.rmtree(staging / "logs", ignore_errors=True)
        shutil.rmtree(staging / "temp_files", ignore_errors=True)

        previews = staging / "previews"
        if previews.exists():
            for leftover in previews.iterdir():
                leftover.unlink() if leftover.is_file() else shutil.rmtree(leftover)
        else:
            previews.mkdir(parents=True)
        write_default_planet_list(previews, overwrite=True)

        pristine_config = PROJECT_ROOT / "config.ini"
        if pristine_config.exists():
            shutil.copy2(pristine_config, staging / "config.ini")

        shutil.make_archive(str(zip_target), "zip", root_dir=str(staging))


def main() -> None:
    """
    Runs the complete build process: cleans, builds, copies runtime files and rclone, zips, and prints result.
    """
    parked_user_data = clean_old_builds()
    try:
        version = get_version()
        run_pyinstaller(version)
    finally:
        # Always put the user's files back, even when the build fails. Without this
        # a crashed build leaves them in a temp folder and the next build writes a
        # fresh config over the top - which is how an FTP password gets lost to a
        # missing PyInstaller.
        restore_user_data(parked_user_data)
    copy_runtime_files()
    copy_rclone_binary_for_current_platform()
    print_result(version)
    zip_build_output(version)


if __name__ == "__main__":
    main()
