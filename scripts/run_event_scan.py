#!/usr/bin/env python3
"""
CLI entrypoint for Level 2 stochastic event simulation.

This script reads a JSON configuration file, runs a repeated event simulation,
and writes the resulting summary either to stdout or to a JSON file.

Supported config structure
--------------------------
{
  "geometry": { ... GeometryModel fields ... },
  "gas_name": "ar_co2_70_30_1atm",
  "simulation": {
    "n_events": 1000,
    "random_seed": 12345,
    "threshold_v": 0.001,
    "return_event_list": false,
    "include_zero_signal_events": true,
    "gain_fluctuation_shape": 1.5,
    "primary_statistics_model": "poisson",
    "survival_statistics_model": "binomial"
  },
  "use_attachment": true,
  "use_gain_surrogate": true,
  "avalanche_pulse_width_s": 1.2e-08,
  "metadata": { ... }
}

Example
-------
python scripts/run_event_scan.py \
    --config examples/level2_event_scan.json \
    --pretty

python scripts/run_event_scan.py \
    --config examples/level2_event_scan.json \
    --output out/event_scan.json \
    --pretty
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from muon_wire_estimator import (
    EventSimulationConfig,
    geometry_from_mapping,
    list_builtin_gases,
)
from muon_wire_estimator.event_stats import summary_to_report_dict
from muon_wire_estimator.stochastic import (
    resolve_gas,
    simulate_and_summarize,
    simulation_summary_to_dict,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the Level 2 stochastic muon wire event simulation."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the event-scan JSON configuration file.",
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
        "--report-view",
        action="store_true",
        help=(
            "Write a compact reporting-oriented summary instead of the full "
            "EventSimulationSummary dictionary."
        ),
    )
    parser.add_argument(
        "--list-gases",
        action="store_true",
        help="List built-in gas names and exit.",
    )
    return parser


def load_json_file(path: Path) -> dict[str, Any]:
    """
    Load a top-level JSON object from disk.
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


def _require_mapping(data: dict[str, Any], field_name: str) -> dict[str, Any]:
    """
    Require that a named field exists and is a dictionary.
    """
    if field_name not in data:
        raise KeyError(f"Missing required top-level field {field_name!r}.")
    value = data[field_name]
    if not isinstance(value, dict):
        raise TypeError(
            f"Field {field_name!r} must be a dictionary, got {type(value).__name__}."
        )
    return value


def _normalize_metadata(value: Any) -> dict[str, Any]:
    """
    Normalize optional metadata into a plain string-keyed dictionary.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(
            f"metadata must be a dictionary when provided, got {type(value).__name__}."
        )
    return {str(key): item for key, item in value.items()}


def simulation_config_from_mapping(data: dict[str, Any]) -> EventSimulationConfig:
    """
    Build EventSimulationConfig from a generic mapping.
    """
    return EventSimulationConfig(
        n_events=int(data.get("n_events", 1000)),
        random_seed=int(data.get("random_seed", 12345)),
        threshold_v=float(data.get("threshold_v", 1.0e-3)),
        return_event_list=bool(data.get("return_event_list", False)),
        include_zero_signal_events=bool(data.get("include_zero_signal_events", True)),
        gain_fluctuation_shape=float(data.get("gain_fluctuation_shape", 1.0)),
        primary_statistics_model=str(data.get("primary_statistics_model", "poisson")),
        survival_statistics_model=str(data.get("survival_statistics_model", "binomial")),
    )


def run_from_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """
    Run the Level 2 simulation from a parsed JSON mapping.
    """
    geometry_map = _require_mapping(data, "geometry")
    simulation_map = _require_mapping(data, "simulation")

    geometry = geometry_from_mapping(geometry_map)
    gas = resolve_gas(str(data.get("gas_name", "air_dry_1atm")))
    sim_config = simulation_config_from_mapping(simulation_map)

    use_attachment = bool(data.get("use_attachment", True))
    use_gain_surrogate = bool(data.get("use_gain_surrogate", True))
    avalanche_pulse_width_s = (
        None
        if data.get("avalanche_pulse_width_s") is None
        else float(data["avalanche_pulse_width_s"])
    )
    metadata = _normalize_metadata(data.get("metadata"))

    summary = simulate_and_summarize(
        geometry,
        gas,
        sim_config,
        use_attachment=use_attachment,
        use_gain_surrogate=use_gain_surrogate,
        avalanche_pulse_width_s=avalanche_pulse_width_s,
    )

    output = simulation_summary_to_dict(summary)
    output["input_metadata"] = metadata
    output["config_snapshot"] = {
        "gas_name": gas.name,
        "use_attachment": use_attachment,
        "use_gain_surrogate": use_gain_surrogate,
        "avalanche_pulse_width_s": avalanche_pulse_width_s,
        "simulation": sim_config.to_dict(),
    }
    return output


def run_report_view_from_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """
    Run the Level 2 simulation and return a more compact report-style view.
    """
    geometry_map = _require_mapping(data, "geometry")
    simulation_map = _require_mapping(data, "simulation")

    geometry = geometry_from_mapping(geometry_map)
    gas = resolve_gas(str(data.get("gas_name", "air_dry_1atm")))
    sim_config = simulation_config_from_mapping(simulation_map)

    use_attachment = bool(data.get("use_attachment", True))
    use_gain_surrogate = bool(data.get("use_gain_surrogate", True))
    avalanche_pulse_width_s = (
        None
        if data.get("avalanche_pulse_width_s") is None
        else float(data["avalanche_pulse_width_s"])
    )
    metadata = _normalize_metadata(data.get("metadata"))

    summary = simulate_and_summarize(
        geometry,
        gas,
        sim_config,
        use_attachment=use_attachment,
        use_gain_surrogate=use_gain_surrogate,
        avalanche_pulse_width_s=avalanche_pulse_width_s,
    )

    report = summary_to_report_dict(summary)
    report["input_metadata"] = metadata
    report["config_snapshot"] = {
        "gas_name": gas.name,
        "use_attachment": use_attachment,
        "use_gain_surrogate": use_gain_surrogate,
        "avalanche_pulse_width_s": avalanche_pulse_width_s,
        "simulation": sim_config.to_dict(),
    }
    return report


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


def print_builtin_gases() -> None:
    """Print available built-in gas names."""
    for name in list_builtin_gases():
        print(name)


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

    if args.list_gases:
        print_builtin_gases()
        return 0

    try:
        config_data = load_json_file(args.config)
        result = (
            run_report_view_from_mapping(config_data)
            if args.report_view
            else run_from_mapping(config_data)
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