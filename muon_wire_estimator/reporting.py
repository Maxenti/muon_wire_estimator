"""
Reporting helpers for default vs calibrated muon wire estimator outputs.

This module provides lightweight, JSON-friendly summary helpers intended for:

- compact deterministic estimate summaries
- compact calibrated/default comparison reports
- consistent report blocks for CLI output and README examples

The goal is not to create a rich rendering system. Instead, it provides stable,
easy-to-read data structures that make it clear what changed when calibration is
applied and which quantities are most relevant for oscilloscope comparison.
"""

from __future__ import annotations

from .calibrated_core import CalibratedDeterministicEstimate
from .models import DeterministicEstimate, JSONValue, PulseEstimate


def _pulse_report_block(pulse: PulseEstimate | None) -> dict[str, JSONValue] | None:
    """
    Convert an optional PulseEstimate into a compact report block.
    """
    if pulse is None:
        return None
    if not isinstance(pulse, PulseEstimate):
        raise TypeError(
            f"pulse must be PulseEstimate or None, got {type(pulse).__name__}."
        )
    return {
        "model_name": pulse.model_name,
        "charge_c": pulse.charge_c,
        "peak_current_a": pulse.peak_current_a,
        "peak_voltage_v": pulse.peak_voltage_v,
        "width_s": pulse.width_s,
        "termination_ohm": pulse.termination_ohm,
        "signal_family": pulse.metadata.get("signal_family"),
    }


def deterministic_report(
    estimate: DeterministicEstimate,
) -> dict[str, JSONValue]:
    """
    Build a compact reporting dictionary for a deterministic estimate.

    The output is intentionally focused on the load-bearing quantities a user is
    likely to compare against oscilloscope measurements.
    """
    if not isinstance(estimate, DeterministicEstimate):
        raise TypeError(
            "estimate must be a DeterministicEstimate instance, "
            f"got {type(estimate).__name__}."
        )

    avalanche_peak_voltage = (
        None if estimate.avalanche_pulse is None else estimate.avalanche_pulse.peak_voltage_v
    )
    direct_peak_voltage = (
        None if estimate.direct_pulse is None else estimate.direct_pulse.peak_voltage_v
    )

    return {
        "estimator_version": estimate.estimator_version,
        "gas_name": estimate.gas.name,
        "created_primary_electrons_mean": estimate.created_primary_electrons_mean,
        "collected_primary_electrons_mean": estimate.collected_primary_electrons_mean,
        "drift_time_s": estimate.drift_time_s,
        "attachment_survival_fraction": estimate.attachment_survival_fraction,
        "collection_fraction_total": estimate.collection_fraction_total,
        "gas_gain_mean": estimate.gas_gain_mean,
        "avalanche_electrons_mean": estimate.avalanche_electrons_mean,
        "avalanche_charge_c": estimate.avalanche_charge_c,
        "direct_pulse": _pulse_report_block(estimate.direct_pulse),
        "avalanche_pulse": _pulse_report_block(estimate.avalanche_pulse),
        "scope_comparison_quantities": {
            "primary_quantity": avalanche_peak_voltage,
            "secondary_quantity": direct_peak_voltage,
            "primary_quantity_name": (
                None if avalanche_peak_voltage is None else "avalanche_pulse.peak_voltage_v"
            ),
            "secondary_quantity_name": (
                None if direct_peak_voltage is None else "direct_pulse.peak_voltage_v"
            ),
        },
        "notes": list(estimate.notes),
    }


def comparison_report(
    result: CalibratedDeterministicEstimate,
) -> dict[str, JSONValue]:
    """
    Build a compact default-vs-calibrated comparison report.

    This report emphasizes:
    - whether calibration actually changed the result
    - how gain changed
    - how avalanche charge changed
    - how the oscilloscope-facing peak voltage changed
    """
    if not isinstance(result, CalibratedDeterministicEstimate):
        raise TypeError(
            "result must be a CalibratedDeterministicEstimate instance, "
            f"got {type(result).__name__}."
        )

    default_estimate = result.default_estimate
    calibrated_estimate = result.calibrated_result

    default_avalanche_peak_v = (
        None
        if default_estimate.avalanche_pulse is None
        else default_estimate.avalanche_pulse.peak_voltage_v
    )
    calibrated_avalanche_peak_v = (
        None
        if calibrated_estimate.avalanche_pulse is None
        else calibrated_estimate.avalanche_pulse.peak_voltage_v
    )

    if (
        default_avalanche_peak_v is None
        or calibrated_avalanche_peak_v is None
    ):
        delta_avalanche_peak_v: float | None = None
        ratio_avalanche_peak_v: float | None = None
    else:
        delta_avalanche_peak_v = calibrated_avalanche_peak_v - default_avalanche_peak_v
        ratio_avalanche_peak_v = (
            None
            if default_avalanche_peak_v == 0.0
            else calibrated_avalanche_peak_v / default_avalanche_peak_v
        )

    delta_gain = calibrated_estimate.gas_gain_mean - default_estimate.gas_gain_mean
    ratio_gain = (
        None
        if default_estimate.gas_gain_mean == 0.0
        else calibrated_estimate.gas_gain_mean / default_estimate.gas_gain_mean
    )

    delta_charge_c = (
        calibrated_estimate.avalanche_charge_c - default_estimate.avalanche_charge_c
    )
    ratio_charge = (
        None
        if default_estimate.avalanche_charge_c == 0.0
        else calibrated_estimate.avalanche_charge_c / default_estimate.avalanche_charge_c
    )

    return {
        "gas_name": default_estimate.gas.name,
        "calibration_applied": result.calibration_applied,
        "calibration_name": (
            None
            if result.calibration_record is None
            else result.calibration_record.calibration_name
        ),
        "calibration_source": (
            None
            if result.calibration_record is None
            else result.calibration_record.source
        ),
        "default": deterministic_report(default_estimate),
        "calibrated": deterministic_report(calibrated_estimate),
        "deltas": {
            "gas_gain_mean_delta": delta_gain,
            "gas_gain_mean_ratio": ratio_gain,
            "avalanche_charge_c_delta": delta_charge_c,
            "avalanche_charge_c_ratio": ratio_charge,
            "avalanche_peak_voltage_v_delta": delta_avalanche_peak_v,
            "avalanche_peak_voltage_v_ratio": ratio_avalanche_peak_v,
        },
        "recommended_scope_comparison": {
            "default_quantity": default_avalanche_peak_v,
            "calibrated_quantity": calibrated_avalanche_peak_v,
            "quantity_name": "avalanche_pulse.peak_voltage_v",
            "interpretation": (
                "Compare the calibrated avalanche peak voltage against oscilloscope "
                "thresholds and measured pulse amplitudes. Keep the direct pulse as "
                "a separate secondary channel."
            ),
        },
        "metadata": dict(result.metadata),
    }


def calibration_status_report(
    result: CalibratedDeterministicEstimate,
) -> dict[str, JSONValue]:
    """
    Build a minimal calibration-status block.

    This helper is useful when the caller only wants to know whether the
    calibrated path differed from the default surrogate path.
    """
    if not isinstance(result, CalibratedDeterministicEstimate):
        raise TypeError(
            "result must be a CalibratedDeterministicEstimate instance, "
            f"got {type(result).__name__}."
        )

    return {
        "calibration_applied": result.calibration_applied,
        "calibration_name": (
            None
            if result.calibration_record is None
            else result.calibration_record.calibration_name
        ),
        "gas_name": result.default_estimate.gas.name,
        "default_gain_mean": result.default_estimate.gas_gain_mean,
        "calibrated_gain_mean": result.calibrated_result.gas_gain_mean,
        "default_avalanche_peak_voltage_v": (
            None
            if result.default_estimate.avalanche_pulse is None
            else result.default_estimate.avalanche_pulse.peak_voltage_v
        ),
        "calibrated_avalanche_peak_voltage_v": (
            None
            if result.calibrated_result.avalanche_pulse is None
            else result.calibrated_result.avalanche_pulse.peak_voltage_v
        ),
    }


__all__ = [
    "calibration_status_report",
    "comparison_report",
    "deterministic_report",
]