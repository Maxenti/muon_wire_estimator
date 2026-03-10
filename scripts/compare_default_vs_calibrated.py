#!/usr/bin/env python3
"""
CLI entrypoint to compare default vs calibrated deterministic estimates.

This script reads a Level 3 JSON configuration file, optionally loads a
calibration JSON file, runs both the default/surrogate and calibrated estimate,
and writes a compact comparison report to stdout or a JSON file.

Example
-------
python scripts/compare_default_vs_calibrated.py \
    --config examples/level3_calibration.json \
    --pretty

python scripts/compare_default_vs_calibrated.py \
    --config examples/level3_calibration.json \
    --output out/comparison.json \
    --pretty
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from muon_wire_estimator.calibrated_core import (
    calibrated_config_from_mapping,
    estimate_calibrated_from_config,
)
from muon_wire_estimator.calibration_loader import (
    load_calibration_record,
    maybe_load_calibration_record,
)
from muon_wire_estimator.reporting import (
    calibration_status_report,
    comparison_report,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Compare default/surrogate vs calibrated deterministic estimates."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the Level 3 estimator JSON configuration file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON file path. Defaults to stdout.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output with indentation.",
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Emit only a minimal calibration-status report.",
    )
    parser.add_argument(
        "--show-calibration",
        action="store_true",
        help="Include the loaded calibration record in the output payload.",
    )
    return parser


def load_json_file(path: Path) -> dict[str, Any]:
    """
    Load a JSON object from disk.

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    ValueError
        If the file cannot be parsed into a top-level JSON object.
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file does not exist: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Configuration path is not a file: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Failed to read configuration file {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse JSON configuration file {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Top-level JSON in {path} must be an object/dictionary, got {type(data).__name__}."
        )

    return data


def _normalize_metadata(value: Any) -> dict[str, Any]:
    """
    Normalize optional metadata into a string-keyed dictionary.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(
            f"metadata must be a dictionary when provided, got {type(value).__name__}."
        )
    return {str(key): item for key, item in value.items()}


def run_from_mapping(
    data: dict[str, Any],
    *,
    status_only: bool,
    show_calibration: bool,
) -> dict[str, Any]:
    """
    Run default vs calibrated comparison from a parsed JSON mapping.

    Expected top-level structure
    ----------------------------
    {
      "geometry": {...},
      "gas_name": "...",
      ...
      "calibration_path": "optional/path.json",
      "metadata": {...}
    }
    """
    config = calibrated_config_from_mapping(data)
    metadata = _normalize_metadata(data.get("metadata"))

    calibration_path_raw = data.get("calibration_path")
    calibration_path: str | None
    if calibration_path_raw is None:
        calibration_path = None
    else:
        calibration_path = str(calibration_path_raw)

    calibration = maybe_load_calibration_record(calibration_path)
    result = estimate_calibrated_from_config(config, calibration=calibration)

    payload: dict[str, Any]
    if status_only:
        payload = calibration_status_report(result)
    else:
        payload = comparison_report(result)

    payload["config_snapshot"] = config.to_dict()
    payload["input_metadata"] = metadata
    payload["calibration_path"] = calibration_path

    if show_calibration and calibration_path is not None:
        loaded = load_calibration_record(calibration_path)
        payload["loaded_calibration_record"] = loaded.to_dict()
    elif show_calibration:
        payload["loaded_calibration_record"] = None

    return payload


def write_json_output(
    data: dict[str, Any],
    *,
    output_path: Path | None,
    pretty: bool,
) -> None:
    """
    Write JSON either to stdout or to a file.
    """
    json_text = json.dumps(
        data,
        indent=2 if pretty else None,
        sort_keys=True,
    )
    if pretty:
        json_text += "\n"

    if output_path is None:
        sys.stdout.write(json_text)
        if not pretty:
            sys.stdout.write("\n")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(json_text, encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Failed to write output file {output_path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    """
    Run the CLI.

    Returns
    -------
    int
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config_data = load_json_file(args.config)
        result = run_from_mapping(
            config_data,
            status_only=args.status_only,
            show_calibration=args.show_calibration,
        )
        write_json_output(
            result,
            output_path=args.output,
            pretty=args.pretty,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())