#!/usr/bin/env python3
from __future__ import annotations

"""
CLI entrypoint for deterministic beta-source ionization estimation.

This script estimates source-side ionization for a reasonably defined beta
source, especially Sr-90 / Y-90 source electrons, before downstream detector
collection / gain / pulse modeling.

It reads a JSON configuration file, builds the beta-source and source-geometry
models, resolves the gas, runs a deterministic source-side ionization estimate,
and writes JSON either to stdout or to an output file.

Expected config structure
-------------------------
{
  "gas_name": "air_dry_1atm",
  "source": {
    "spectrum_model": "sr90_y90_combined",
    "include_sr90_branch": true,
    "include_y90_branch": true,
    "track_length_model": "range_limited"
  },
  "source_geometry": {
    "source_distance_mm": 5.0,
    "placement_model": "point_isotropic",
    "active_region_thickness_mm": 5.0,
    "fixed_track_length_cm": 0.5,
    "track_length_model": "range_limited"
  },
  "metadata": {
    "label": "example"
  }
}

Notes
-----
This script estimates source-side quantities such as:
- representative beta kinetic energy
- deposited energy in gas
- created primary electrons

It does not by itself compute drift / gain / pulse response unless later
downstream integration is added elsewhere in the repository.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from muon_wire_estimator.beta_ionization import (
    estimate_beta_ionization,
    source_ionization_estimate_to_dict,
)
from muon_wire_estimator.gases import get_gas, list_builtin_gases
from muon_wire_estimator.source_geometry import (
    source_geometry_from_mapping,
    summarize_source_geometry,
)
from muon_wire_estimator.source_models import (
    sr90_beta_source_config_from_mapping,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a deterministic beta-source ionization estimate from JSON."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the beta estimator JSON configuration file.",
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
        "--list-gases",
        action="store_true",
        help="List built-in gas names and exit.",
    )
    return parser


def load_json_file(path: Path) -> dict[str, Any]:
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
        raise ValueError(f"Failed to parse JSON configuration file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Top-level JSON in {path} must be an object/dictionary, got {type(data).__name__}."
        )
    return data


def write_json_output(
    data: dict[str, Any],
    *,
    output_path: Path | None,
    pretty: bool,
) -> None:
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


def _require_mapping(data: dict[str, Any], field_name: str) -> dict[str, Any]:
    if field_name not in data:
        raise KeyError(f"Missing required top-level field {field_name!r}.")
    value = data[field_name]
    if not isinstance(value, dict):
        raise TypeError(
            f"Field {field_name!r} must be a dictionary, got {type(value).__name__}."
        )
    return value


def _normalize_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(
            f"metadata must be a dictionary when provided, got {type(value).__name__}."
        )
    return {str(key): item for key, item in value.items()}


def run_from_mapping(data: dict[str, Any]) -> dict[str, Any]:
    source_map = _require_mapping(data, "source")
    source_geometry_map = _require_mapping(data, "source_geometry")

    gas_name = str(data.get("gas_name", "air_dry_1atm"))
    gas = get_gas(gas_name)

    source_config = sr90_beta_source_config_from_mapping(source_map)
    source_geometry = source_geometry_from_mapping(source_geometry_map)
    estimate = estimate_beta_ionization(
        source_config=source_config,
        gas=gas,
        source_geometry=source_geometry,
    )

    output = source_ionization_estimate_to_dict(estimate)
    output["gas"] = gas.to_dict()
    output["source"] = source_config.to_dict()
    output["source_geometry"] = source_geometry.to_dict()
    output["source_geometry_summary"] = summarize_source_geometry(source_geometry).to_dict()
    output["input_metadata"] = _normalize_metadata(data.get("metadata"))
    output["config_snapshot"] = {
        "gas_name": gas.name,
        "source": source_config.to_dict(),
        "source_geometry": source_geometry.to_dict(),
    }
    return output


def print_builtin_gases() -> None:
    for name in list_builtin_gases():
        print(name)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_gases:
        print_builtin_gases()
        return 0

    try:
        config_data = load_json_file(args.config)
        result = run_from_mapping(config_data)
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