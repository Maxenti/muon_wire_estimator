#!/usr/bin/env python3
from __future__ import annotations

"""
CLI entrypoint for stochastic beta-source event simulation.

This script repeatedly samples beta-source events for a reasonably defined
Sr-90 / Y-90 source configuration and summarizes source-side ionization
quantities such as:

- sampled beta kinetic energy
- deposited energy in gas
- created primary electrons
- fraction entering the active region

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
  "simulation": {
    "n_events": 1000,
    "random_seed": 12345,
    "return_event_list": false
  },
  "metadata": {
    "label": "example"
  }
}
"""

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

from muon_wire_estimator.beta_ionization import (
    simulate_beta_source_event,
    source_event_summary_to_dict,
)
from muon_wire_estimator.gases import get_gas, list_builtin_gases
from muon_wire_estimator.randomness import make_rng
from muon_wire_estimator.source_geometry import (
    source_geometry_from_mapping,
    summarize_source_geometry,
)
from muon_wire_estimator.source_models import (
    sr90_beta_source_config_from_mapping,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a stochastic beta-source event simulation from JSON."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the beta event-scan JSON configuration file.",
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


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _min(values: list[float]) -> float:
    return min(values) if values else 0.0


def _max(values: list[float]) -> float:
    return max(values) if values else 0.0


def run_from_mapping(data: dict[str, Any]) -> dict[str, Any]:
    source_map = _require_mapping(data, "source")
    source_geometry_map = _require_mapping(data, "source_geometry")
    simulation_map = _require_mapping(data, "simulation")

    gas_name = str(data.get("gas_name", "air_dry_1atm"))
    gas = get_gas(gas_name)

    source_config = sr90_beta_source_config_from_mapping(source_map)
    source_geometry = source_geometry_from_mapping(source_geometry_map)

    n_events = int(simulation_map.get("n_events", 1000))
    if n_events <= 0:
        raise ValueError(f"simulation.n_events must be > 0, got {n_events!r}.")

    random_seed = int(simulation_map.get("random_seed", 12345))
    return_event_list = bool(simulation_map.get("return_event_list", False))

    rng = make_rng(random_seed)

    event_objects = [
        simulate_beta_source_event(
            event_index=i,
            source_config=source_config,
            gas=gas,
            source_geometry=source_geometry,
            rng=rng,
        )
        for i in range(n_events)
    ]

    sampled_energies = [event.sampled_particle_energy_mev for event in event_objects]
    deposited_energies = [event.deposited_energy_mev for event in event_objects]
    created_primary = [event.created_primary_electrons for event in event_objects]
    entered_flags = [1.0 if event.entered_active_region else 0.0 for event in event_objects]

    output: dict[str, Any] = {
        "n_events": n_events,
        "random_seed": random_seed,
        "gas_name": gas.name,
        "source_type": "sr90_beta",
        "mean_sampled_particle_energy_mev": _mean(sampled_energies),
        "median_sampled_particle_energy_mev": _median(sampled_energies),
        "min_sampled_particle_energy_mev": _min(sampled_energies),
        "max_sampled_particle_energy_mev": _max(sampled_energies),
        "mean_deposited_energy_mev": _mean(deposited_energies),
        "median_deposited_energy_mev": _median(deposited_energies),
        "min_deposited_energy_mev": _min(deposited_energies),
        "max_deposited_energy_mev": _max(deposited_energies),
        "mean_created_primary_electrons": _mean(created_primary),
        "median_created_primary_electrons": _median(created_primary),
        "min_created_primary_electrons": _min(created_primary),
        "max_created_primary_electrons": _max(created_primary),
        "fraction_entering_active_region": _mean(entered_flags),
        "gas": gas.to_dict(),
        "source": source_config.to_dict(),
        "source_geometry": source_geometry.to_dict(),
        "source_geometry_summary": summarize_source_geometry(source_geometry).to_dict(),
        "input_metadata": _normalize_metadata(data.get("metadata")),
        "config_snapshot": {
            "gas_name": gas.name,
            "source": source_config.to_dict(),
            "source_geometry": source_geometry.to_dict(),
            "simulation": {
                "n_events": n_events,
                "random_seed": random_seed,
                "return_event_list": return_event_list,
            },
        },
    }

    if return_event_list:
        output["event_records"] = [
            source_event_summary_to_dict(event)
            for event in event_objects
        ]
    else:
        output["event_records"] = []

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