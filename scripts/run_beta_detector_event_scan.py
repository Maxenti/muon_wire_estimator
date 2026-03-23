#!/usr/bin/env python3
from __future__ import annotations

"""
CLI entrypoint for stochastic beta-source detector-chain event scans.

This script reads a JSON configuration containing:
- gas_name
- geometry
- source
- source_geometry
- optional simulation block
- optional threshold_v

and runs the full stochastic beta detector-chain event scan:
- beta-source stochastic event generation
- drift / attachment
- collected primary electrons
- gain surrogate
- avalanche pulse estimate
- visibility summaries such as fraction_above_threshold

It writes the raw detector-event-scan style JSON returned by
muon_wire_estimator.beta_detector_chain.run_beta_detector_event_scan(...).

Expected config structure
-------------------------
{
  "gas_name": "air_dry_1atm",
  "geometry": {
    "sense_wire_radius_m": 1.25e-05,
    "effective_outer_radius_m": 0.005,
    "bias_voltage_v": 1500.0,
    "track_closest_approach_m": 0.001,
    "active_length_m": 0.3,
    "track_length_in_active_m": 0.05,
    "scope_termination_ohm": 50.0,
    "electronics_rise_time_s": 5.0e-09,
    "electronics_fall_time_s": 2.0e-08,
    "mean_avalanche_pulse_width_s": 1.0e-08,
    "effective_capacitance_f": 0.0
  },
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
  "threshold_v": 1.0e-3,
  "simulation": {
    "n_events": 2000,
    "random_seed": 12345,
    "return_event_list": false
  },
  "use_attachment": true,
  "use_gain_surrogate": true,
  "include_direct_image_pulse": true,
  "include_avalanche_signal": true,
  "direct_charge_efficiency": 1.0,
  "avalanche_pulse_width_s": 1.2e-08,
  "metadata": {
    "label": "example"
  }
}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from muon_wire_estimator.beta_detector_chain import (
    beta_detector_chain_config_from_mapping,
    run_beta_detector_event_scan,
)
from muon_wire_estimator.gases import list_builtin_gases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a stochastic beta-source detector-chain event scan from JSON."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the beta detector-event-scan JSON configuration file.",
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
            f"Top-level JSON in {path} must be an object/dictionary, "
            f"got {type(data).__name__}."
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
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(json_text, encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Failed to write output JSON to {output_path}: {exc}") from exc


def _read_simulation_block(data: dict[str, Any]) -> tuple[int, int, float, bool]:
    simulation = data.get("simulation", {})
    if simulation is None:
        simulation = {}
    if not isinstance(simulation, dict):
        raise ValueError(
            f"'simulation' must be a dictionary when provided, got {type(simulation).__name__}."
        )

    n_events = int(simulation.get("n_events", 2000))
    random_seed = int(simulation.get("random_seed", 12345))
    return_event_list = bool(simulation.get("return_event_list", False))
    threshold_v = float(data.get("threshold_v", 1.0e-3))

    if n_events <= 0:
        raise ValueError(f"simulation.n_events must be > 0, got {n_events!r}.")
    if threshold_v < 0.0:
        raise ValueError(f"threshold_v must be >= 0, got {threshold_v!r}.")

    return n_events, random_seed, threshold_v, return_event_list


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_gases:
        for gas_name in list_builtin_gases():
            print(gas_name)
        return 0

    cfg_data = load_json_file(args.config)
    config = beta_detector_chain_config_from_mapping(cfg_data)
    n_events, random_seed, threshold_v, return_event_list = _read_simulation_block(
        cfg_data
    )

    result = run_beta_detector_event_scan(
        config,
        n_events=n_events,
        random_seed=random_seed,
        threshold_v=threshold_v,
        return_event_list=return_event_list,
    )

    write_json_output(
        result,
        output_path=args.output,
        pretty=args.pretty,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())