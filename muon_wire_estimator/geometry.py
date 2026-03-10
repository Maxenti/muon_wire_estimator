"""
Geometry and electrostatics helpers for the muon wire estimator.

This module keeps the geometry-facing logic lightweight and explicit. It
provides:

- validation helpers around the GeometryModel dataclass
- cylindrical electrostatics utilities
- track-to-wire drift distance helpers
- direct image-pulse charge partition helpers
- JSON-friendly geometry summaries

The formulas here are intentionally simple and readable. They are meant for
engineering estimates, not full field-solver replacement.
"""

from __future__ import annotations

import math
from typing import Any

from .models import GeometryModel, JSONValue


VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12


def validate_geometry(geometry: GeometryModel) -> GeometryModel:
    """
    Validate and return a geometry model.

    The dataclass itself already performs strong validation in __post_init__.
    This function exists as the public validation entrypoint for other modules.
    """
    if not isinstance(geometry, GeometryModel):
        raise TypeError(
            "geometry must be a GeometryModel instance, "
            f"got {type(geometry).__name__}."
        )
    return geometry


def cylindrical_surface_field_v_per_m(geometry: GeometryModel) -> float:
    """
    Estimate the electric field at the sense-wire surface for a cylindrical
    coaxial approximation.

    Formula
    -------
    E(a) = V / (a * ln(b / a))

    where:
    - a is the sense-wire radius
    - b is the effective outer radius
    - V is the bias voltage magnitude

    Returns
    -------
    float
        Surface electric field magnitude in V/m.
    """
    validate_geometry(geometry)
    if geometry.bias_voltage_v == 0.0:
        return 0.0
    return abs(geometry.bias_voltage_v) / (
        geometry.sense_wire_radius_m * geometry.ln_b_over_a
    )


def cylindrical_field_v_per_m(geometry: GeometryModel, radius_m: float) -> float:
    """
    Estimate the electric field magnitude at radius r in the cylindrical model.

    Formula
    -------
    E(r) = V / (r * ln(b / a))

    The radius is clamped into the physical interval [a, b].
    """
    validate_geometry(geometry)
    if radius_m <= 0.0:
        raise ValueError(f"radius_m must be > 0, got {radius_m!r}.")
    if geometry.bias_voltage_v == 0.0:
        return 0.0
    r = clamp_radius_to_geometry(geometry, radius_m)
    return abs(geometry.bias_voltage_v) / (r * geometry.ln_b_over_a)


def potential_v(geometry: GeometryModel, radius_m: float) -> float:
    """
    Estimate the cylindrical potential relative to the outer boundary.

    Convention
    ----------
    The outer radius b is taken as 0 V and the sense wire is at bias_voltage_v.

    Formula
    -------
    phi(r) = V * ln(b / r) / ln(b / a)

    where V is geometry.bias_voltage_v with sign preserved.
    """
    validate_geometry(geometry)
    if radius_m <= 0.0:
        raise ValueError(f"radius_m must be > 0, got {radius_m!r}.")
    r = clamp_radius_to_geometry(geometry, radius_m)
    return geometry.bias_voltage_v * math.log(geometry.effective_outer_radius_m / r) / (
        geometry.ln_b_over_a
    )


def clamp_radius_to_geometry(geometry: GeometryModel, radius_m: float) -> float:
    """
    Clamp a radius into the allowed cylindrical geometry interval [a, b].
    """
    validate_geometry(geometry)
    if radius_m <= geometry.sense_wire_radius_m:
        return geometry.sense_wire_radius_m
    if radius_m >= geometry.effective_outer_radius_m:
        return geometry.effective_outer_radius_m
    return radius_m


def track_radius_m(geometry: GeometryModel) -> float:
    """
    Return the track closest-approach radius clamped into the active geometry.
    """
    validate_geometry(geometry)
    return clamp_radius_to_geometry(geometry, geometry.track_closest_approach_m)


def radial_drift_distance_m(geometry: GeometryModel) -> float:
    """
    Estimate the radial electron drift distance from the track to the wire.

    This uses the track closest approach as the starting radius and returns the
    distance to the wire surface rather than to the wire center.

    Returns
    -------
    float
        Non-negative drift distance in meters.
    """
    validate_geometry(geometry)
    return max(
        0.0,
        track_radius_m(geometry) - geometry.sense_wire_radius_m,
    )


def mean_drift_path_radius_m(geometry: GeometryModel) -> float:
    """
    Return a simple characteristic radius for average-field drift estimates.

    This is the midpoint between the wire surface radius and the track radius.
    """
    validate_geometry(geometry)
    return 0.5 * (geometry.sense_wire_radius_m + track_radius_m(geometry))


def average_drift_field_v_per_m(geometry: GeometryModel) -> float:
    """
    Estimate a characteristic drift-region field using the midpoint radius.
    """
    validate_geometry(geometry)
    return cylindrical_field_v_per_m(geometry, mean_drift_path_radius_m(geometry))


def wire_capacitance_per_length_f_per_m(geometry: GeometryModel) -> float:
    """
    Estimate the capacitance per unit length of the cylindrical geometry.

    Formula
    -------
    C' = 2 * pi * epsilon0 / ln(b / a)
    """
    validate_geometry(geometry)
    return (2.0 * math.pi * VACUUM_PERMITTIVITY_F_PER_M) / geometry.ln_b_over_a


def effective_wire_capacitance_f(geometry: GeometryModel) -> float:
    """
    Estimate the total effective capacitance seen by the active length.

    If the GeometryModel already provides an explicit effective_capacitance_f
    greater than zero, that value is used. Otherwise a simple cylindrical
    capacitance-per-length estimate times active length is returned.
    """
    validate_geometry(geometry)
    if geometry.effective_capacitance_f > 0.0:
        return geometry.effective_capacitance_f
    return wire_capacitance_per_length_f_per_m(geometry) * geometry.active_length_m


def active_track_fraction(geometry: GeometryModel) -> float:
    """
    Return the fraction of the total active wire length traversed by the track.

    The track length within the active region is capped at the active length.
    """
    validate_geometry(geometry)
    traversed = min(geometry.track_length_in_active_m, geometry.active_length_m)
    return traversed / geometry.active_length_m


def direct_image_charge_sharing_factor(geometry: GeometryModel) -> float:
    """
    Estimate a simple coupling factor for the direct muon image pulse.

    This intentionally conservative helper scales the effective induced direct
    charge by both:
    - how much active wire length the track samples
    - how close the track is to the wire in logarithmic cylindrical coordinates

    The result is a dimensionless factor in [0, 1].
    """
    validate_geometry(geometry)
    radial_fraction = 1.0 - (
        math.log(track_radius_m(geometry) / geometry.sense_wire_radius_m)
        / geometry.ln_b_over_a
    )
    radial_fraction = min(1.0, max(0.0, radial_fraction))
    return radial_fraction * active_track_fraction(geometry)


def geometry_summary(geometry: GeometryModel) -> dict[str, JSONValue]:
    """
    Return a JSON-friendly summary of useful derived geometry quantities.
    """
    validate_geometry(geometry)
    return {
        "sense_wire_radius_m": geometry.sense_wire_radius_m,
        "effective_outer_radius_m": geometry.effective_outer_radius_m,
        "bias_voltage_v": geometry.bias_voltage_v,
        "track_closest_approach_m": geometry.track_closest_approach_m,
        "track_radius_m_clamped": track_radius_m(geometry),
        "active_length_m": geometry.active_length_m,
        "track_length_in_active_m": geometry.track_length_in_active_m,
        "scope_termination_ohm": geometry.scope_termination_ohm,
        "electronics_rise_time_s": geometry.electronics_rise_time_s,
        "electronics_fall_time_s": geometry.electronics_fall_time_s,
        "mean_avalanche_pulse_width_s": geometry.mean_avalanche_pulse_width_s,
        "ln_b_over_a": geometry.ln_b_over_a,
        "surface_field_v_per_m": cylindrical_surface_field_v_per_m(geometry),
        "average_drift_field_v_per_m": average_drift_field_v_per_m(geometry),
        "radial_drift_distance_m": radial_drift_distance_m(geometry),
        "wire_capacitance_per_length_f_per_m": wire_capacitance_per_length_f_per_m(
            geometry
        ),
        "effective_wire_capacitance_f": effective_wire_capacitance_f(geometry),
        "active_track_fraction": active_track_fraction(geometry),
        "direct_image_charge_sharing_factor": direct_image_charge_sharing_factor(
            geometry
        ),
        "notes": geometry.notes,
    }


def geometry_from_mapping(data: dict[str, Any]) -> GeometryModel:
    """
    Build a GeometryModel from a generic mapping.

    This is useful for CLI/config JSON loading.
    """
    if not isinstance(data, dict):
        raise TypeError(
            f"data must be a dictionary, got {type(data).__name__}."
        )
    try:
        return GeometryModel(
            sense_wire_radius_m=float(data["sense_wire_radius_m"]),
            effective_outer_radius_m=float(data["effective_outer_radius_m"]),
            bias_voltage_v=float(data["bias_voltage_v"]),
            track_closest_approach_m=float(data["track_closest_approach_m"]),
            active_length_m=float(data["active_length_m"]),
            track_length_in_active_m=float(data["track_length_in_active_m"]),
            scope_termination_ohm=float(data.get("scope_termination_ohm", 50.0)),
            electronics_rise_time_s=float(data.get("electronics_rise_time_s", 5.0e-9)),
            electronics_fall_time_s=float(data.get("electronics_fall_time_s", 20.0e-9)),
            mean_avalanche_pulse_width_s=float(
                data.get("mean_avalanche_pulse_width_s", 10.0e-9)
            ),
            effective_capacitance_f=float(data.get("effective_capacitance_f", 0.0)),
            notes=str(data.get("notes", "")),
        )
    except KeyError as exc:
        raise KeyError(
            f"Missing required geometry field: {exc.args[0]!r}."
        ) from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid geometry configuration: {exc}") from exc


__all__ = [
    "VACUUM_PERMITTIVITY_F_PER_M",
    "active_track_fraction",
    "average_drift_field_v_per_m",
    "clamp_radius_to_geometry",
    "cylindrical_field_v_per_m",
    "cylindrical_surface_field_v_per_m",
    "direct_image_charge_sharing_factor",
    "effective_wire_capacitance_f",
    "geometry_from_mapping",
    "geometry_summary",
    "mean_drift_path_radius_m",
    "potential_v",
    "radial_drift_distance_m",
    "track_radius_m",
    "validate_geometry",
    "wire_capacitance_per_length_f_per_m",
]