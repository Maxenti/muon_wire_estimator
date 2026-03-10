"""
Event-level summary statistics for Level 2 stochastic muon wire simulations.

This module provides lightweight statistical helpers for collections of
EventPulseRecord objects and voltage samples. It is deliberately standard
library only and is designed to support:

- summary stats for repeated event simulations
- threshold-crossing fractions
- compact JSON-friendly report blocks
- reuse by CLI/reporting/calibration comparison layers

The statistics here are descriptive summaries, not inference tools.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import EventPulseRecord, EventSimulationSummary, JSONValue
from .thresholds import fraction_events_above_threshold


@dataclass(slots=True)
class VoltageStats:
    """
    Descriptive statistics for a collection of peak voltages.
    """

    count: int
    mean_v: float
    median_v: float
    min_v: float
    max_v: float
    stddev_v: float

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError(f"count must be > 0, got {self.count!r}.")
        if self.mean_v < 0.0:
            raise ValueError(f"mean_v must be >= 0, got {self.mean_v!r}.")
        if self.median_v < 0.0:
            raise ValueError(f"median_v must be >= 0, got {self.median_v!r}.")
        if self.min_v < 0.0:
            raise ValueError(f"min_v must be >= 0, got {self.min_v!r}.")
        if self.max_v < 0.0:
            raise ValueError(f"max_v must be >= 0, got {self.max_v!r}.")
        if self.stddev_v < 0.0:
            raise ValueError(f"stddev_v must be >= 0, got {self.stddev_v!r}.")

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return {
            "count": self.count,
            "mean_v": self.mean_v,
            "median_v": self.median_v,
            "min_v": self.min_v,
            "max_v": self.max_v,
            "stddev_v": self.stddev_v,
        }


def _validate_peak_voltages(peak_voltages_v: list[float]) -> list[float]:
    """
    Validate a non-empty list of non-negative peak voltages.
    """
    if not peak_voltages_v:
        raise ValueError("peak_voltages_v must be non-empty.")
    cleaned: list[float] = []
    for value in peak_voltages_v:
        numeric = float(value)
        if numeric < 0.0:
            raise ValueError(
                f"All peak voltages must be >= 0, got {numeric!r}."
            )
        cleaned.append(numeric)
    return cleaned


def _sorted_copy(values: list[float]) -> list[float]:
    """Return a sorted copy of numeric values."""
    return sorted(values)


def mean(values: list[float]) -> float:
    """
    Compute the arithmetic mean of a non-empty numeric list.
    """
    if not values:
        raise ValueError("values must be non-empty.")
    return sum(values) / len(values)


def median(values: list[float]) -> float:
    """
    Compute the median of a non-empty numeric list.
    """
    if not values:
        raise ValueError("values must be non-empty.")
    ordered = _sorted_copy(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def variance(values: list[float], *, sample: bool = False) -> float:
    """
    Compute variance of a non-empty numeric list.

    Parameters
    ----------
    sample:
        If True, use n-1 in the denominator. Otherwise use population variance.
    """
    if not values:
        raise ValueError("values must be non-empty.")
    n = len(values)
    if sample and n < 2:
        raise ValueError("At least two values are required for sample variance.")
    avg = mean(values)
    ss = sum((value - avg) ** 2 for value in values)
    denom = n - 1 if sample else n
    return ss / denom


def stddev(values: list[float], *, sample: bool = False) -> float:
    """
    Compute standard deviation of a non-empty numeric list.
    """
    return math.sqrt(variance(values, sample=sample))


def summarize_peak_voltages(peak_voltages_v: list[float]) -> VoltageStats:
    """
    Produce descriptive statistics for peak voltages.
    """
    values = _validate_peak_voltages(peak_voltages_v)
    ordered = _sorted_copy(values)
    return VoltageStats(
        count=len(ordered),
        mean_v=mean(ordered),
        median_v=median(ordered),
        min_v=ordered[0],
        max_v=ordered[-1],
        stddev_v=stddev(ordered, sample=False),
    )


def extract_peak_voltages(event_records: list[EventPulseRecord]) -> list[float]:
    """
    Extract peak voltages from event records.
    """
    if not event_records:
        raise ValueError("event_records must be non-empty.")
    voltages: list[float] = []
    for event in event_records:
        if not isinstance(event, EventPulseRecord):
            raise TypeError(
                "event_records must contain EventPulseRecord instances, "
                f"got {type(event).__name__}."
            )
        if event.peak_voltage_v < 0.0:
            raise ValueError(
                f"Encountered negative peak voltage {event.peak_voltage_v!r}."
            )
        voltages.append(event.peak_voltage_v)
    return voltages


def summarize_event_records(event_records: list[EventPulseRecord]) -> dict[str, JSONValue]:
    """
    Produce a compact JSON-friendly summary for event records.
    """
    if not event_records:
        raise ValueError("event_records must be non-empty.")

    peak_voltages = extract_peak_voltages(event_records)
    voltage_stats = summarize_peak_voltages(peak_voltages)

    n_events = len(event_records)
    mean_primary_created = sum(
        event.primary_electrons_created for event in event_records
    ) / n_events
    mean_primary_collected = sum(
        event.primary_electrons_collected for event in event_records
    ) / n_events
    mean_gas_gain = sum(event.gas_gain_sample for event in event_records) / n_events
    max_avalanche_charge_c = max(event.avalanche_charge_c for event in event_records)

    return {
        "n_events": n_events,
        "voltage_stats": voltage_stats.to_dict(),
        "mean_primary_electrons_created": mean_primary_created,
        "mean_primary_electrons_collected": mean_primary_collected,
        "mean_gas_gain": mean_gas_gain,
        "max_avalanche_charge_c": max_avalanche_charge_c,
    }


def threshold_summary(
    event_records: list[EventPulseRecord],
    threshold_v: float,
) -> dict[str, JSONValue]:
    """
    Summarize threshold crossing for a collection of event records.
    """
    if not event_records:
        raise ValueError("event_records must be non-empty.")
    if threshold_v < 0.0:
        raise ValueError(f"threshold_v must be >= 0, got {threshold_v!r}.")

    n_total = len(event_records)
    n_pass = sum(1 for event in event_records if event.peak_voltage_v >= threshold_v)
    fraction_pass = fraction_events_above_threshold(event_records, threshold_v)

    return {
        "threshold_v": threshold_v,
        "n_total": n_total,
        "n_pass": n_pass,
        "fraction_pass": fraction_pass,
    }


def summary_to_report_dict(
    summary: EventSimulationSummary,
) -> dict[str, JSONValue]:
    """
    Convert an EventSimulationSummary into a reporting-friendly dictionary.

    This helper adds a derived voltage stats block from any attached event
    records when available, while keeping the base summary intact.
    """
    if not isinstance(summary, EventSimulationSummary):
        raise TypeError(
            "summary must be an EventSimulationSummary instance, "
            f"got {type(summary).__name__}."
        )

    report: dict[str, JSONValue] = {
        "n_events": summary.n_events,
        "threshold_v": summary.threshold_v,
        "mean_peak_voltage_v": summary.mean_peak_voltage_v,
        "median_peak_voltage_v": summary.median_peak_voltage_v,
        "max_peak_voltage_v": summary.max_peak_voltage_v,
        "min_peak_voltage_v": summary.min_peak_voltage_v,
        "fraction_above_threshold": summary.fraction_above_threshold,
        "mean_primary_electrons_created": summary.mean_primary_electrons_created,
        "mean_primary_electrons_collected": summary.mean_primary_electrons_collected,
        "mean_gas_gain": summary.mean_gas_gain,
        "metadata": dict(summary.metadata),
    }

    if summary.event_records:
        report["event_record_summary"] = summarize_event_records(summary.event_records)

    return report


__all__ = [
    "VoltageStats",
    "extract_peak_voltages",
    "mean",
    "median",
    "stddev",
    "summarize_event_records",
    "summarize_peak_voltages",
    "summary_to_report_dict",
    "threshold_summary",
    "variance",
]