"""
Main entry point for generating Factorio map previews from a map exchange string.

Converts the exchange string to map-gen-settings,
and runs preview generation for all configured planets.
"""

import argparse
import sys
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, field_validator

from src.FactorioPreviewToolkit.preview_generator.preview_generation import (
    run_full_preview_generation,
)
from src.FactorioPreviewToolkit.preview_generator.preview_generation_setup import (
    run_preview_setup_pipeline,
)
from src.FactorioPreviewToolkit.shared.error_popup import show_error_popup
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section
from src.FactorioPreviewToolkit.shared.utils import is_valid_map_string


class Args(BaseModel):
    """
    Validates CLI arguments using Pydantic.
    """

    factorio_path: Path
    map_string: str

    @field_validator("factorio_path")
    def check_factorio_path(cls, v: Path) -> Path:
        """
        Validates that the Factorio path exists and points to a file.
        """
        v = v.resolve()
        if not v.exists() or not v.is_file():
            raise ValueError(f"Factorio path is invalid or does not exist: {v}")
        return v

    @field_validator("map_string")
    def check_map_string(cls, v: str) -> str:
        """
        Validates that the input is a valid map exchange string.
        """
        if not is_valid_map_string(v):
            raise ValueError(f"Invalid map exchange string: {v}")
        return v


def parse_arguments(argv: Sequence[str] | None = None) -> Args:
    """
    Parses and validates command-line arguments.
    """
    raw_args = argv if argv is not None else sys.argv[1:]

    if "--preview-generator-mode" in raw_args:
        preview_index = raw_args.index("--preview-generator-mode")
        raw_args = raw_args[preview_index + 1 :]

    parser = argparse.ArgumentParser(description="Factorio map preview generator")
    parser.add_argument("factorio_path", type=Path)
    parser.add_argument("map_string", type=str)

    args = parser.parse_args(raw_args)
    return Args(**vars(args))


def main(argv: Sequence[str] | None = None) -> None:
    """
    Runs the full preview generation pipeline from CLI arguments.
    """
    try:
        with log_section("🚀 Preview Generator started. Processing map string..."):
            arguments = parse_arguments(argv)
            run_preview_setup_pipeline(arguments.factorio_path, arguments.map_string)
            run_full_preview_generation(arguments.factorio_path)
            log.info("✅ Preview Generator completed successfully.")
    except Exception as e:
        log.exception("❌ Preview Generator failed with an exception.")
        show_error_popup("Factorio Toolkit Error", str(e))
        raise
    finally:
        log.info("👋 Preview Generator exited.")


if __name__ == "__main__":
    main()
