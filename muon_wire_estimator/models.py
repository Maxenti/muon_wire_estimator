"""
Core data models for the muon wire estimator package.

This module defines the stable, JSON-friendly dataclasses used across all
three estimator realism levels. The intent is to keep the package readable
and lightweight while still providing a disciplined schema for:

- geometry and gas descriptions
- deterministic mean-estimate outputs
- event simulation configuration and summaries
- calibration record structures

The package is designed to remain standard-library-only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Mapping


JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


def _ensure_positive(name: str, value: float, *, allow_zero: bool = False) -> None:
    """Validate that a numeric value is positive (or non-negative if allowed)."""
    if allow_zero:
        if value < 0.0:
            raise ValueError(f"{name} must be >= 0, got {value!r}.")
        return
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0, got {value!r}.")


def _ensure_fraction(name: str, value: float) -> None:
    """Validate that a numeric value lies in the closed interval [0, 1]."""
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}.")


def _ensure_non_empty(name: str, value: str) -> None:
    """Validate that a required string is not empty or whitespace."""
    if not value or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")


def dataclass_to_dict(value: Any) -> JSONValue:
    """
    Recursively convert supported Python values into JSON-friendly structures.

    This is intended for estimator outputs and configuration snapshots.
    """
    if is_dataclass(value):
        return {k: dataclass_to_dict(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): dataclass_to_dict(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [dataclass_to_dict(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(
        f"Unsupported value type for JSON conversion: {type(value).__name__}"
    )


@dataclass(slots=True)
class GeometryModel:
    """
    Geometric/electrical description of the single-wire problem.

    Distances are expressed in meters unless explicitly labeled otherwise.
    The model is intentionally generic so that future files can use either a
    simple cylindrical effective geometry or more specialized approximations.
    """

    sense_wire_radius_m: float
    effective_outer_radius_m: float
    bias_voltage_v: float
    track_closest_approach_m: float
    active_length_m: float
    track_length_in_active_m: float
    scope_termination_ohm: float = 50.0
    electronics_rise_time_s: float = 5.0e-9
    electronics_fall_time_s: float = 20.0e-9
    mean_avalanche_pulse_width_s: float = 10.0e-9
    effective_capacitance_f: float = 0.0
    notes: str = ""

    def __post_init__(self) -> None:
        _ensure_positive("sense_wire_radius_m", self.sense_wire_radius_m)
        _ensure_positive("effective_outer_radius_m", self.effective_outer_radius_m)
        if self.effective_outer_radius_m <= self.sense_wire_radius_m:
            raise ValueError(
                "effective_outer_radius_m must exceed sense_wire_radius_m."
            )
        _ensure_positive("track_closest_approach_m", self.track_closest_approach_m)
        _ensure_positive("active_length_m", self.active_length_m)
        _ensure_positive("track_length_in_active_m", self.track_length_in_active_m)
        _ensure_positive("scope_termination_ohm", self.scope_termination_ohm)
        _ensure_positive("electronics_rise_time_s", self.electronics_rise_time_s)
        _ensure_positive("electronics_fall_time_s", self.electronics_fall_time_s)
        _ensure_positive(
            "mean_avalanche_pulse_width_s", self.mean_avalanche_pulse_width_s
        )
        _ensure_positive("effective_capacitance_f", self.effective_capacitance_f, allow_zero=True)

    @property
    def ln_b_over_a(self) -> float:
        """Return ln(b/a) for cylindrical field approximations."""
        import math

        return math.log(self.effective_outer_radius_m / self.sense_wire_radius_m)

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]


@dataclass(slots=True)
class GasModel:
    """
    Effective gas description for deterministic and stochastic estimation.

    The parameters are deliberately phenomenological rather than claiming
    microscopic Garfield++ accuracy. They are meant to support a useful,
    modular estimator that can later be calibrated.

    Attributes
    ----------
    w_value_ev:
        Effective mean energy required to produce one electron-ion pair.
    mean_energy_loss_mev_per_cm:
        Effective average muon energy loss in the medium.
    drift_velocity_m_per_s:
        Characteristic electron drift velocity used for rough timing.
    attachment_time_s:
        Mean attachment lifetime. None means effectively no attachment loss.
    collection_efficiency:
        Additional collection factor representing non-attachment transport losses.
    gain_field_scale_v_per_m:
        Characteristic field scale controlling onset of avalanche gain surrogate.
    gain_slope:
        Dimensionless slope parameter controlling how rapidly gain rises.
    gain_cap:
        Hard upper cap on surrogate mean gas gain.
    """
    name: str
    pressure_atm: float
    temperature_k: float
    w_value_ev: float
    mean_energy_loss_mev_per_cm: float
    drift_velocity_m_per_s: float
    attachment_time_s: float | None = None
    collection_efficiency: float = 1.0
    gain_field_scale_v_per_m: float = 5.0e6
    gain_slope: float = 0.7
    gain_cap: float = 1.0e5
    fano_factor: float = 0.2
    mean_cluster_size_electrons: float = 2.0
    notes: str = ""

    def __post_init__(self) -> None:
        _ensure_non_empty("name", self.name)
        _ensure_positive("pressure_atm", self.pressure_atm)
        _ensure_positive("temperature_k", self.temperature_k)
        _ensure_positive("w_value_ev", self.w_value_ev)
        _ensure_positive(
            "mean_energy_loss_mev_per_cm", self.mean_energy_loss_mev_per_cm
        )
        _ensure_positive("drift_velocity_m_per_s", self.drift_velocity_m_per_s)
        if self.attachment_time_s is not None:
            _ensure_positive("attachment_time_s", self.attachment_time_s)
        _ensure_fraction("collection_efficiency", self.collection_efficiency)
        _ensure_positive("gain_field_scale_v_per_m", self.gain_field_scale_v_per_m)
        _ensure_positive("gain_slope", self.gain_slope)
        _ensure_positive("gain_cap", self.gain_cap)
        _ensure_positive("fano_factor", self.fano_factor, allow_zero=True)
        _ensure_positive(
            "mean_cluster_size_electrons", self.mean_cluster_size_electrons
        )

    @property
    def has_attachment(self) -> bool:
        """Return True if the gas uses a finite attachment lifetime."""
        return self.attachment_time_s is not None

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]


@dataclass(slots=True)
class PulseEstimate:
    """
    Compact description of an electrical pulse estimate.

    This can represent the direct muon image pulse or the gas-avalanche pulse.
    All charge/current/voltage quantities use SI units.
    """

    charge_c: float
    peak_current_a: float
    peak_voltage_v: float
    width_s: float
    rise_time_s: float
    fall_time_s: float
    termination_ohm: float
    model_name: str
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_positive("width_s", self.width_s)
        _ensure_positive("rise_time_s", self.rise_time_s)
        _ensure_positive("fall_time_s", self.fall_time_s)
        _ensure_positive("termination_ohm", self.termination_ohm)
        _ensure_non_empty("model_name", self.model_name)
        if self.charge_c < 0.0:
            raise ValueError(f"charge_c must be >= 0, got {self.charge_c!r}.")
        if self.peak_current_a < 0.0:
            raise ValueError(
                f"peak_current_a must be >= 0, got {self.peak_current_a!r}."
            )
        if self.peak_voltage_v < 0.0:
            raise ValueError(
                f"peak_voltage_v must be >= 0, got {self.peak_voltage_v!r}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]


@dataclass(slots=True)
class EstimatorConfig:
    """
    Top-level deterministic estimator configuration.

    This structure keeps the direct image-pulse path distinct from the
    avalanche path and provides toggles for mean-estimate calculations.
    """

    geometry: GeometryModel
    gas_name: str = "air_dry_1atm"
    include_direct_image_pulse: bool = True
    include_avalanche_signal: bool = True
    use_attachment: bool = True
    use_gain_surrogate: bool = True
    direct_charge_efficiency: float = 1.0
    avalanche_pulse_width_s: float | None = None
    output_event_details: bool = False
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("gas_name", self.gas_name)
        _ensure_fraction("direct_charge_efficiency", self.direct_charge_efficiency)
        if self.avalanche_pulse_width_s is not None:
            _ensure_positive("avalanche_pulse_width_s", self.avalanche_pulse_width_s)

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]


@dataclass(slots=True)
class DeterministicEstimate:
    """
    Mean-estimate output for a single configuration.

    The `direct_pulse` block and `avalanche_pulse` block are intentionally
    separated so users can compare the ordinary gas avalanche signal against
    the much smaller direct image-pulse picture.
    """

    estimator_version: str
    geometry: GeometryModel
    gas: GasModel
    created_primary_electrons_mean: float
    collected_primary_electrons_mean: float
    drift_time_s: float
    attachment_survival_fraction: float
    collection_fraction_total: float
    gas_gain_mean: float
    avalanche_electrons_mean: float
    avalanche_charge_c: float
    direct_pulse: PulseEstimate | None
    avalanche_pulse: PulseEstimate | None
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("estimator_version", self.estimator_version)
        _ensure_positive(
            "created_primary_electrons_mean",
            self.created_primary_electrons_mean,
            allow_zero=True,
        )
        _ensure_positive(
            "collected_primary_electrons_mean",
            self.collected_primary_electrons_mean,
            allow_zero=True,
        )
        _ensure_positive("drift_time_s", self.drift_time_s, allow_zero=True)
        _ensure_fraction(
            "attachment_survival_fraction", self.attachment_survival_fraction
        )
        _ensure_fraction("collection_fraction_total", self.collection_fraction_total)
        _ensure_positive("gas_gain_mean", self.gas_gain_mean, allow_zero=True)
        _ensure_positive(
            "avalanche_electrons_mean", self.avalanche_electrons_mean, allow_zero=True
        )
        _ensure_positive("avalanche_charge_c", self.avalanche_charge_c, allow_zero=True)

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]


@dataclass(slots=True)
class EventSimulationConfig:
    """
    Configuration for Level 2 repeated event simulation.

    This controls stochastic sampling of primary ionization, transport,
    avalanche gain, and threshold-crossing calculations.
    """

    n_events: int = 1000
    random_seed: int = 12345
    threshold_v: float = 1.0e-3
    return_event_list: bool = False
    include_zero_signal_events: bool = True
    gain_fluctuation_shape: float = 1.0
    primary_statistics_model: str = "poisson"
    survival_statistics_model: str = "binomial"

    def __post_init__(self) -> None:
        if self.n_events <= 0:
            raise ValueError(f"n_events must be > 0, got {self.n_events!r}.")
        if self.threshold_v < 0.0:
            raise ValueError(f"threshold_v must be >= 0, got {self.threshold_v!r}.")
        _ensure_positive(
            "gain_fluctuation_shape", self.gain_fluctuation_shape, allow_zero=False
        )
        _ensure_non_empty("primary_statistics_model", self.primary_statistics_model)
        _ensure_non_empty("survival_statistics_model", self.survival_statistics_model)

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]


@dataclass(slots=True)
class EventPulseRecord:
    """
    Per-event stochastic result for Level 2 simulations.
    """

    event_index: int
    primary_electrons_created: int
    primary_electrons_collected: int
    gas_gain_sample: float
    avalanche_electrons: float
    avalanche_charge_c: float
    peak_voltage_v: float
    passed_threshold: bool
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.event_index < 0:
            raise ValueError(
                f"event_index must be >= 0, got {self.event_index!r}."
            )
        if self.primary_electrons_created < 0:
            raise ValueError(
                "primary_electrons_created must be >= 0, "
                f"got {self.primary_electrons_created!r}."
            )
        if self.primary_electrons_collected < 0:
            raise ValueError(
                "primary_electrons_collected must be >= 0, "
                f"got {self.primary_electrons_collected!r}."
            )
        if self.gas_gain_sample < 0.0:
            raise ValueError(
                f"gas_gain_sample must be >= 0, got {self.gas_gain_sample!r}."
            )
        if self.avalanche_electrons < 0.0:
            raise ValueError(
                f"avalanche_electrons must be >= 0, got {self.avalanche_electrons!r}."
            )
        if self.avalanche_charge_c < 0.0:
            raise ValueError(
                f"avalanche_charge_c must be >= 0, got {self.avalanche_charge_c!r}."
            )
        if self.peak_voltage_v < 0.0:
            raise ValueError(
                f"peak_voltage_v must be >= 0, got {self.peak_voltage_v!r}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]


@dataclass(slots=True)
class EventSimulationSummary:
    """
    Aggregate summary for repeated event simulation.
    """

    n_events: int
    threshold_v: float
    mean_peak_voltage_v: float
    median_peak_voltage_v: float
    max_peak_voltage_v: float
    min_peak_voltage_v: float
    fraction_above_threshold: float
    mean_primary_electrons_created: float
    mean_primary_electrons_collected: float
    mean_gas_gain: float
    event_records: list[EventPulseRecord] = field(default_factory=list)
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.n_events <= 0:
            raise ValueError(f"n_events must be > 0, got {self.n_events!r}.")
        if self.threshold_v < 0.0:
            raise ValueError(f"threshold_v must be >= 0, got {self.threshold_v!r}.")
        if self.mean_peak_voltage_v < 0.0:
            raise ValueError("mean_peak_voltage_v must be >= 0.")
        if self.median_peak_voltage_v < 0.0:
            raise ValueError("median_peak_voltage_v must be >= 0.")
        if self.max_peak_voltage_v < 0.0:
            raise ValueError("max_peak_voltage_v must be >= 0.")
        if self.min_peak_voltage_v < 0.0:
            raise ValueError("min_peak_voltage_v must be >= 0.")
        _ensure_fraction("fraction_above_threshold", self.fraction_above_threshold)
        if self.mean_primary_electrons_created < 0.0:
            raise ValueError("mean_primary_electrons_created must be >= 0.")
        if self.mean_primary_electrons_collected < 0.0:
            raise ValueError("mean_primary_electrons_collected must be >= 0.")
        if self.mean_gas_gain < 0.0:
            raise ValueError("mean_gas_gain must be >= 0.")

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]


@dataclass(slots=True)
class CalibrationRecord:
    """
    Level 3 calibration schema.

    This record supports partial overrides of default surrogate behavior.
    Future Garfield++-derived parameterizations can populate the same
    structure without changing the package's public interface.
    """

    calibration_name: str
    version: str
    source: str
    applies_to_gas: str | None = None
    gas_overrides: dict[str, JSONValue] = field(default_factory=dict)
    gain_overrides: dict[str, JSONValue] = field(default_factory=dict)
    drift_overrides: dict[str, JSONValue] = field(default_factory=dict)
    pulse_overrides: dict[str, JSONValue] = field(default_factory=dict)
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("calibration_name", self.calibration_name)
        _ensure_non_empty("version", self.version)
        _ensure_non_empty("source", self.source)
        if self.applies_to_gas is not None and not self.applies_to_gas.strip():
            raise ValueError("applies_to_gas must be None or a non-empty string.")

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]


def merge_mappings(
    base: Mapping[str, JSONValue], override: Mapping[str, JSONValue]
) -> dict[str, JSONValue]:
    """
    Shallow merge two JSON-like mappings, with override values taking precedence.
    """
    merged: dict[str, JSONValue] = dict(base)
    merged.update(override)
    return merged