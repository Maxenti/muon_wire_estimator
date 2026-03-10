"""
Stochastic event-by-event simulation for the muon wire estimator.

This module provides the Level 2 realism layer on top of the deterministic
Level 1 estimator. It introduces:

- seeded reproducible event simulation
- stochastic primary ionization
- stochastic transport / survival
- stochastic gas gain
- event-level avalanche pulse prediction
- optional event-record output
- summary-statistics-ready outputs

The design keeps deterministic mean-estimate logic separate from stochastic
sampling logic while reusing the same gas, geometry, drift, gain, and pulse
concepts.

Notes
-----
This is still a surrogate estimator. The stochastic model is intended for
engineering scans and threshold-crossing studies, not microscopic Garfield++
physics. Later calibration infrastructure can replace or tune pieces of this.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .drift import estimate_collection_fraction_total
from .gain import estimate_gas_gain
from .gases import get_gas
from .geometry import validate_geometry
from .ionization import estimate_mean_ionization, estimate_primary_statistics_proxy
from .models import (
    EventPulseRecord,
    EventSimulationConfig,
    EventSimulationSummary,
    GasModel,
    GeometryModel,
    JSONValue,
)
from .pulse import build_avalanche_pulse
from .randomness import (
    SeededRNG,
    make_rng,
    sample_binomial,
    sample_gamma_gain,
    sample_poisson,
)


@dataclass(slots=True)
class StochasticEventResult:
    """
    Internal event-level stochastic result.

    This structure is intentionally simple and can be losslessly converted into
    the public EventPulseRecord dataclass.
    """

    event_index: int
    primary_electrons_created: int
    primary_electrons_collected: int
    gas_gain_sample: float
    avalanche_electrons: float
    avalanche_charge_c: float
    peak_voltage_v: float
    passed_threshold: bool
    metadata: dict[str, JSONValue]

    def to_event_record(self) -> EventPulseRecord:
        """Convert to the public EventPulseRecord dataclass."""
        return EventPulseRecord(
            event_index=self.event_index,
            primary_electrons_created=self.primary_electrons_created,
            primary_electrons_collected=self.primary_electrons_collected,
            gas_gain_sample=self.gas_gain_sample,
            avalanche_electrons=self.avalanche_electrons,
            avalanche_charge_c=self.avalanche_charge_c,
            peak_voltage_v=self.peak_voltage_v,
            passed_threshold=self.passed_threshold,
            metadata=dict(self.metadata),
        )


def resolve_gas(gas: GasModel | str) -> GasModel:
    """
    Resolve a gas model instance or built-in gas name.
    """
    if isinstance(gas, GasModel):
        return gas
    if isinstance(gas, str):
        return get_gas(gas)
    raise TypeError(f"gas must be GasModel or str, got {type(gas).__name__}.")


def _sample_primary_electrons(
    rng: SeededRNG,
    *,
    mean_primary_electrons: float,
    model_name: str,
) -> int:
    """
    Sample the number of created primary electrons for one event.

    Supported models
    ----------------
    - "poisson": Poisson(mean)
    - "gaussian_proxy": Gaussian using Fano-style width is handled upstream
      by converting back to an effective Poisson-like draw if desired

    Current Level 2 behavior intentionally keeps this conservative and simple.
    """
    if mean_primary_electrons < 0.0:
        raise ValueError(
            f"mean_primary_electrons must be >= 0, got {mean_primary_electrons!r}."
        )

    if model_name == "poisson":
        return rng.poisson(mean_primary_electrons)

    if model_name == "gaussian_proxy":
        sigma = math.sqrt(max(mean_primary_electrons, 0.0))
        sample = int(round(rng.gauss(mean_primary_electrons, sigma)))
        return max(sample, 0)

    raise ValueError(
        f"Unsupported primary_statistics_model {model_name!r}. "
        "Supported values: 'poisson', 'gaussian_proxy'."
    )


def _sample_collected_primary_electrons(
    rng: SeededRNG,
    *,
    n_created: int,
    collection_fraction: float,
    model_name: str,
) -> int:
    """
    Sample the number of primary electrons that survive/collect.

    Supported models
    ----------------
    - "binomial": Binomial(n_created, collection_fraction)
    - "mean_only_round": deterministic rounded mean
    """
    if n_created < 0:
        raise ValueError(f"n_created must be >= 0, got {n_created!r}.")
    if not 0.0 <= collection_fraction <= 1.0:
        raise ValueError(
            "collection_fraction must be in [0, 1], "
            f"got {collection_fraction!r}."
        )

    if model_name == "binomial":
        return rng.binomial(n_created, collection_fraction)

    if model_name == "mean_only_round":
        return max(int(round(n_created * collection_fraction)), 0)

    raise ValueError(
        f"Unsupported survival_statistics_model {model_name!r}. "
        "Supported values: 'binomial', 'mean_only_round'."
    )


def _sample_gas_gain(
    rng: SeededRNG,
    *,
    mean_gain: float,
    shape: float,
) -> float:
    """
    Sample a stochastic gas gain.

    The mean gain comes from the deterministic surrogate; fluctuations are added
    with a Gamma distribution so the gain remains non-negative and tunable.
    """
    if mean_gain < 0.0:
        raise ValueError(f"mean_gain must be >= 0, got {mean_gain!r}.")
    if shape <= 0.0:
        raise ValueError(f"shape must be > 0, got {shape!r}.")
    if mean_gain == 0.0:
        return 0.0
    if mean_gain == 1.0:
        # Even unity-gain mode can fluctuate if the user requests it, but in
        # practice a deterministic 1 is cleaner and more stable.
        return 1.0
    return sample_gamma_gain(
        rng.generator,
        mean_gain=mean_gain,
        shape=shape,
    )


def simulate_event(
    geometry: GeometryModel,
    gas: GasModel | str,
    sim_config: EventSimulationConfig,
    *,
    event_index: int,
    rng: SeededRNG,
    use_attachment: bool = True,
    use_gain_surrogate: bool = True,
    avalanche_pulse_width_s: float | None = None,
) -> StochasticEventResult:
    """
    Simulate one stochastic event.

    This function reuses deterministic means from Level 1, then samples around
    those means to produce an event-level avalanche pulse estimate.
    """
    if event_index < 0:
        raise ValueError(f"event_index must be >= 0, got {event_index!r}.")
    if not isinstance(sim_config, EventSimulationConfig):
        raise TypeError(
            "sim_config must be an EventSimulationConfig instance, "
            f"got {type(sim_config).__name__}."
        )

    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)

    ionization = estimate_mean_ionization(geometry, gas_model)
    mean_primary = ionization.primary_electrons_mean

    n_created = _sample_primary_electrons(
        rng,
        mean_primary_electrons=mean_primary,
        model_name=sim_config.primary_statistics_model,
    )

    collection_fraction = estimate_collection_fraction_total(
        geometry,
        gas_model,
        use_attachment=use_attachment,
    )

    n_collected = _sample_collected_primary_electrons(
        rng,
        n_created=n_created,
        collection_fraction=collection_fraction,
        model_name=sim_config.survival_statistics_model,
    )

    mean_gain = estimate_gas_gain(
        geometry,
        gas_model,
        use_gain_surrogate=use_gain_surrogate,
    )

    gain_sample = _sample_gas_gain(
        rng,
        mean_gain=mean_gain,
        shape=sim_config.gain_fluctuation_shape,
    )

    avalanche_electrons = float(n_collected) * gain_sample
    avalanche_charge_c = avalanche_electrons * 1.602176634e-19

    pulse = build_avalanche_pulse(
        avalanche_charge_c,
        geometry,
        override_width_s=avalanche_pulse_width_s,
    )
    peak_voltage = pulse.peak_voltage_v
    passed_threshold = peak_voltage >= sim_config.threshold_v

    return StochasticEventResult(
        event_index=event_index,
        primary_electrons_created=n_created,
        primary_electrons_collected=n_collected,
        gas_gain_sample=gain_sample,
        avalanche_electrons=avalanche_electrons,
        avalanche_charge_c=avalanche_charge_c,
        peak_voltage_v=peak_voltage,
        passed_threshold=passed_threshold,
        metadata={
            "threshold_v": sim_config.threshold_v,
            "gas_name": gas_model.name,
            "use_attachment": use_attachment,
            "use_gain_surrogate": use_gain_surrogate,
            "collection_fraction_mean": collection_fraction,
            "mean_gain": mean_gain,
        },
    )


def simulate_events(
    geometry: GeometryModel,
    gas: GasModel | str,
    sim_config: EventSimulationConfig,
    *,
    use_attachment: bool = True,
    use_gain_surrogate: bool = True,
    avalanche_pulse_width_s: float | None = None,
) -> list[StochasticEventResult]:
    """
    Simulate a sequence of stochastic events with deterministic seeded RNG.
    """
    if not isinstance(sim_config, EventSimulationConfig):
        raise TypeError(
            "sim_config must be an EventSimulationConfig instance, "
            f"got {type(sim_config).__name__}."
        )

    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)
    rng = make_rng(sim_config.random_seed)

    events: list[StochasticEventResult] = []
    for event_index in range(sim_config.n_events):
        event = simulate_event(
            geometry,
            gas_model,
            sim_config,
            event_index=event_index,
            rng=rng,
            use_attachment=use_attachment,
            use_gain_surrogate=use_gain_surrogate,
            avalanche_pulse_width_s=avalanche_pulse_width_s,
        )
        if sim_config.include_zero_signal_events or event.peak_voltage_v > 0.0:
            events.append(event)

    return events


def summarize_events(
    events: list[StochasticEventResult],
    sim_config: EventSimulationConfig,
    *,
    include_event_records: bool,
    metadata: dict[str, JSONValue] | None = None,
) -> EventSimulationSummary:
    """
    Convert event-level stochastic results into a public summary dataclass.
    """
    if not events:
        raise ValueError("events must be non-empty for summary generation.")
    if not isinstance(sim_config, EventSimulationConfig):
        raise TypeError(
            "sim_config must be an EventSimulationConfig instance, "
            f"got {type(sim_config).__name__}."
        )

    peak_voltages = sorted(event.peak_voltage_v for event in events)
    n_events = len(events)

    mean_peak_voltage = sum(peak_voltages) / n_events
    if n_events % 2 == 1:
        median_peak_voltage = peak_voltages[n_events // 2]
    else:
        median_peak_voltage = 0.5 * (
            peak_voltages[n_events // 2 - 1] + peak_voltages[n_events // 2]
        )

    max_peak_voltage = peak_voltages[-1]
    min_peak_voltage = peak_voltages[0]
    fraction_above_threshold = (
        sum(1 for event in events if event.passed_threshold) / n_events
    )
    mean_primary_created = (
        sum(event.primary_electrons_created for event in events) / n_events
    )
    mean_primary_collected = (
        sum(event.primary_electrons_collected for event in events) / n_events
    )
    mean_gas_gain = sum(event.gas_gain_sample for event in events) / n_events

    event_records = (
        [event.to_event_record() for event in events]
        if include_event_records
        else []
    )

    summary_metadata: dict[str, JSONValue] = {
        "random_seed": sim_config.random_seed,
        "input_n_events": sim_config.n_events,
        "retained_n_events": n_events,
        "primary_statistics_model": sim_config.primary_statistics_model,
        "survival_statistics_model": sim_config.survival_statistics_model,
        "gain_fluctuation_shape": sim_config.gain_fluctuation_shape,
    }
    if metadata:
        summary_metadata.update(metadata)

    return EventSimulationSummary(
        n_events=n_events,
        threshold_v=sim_config.threshold_v,
        mean_peak_voltage_v=mean_peak_voltage,
        median_peak_voltage_v=median_peak_voltage,
        max_peak_voltage_v=max_peak_voltage,
        min_peak_voltage_v=min_peak_voltage,
        fraction_above_threshold=fraction_above_threshold,
        mean_primary_electrons_created=mean_primary_created,
        mean_primary_electrons_collected=mean_primary_collected,
        mean_gas_gain=mean_gas_gain,
        event_records=event_records,
        metadata=summary_metadata,
    )


def simulate_and_summarize(
    geometry: GeometryModel,
    gas: GasModel | str,
    sim_config: EventSimulationConfig,
    *,
    use_attachment: bool = True,
    use_gain_surrogate: bool = True,
    avalanche_pulse_width_s: float | None = None,
) -> EventSimulationSummary:
    """
    Run the full Level 2 stochastic simulation and return a summary.
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)

    events = simulate_events(
        geometry,
        gas_model,
        sim_config,
        use_attachment=use_attachment,
        use_gain_surrogate=use_gain_surrogate,
        avalanche_pulse_width_s=avalanche_pulse_width_s,
    )

    ionization_proxy = estimate_primary_statistics_proxy(geometry, gas_model)

    return summarize_events(
        events,
        sim_config,
        include_event_records=sim_config.return_event_list,
        metadata={
            "gas_name": gas_model.name,
            "use_attachment": use_attachment,
            "use_gain_surrogate": use_gain_surrogate,
            "primary_statistics_proxy": ionization_proxy,
        },
    )


def simulation_summary_to_dict(
    summary: EventSimulationSummary,
) -> dict[str, JSONValue]:
    """
    Convert an EventSimulationSummary into a JSON-friendly dictionary.
    """
    if not isinstance(summary, EventSimulationSummary):
        raise TypeError(
            "summary must be an EventSimulationSummary instance, "
            f"got {type(summary).__name__}."
        )
    return summary.to_dict()


__all__ = [
    "StochasticEventResult",
    "resolve_gas",
    "simulate_event",
    "simulate_events",
    "simulate_and_summarize",
    "simulation_summary_to_dict",
    "summarize_events",
]