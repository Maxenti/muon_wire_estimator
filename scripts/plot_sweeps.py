#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


FILENAME_RE = re.compile(
    r"^(?P<wire>.+?)__(?P<gas>.+?)__V(?P<voltage>[0-9]+(?:\.[0-9]+)?)__r(?P<radius>[0-9]+p[0-9]+|[0-9]+)\.json$"
)


def parse_metadata_from_filename(path: Path) -> dict:
    match = FILENAME_RE.match(path.name)
    if not match:
        return {
            "wire_name": None,
            "gas_name": None,
            "wire_voltage_V": None,
            "muon_closest_approach_mm": None,
        }
    return {
        "wire_name": match.group("wire"),
        "gas_name": match.group("gas"),
        "wire_voltage_V": float(match.group("voltage")),
        "muon_closest_approach_mm": float(match.group("radius").replace("p", ".")),
    }


def load_rows(directory: Path, kind: str) -> list[dict]:
    rows: list[dict] = []
    if not directory.exists():
        return rows

    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception as exc:
            print(f"Skipping {path}: {exc}")
            continue

        meta = parse_metadata_from_filename(path)
        row = {
            "kind": kind,
            "file": str(path),
            **meta,
        }

        if kind == "deterministic":
            row.update(extract_deterministic(data))
        elif kind == "stochastic":
            row.update(extract_stochastic(data))

        rows.append(row)

    return rows


def extract_deterministic(data: dict) -> dict:
    avalanche_pulse = data.get("avalanche_pulse", {})
    direct_pulse = data.get("direct_pulse", {})

    avalanche_charge_c = data.get("avalanche_charge_c")
    drift_time_s = data.get("drift_time_s")

    out = {
        "attachment_survival_fraction": data.get("attachment_survival_fraction"),
        "created_primary_electrons_mean": data.get("created_primary_electrons_mean"),
        "collected_primary_electrons_mean": data.get("collected_primary_electrons_mean"),
        "collection_fraction_total": data.get("collection_fraction_total"),
        "gas_gain_mean": data.get("gas_gain_mean"),
        "avalanche_charge_fC": None if avalanche_charge_c is None else avalanche_charge_c * 1.0e15,
        "drift_time_ns": None if drift_time_s is None else drift_time_s * 1.0e9,
        "det_peak_voltage_mV": None
        if avalanche_pulse.get("peak_voltage_v") is None
        else avalanche_pulse["peak_voltage_v"] * 1.0e3,
        "det_peak_current_nA": None
        if avalanche_pulse.get("peak_current_a") is None
        else avalanche_pulse["peak_current_a"] * 1.0e9,
        "direct_peak_voltage_mV": None
        if direct_pulse.get("peak_voltage_v") is None
        else direct_pulse["peak_voltage_v"] * 1.0e3,
    }

    gas = data.get("gas", {})
    out["gas_from_payload"] = gas.get("name")
    return out


def extract_stochastic(data: dict) -> dict:
    out = {
        "event_mean_peak_mV": None
        if data.get("mean_peak_voltage_v") is None
        else data["mean_peak_voltage_v"] * 1.0e3,
        "event_median_peak_mV": None
        if data.get("median_peak_voltage_v") is None
        else data["median_peak_voltage_v"] * 1.0e3,
        "event_max_peak_mV": None
        if data.get("max_peak_voltage_v") is None
        else data["max_peak_voltage_v"] * 1.0e3,
        "event_min_peak_mV": None
        if data.get("min_peak_voltage_v") is None
        else data["min_peak_voltage_v"] * 1.0e3,
        "fraction_above_threshold": data.get("fraction_above_threshold"),
        "mean_gas_gain": data.get("mean_gas_gain"),
        "mean_primary_electrons_collected": data.get("mean_primary_electrons_collected"),
        "mean_primary_electrons_created": data.get("mean_primary_electrons_created"),
        "threshold_mV": None
        if data.get("threshold_v") is None
        else data["threshold_v"] * 1.0e3,
        "n_events": data.get("n_events"),
    }

    meta = data.get("metadata", {})
    out["gas_from_payload"] = meta.get("gas_name")
    return out


def unique_wire_names(rows: list[dict]) -> list[str]:
    return sorted({row["wire_name"] for row in rows if row.get("wire_name") is not None})


def group_rows(rows: list[dict]):
    grouped = defaultdict(list)
    for row in rows:
        key = (
            row.get("wire_name"),
            row.get("gas_name"),
            row.get("muon_closest_approach_mm"),
        )
        grouped[key].append(row)

    for key in grouped:
        grouped[key].sort(key=lambda x: x.get("wire_voltage_V", 0.0))
    return grouped


def plot_quantity(
    rows: list[dict],
    quantity_key: str,
    ylabel: str,
    output_path: Path,
    title_prefix: str,
) -> None:
    wires = unique_wire_names(rows)
    if not wires:
        print(f"Skipping {quantity_key}: no wire metadata found.")
        return

    fig, axes = plt.subplots(len(wires), 1, figsize=(10, 4 * len(wires)), squeeze=False)
    axes = axes[:, 0]
    grouped = group_rows(rows)

    for ax, wire in zip(axes, wires):
        plotted = False
        for (w, gas, rmm), entries in grouped.items():
            if w != wire:
                continue

            xy = []
            for e in entries:
                x = e.get("wire_voltage_V")
                y = e.get(quantity_key)
                if x is not None and y is not None:
                    xy.append((x, y))

            if not xy:
                continue

            xs, ys = zip(*xy)
            ax.plot(xs, ys, marker="o", label=f"{gas}, r={rmm} mm")
            plotted = True

        ax.set_title(f"{title_prefix}: {wire}")
        ax.set_xlabel("Wire voltage [V]")
        ax.set_ylabel(ylabel)
        ax.grid(True)
        if plotted:
            ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    print(f"Wrote {output_path}")


def main() -> None:
    det_rows = load_rows(Path("sweep_outputs/deterministic"), "deterministic")
    sto_rows = load_rows(Path("sweep_outputs/stochastic"), "stochastic")

    print(f"Loaded {len(det_rows)} deterministic rows")
    print(f"Loaded {len(sto_rows)} stochastic rows")

    out_dir = Path("sweep_plots")
    out_dir.mkdir(parents=True, exist_ok=True)

    if det_rows:
        plot_quantity(det_rows, "created_primary_electrons_mean", "Created primary electrons", out_dir / "det_created_primary_electrons_mean.png", "Deterministic created primary electrons")
        plot_quantity(det_rows, "collected_primary_electrons_mean", "Collected primary electrons", out_dir / "det_collected_primary_electrons_mean.png", "Deterministic collected primary electrons")
        plot_quantity(det_rows, "collection_fraction_total", "Collection fraction", out_dir / "det_collection_fraction_total.png", "Deterministic collection fraction")
        plot_quantity(det_rows, "attachment_survival_fraction", "Attachment survival fraction", out_dir / "det_attachment_survival_fraction.png", "Deterministic attachment survival")
        plot_quantity(det_rows, "gas_gain_mean", "Mean gas gain", out_dir / "det_gas_gain_mean.png", "Deterministic gas gain")
        plot_quantity(det_rows, "avalanche_charge_fC", "Avalanche charge [fC]", out_dir / "det_avalanche_charge_fC.png", "Deterministic avalanche charge")
        plot_quantity(det_rows, "det_peak_voltage_mV", "Peak voltage into 50 Ω [mV]", out_dir / "det_peak_voltage_mV.png", "Deterministic avalanche peak voltage")
        plot_quantity(det_rows, "direct_peak_voltage_mV", "Direct pulse peak voltage [mV]", out_dir / "det_direct_peak_voltage_mV.png", "Direct muon image peak voltage")
        plot_quantity(det_rows, "drift_time_ns", "Drift time [ns]", out_dir / "det_drift_time_ns.png", "Deterministic drift time")

    if sto_rows:
        plot_quantity(sto_rows, "mean_primary_electrons_created", "Mean created primary electrons", out_dir / "sto_mean_primary_electrons_created.png", "Stochastic mean created primary electrons")
        plot_quantity(sto_rows, "mean_primary_electrons_collected", "Mean collected primary electrons", out_dir / "sto_mean_primary_electrons_collected.png", "Stochastic mean collected primary electrons")
        plot_quantity(sto_rows, "mean_gas_gain", "Mean gas gain", out_dir / "sto_mean_gas_gain.png", "Stochastic mean gas gain")
        plot_quantity(sto_rows, "event_mean_peak_mV", "Mean peak voltage [mV]", out_dir / "sto_event_mean_peak_mV.png", "Stochastic mean peak voltage")
        plot_quantity(sto_rows, "event_median_peak_mV", "Median peak voltage [mV]", out_dir / "sto_event_median_peak_mV.png", "Stochastic median peak voltage")
        plot_quantity(sto_rows, "event_max_peak_mV", "Max peak voltage [mV]", out_dir / "sto_event_max_peak_mV.png", "Stochastic max peak voltage")
        plot_quantity(sto_rows, "fraction_above_threshold", "Fraction above threshold", out_dir / "sto_fraction_above_threshold.png", "Threshold crossing fraction")


if __name__ == "__main__":
    main()