"""
Pulse-shape and readout conversion helpers for the muon wire estimator.

This module translates charge estimates into compact electrical pulse estimates.
It intentionally keeps the two signal paths separate:

- direct muon image pulse
- ordinary gas-avalanche pulse

The Level 1 goal is a simple, readable conversion from charge to:

- peak current
- peak voltage into a termination
- pulse width metadata

The model is intentionally lightweight. It does not attempt a full electronics
transfer function or full Shockley-Ramo current evolution. Instead, it provides
a finite-width pulse estimate suitable for engineering comparisons against
oscilloscope sensitivity and threshold levels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .geometry import effective_wire_capacitance_f, validate_geometry
from .models import GeometryModel, JSONValue, PulseEstimate


@dataclass(slots=True)
class PulseComputation:
    """
    Internal pulse-computation helper structure.

    Attributes
    ----------
    charge_c:
        Input charge in Coulombs.
    effective_width_s:
        Effective pulse width used to estimate peak current.
    peak_current_a:
        Estimated peak current.
    peak_voltage_v:
        Estimated peak voltage across the termination.
    metadata:
        JSON-friendly supporting details.
    """

    charge_c: float
    effective_width_s: float
    peak_current_a: float
    peak_voltage_v: float
    metadata: dict[str, JSONValue]

    def __post_init__(self) -> None:
        if self.charge_c < 0.0:
            raise ValueError(f"charge_c must be >= 0, got {self.charge_c!r}.")
        if self.effective_width_s <= 0.0:
            raise ValueError(
                f"effective_width_s must be > 0, got {self.effective_width_s!r}."
            )
        if self.peak_current_a < 0.0:
            raise ValueError(
                f"peak_current_a must be >= 0, got {self.peak_current_a!r}."
            )
        if self.peak_voltage_v < 0.0:
            raise ValueError(
                f"peak_voltage_v must be >= 0, got {self.peak_voltage_v!r}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "charge_c": self.charge_c,
            "effective_width_s": self.effective_width_s,
            "peak_current_a": self.peak_current_a,
            "peak_voltage_v": self.peak_voltage_v,
            "metadata": dict(self.metadata),
        }


def pulse_width_s(
    geometry: GeometryModel,
    *,
    override_width_s: float | None = None,
) -> float:
    """
    Return the pulse width used for peak-current estimation.

    If an override width is provided, it is used directly. Otherwise the
    geometry's mean avalanche pulse width is used.
    """
    validate_geometry(geometry)
    if override_width_s is not None:
        if override_width_s <= 0.0:
            raise ValueError(
                f"override_width_s must be > 0, got {override_width_s!r}."
            )
        return override_width_s
    return geometry.mean_avalanche_pulse_width_s


def rc_time_constant_s(geometry: GeometryModel) -> float:
    """
    Estimate a simple RC time constant from effective wire capacitance and load.

    This is not used as the sole pulse-width model, but is reported in metadata
    because it is physically informative for scope/readout interpretation.
    """
    validate_geometry(geometry)
    return effective_wire_capacitance_f(geometry) * geometry.scope_termination_ohm


def effective_pulse_width_s(
    geometry: GeometryModel,
    *,
    override_width_s: float | None = None,
) -> float:
    """
    Estimate an effective pulse width for peak-current conversion.

    The model combines:
    - chosen intrinsic pulse width
    - electronics rise/fall timing
    - a simple RC load contribution

    in quadrature to avoid underestimating width when several effects compete.
    """
    validate_geometry(geometry)

    intrinsic = pulse_width_s(geometry, override_width_s=override_width_s)
    rise = geometry.electronics_rise_time_s
    fall = geometry.electronics_fall_time_s
    rc_tau = rc_time_constant_s(geometry)

    return math.sqrt(
        intrinsic * intrinsic
        + rise * rise
        + fall * fall
        + rc_tau * rc_tau
    )


def peak_current_a(
    charge_c: float,
    geometry: GeometryModel,
    *,
    override_width_s: float | None = None,
) -> float:
    """
    Estimate peak current from charge and effective pulse width.

    Model
    -----
    I_peak ≈ Q / t_eff

    This is a simple finite-width engineering estimate, not a detailed shaped
    waveform model.
    """
    validate_geometry(geometry)
    if charge_c < 0.0:
        raise ValueError(f"charge_c must be >= 0, got {charge_c!r}.")
    if charge_c == 0.0:
        return 0.0

    width = effective_pulse_width_s(geometry, override_width_s=override_width_s)
    return charge_c / width


def peak_voltage_v(
    peak_current_a_value: float,
    geometry: GeometryModel,
) -> float:
    """
    Estimate peak voltage across the termination from peak current.

    Model
    -----
    V_peak ≈ I_peak * R_term
    """
    validate_geometry(geometry)
    if peak_current_a_value < 0.0:
        raise ValueError(
            "peak_current_a_value must be >= 0, "
            f"got {peak_current_a_value!r}."
        )
    return peak_current_a_value * geometry.scope_termination_ohm


def compute_pulse(
    charge_c: float,
    geometry: GeometryModel,
    *,
    override_width_s: float | None = None,
    model_name: str,
    extra_metadata: dict[str, JSONValue] | None = None,
) -> PulseComputation:
    """
    Compute peak current and voltage for a charge packet.
    """
    validate_geometry(geometry)
    if not model_name or not model_name.strip():
        raise ValueError("model_name must be a non-empty string.")
    if charge_c < 0.0:
        raise ValueError(f"charge_c must be >= 0, got {charge_c!r}.")

    width = effective_pulse_width_s(geometry, override_width_s=override_width_s)
    current = peak_current_a(charge_c, geometry, override_width_s=override_width_s)
    voltage = peak_voltage_v(current, geometry)

    metadata: dict[str, JSONValue] = {
        "termination_ohm": geometry.scope_termination_ohm,
        "intrinsic_width_s": pulse_width_s(geometry, override_width_s=override_width_s),
        "effective_width_s": width,
        "electronics_rise_time_s": geometry.electronics_rise_time_s,
        "electronics_fall_time_s": geometry.electronics_fall_time_s,
        "effective_wire_capacitance_f": effective_wire_capacitance_f(geometry),
        "rc_time_constant_s": rc_time_constant_s(geometry),
        "model_name": model_name,
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    return PulseComputation(
        charge_c=charge_c,
        effective_width_s=width,
        peak_current_a=current,
        peak_voltage_v=voltage,
        metadata=metadata,
    )


def build_pulse_estimate(
    charge_c: float,
    geometry: GeometryModel,
    *,
    override_width_s: float | None = None,
    model_name: str,
    extra_metadata: dict[str, JSONValue] | None = None,
) -> PulseEstimate:
    """
    Build the public PulseEstimate dataclass from a charge packet.
    """
    geometry = validate_geometry(geometry)
    computed = compute_pulse(
        charge_c,
        geometry,
        override_width_s=override_width_s,
        model_name=model_name,
        extra_metadata=extra_metadata,
    )

    return PulseEstimate(
        charge_c=charge_c,
        peak_current_a=computed.peak_current_a,
        peak_voltage_v=computed.peak_voltage_v,
        width_s=computed.effective_width_s,
        rise_time_s=geometry.electronics_rise_time_s,
        fall_time_s=geometry.electronics_fall_time_s,
        termination_ohm=geometry.scope_termination_ohm,
        model_name=model_name,
        metadata=computed.metadata,
    )


def build_direct_image_pulse(
    direct_charge_c: float,
    geometry: GeometryModel,
) -> PulseEstimate:
    """
    Build a PulseEstimate for the direct muon image pulse.

    The direct path uses the same lightweight readout conversion but keeps a
    distinct model label and slightly richer metadata so downstream outputs can
    remain clearly separated.
    """
    return build_pulse_estimate(
        direct_charge_c,
        geometry,
        model_name="direct_muon_image_pulse",
        extra_metadata={"signal_family": "direct"},
    )


def build_avalanche_pulse(
    avalanche_charge_c: float,
    geometry: GeometryModel,
    *,
    override_width_s: float | None = None,
) -> PulseEstimate:
    """
    Build a PulseEstimate for the ordinary gas-avalanche signal.
    """
    return build_pulse_estimate(
        avalanche_charge_c,
        geometry,
        override_width_s=override_width_s,
        model_name="gas_avalanche_pulse",
        extra_metadata={"signal_family": "avalanche"},
    )


def pulse_summary(
    charge_c: float,
    geometry: GeometryModel,
    *,
    override_width_s: float | None = None,
    model_name: str,
    extra_metadata: dict[str, JSONValue] | None = None,
) -> dict[str, JSONValue]:
    """
    Return a JSON-friendly pulse summary.
    """
    pulse = build_pulse_estimate(
        charge_c,
        geometry,
        override_width_s=override_width_s,
        model_name=model_name,
        extra_metadata=extra_metadata,
    )
    return pulse.to_dict()


__all__ = [
    "PulseComputation",
    "build_avalanche_pulse",
    "build_direct_image_pulse",
    "build_pulse_estimate",
    "compute_pulse",
    "effective_pulse_width_s",
    "peak_current_a",
    "peak_voltage_v",
    "pulse_summary",
    "pulse_width_s",
    "rc_time_constant_s",
]