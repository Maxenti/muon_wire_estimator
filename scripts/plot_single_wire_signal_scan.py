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


def parse_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    lowered = str(value).strip().lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    return None


def derive_plot_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    Normalize the single_wire_signal_scan CSV schema into a plotting schema
    closer to the beta visibility plotting script.

    Derived mappings:
    - voltage_v                       -> wire_voltage_V
    - gas_key / gas_label             -> gas_name / gas_label
    - wire_key / wire_label           -> wire_name / wire_label
    - source_key / source_label       -> source_name / source_label
    - primary_electrons               -> src_primary_electrons_mean
    - primary_electrons * survival    -> det_collected_primary_electrons_mean
    - gain                            -> det_gas_gain_mean
    - peak_voltage_mv                 -> det_peak_voltage_mV
    """
    out: list[dict[str, str]] = []

    for row in rows:
        primary = parse_float(row.get("primary_electrons"))
        survival = parse_float(row.get("survival_factor"))

        collected_primary = None
        if primary is not None and survival is not None:
            collected_primary = primary * survival

        air_corona_flag = parse_bool(row.get("air_corona_region_flag"))

        derived = dict(row)
        derived["wire_voltage_V"] = row.get("voltage_v", "")
        derived["gas_name"] = row.get("gas_key") or row.get("gas_label") or ""
        derived["gas_label"] = row.get("gas_label") or row.get("gas_key") or ""
        derived["wire_name"] = row.get("wire_key") or row.get("wire_label") or ""
        derived["wire_label"] = row.get("wire_label") or row.get("wire_key") or ""
        derived["source_name"] = row.get("source_key") or row.get("source_label") or ""
        derived["source_label"] = row.get("source_label") or row.get("source_key") or ""

        derived["src_primary_electrons_mean"] = (
            "" if primary is None else f"{primary:.12g}"
        )
        derived["det_collected_primary_electrons_mean"] = (
            "" if collected_primary is None else f"{collected_primary:.12g}"
        )
        derived["det_gas_gain_mean"] = row.get("gain", "")
        derived["det_peak_voltage_mV"] = row.get("peak_voltage_mv", "")

        # Extra deterministic plots that the original beta plotter does not have
        derived["det_collected_charge_pC"] = row.get("collected_charge_pc", "")
        derived["det_surface_field_kV_per_cm"] = row.get("surface_field_kv_per_cm", "")
        derived["det_survival_factor"] = row.get("survival_factor", "")
        derived["det_v0_v"] = row.get("v0_v", "")
        derived["det_air_corona_region_flag"] = (
            "" if air_corona_flag is None else ("1" if air_corona_flag else "0")
        )

        out.append(derived)

    return out


def unique_values(rows: list[dict[str, str]], key: str) -> list[str]:
    return sorted({row[key] for row in rows if row.get(key, "") != ""})


def build_lookup(rows: list[dict[str, str]], key: str, value_key: str) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in rows:
        k = row.get(key, "")
        v = row.get(value_key, "")
        if k and v and k not in lookup:
            lookup[k] = v
    return lookup


def group_rows(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["wire_name"], row["gas_name"])
        groups[key].append(row)

    for key in groups:
        groups[key].sort(key=lambda r: float(r["wire_voltage_V"]))
    return groups


def infer_threshold(rows: list[dict[str, str]], key: str, fallback: float | None = None) -> float | None:
    for row in rows:
        value = parse_float(row.get(key))
        if value is not None:
            return value
    return fallback


def plot_quantity(
    rows: list[dict[str, str]],
    *,
    quantity_key: str,
    ylabel: str,
    output_path: Path,
    title_prefix: str,
    use_log_y: bool = False,
    reference_lines: list[tuple[float, str, str]] | None = None,
) -> None:
    wire_names = unique_values(rows, "wire_name")
    if not wire_names:
        return

    wire_label_lookup = build_lookup(rows, "wire_name", "wire_label")
    gas_label_lookup = build_lookup(rows, "gas_name", "gas_label")
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

            label = gas_label_lookup.get(gas, gas)
            ax.plot(xs, ys, marker="o", label=label)
            plotted = True

        if reference_lines:
            for y, label, color in reference_lines:
                if not use_log_y or y > 0.0:
                    ax.axhline(
                        y,
                        color=color,
                        linestyle="--",
                        linewidth=1.5,
                        label=label,
                    )

        title_wire = wire_label_lookup.get(wire_name, wire_name)
        ax.set_title(f"{title_prefix}: {title_wire}")
        ax.set_xlabel("Wire voltage [V]")
        ax.set_ylabel(ylabel)
        ax.grid(True)
        if use_log_y:
            ax.set_yscale("log")
        if plotted or reference_lines:
            ax.legend()

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    print(f"Wrote {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plot single_wire_signal_scan.py CSV outputs in a format aligned with the beta visibility plotter."
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        required=True,
        help="CSV output from single_wire_signal_scan.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for plot PNGs",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help=(
            "Optional source_key to plot only one source "
            "(for example: cosmic_muon or sr90_beta). "
            "By default, plots all sources into separate subdirectories."
        ),
    )
    parser.add_argument(
        "--visibility-line-mv",
        type=float,
        default=None,
        help=(
            "Reliable visibility guide line in mV for peak-voltage plots. "
            "Defaults to reliable_threshold_mv from the CSV, or 20.0 if absent."
        ),
    )
    parser.add_argument(
        "--show-barely-visible-line",
        action="store_true",
        help="Also draw the barely-visible threshold from visible_threshold_mv, if present.",
    )
    args = parser.parse_args()

    raw_rows = read_csv_rows(args.summary_csv)
    rows = derive_plot_rows(raw_rows)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    all_sources = unique_values(rows, "source_name")
    if args.source is not None:
        sources = [args.source]
    else:
        sources = all_sources

    for source_name in sources:
        source_rows = [row for row in rows if row.get("source_name") == source_name]
        if not source_rows:
            print(f"Skipping source {source_name!r}: no rows found.")
            continue

        source_label = source_rows[0].get("source_label", source_name) or source_name
        source_output_dir = output_dir / source_name
        source_output_dir.mkdir(parents=True, exist_ok=True)

        reliable_line = (
            float(args.visibility_line_mv)
            if args.visibility_line_mv is not None
            else infer_threshold(source_rows, "reliable_threshold_mv", 20.0)
        )

        reference_lines: list[tuple[float, str, str]] = []
        if reliable_line is not None:
            reference_lines.append(
                (reliable_line, f"reliable visibility ≈ {reliable_line:g} mV", "red")
            )

        if args.show_barely_visible_line:
            barely_visible_line = infer_threshold(source_rows, "visible_threshold_mv", 5.0)
            if barely_visible_line is not None:
                reference_lines.append(
                    (
                        barely_visible_line,
                        f"barely visible ≈ {barely_visible_line:g} mV",
                        "orange",
                    )
                )

        # Closest analogs to the beta plotter
        plot_quantity(
            source_rows,
            quantity_key="src_primary_electrons_mean",
            ylabel="Created primary electrons",
            output_path=source_output_dir / "src_primary_electrons_mean_linear.png",
            title_prefix=f"{source_label} | Source-side created primary electrons",
            use_log_y=False,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_collected_primary_electrons_mean",
            ylabel="Collected primary electrons",
            output_path=source_output_dir / "det_collected_primary_electrons_linear.png",
            title_prefix=f"{source_label} | Detector collected primary electrons",
            use_log_y=False,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_gas_gain_mean",
            ylabel="Deterministic gas gain",
            output_path=source_output_dir / "det_gas_gain_mean_linear.png",
            title_prefix=f"{source_label} | Deterministic gas gain",
            use_log_y=False,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_gas_gain_mean",
            ylabel="Deterministic gas gain",
            output_path=source_output_dir / "det_gas_gain_mean_log.png",
            title_prefix=f"{source_label} | Deterministic gas gain",
            use_log_y=True,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_peak_voltage_mV",
            ylabel="Deterministic peak voltage [mV]",
            output_path=source_output_dir / "det_peak_voltage_mV_linear.png",
            title_prefix=f"{source_label} | Deterministic avalanche peak voltage",
            use_log_y=False,
            reference_lines=reference_lines,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_peak_voltage_mV",
            ylabel="Deterministic peak voltage [mV]",
            output_path=source_output_dir / "det_peak_voltage_mV_log.png",
            title_prefix=f"{source_label} | Deterministic avalanche peak voltage",
            use_log_y=True,
            reference_lines=reference_lines,
        )

        # Additional deterministic plots available from this CSV
        plot_quantity(
            source_rows,
            quantity_key="det_collected_charge_pC",
            ylabel="Collected charge [pC]",
            output_path=source_output_dir / "det_collected_charge_pC_linear.png",
            title_prefix=f"{source_label} | Collected charge",
            use_log_y=False,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_collected_charge_pC",
            ylabel="Collected charge [pC]",
            output_path=source_output_dir / "det_collected_charge_pC_log.png",
            title_prefix=f"{source_label} | Collected charge",
            use_log_y=True,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_surface_field_kV_per_cm",
            ylabel="Surface field [kV/cm]",
            output_path=source_output_dir / "det_surface_field_kV_per_cm_linear.png",
            title_prefix=f"{source_label} | Surface field",
            use_log_y=False,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_surface_field_kV_per_cm",
            ylabel="Surface field [kV/cm]",
            output_path=source_output_dir / "det_surface_field_kV_per_cm_log.png",
            title_prefix=f"{source_label} | Surface field",
            use_log_y=True,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_survival_factor",
            ylabel="Survival factor",
            output_path=source_output_dir / "det_survival_factor_linear.png",
            title_prefix=f"{source_label} | Survival factor",
            use_log_y=False,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_v0_v",
            ylabel="Diethorn-like V0 [V]",
            output_path=source_output_dir / "det_v0_v_linear.png",
            title_prefix=f"{source_label} | V0 surrogate parameter",
            use_log_y=False,
        )
        plot_quantity(
            source_rows,
            quantity_key="det_air_corona_region_flag",
            ylabel="Air corona-region flag [0/1]",
            output_path=source_output_dir / "det_air_corona_region_flag_linear.png",
            title_prefix=f"{source_label} | Air corona-region flag",
            use_log_y=False,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())