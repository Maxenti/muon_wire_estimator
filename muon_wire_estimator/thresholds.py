"""
Threshold and event-selection helpers for the muon wire estimator.

This module provides lightweight utilities for comparing simulated event
amplitudes against user-defined voltage thresholds. It is intentionally simple
and standard-library-only, with interfaces designed to work cleanly with the
Level 2 stochastic event outputs.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import EventPulseRecord, JSONValue


@dataclass(slots=True)
class ThresholdDecision:
    """
    Result of comparing a single peak voltage against a threshold.
    """

    threshold_v: float
    peak_voltage_v: float
    passed: bool
    margin_v: float

    def __post_init__(self) -> None:
        if self.threshold_v < 0.0:
            raise ValueError(f"threshold_v must be >= 0, got {self.threshold_v!r}.")
        if self.peak_voltage_v < 0.0:
            raise ValueError(
                f"peak_voltage_v must be >= 0, got {self.peak_voltage_v!r}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return {
            "threshold_v": self.threshold_v,
            "peak_voltage_v": self.peak_voltage_v,
            "passed": self.passed,
            "margin_v": self.margin_v,
        }


def passes_threshold(peak_voltage_v: float, threshold_v: float) -> bool:
    """
    Return True if the peak voltage is at or above threshold.
    """
    if peak_voltage_v < 0.0:
        raise ValueError(
            f"peak_voltage_v must be >= 0, got {peak_voltage_v!r}."
        )
    if threshold_v < 0.0:
        raise ValueError(f"threshold_v must be >= 0, got {threshold_v!r}.")
    return peak_voltage_v >= threshold_v


def threshold_margin_v(peak_voltage_v: float, threshold_v: float) -> float:
    """
    Return peak minus threshold in volts.

    Positive values indicate passing events.
    """
    if peak_voltage_v < 0.0:
        raise ValueError(
            f"peak_voltage_v must be >= 0, got {peak_voltage_v!r}."
        )
    if threshold_v < 0.0:
        raise ValueError(f"threshold_v must be >= 0, got {threshold_v!r}.")
    return peak_voltage_v - threshold_v


def evaluate_threshold(peak_voltage_v: float, threshold_v: float) -> ThresholdDecision:
    """
    Evaluate a threshold decision for a single event amplitude.
    """
    passed = passes_threshold(peak_voltage_v, threshold_v)
    margin = threshold_margin_v(peak_voltage_v, threshold_v)
    return ThresholdDecision(
        threshold_v=threshold_v,
        peak_voltage_v=peak_voltage_v,
        passed=passed,
        margin_v=margin,
    )


def filter_events_above_threshold(
    event_records: list[EventPulseRecord],
    threshold_v: float,
) -> list[EventPulseRecord]:
    """
    Return only events whose peak voltage passes the threshold.
    """
    if threshold_v < 0.0:
        raise ValueError(f"threshold_v must be >= 0, got {threshold_v!r}.")
    output: list[EventPulseRecord] = []
    for event in event_records:
        if not isinstance(event, EventPulseRecord):
            raise TypeError(
                "event_records must contain EventPulseRecord instances, "
                f"got {type(event).__name__}."
            )
        if event.peak_voltage_v >= threshold_v:
            output.append(event)
    return output


def count_events_above_threshold(
    event_records: list[EventPulseRecord],
    threshold_v: float,
) -> int:
    """
    Count how many event records pass the threshold.
    """
    return len(filter_events_above_threshold(event_records, threshold_v))


def fraction_events_above_threshold(
    event_records: list[EventPulseRecord],
    threshold_v: float,
) -> float:
    """
    Compute the fraction of event records that pass threshold.
    """
    if not event_records:
        raise ValueError("event_records must be non-empty.")
    count = count_events_above_threshold(event_records, threshold_v)
    return count / len(event_records)


def threshold_scan(
    peak_voltages_v: list[float],
    thresholds_v: list[float],
) -> list[dict[str, JSONValue]]:
    """
    Evaluate fractions passing for multiple threshold values.

    Returns a JSON-friendly list of dictionaries with:
    - threshold_v
    - n_total
    - n_pass
    - fraction_pass
    """
    if not peak_voltages_v:
        raise ValueError("peak_voltages_v must be non-empty.")
    for value in peak_voltages_v:
        if value < 0.0:
            raise ValueError(
                f"All peak voltages must be >= 0, got {value!r}."
            )

    results: list[dict[str, JSONValue]] = []
    n_total = len(peak_voltages_v)
    for threshold_v in thresholds_v:
        if threshold_v < 0.0:
            raise ValueError(
                f"All thresholds must be >= 0, got {threshold_v!r}."
            )
        n_pass = sum(1 for value in peak_voltages_v if value >= threshold_v)
        results.append(
            {
                "threshold_v": threshold_v,
                "n_total": n_total,
                "n_pass": n_pass,
                "fraction_pass": n_pass / n_total,
            }
        )
    return results


__all__ = [
    "ThresholdDecision",
    "count_events_above_threshold",
    "evaluate_threshold",
    "filter_events_above_threshold",
    "fraction_events_above_threshold",
    "passes_threshold",
    "threshold_margin_v",
    "threshold_scan",
]