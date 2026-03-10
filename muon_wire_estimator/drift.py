"""
Drift and attachment-survival helpers for the muon wire estimator.

This module provides lightweight deterministic transport estimates for Level 1.
The goal is to keep the logic understandable and explicit while separating:

- geometric drift distance
- characteristic drift time
- attachment survival
- total primary-electron collection fraction

These are engineering surrogates, not microscopic transport calculations.
They are intended to preserve the baseline estimator's simplicity while making
the nonzero-field path more realistic and easier to calibrate later.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .gases import get_gas
from .geometry import (
    average_drift_field_v_per_m,
    radial_drift_distance_m,
    validate_geometry,
)
from .models import GasModel, GeometryModel, JSONValue


@dataclass(slots=True)
class DriftEstimate:
    """
    Deterministic drift/transport estimate for a single-wire configuration.

    Attributes
    ----------
    drift_distance_m:
        Characteristic electron drift distance from the track radius to the
        wire surface.
    drift_velocity_m_per_s:
        Effective drift velocity used for the estimate.
    drift_time_s:
        Characteristic drift time.
    attachment_survival_fraction:
        Survival from attachment alone.
    collection_fraction_total:
        Net collection efficiency including both attachment survival and the
        gas-level collection efficiency term.
    metadata:
        JSON-friendly auxiliary transport details.
    """

    drift_distance_m: float
    drift_velocity_m_per_s: float
    drift_time_s: float
    attachment_survival_fraction: float
    collection_fraction_total: float
    metadata: dict[str, JSONValue]

    def __post_init__(self) -> None:
        if self.drift_distance_m < 0.0:
            raise ValueError(
                f"drift_distance_m must be >= 0, got {self.drift_distance_m!r}."
            )
        if self.drift_velocity_m_per_s < 0.0:
            raise ValueError(
                "drift_velocity_m_per_s must be >= 0, "
                f"got {self.drift_velocity_m_per_s!r}."
            )
        if self.drift_time_s < 0.0:
            raise ValueError(f"drift_time_s must be >= 0, got {self.drift_time_s!r}.")
        if not 0.0 <= self.attachment_survival_fraction <= 1.0:
            raise ValueError(
                "attachment_survival_fraction must be in [0, 1], "
                f"got {self.attachment_survival_fraction!r}."
            )
        if not 0.0 <= self.collection_fraction_total <= 1.0:
            raise ValueError(
                "collection_fraction_total must be in [0, 1], "
                f"got {self.collection_fraction_total!r}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "drift_distance_m": self.drift_distance_m,
            "drift_velocity_m_per_s": self.drift_velocity_m_per_s,
            "drift_time_s": self.drift_time_s,
            "attachment_survival_fraction": self.attachment_survival_fraction,
            "collection_fraction_total": self.collection_fraction_total,
            "metadata": dict(self.metadata),
        }


def validate_gas(gas: GasModel) -> GasModel:
    """Validate and return a GasModel."""
    if not isinstance(gas, GasModel):
        raise TypeError(f"gas must be a GasModel instance, got {type(gas).__name__}.")
    return gas


def resolve_gas(gas: GasModel | str) -> GasModel:
    """
    Resolve either a GasModel object or a built-in gas name.
    """
    if isinstance(gas, GasModel):
        return validate_gas(gas)
    if isinstance(gas, str):
        return get_gas(gas)
    raise TypeError(f"gas must be GasModel or str, got {type(gas).__name__}.")


def effective_drift_velocity_m_per_s(
    geometry: GeometryModel,
    gas: GasModel | str,
) -> float:
    """
    Return the effective drift velocity used for deterministic timing.

    Current model
    -------------
    Level 1 intentionally uses the gas's characteristic drift velocity
    directly, while still exposing the average drift field in metadata for
    later calibration or field-dependent upgrades.
    """
    validate_geometry(geometry)
    gas_model = resolve_gas(gas)
    return gas_model.drift_velocity_m_per_s


def estimate_drift_time_s(
    geometry: GeometryModel,
    gas: GasModel | str,
) -> float:
    """
    Estimate the characteristic electron drift time.

    Formula
    -------
    t_drift = d / v_drift
    """
    geometry = validate_geometry(geometry)
    velocity = effective_drift_velocity_m_per_s(geometry, gas)
    distance = radial_drift_distance_m(geometry)

    if velocity <= 0.0:
        return 0.0 if distance == 0.0 else math.inf
    return distance / velocity


def estimate_attachment_survival_fraction(
    drift_time_s: float,
    gas: GasModel | str,
    *,
    use_attachment: bool = True,
) -> float:
    """
    Estimate survival against attachment during drift.

    Model
    -----
    If attachment is disabled or the gas has no finite attachment time,
    survival is 1.

    Otherwise:
        survival = exp(-t_drift / tau_attach)
    """
    if drift_time_s < 0.0:
        raise ValueError(f"drift_time_s must be >= 0, got {drift_time_s!r}.")

    gas_model = resolve_gas(gas)

    if not use_attachment:
        return 1.0

    tau = gas_model.attachment_time_s
    if tau is None:
        return 1.0
    if tau <= 0.0:
        raise ValueError(
            "GasModel.attachment_time_s must be positive when provided, "
            f"got {tau!r}."
        )
    if math.isinf(drift_time_s):
        return 0.0
    return math.exp(-drift_time_s / tau)


def estimate_collection_fraction_total(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    use_attachment: bool = True,
) -> float:
    """
    Estimate the net primary-electron collection fraction.

    Current model
    -------------
    total_collection = attachment_survival * gas.collection_efficiency
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)
    drift_time = estimate_drift_time_s(geometry, gas_model)
    survival = estimate_attachment_survival_fraction(
        drift_time,
        gas_model,
        use_attachment=use_attachment,
    )
    total = survival * gas_model.collection_efficiency
    return min(1.0, max(0.0, total))


def estimate_collected_primary_electrons(
    created_primary_electrons_mean: float,
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    use_attachment: bool = True,
) -> float:
    """
    Estimate the mean number of primary electrons arriving near the gain region.
    """
    if created_primary_electrons_mean < 0.0:
        raise ValueError(
            "created_primary_electrons_mean must be >= 0, "
            f"got {created_primary_electrons_mean!r}."
        )
    collection_fraction = estimate_collection_fraction_total(
        geometry,
        gas,
        use_attachment=use_attachment,
    )
    return created_primary_electrons_mean * collection_fraction


def estimate_drift(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    use_attachment: bool = True,
) -> DriftEstimate:
    """
    Produce a complete deterministic drift/transport estimate.
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)

    distance = radial_drift_distance_m(geometry)
    drift_velocity = effective_drift_velocity_m_per_s(geometry, gas_model)
    drift_time = estimate_drift_time_s(geometry, gas_model)
    survival = estimate_attachment_survival_fraction(
        drift_time,
        gas_model,
        use_attachment=use_attachment,
    )
    total_collection = estimate_collection_fraction_total(
        geometry,
        gas_model,
        use_attachment=use_attachment,
    )

    return DriftEstimate(
        drift_distance_m=distance,
        drift_velocity_m_per_s=drift_velocity,
        drift_time_s=drift_time,
        attachment_survival_fraction=survival,
        collection_fraction_total=total_collection,
        metadata={
            "gas_name": gas_model.name,
            "use_attachment": use_attachment,
            "average_drift_field_v_per_m": average_drift_field_v_per_m(geometry),
            "gas_collection_efficiency": gas_model.collection_efficiency,
            "attachment_time_s": gas_model.attachment_time_s,
        },
    )


def drift_summary(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    use_attachment: bool = True,
) -> dict[str, JSONValue]:
    """
    Return a JSON-friendly deterministic drift summary block.
    """
    estimate = estimate_drift(geometry, gas, use_attachment=use_attachment)
    return estimate.to_dict()


__all__ = [
    "DriftEstimate",
    "drift_summary",
    "effective_drift_velocity_m_per_s",
    "estimate_attachment_survival_fraction",
    "estimate_collection_fraction_total",
    "estimate_collected_primary_electrons",
    "estimate_drift",
    "estimate_drift_time_s",
    "resolve_gas",
    "validate_gas",
]