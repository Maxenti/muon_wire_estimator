#!/usr/bin/env python3
"""
single_wire_signal_scan.py

Compute simple single-wire signal estimates for:
- gases: air, 75Ar25CO2
- wire types:
    1) 7.7 um CF core + 0.3 um Ni coating on each side (8.3 um total diameter)
    2) 25 um carbon fiber
- source types:
    1) cosmic muon
    2) somewhat realistic Sr90/Y90 beta

Outputs a CSV suitable for Excel.

Model choices (kept consistent with the earlier hand calculations):
- Effective cylindrical outer cathode radius b = 5 mm
- 50 ohm termination
- 10 ns effective pulse width
- Visibility thresholds:
    barely visible: 5 mV
    reliable: 20 mV
- 75Ar25CO2:
    uses a Diethorn-style surrogate gain model
- air:
    does NOT use stable proportional avalanche gain here;
    direct primary signal only (gain = 1)
    an optional rough "air_corona_region_flag" is included using
    previously used approximate onset voltages:
        thin Ni-coated wire: ~1400 V
        25 um CF wire:       ~2200 V

This is a compact engineering model, not a Garfield++ simulation.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


# ----------------------------
# Constants / assumptions
# ----------------------------

E_CHARGE_C = 1.602e-19

OUTER_RADIUS_CM = 0.5          # 5 mm effective grounded cylinder radius
TERMINATION_OHM = 50.0
PULSE_WIDTH_NS = 10.0
PULSE_WIDTH_S = PULSE_WIDTH_NS * 1.0e-9

VISIBLE_THRESHOLD_MV = 5.0
RELIABLE_THRESHOLD_MV = 20.0

# 75Ar25CO2 gain-surrogate parameters
PRESSURE_TORR = 760.0
E_MIN_OVER_P = 50.0            # V / (cm * Torr)
DELTA_V = 35.0                 # V

# Rough air-corona onset estimates used in the earlier hand estimates
AIR_CORONA_ONSET_ESTIMATE_V = {
    "cf_7p7um_core_plus_0p3um_ni_each_side": 1400.0,
    "cf_25um": 2200.0,
}


@dataclass(frozen=True)
class WireSpec:
    key: str
    label: str
    diameter_um: float
    radius_cm: float


@dataclass(frozen=True)
class GasSpec:
    key: str
    label: str


@dataclass(frozen=True)
class SourceSpec:
    key: str
    label: str


WIRES: Dict[str, WireSpec] = {
    "cf_7p7um_core_plus_0p3um_ni_each_side": WireSpec(
        key="cf_7p7um_core_plus_0p3um_ni_each_side",
        label="7.7 um CF core + 0.3 um Ni each side (8.3 um total dia.)",
        diameter_um=8.3,
        radius_cm=4.15e-4,
    ),
    "cf_25um": WireSpec(
        key="cf_25um",
        label="25 um carbon fiber",
        diameter_um=25.0,
        radius_cm=1.25e-3,
    ),
}

GASES: Dict[str, GasSpec] = {
    "air": GasSpec(key="air", label="air"),
    "75Ar25CO2": GasSpec(key="75Ar25CO2", label="75Ar25CO2"),
}

SOURCES: Dict[str, SourceSpec] = {
    "cosmic_muon": SourceSpec(key="cosmic_muon", label="cosmic muon"),
    "sr90_beta": SourceSpec(key="sr90_beta", label="Sr90/Y90 beta"),
}


def primary_electrons(source_key: str, gas_key: str) -> float:
    """
    Primary-electron counts used in the earlier hand calculations.
    """
    if source_key == "cosmic_muon":
        if gas_key == "75Ar25CO2":
            return 130.0
        if gas_key == "air":
            return 70.0
    elif source_key == "sr90_beta":
        if gas_key == "75Ar25CO2":
            return 121.0
        if gas_key == "air":
            return 70.9
    raise ValueError(f"Unsupported source/gas combination: {source_key}, {gas_key}")


def survival_factor(source_key: str, gas_key: str) -> float:
    """
    Kept consistent with earlier calculations:
    - 75Ar25CO2: 0.95
    - air: use direct-primary estimate only -> effectively 1.0 here
    """
    if gas_key == "75Ar25CO2":
        return 0.95
    if gas_key == "air":
        return 1.0
    raise ValueError(f"Unsupported gas: {gas_key}")


def ln_b_over_a(radius_cm: float, outer_radius_cm: float = OUTER_RADIUS_CM) -> float:
    return math.log(outer_radius_cm / radius_cm)


def surface_field_v_per_cm(voltage_v: float, radius_cm: float, outer_radius_cm: float = OUTER_RADIUS_CM) -> float:
    denom = radius_cm * ln_b_over_a(radius_cm, outer_radius_cm)
    return voltage_v / denom


def v0_diethorn_like(radius_cm: float, outer_radius_cm: float = OUTER_RADIUS_CM) -> float:
    """
    V0 = p * a * ln(b/a) * (Emin/p)
    """
    return PRESSURE_TORR * radius_cm * ln_b_over_a(radius_cm, outer_radius_cm) * E_MIN_OVER_P


def gain_75ar25co2(voltage_v: float, radius_cm: float, outer_radius_cm: float = OUTER_RADIUS_CM) -> float:
    """
    Diethorn-style surrogate used in the earlier hand estimates:
        ln M = (V / ln(b/a)) * (ln2 / DeltaV) * ln(V / V0)
    with M clamped to >= 1.
    """
    log_ba = ln_b_over_a(radius_cm, outer_radius_cm)
    v0 = v0_diethorn_like(radius_cm, outer_radius_cm)

    if voltage_v <= 0.0 or voltage_v <= v0:
        return 1.0

    ln_m = (voltage_v / log_ba) * (math.log(2.0) / DELTA_V) * math.log(voltage_v / v0)
    if ln_m <= 0.0:
        return 1.0
    return math.exp(ln_m)


def gain(gas_key: str, voltage_v: float, radius_cm: float) -> float:
    """
    75Ar25CO2 -> surrogate proportional gain
    air       -> no stable avalanche gain modeled here; direct primary only
    """
    if gas_key == "75Ar25CO2":
        return gain_75ar25co2(voltage_v, radius_cm)
    if gas_key == "air":
        return 1.0
    raise ValueError(f"Unsupported gas: {gas_key}")


def collected_charge_c(
    n_primary: float,
    surv: float,
    gain_value: float,
) -> float:
    return n_primary * surv * E_CHARGE_C * gain_value


def peak_voltage_v(charge_c: float) -> float:
    return (charge_c / PULSE_WIDTH_S) * TERMINATION_OHM


def visibility_class(v_peak_mv: float) -> str:
    if v_peak_mv >= RELIABLE_THRESHOLD_MV:
        return "reliable"
    if v_peak_mv >= VISIBLE_THRESHOLD_MV:
        return "barely_visible"
    return "not_enough"


def gain_model_tag(gas_key: str) -> str:
    if gas_key == "75Ar25CO2":
        return "diethorn_like_surrogate"
    return "direct_primary_only_no_stable_air_avalanche_modeled"


def note_for_row(gas_key: str, wire_key: str, voltage_v: float) -> str:
    if gas_key == "75Ar25CO2":
        return "75Ar25CO2 proportional-gain surrogate model"
    onset = AIR_CORONA_ONSET_ESTIMATE_V[wire_key]
    if voltage_v >= onset:
        return "air direct-primary estimate only; above rough corona-onset estimate"
    return "air direct-primary estimate only; below rough corona-onset estimate"


def iter_voltage_points(v_min: int, v_max: int, v_step: int) -> Iterable[int]:
    v = v_min
    while v <= v_max:
        yield v
        v += v_step


def build_rows(v_min: int, v_max: int, v_step: int) -> List[dict]:
    rows: List[dict] = []

    for voltage_v in iter_voltage_points(v_min, v_max, v_step):
        for gas in GASES.values():
            for wire in WIRES.values():
                for source in SOURCES.values():
                    n_primary = primary_electrons(source.key, gas.key)
                    surv = survival_factor(source.key, gas.key)
                    log_ba = ln_b_over_a(wire.radius_cm)
                    e_surface_v_per_cm = surface_field_v_per_cm(voltage_v, wire.radius_cm)
                    e_surface_kv_per_cm = e_surface_v_per_cm / 1.0e3

                    if gas.key == "75Ar25CO2":
                        v0_v = v0_diethorn_like(wire.radius_cm)
                    else:
                        v0_v = ""

                    gain_value = gain(gas.key, voltage_v, wire.radius_cm)
                    q_c = collected_charge_c(n_primary, surv, gain_value)
                    q_pc = q_c * 1.0e12
                    vpk_v = peak_voltage_v(q_c)
                    vpk_mv = vpk_v * 1.0e3

                    air_corona_onset_v = AIR_CORONA_ONSET_ESTIMATE_V[wire.key] if gas.key == "air" else ""
                    air_corona_region_flag = (
                        (gas.key == "air") and (float(voltage_v) >= AIR_CORONA_ONSET_ESTIMATE_V[wire.key])
                    )

                    row = {
                        "voltage_v": voltage_v,
                        "gas_key": gas.key,
                        "gas_label": gas.label,
                        "wire_key": wire.key,
                        "wire_label": wire.label,
                        "source_key": source.key,
                        "source_label": source.label,
                        "wire_diameter_um": wire.diameter_um,
                        "wire_radius_cm": wire.radius_cm,
                        "outer_radius_cm": OUTER_RADIUS_CM,
                        "ln_b_over_a": log_ba,
                        "surface_field_v_per_cm": e_surface_v_per_cm,
                        "surface_field_kv_per_cm": e_surface_kv_per_cm,
                        "primary_electrons": n_primary,
                        "survival_factor": surv,
                        "gain_model": gain_model_tag(gas.key),
                        "v0_v": v0_v,
                        "gain": gain_value,
                        "collected_charge_c": q_c,
                        "collected_charge_pc": q_pc,
                        "pulse_width_ns": PULSE_WIDTH_NS,
                        "termination_ohm": TERMINATION_OHM,
                        "peak_voltage_v": vpk_v,
                        "peak_voltage_mv": vpk_mv,
                        "visible_threshold_mv": VISIBLE_THRESHOLD_MV,
                        "reliable_threshold_mv": RELIABLE_THRESHOLD_MV,
                        "visibility_class": visibility_class(vpk_mv),
                        "air_corona_onset_estimate_v": air_corona_onset_v,
                        "air_corona_region_flag": air_corona_region_flag,
                        "notes": note_for_row(gas.key, wire.key, voltage_v),
                    }
                    rows.append(row)

    return rows


def write_csv(rows: List[dict], output_path: Path) -> None:
    if not rows:
        raise ValueError("No rows to write.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "voltage_v",
        "gas_key",
        "gas_label",
        "wire_key",
        "wire_label",
        "source_key",
        "source_label",
        "wire_diameter_um",
        "wire_radius_cm",
        "outer_radius_cm",
        "ln_b_over_a",
        "surface_field_v_per_cm",
        "surface_field_kv_per_cm",
        "primary_electrons",
        "survival_factor",
        "gain_model",
        "v0_v",
        "gain",
        "collected_charge_c",
        "collected_charge_pc",
        "pulse_width_ns",
        "termination_ohm",
        "peak_voltage_v",
        "peak_voltage_mv",
        "visible_threshold_mv",
        "reliable_threshold_mv",
        "visibility_class",
        "air_corona_onset_estimate_v",
        "air_corona_region_flag",
        "notes",
    ]

    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: List[dict]) -> None:
    combos = {}
    for row in rows:
        key = (row["gas_key"], row["wire_key"], row["source_key"])
        combos.setdefault(key, []).append(row)

    print("Summary by (gas, wire, source):")
    for key, combo_rows in sorted(combos.items()):
        first_barely = next((r["voltage_v"] for r in combo_rows if r["visibility_class"] == "barely_visible"), None)
        first_reliable = next((r["voltage_v"] for r in combo_rows if r["visibility_class"] == "reliable"), None)
        gas_key, wire_key, source_key = key
        print(
            f"  gas={gas_key:10s}  wire={wire_key:40s}  source={source_key:12s}  "
            f"first_barely={first_barely!s:>5s} V  first_reliable={first_reliable!s:>5s} V"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan single-wire signal estimates and write CSV."
    )
    parser.add_argument(
        "--vmin",
        type=int,
        default=0,
        help="Minimum voltage in V (default: 0)",
    )
    parser.add_argument(
        "--vmax",
        type=int,
        default=2400,
        help="Maximum voltage in V (default: 2400)",
    )
    parser.add_argument(
        "--vstep",
        type=int,
        default=100,
        help="Voltage step in V (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("single_wire_signal_scan.csv"),
        help="Output CSV path (default: single_wire_signal_scan.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.vstep <= 0:
        raise ValueError("--vstep must be positive")
    if args.vmax < args.vmin:
        raise ValueError("--vmax must be >= --vmin")

    rows = build_rows(args.vmin, args.vmax, args.vstep)
    write_csv(rows, args.output)

    print(f"Wrote {len(rows)} rows to: {args.output}")
    print_summary(rows)


if __name__ == "__main__":
    main()