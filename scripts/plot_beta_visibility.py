#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def unique_wire_names(rows: list[dict[str, str]]) -> list[str]:
    return sorted({row["wire_name"] for row in rows})


def group_rows(rows: list[dict[str, str]]):
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["wire_name"], row["gas_name"])
        groups[key].append(row)

    for key in groups:
        groups[key].sort(key=lambda r: float(r["wire_voltage_V"]))
    return groups


def plot_quantity(
    rows: list[dict[str, str]],
    *,
    quantity_key: str,
    ylabel: str,
    output_path: Path,
    title_prefix: str,
    use_log_y: bool = False,
    reference_line_y: float | None = None,
    reference_line_label: str | None = None,
) -> None:
    wire_names = unique_wire_names(rows)
    if not wire_names:
        return

    groups = group_rows(rows)

    fig, axes = plt.subplots(
        len(wire_names),
        1,
        figsize=(10, 4 * len(wire_names)),
        squeeze=False,
    )
    axes = axes[:, 0]

    for ax, wire_name in zip(axes, wire_names):
        plotted = False

        for (wire, gas), entries in groups.items():
            if wire != wire_name:
                continue

            xs: list[float] = []
            ys: list[float] = []

            for row in entries:
                x = parse_float(row.get("wire_voltage_V"))
                y = parse_float(row.get(quantity_key))
                if x is None or y is None:
                    continue
                if use_log_y and y <= 0.0:
                    continue
                xs.append(x)
                ys.append(y)

            if not xs:
                continue

            ax.plot(xs, ys, marker="o", label=gas)
            plotted = True

        if reference_line_y is not None and (not use_log_y or reference_line_y > 0.0):
            ax.axhline(
                reference_line_y,
                color="red",
                linestyle="--",
                linewidth=1.5,
                label=reference_line_label or f"{reference_line_y:g} mV guide",
            )

        ax.set_title(f"{title_prefix}: {wire_name}")
        ax.set_xlabel("Wire voltage [V]")
        ax.set_ylabel(ylabel)
        ax.grid(True)
        if use_log_y:
            ax.set_yscale("log")
        if plotted or reference_line_y is not None:
            ax.legend()

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    print(f"Wrote {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plot beta visibility scan results from summary CSV."
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        required=True,
        help="Summary CSV from scan_beta_visibility.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for plot PNGs",
    )
    parser.add_argument(
        "--visibility-line-mv",
        type=float,
        default=30.0,
        help="Horizontal visibility guide line in mV for peak-voltage plots. Default: 30.0",
    )
    args = parser.parse_args()

    rows = read_csv_rows(args.summary_csv)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    vis_line = float(args.visibility_line_mv)
    vis_label = f"practical scope visibility ≈ {vis_line:g} mV"

    # Source-side plots
    plot_quantity(
        rows,
        quantity_key="src_particle_kinetic_energy_mev",
        ylabel="Representative beta kinetic energy [MeV]",
        output_path=output_dir / "src_particle_kinetic_energy_mev.png",
        title_prefix="Source-side representative beta energy",
        use_log_y=False,
    )
    plot_quantity(
        rows,
        quantity_key="src_deposited_energy_mev",
        ylabel="Deposited energy [MeV]",
        output_path=output_dir / "src_deposited_energy_mev_linear.png",
        title_prefix="Source-side deposited energy",
        use_log_y=False,
    )
    plot_quantity(
        rows,
        quantity_key="src_primary_electrons_mean",
        ylabel="Created primary electrons",
        output_path=output_dir / "src_primary_electrons_mean_linear.png",
        title_prefix="Source-side created primary electrons",
        use_log_y=False,
    )

    # Deterministic detector-side plots
    plot_quantity(
        rows,
        quantity_key="det_collected_primary_electrons_mean",
        ylabel="Collected primary electrons",
        output_path=output_dir / "det_collected_primary_electrons_linear.png",
        title_prefix="Detector collected primary electrons",
        use_log_y=False,
    )
    plot_quantity(
        rows,
        quantity_key="det_gas_gain_mean",
        ylabel="Deterministic gas gain",
        output_path=output_dir / "det_gas_gain_mean_linear.png",
        title_prefix="Deterministic gas gain",
        use_log_y=False,
    )
    plot_quantity(
        rows,
        quantity_key="det_gas_gain_mean",
        ylabel="Deterministic gas gain",
        output_path=output_dir / "det_gas_gain_mean_log.png",
        title_prefix="Deterministic gas gain",
        use_log_y=True,
    )
    plot_quantity(
        rows,
        quantity_key="det_peak_voltage_mV",
        ylabel="Deterministic peak voltage [mV]",
        output_path=output_dir / "det_peak_voltage_mV_linear.png",
        title_prefix="Deterministic avalanche peak voltage",
        use_log_y=False,
        reference_line_y=vis_line,
        reference_line_label=vis_label,
    )
    plot_quantity(
        rows,
        quantity_key="det_peak_voltage_mV",
        ylabel="Deterministic peak voltage [mV]",
        output_path=output_dir / "det_peak_voltage_mV_log.png",
        title_prefix="Deterministic avalanche peak voltage",
        use_log_y=True,
        reference_line_y=vis_line,
        reference_line_label=vis_label,
    )

    # Stochastic detector-side plots
    plot_quantity(
        rows,
        quantity_key="sto_mean_created_primary_electrons",
        ylabel="Mean created primary electrons",
        output_path=output_dir / "sto_mean_created_primary_electrons_linear.png",
        title_prefix="Stochastic created primary electrons",
        use_log_y=False,
    )
    plot_quantity(
        rows,
        quantity_key="sto_mean_peak_voltage_mV",
        ylabel="Mean peak voltage [mV]",
        output_path=output_dir / "sto_mean_peak_voltage_mV_linear.png",
        title_prefix="Stochastic mean peak voltage",
        use_log_y=False,
        reference_line_y=vis_line,
        reference_line_label=vis_label,
    )
    plot_quantity(
        rows,
        quantity_key="sto_mean_peak_voltage_mV",
        ylabel="Mean peak voltage [mV]",
        output_path=output_dir / "sto_mean_peak_voltage_mV_log.png",
        title_prefix="Stochastic mean peak voltage",
        use_log_y=True,
        reference_line_y=vis_line,
        reference_line_label=vis_label,
    )
    plot_quantity(
        rows,
        quantity_key="sto_median_peak_voltage_mV",
        ylabel="Median peak voltage [mV]",
        output_path=output_dir / "sto_median_peak_voltage_mV_linear.png",
        title_prefix="Stochastic median peak voltage",
        use_log_y=False,
        reference_line_y=vis_line,
        reference_line_label=vis_label,
    )
    plot_quantity(
        rows,
        quantity_key="sto_median_peak_voltage_mV",
        ylabel="Median peak voltage [mV]",
        output_path=output_dir / "sto_median_peak_voltage_mV_log.png",
        title_prefix="Stochastic median peak voltage",
        use_log_y=True,
        reference_line_y=vis_line,
        reference_line_label=vis_label,
    )
    plot_quantity(
        rows,
        quantity_key="sto_max_peak_voltage_mV",
        ylabel="Max peak voltage [mV]",
        output_path=output_dir / "sto_max_peak_voltage_mV_linear.png",
        title_prefix="Stochastic max peak voltage",
        use_log_y=False,
        reference_line_y=vis_line,
        reference_line_label=vis_label,
    )
    plot_quantity(
        rows,
        quantity_key="sto_max_peak_voltage_mV",
        ylabel="Max peak voltage [mV]",
        output_path=output_dir / "sto_max_peak_voltage_mV_log.png",
        title_prefix="Stochastic max peak voltage",
        use_log_y=True,
        reference_line_y=vis_line,
        reference_line_label=vis_label,
    )
    plot_quantity(
        rows,
        quantity_key="sto_fraction_above_threshold",
        ylabel="Fraction above threshold",
        output_path=output_dir / "sto_fraction_above_threshold_linear.png",
        title_prefix="Threshold crossing fraction",
        use_log_y=False,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())