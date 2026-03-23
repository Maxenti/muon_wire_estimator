#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_command(cmd: list[str]) -> None:
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def build_geometry_for_current_repo(
    *,
    wire_name: str,
    diameter_um: float,
    coating_thickness_um: float,
    voltage_v: float,
    closest_approach_mm: float,
    outer_radius_mm: float,
    active_length_m: float,
    track_length_in_active_m: float,
    notes: str = "",
) -> dict[str, Any]:
    effective_diameter_um = diameter_um + 2.0 * coating_thickness_um
    sense_wire_radius_m = 0.5 * effective_diameter_um * 1.0e-6

    return {
        "sense_wire_radius_m": sense_wire_radius_m,
        "effective_outer_radius_m": outer_radius_mm * 1.0e-3,
        "bias_voltage_v": voltage_v,
        "track_closest_approach_m": closest_approach_mm * 1.0e-3,
        "active_length_m": active_length_m,
        "track_length_in_active_m": track_length_in_active_m,
        "scope_termination_ohm": 50.0,
        "electronics_rise_time_s": 5.0e-9,
        "electronics_fall_time_s": 20.0e-9,
        "mean_avalanche_pulse_width_s": 1.0e-8,
        "effective_capacitance_f": 0.0,
        "notes": notes or wire_name,
        # human-readable extras kept for provenance
        "wire_name": wire_name,
        "wire_core_diameter_um": diameter_um,
        "coating_thickness_um": coating_thickness_um,
        "muon_closest_approach_mm": closest_approach_mm,
        "wire_voltage_V": voltage_v,
    }


def extract_summary_row(
    *,
    gas_name: str,
    wire_name: str,
    diameter_um: float,
    coating_thickness_um: float,
    voltage_v: float,
    closest_approach_mm: float,
    threshold_v: float,
    deterministic: dict[str, Any],
    stochastic: dict[str, Any],
) -> dict[str, Any]:
    avalanche_pulse = deterministic.get("avalanche_pulse", {})
    direct_pulse = deterministic.get("direct_pulse", {})

    return {
        "gas_name": gas_name,
        "wire_name": wire_name,
        "wire_core_diameter_um": diameter_um,
        "coating_thickness_um": coating_thickness_um,
        "effective_diameter_um": diameter_um + 2.0 * coating_thickness_um,
        "wire_voltage_V": voltage_v,
        "muon_closest_approach_mm": closest_approach_mm,
        "threshold_v": threshold_v,
        "threshold_mV": threshold_v * 1.0e3,
        # deterministic
        "det_created_primary_electrons_mean": deterministic.get("created_primary_electrons_mean"),
        "det_collected_primary_electrons_mean": deterministic.get("collected_primary_electrons_mean"),
        "det_attachment_survival_fraction": deterministic.get("attachment_survival_fraction"),
        "det_collection_fraction_total": deterministic.get("collection_fraction_total"),
        "det_gas_gain_mean": deterministic.get("gas_gain_mean"),
        "det_avalanche_charge_c": deterministic.get("avalanche_charge_c"),
        "det_avalanche_charge_fC": (
            None if deterministic.get("avalanche_charge_c") is None
            else deterministic["avalanche_charge_c"] * 1.0e15
        ),
        "det_drift_time_s": deterministic.get("drift_time_s"),
        "det_drift_time_ns": (
            None if deterministic.get("drift_time_s") is None
            else deterministic["drift_time_s"] * 1.0e9
        ),
        "det_peak_voltage_v": avalanche_pulse.get("peak_voltage_v"),
        "det_peak_voltage_mV": (
            None if avalanche_pulse.get("peak_voltage_v") is None
            else avalanche_pulse["peak_voltage_v"] * 1.0e3
        ),
        "det_peak_current_a": avalanche_pulse.get("peak_current_a"),
        "det_peak_current_nA": (
            None if avalanche_pulse.get("peak_current_a") is None
            else avalanche_pulse["peak_current_a"] * 1.0e9
        ),
        "direct_peak_voltage_v": direct_pulse.get("peak_voltage_v"),
        "direct_peak_voltage_mV": (
            None if direct_pulse.get("peak_voltage_v") is None
            else direct_pulse["peak_voltage_v"] * 1.0e3
        ),
        # stochastic
        "sto_n_events": stochastic.get("n_events"),
        "sto_mean_primary_electrons_created": stochastic.get("mean_primary_electrons_created"),
        "sto_mean_primary_electrons_collected": stochastic.get("mean_primary_electrons_collected"),
        "sto_mean_gas_gain": stochastic.get("mean_gas_gain"),
        "sto_min_peak_voltage_v": stochastic.get("min_peak_voltage_v"),
        "sto_mean_peak_voltage_v": stochastic.get("mean_peak_voltage_v"),
        "sto_median_peak_voltage_v": stochastic.get("median_peak_voltage_v"),
        "sto_max_peak_voltage_v": stochastic.get("max_peak_voltage_v"),
        "sto_min_peak_voltage_mV": (
            None if stochastic.get("min_peak_voltage_v") is None
            else stochastic["min_peak_voltage_v"] * 1.0e3
        ),
        "sto_mean_peak_voltage_mV": (
            None if stochastic.get("mean_peak_voltage_v") is None
            else stochastic["mean_peak_voltage_v"] * 1.0e3
        ),
        "sto_median_peak_voltage_mV": (
            None if stochastic.get("median_peak_voltage_v") is None
            else stochastic["median_peak_voltage_v"] * 1.0e3
        ),
        "sto_max_peak_voltage_mV": (
            None if stochastic.get("max_peak_voltage_v") is None
            else stochastic["max_peak_voltage_v"] * 1.0e3
        ),
        "sto_fraction_above_threshold": stochastic.get("fraction_above_threshold"),
    }


def choose_visibility_voltage(
    rows: list[dict[str, Any]],
    *,
    fraction_required: float,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, float, float], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            row["gas_name"],
            row["wire_name"],
            row["wire_core_diameter_um"],
            row["coating_thickness_um"],
        )
        grouped.setdefault(key, []).append(row)

    output: list[dict[str, Any]] = []
    for key, entries in grouped.items():
        entries.sort(key=lambda r: float(r["wire_voltage_V"]))
        visible = next(
            (
                r for r in entries
                if r.get("sto_fraction_above_threshold") is not None
                and float(r["sto_fraction_above_threshold"]) >= fraction_required
            ),
            None,
        )

        gas_name, wire_name, diameter_um, coating_thickness_um = key
        output.append({
            "gas_name": gas_name,
            "wire_name": wire_name,
            "wire_core_diameter_um": diameter_um,
            "coating_thickness_um": coating_thickness_um,
            "effective_diameter_um": diameter_um + 2.0 * coating_thickness_um,
            "fraction_required": fraction_required,
            "minimum_visible_voltage_V": None if visible is None else visible["wire_voltage_V"],
            "visible_at_scan_max": visible is not None,
            "threshold_v": None if visible is None else visible["threshold_v"],
            "sto_fraction_above_threshold_at_first_visible": None if visible is None else visible["sto_fraction_above_threshold"],
            "sto_median_peak_voltage_mV_at_first_visible": None if visible is None else visible["sto_median_peak_voltage_mV"],
            "sto_max_peak_voltage_mV_at_first_visible": None if visible is None else visible["sto_max_peak_voltage_mV"],
            "det_peak_voltage_mV_at_first_visible": None if visible is None else visible["det_peak_voltage_mV"],
        })
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sweep gas, voltage, and wire configs and summarize oscilloscope visibility."
    )
    parser.add_argument("--scan-config", type=Path, required=True, help="Path to scan input JSON.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for outputs.")
    parser.add_argument(
        "--fraction-required",
        type=float,
        default=0.5,
        help="Minimum stochastic fraction_above_threshold to call a config 'visible'. Default: 0.5",
    )
    args = parser.parse_args()

    scan_cfg = load_json(args.scan_config)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    voltages = scan_cfg["voltages_V"]
    gases = scan_cfg["gases"]
    wires = scan_cfg["wire_configs"]
    closest_approach_mm = float(scan_cfg.get("muon_closest_approach_mm", 1.0))
    outer_radius_mm = float(scan_cfg.get("effective_outer_radius_mm", 5.0))
    active_length_m = float(scan_cfg.get("active_length_m", 0.30))
    track_length_in_active_m = float(scan_cfg.get("track_length_in_active_m", 0.05))
    threshold_v = float(scan_cfg.get("threshold_v", 1.0e-3))
    n_events = int(scan_cfg.get("n_events", 2000))
    random_seed = int(scan_cfg.get("random_seed", 12345))

    rows: list[dict[str, Any]] = []
    detailed_results: list[dict[str, Any]] = []

    for gas_name in gases:
        for wire in wires:
            wire_name = str(wire["wire_name"])
            diameter_um = float(wire["wire_core_diameter_um"])
            coating_thickness_um = float(wire.get("coating_thickness_um", 0.0))

            for voltage_v in voltages:
                geometry = build_geometry_for_current_repo(
                    wire_name=wire_name,
                    diameter_um=diameter_um,
                    coating_thickness_um=coating_thickness_um,
                    voltage_v=float(voltage_v),
                    closest_approach_mm=closest_approach_mm,
                    outer_radius_mm=outer_radius_mm,
                    active_length_m=active_length_m,
                    track_length_in_active_m=track_length_in_active_m,
                    notes=f"{wire_name}, {gas_name}, V={voltage_v}",
                )

                det_cfg = {
                    "geometry": geometry,
                    "gas_name": gas_name,
                    "use_attachment": True,
                    "use_gain_surrogate": True,
                    "avalanche_pulse_width_s": 1.2e-8,
                    "metadata": {
                        "scan_kind": "visibility_scan",
                    },
                }

                sto_cfg = {
                    "geometry": geometry,
                    "gas_name": gas_name,
                    "use_attachment": True,
                    "use_gain_surrogate": True,
                    "avalanche_pulse_width_s": 1.2e-8,
                    "simulation": {
                        "n_events": n_events,
                        "random_seed": random_seed,
                        "threshold_v": threshold_v,
                        "return_event_list": False,
                        "include_zero_signal_events": True,
                        "gain_fluctuation_shape": 1.5,
                        "primary_statistics_model": "poisson",
                        "survival_statistics_model": "binomial",
                    },
                    "metadata": {
                        "scan_kind": "visibility_scan",
                    },
                }

                with tempfile.TemporaryDirectory() as tmpdir:
                    tmpdir_path = Path(tmpdir)
                    det_cfg_path = tmpdir_path / "det.json"
                    sto_cfg_path = tmpdir_path / "sto.json"
                    det_out_path = tmpdir_path / "det_out.json"
                    sto_out_path = tmpdir_path / "sto_out.json"

                    write_json(det_cfg_path, det_cfg)
                    write_json(sto_cfg_path, sto_cfg)

                    run_command([
                        sys.executable,
                        "scripts/run_estimator.py",
                        "--config", str(det_cfg_path),
                        "--output", str(det_out_path),
                        "--pretty",
                    ])
                    run_command([
                        sys.executable,
                        "scripts/run_event_scan.py",
                        "--config", str(sto_cfg_path),
                        "--output", str(sto_out_path),
                        "--pretty",
                    ])

                    deterministic = load_json(det_out_path)
                    stochastic = load_json(sto_out_path)

                row = extract_summary_row(
                    gas_name=gas_name,
                    wire_name=wire_name,
                    diameter_um=diameter_um,
                    coating_thickness_um=coating_thickness_um,
                    voltage_v=float(voltage_v),
                    closest_approach_mm=closest_approach_mm,
                    threshold_v=threshold_v,
                    deterministic=deterministic,
                    stochastic=stochastic,
                )
                rows.append(row)

                detailed_results.append({
                    "scan_point": {
                        "gas_name": gas_name,
                        "wire_name": wire_name,
                        "wire_core_diameter_um": diameter_um,
                        "coating_thickness_um": coating_thickness_um,
                        "wire_voltage_V": float(voltage_v),
                        "muon_closest_approach_mm": closest_approach_mm,
                    },
                    "deterministic": deterministic,
                    "stochastic": stochastic,
                })

    visibility_rows = choose_visibility_voltage(
        rows,
        fraction_required=float(args.fraction_required),
    )

    write_json(output_dir / "visibility_scan_full.json", {
        "scan_config": scan_cfg,
        "rows": rows,
        "visibility_summary": visibility_rows,
        "detailed_results": detailed_results,
    })
    write_csv(output_dir / "visibility_scan_summary.csv", rows)
    write_csv(output_dir / "minimum_visible_voltage.csv", visibility_rows)

    print(f"Wrote {output_dir / 'visibility_scan_full.json'}")
    print(f"Wrote {output_dir / 'visibility_scan_summary.csv'}")
    print(f"Wrote {output_dir / 'minimum_visible_voltage.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())