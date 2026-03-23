from __future__ import annotations

"""
Source-to-detector geometry helpers for particle-source ionization estimates.

This module defines a lightweight geometry layer describing how a particle
source sits relative to the active gas region around a single wire. It is
intended to be used by source-side models such as:

- cosmic muon approximations
- Sr-90 / Y-90 beta source approximations

Scope
-----
The goal is not full transport Monte Carlo. Instead, this module provides
explicit, transparent geometry surrogates that answer questions like:

- how far is the source from the active region?
- is the source collimated?
- what active path length should be used?
- what is the approximate source-side probability that a particle enters the
  active gas region?

These source-side geometry factors are distinct from downstream detector
transport quantities such as drift time, attachment survival, gas gain, and
pulse shaping.

Design goals
------------
- standard-library only
- deterministic
- JSON-friendly
- easy to calibrate later
- usable by both deterministic and stochastic source models

Units
-----
- distances are expressed in mm or cm only when explicit in field names
- internal path-length outputs are provided in cm where convenient for
  deposited-energy calculations
"""

import math
from dataclasses import dataclass, field
from typing import Any, Literal


JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


SourcePlacementModel = Literal[
    "point_isotropic",
    "point_collimated",
    "planar_collimated",
]

TrackLengthModel = Literal[
    "fixed_length",
    "projected_length",
    "range_limited",
]


def _ensure_positive(name: str, value: float, *, allow_zero: bool = False) -> None:
    if allow_zero:
        if value < 0.0:
            raise ValueError(f"{name} must be >= 0, got {value!r}.")
        return
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0, got {value!r}.")


def _ensure_fraction(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}.")


def _ensure_literal(name: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of {{{allowed_text}}}, got {value!r}.")


def _json_safe_mapping(value: dict[str, Any] | None) -> dict[str, JSONValue]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"metadata must be a dictionary, got {type(value).__name__}.")
    out: dict[str, JSONValue] = {}
    for key, item in value.items():
        out[str(key)] = _json_safe_value(item, path=str(key))
    return out


def _json_safe_value(value: Any, *, path: str) -> JSONValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_json_safe_value(v, path=f"{path}[]") for v in value]
    if isinstance(value, tuple):
        return [_json_safe_value(v, path=f"{path}[]") for v in value]
    if isinstance(value, dict):
        return {
            str(k): _json_safe_value(v, path=f"{path}.{k}")
            for k, v in value.items()
        }
    raise TypeError(
        f"Unsupported metadata value type at {path!r}: {type(value).__name__}."
    )


@dataclass(slots=True)
class SourceGeometryConfig:
    """
    Geometry description of a particle source relative to the active gas region.

    Parameters
    ----------
    source_distance_mm:
        Distance from the source to the nominal active region / wire vicinity.
    placement_model:
        Coarse source-placement model controlling acceptance behavior.
    collimated:
        Whether the source is treated as directionally constrained.
    angular_spread_deg:
        Half-angle spread for the source emission cone.
    incidence_angle_deg:
        Central incidence angle relative to the active-region normal.
    active_region_thickness_mm:
        Characteristic thickness of the active gas region traversed by the
        source particle if it enters the detector.
    fixed_track_length_cm:
        Used when track_length_model == "fixed_length".
    track_length_model:
        Rule for converting geometry into an effective active track length.
    active_region_entry_probability:
        Optional extra multiplicative factor accounting for apertures, source
        masking, trigger geometry, or simple acceptance effects.
    notes:
        Optional descriptive note.
    metadata:
        JSON-friendly metadata for provenance.
    """

    source_distance_mm: float
    placement_model: SourcePlacementModel = "point_isotropic"
    collimated: bool = False
    angular_spread_deg: float = 90.0
    incidence_angle_deg: float = 0.0
    active_region_thickness_mm: float = 5.0
    fixed_track_length_cm: float = 0.5
    track_length_model: TrackLengthModel = "range_limited"
    active_region_entry_probability: float = 1.0
    notes: str = ""
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_positive("source_distance_mm", self.source_distance_mm, allow_zero=True)
        _ensure_literal(
            "placement_model",
            self.placement_model,
            {"point_isotropic", "point_collimated", "planar_collimated"},
        )
        _ensure_positive("angular_spread_deg", self.angular_spread_deg, allow_zero=True)
        _ensure_positive(
            "active_region_thickness_mm",
            self.active_region_thickness_mm,
            allow_zero=True,
        )
        _ensure_positive(
            "fixed_track_length_cm",
            self.fixed_track_length_cm,
            allow_zero=True,
        )
        _ensure_literal(
            "track_length_model",
            self.track_length_model,
            {"fixed_length", "projected_length", "range_limited"},
        )
        _ensure_fraction(
            "active_region_entry_probability",
            self.active_region_entry_probability,
        )
        if not isinstance(self.incidence_angle_deg, (int, float)):
            raise TypeError(
                "incidence_angle_deg must be numeric, "
                f"got {type(self.incidence_angle_deg).__name__}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "source_distance_mm": self.source_distance_mm,
            "placement_model": self.placement_model,
            "collimated": self.collimated,
            "angular_spread_deg": self.angular_spread_deg,
            "incidence_angle_deg": self.incidence_angle_deg,
            "active_region_thickness_mm": self.active_region_thickness_mm,
            "fixed_track_length_cm": self.fixed_track_length_cm,
            "track_length_model": self.track_length_model,
            "active_region_entry_probability": self.active_region_entry_probability,
            "notes": self.notes,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class SourceGeometrySummary:
    """
    Derived source-geometry summary suitable for reporting/debugging.

    Parameters
    ----------
    source_distance_mm:
        Input source distance.
    active_path_length_cm:
        Effective active path length used by the source model.
    geometric_acceptance_factor:
        Pure geometry/placement acceptance factor.
    source_survival_to_active_region_probability:
        Total source-side probability to contribute to the active region.
    metadata:
        JSON-friendly intermediate values.
    """

    source_distance_mm: float
    active_path_length_cm: float
    geometric_acceptance_factor: float
    source_survival_to_active_region_probability: float
    metadata: dict[str, JSONValue]

    def __post_init__(self) -> None:
        _ensure_positive("source_distance_mm", self.source_distance_mm, allow_zero=True)
        _ensure_positive("active_path_length_cm", self.active_path_length_cm, allow_zero=True)
        _ensure_fraction("geometric_acceptance_factor", self.geometric_acceptance_factor)
        _ensure_fraction(
            "source_survival_to_active_region_probability",
            self.source_survival_to_active_region_probability,
        )

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "source_distance_mm": self.source_distance_mm,
            "active_path_length_cm": self.active_path_length_cm,
            "geometric_acceptance_factor": self.geometric_acceptance_factor,
            "source_survival_to_active_region_probability": (
                self.source_survival_to_active_region_probability
            ),
            "metadata": dict(self.metadata),
        }


def _cosd(angle_deg: float) -> float:
    return math.cos(math.radians(angle_deg))


def geometric_acceptance_factor(source_geometry: SourceGeometryConfig) -> float:
    """
    Estimate a coarse geometry/placement acceptance factor in [0, 1].

    Interpretation
    --------------
    This is a source-side factor describing how likely it is that a particle
    emitted from the source geometry actually enters the active gas region.

    Surrogate rules
    ---------------
    - planar_collimated:
        accept the configured entry probability directly
    - point_collimated:
        use the entry probability, mildly reduced by incidence mismatch
    - point_isotropic:
        apply an isotropic solid-angle surrogate scaled by incidence alignment

    The isotropic surrogate is intentionally simple:
        acceptance ~ 0.5 * (1 + cos(theta_spread))
    when the source is forward-facing, then modulated by incidence angle.
    """
    if not isinstance(source_geometry, SourceGeometryConfig):
        raise TypeError(
            "source_geometry must be SourceGeometryConfig, "
            f"got {type(source_geometry).__name__}."
        )

    base = source_geometry.active_region_entry_probability
    incidence_alignment = max(_cosd(source_geometry.incidence_angle_deg), 0.0)

    if source_geometry.placement_model == "planar_collimated":
        return min(1.0, max(0.0, base))

    if source_geometry.placement_model == "point_collimated":
        spread_factor = max(_cosd(source_geometry.angular_spread_deg), 0.0)
        acceptance = base * max(incidence_alignment, spread_factor)
        return min(1.0, max(0.0, acceptance))

    # point_isotropic
    spread_half_angle_deg = min(max(source_geometry.angular_spread_deg, 0.0), 180.0)
    isotropic_cone_factor = 0.5 * (1.0 - _cosd(spread_half_angle_deg))
    # If the source is "fully isotropic" with 180 deg half-angle, this reaches 1.
    acceptance = base * isotropic_cone_factor * max(incidence_alignment, 0.25)
    return min(1.0, max(0.0, acceptance))


def projected_active_path_length_cm(source_geometry: SourceGeometryConfig) -> float:
    """
    Estimate active path length through the gas using a projected-thickness model.

    Formula
    -------
    path_length = thickness / max(cos(theta), floor)

    where theta is the incidence angle relative to the active-region normal.
    """
    if not isinstance(source_geometry, SourceGeometryConfig):
        raise TypeError(
            "source_geometry must be SourceGeometryConfig, "
            f"got {type(source_geometry).__name__}."
        )

    thickness_cm = source_geometry.active_region_thickness_mm * 0.1
    if thickness_cm == 0.0:
        return 0.0

    cos_theta = abs(_cosd(source_geometry.incidence_angle_deg))
    cos_floor = 0.05
    effective_cos = max(cos_theta, cos_floor)
    return thickness_cm / effective_cos


def active_path_length_cm(source_geometry: SourceGeometryConfig) -> float:
    """
    Return the effective active gas path length in cm.

    Supported models
    ----------------
    fixed_length:
        use fixed_track_length_cm directly
    projected_length:
        use projected thickness through the active region
    range_limited:
        use the smaller of fixed_track_length_cm and projected_length

    The `range_limited` model is a simple way to acknowledge that finite-range
    particles may not fully realize arbitrarily long projected paths.
    """
    if not isinstance(source_geometry, SourceGeometryConfig):
        raise TypeError(
            "source_geometry must be SourceGeometryConfig, "
            f"got {type(source_geometry).__name__}."
        )

    if source_geometry.track_length_model == "fixed_length":
        return source_geometry.fixed_track_length_cm

    projected = projected_active_path_length_cm(source_geometry)
    if source_geometry.track_length_model == "projected_length":
        return projected

    # range_limited
    return min(source_geometry.fixed_track_length_cm, projected)


def source_survival_to_active_region_probability(
    source_geometry: SourceGeometryConfig,
) -> float:
    """
    Return the total source-side probability that the particle contributes to
    the active region.

    At the current surrogate level, this is just the geometric acceptance
    factor. The function is kept separate so later versions can fold in source
    window losses, air gaps, absorber foils, or range limits outside the active
    volume without changing downstream call sites.
    """
    return geometric_acceptance_factor(source_geometry)


def summarize_source_geometry(
    source_geometry: SourceGeometryConfig,
) -> SourceGeometrySummary:
    """
    Build a derived source-geometry summary.
    """
    if not isinstance(source_geometry, SourceGeometryConfig):
        raise TypeError(
            "source_geometry must be SourceGeometryConfig, "
            f"got {type(source_geometry).__name__}."
        )

    acceptance = geometric_acceptance_factor(source_geometry)
    path_length = active_path_length_cm(source_geometry)
    survival = source_survival_to_active_region_probability(source_geometry)

    metadata: dict[str, JSONValue] = {
        "projected_active_path_length_cm": projected_active_path_length_cm(source_geometry),
        "incidence_cosine_abs": abs(_cosd(source_geometry.incidence_angle_deg)),
        "placement_model": source_geometry.placement_model,
        "track_length_model": source_geometry.track_length_model,
    }

    return SourceGeometrySummary(
        source_distance_mm=source_geometry.source_distance_mm,
        active_path_length_cm=path_length,
        geometric_acceptance_factor=acceptance,
        source_survival_to_active_region_probability=survival,
        metadata=metadata,
    )


def source_geometry_from_mapping(data: dict[str, Any]) -> SourceGeometryConfig:
    """
    Construct SourceGeometryConfig from a mapping.

    Accepted keys
    -------------
    Required:
    - source_distance_mm

    Optional:
    - placement_model
    - collimated
    - angular_spread_deg
    - incidence_angle_deg
    - active_region_thickness_mm
    - fixed_track_length_cm
    - track_length_model
    - active_region_entry_probability
    - notes
    - metadata

    Aliases
    -------
    A few user-friendly aliases are also accepted:
    - source_to_wire_distance_mm -> source_distance_mm
    - active_thickness_mm -> active_region_thickness_mm
    - path_length_cm -> fixed_track_length_cm
    """
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dictionary, got {type(data).__name__}.")

    if "source_distance_mm" in data:
        source_distance_mm = float(data["source_distance_mm"])
    elif "source_to_wire_distance_mm" in data:
        source_distance_mm = float(data["source_to_wire_distance_mm"])
    else:
        raise KeyError(
            "Missing required field 'source_distance_mm' "
            "(or alias 'source_to_wire_distance_mm')."
        )

    active_region_thickness_mm_raw = (
        data["active_region_thickness_mm"]
        if "active_region_thickness_mm" in data
        else data.get("active_thickness_mm", 5.0)
    )

    fixed_track_length_cm_raw = (
        data["fixed_track_length_cm"]
        if "fixed_track_length_cm" in data
        else data.get("path_length_cm", 0.5)
    )

    metadata_raw = data.get("metadata")
    metadata = _json_safe_mapping(metadata_raw)

    return SourceGeometryConfig(
        source_distance_mm=source_distance_mm,
        placement_model=str(data.get("placement_model", "point_isotropic")),  # type: ignore[arg-type]
        collimated=bool(data.get("collimated", False)),
        angular_spread_deg=float(data.get("angular_spread_deg", 90.0)),
        incidence_angle_deg=float(data.get("incidence_angle_deg", 0.0)),
        active_region_thickness_mm=float(active_region_thickness_mm_raw),
        fixed_track_length_cm=float(fixed_track_length_cm_raw),
        track_length_model=str(data.get("track_length_model", "range_limited")),  # type: ignore[arg-type]
        active_region_entry_probability=float(
            data.get("active_region_entry_probability", 1.0)
        ),
        notes=str(data.get("notes", "")),
        metadata=metadata,
    )


__all__ = [
    "SourceGeometryConfig",
    "SourceGeometrySummary",
    "SourcePlacementModel",
    "TrackLengthModel",
    "active_path_length_cm",
    "geometric_acceptance_factor",
    "projected_active_path_length_cm",
    "source_geometry_from_mapping",
    "source_survival_to_active_region_probability",
    "summarize_source_geometry",
]