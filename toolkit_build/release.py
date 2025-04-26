"""
- Use via 'python -m toolkit_build.release'

Triggers a full release:
- Bumps patch version in pyproject.toml
- Commits the version change
- Tags the commit
- Pushes to origin (including tag)

This automatically triggers the GitHub Actions build + upload.
"""

import re
import subprocess
from pathlib import Path

from toolkit_build.version import bump_patch_version


def get_new_version(pyproject: Path) -> str:
    """
    Extracts the version string from pyproject.toml.
    """
    content = pyproject.read_text(encoding="utf-8")
    version_line = re.search(r'version\s*=\s*"([\d.]+)"', content)
    if not version_line:
        raise ValueError("Could not find version in pyproject.toml")
    return version_line.group(1)


def enforce_https_remote(repo_url: str) -> None:
    """
    Forces the 'origin' remote to use HTTPS instead of SSH.
    """
    subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=True)


def main() -> None:
    """
    Bumps the version, commits and tags the release, and pushes to GitHub.
    """
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        raise FileNotFoundError("pyproject.toml not found")

    # Step 1: Ensure we're using HTTPS remote
    enforce_https_remote("https://github.com/AntiElitz/FactorioPreviewToolkit.git")  # ← CHANGE THIS

    # Step 2: Bump patch version
    version = bump_patch_version()
    print(f"Bumped to version v{version}")

    # Step 3: Git commit + tag
    tag = f"v{version}"
    subprocess.run(["git", "add", "pyproject.toml"], check=True)
    subprocess.run(["git", "commit", "-m", f"🔖 Release {tag}"], check=True)
    subprocess.run(["git", "tag", tag], check=True)
    subprocess.run(["git", "push"], check=True)
    subprocess.run(["git", "push", "origin", tag], check=True)

    print(f"\nRelease {tag} pushed. GitHub Actions will now build and publish.\n")


if __name__ == "__main__":
    main()
