from pathlib import Path
from typing import Any, cast, TypedDict

import tomli
import tomli_w

PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


class ProjectSection(TypedDict):
    version: str


class PyProjectData(TypedDict):
    project: ProjectSection


def get_version() -> str:
    with PYPROJECT.open("rb") as f:
        raw_data: Any = tomli.load(f)
    data = cast(PyProjectData, raw_data)
    return data["project"]["version"]


def bump_patch_version() -> str:
    with PYPROJECT.open("rb") as f:
        raw_data: dict[str, Any] = tomli.load(f)
    data = cast(PyProjectData, raw_data)

    version = data["project"]["version"]
    major, minor, patch = map(int, version.split("."))
    new_version = f"{major}.{minor}.{patch + 1}"
    data["project"]["version"] = new_version

    with PYPROJECT.open("wb") as f:
        tomli_w.dump(data, f)

    print(f"🔢 Auto-bumped version: {version} → {new_version}")
    return new_version
