"""
Avalanche-gain surrogate models for the muon wire estimator.

This module provides the Level 1 deterministic gas-gain estimate. The purpose
is not to reproduce microscopic Garfield++ avalanche physics, but to provide a
compact, transparent engineering model with the right control knobs so that:

- air and common chamber gases behave differently
- higher surface field generally produces larger gain
- attachment/collection losses remain separate from gain itself
- later calibration layers can override the surrogate cleanly

Design philosophy
-----------------
The Level 1 gain surrogate is based on the cylindrical surface field at the
sense wire and a gas-specific field scale/slope/cap:

    x = max(E_surface / E_scale - 1, 0)
    gain = min(exp(slope * x), gain_cap)

This gives the desired behavior:

- below the gas-specific onset scale, gain is ~1
- above onset, gain rises monotonically
- each gas can have a very different threshold and growth
- gain is bounded to avoid pathological outputs in a simple estimator

This module also provides helpers to convert collected primary electrons into
avalanche electrons and avalanche charge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .gases import get_gas
from .geometry import cylindrical_surface_field_v_per_m, validate_geometry
from .models import GasModel, GeometryModel, JSONValue


ELECTRON_CHARGE_C = 1.602176634e-19


@dataclass(slots=True)
class GainEstimate:
    """
    Deterministic avalanche-gain estimate for a single configuration.

    Attributes
    ----------
    surface_field_v_per_m:
        Cylindrical surface electric field at the sense-wire radius.
    gain_activation_argument:
        Dimensionless field-activation variable used by the surrogate.
    gas_gain_mean:
        Mean avalanche gas gain from the surrogate model.
    collected_primary_electrons_mean:
        Mean number of electrons reaching the multiplication region.
    avalanche_electrons_mean:
        Mean number of electrons after multiplication.
    avalanche_charge_c:
        Mean avalanche charge in Coulombs.
    metadata:
        JSON-friendly auxiliary information.
    """

    surface_field_v_per_m: float
    gain_activation_argument: float
    gas_gain_mean: float
    collected_primary_electrons_mean: float
    avalanche_electrons_mean: float
    avalanche_charge_c: float
    metadata: dict[str, JSONValue]

    def __post_init__(self) -> None:
        if self.surface_field_v_per_m < 0.0:
            raise ValueError(
                "surface_field_v_per_m must be >= 0, "
                f"got {self.surface_field_v_per_m!r}."
            )
        if self.gain_activation_argument < 0.0:
            raise ValueError(
                "gain_activation_argument must be >= 0, "
                f"got {self.gain_activation_argument!r}."
            )
        if self.gas_gain_mean < 0.0:
            raise ValueError(
                f"gas_gain_mean must be >= 0, got {self.gas_gain_mean!r}."
            )
        if self.collected_primary_electrons_mean < 0.0:
            raise ValueError(
                "collected_primary_electrons_mean must be >= 0, "
                f"got {self.collected_primary_electrons_mean!r}."
            )
        if self.avalanche_electrons_mean < 0.0:
            raise ValueError(
                "avalanche_electrons_mean must be >= 0, "
                f"got {self.avalanche_electrons_mean!r}."
            )
        if self.avalanche_charge_c < 0.0:
            raise ValueError(
                f"avalanche_charge_c must be >= 0, got {self.avalanche_charge_c!r}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "surface_field_v_per_m": self.surface_field_v_per_m,
            "gain_activation_argument": self.gain_activation_argument,
            "gas_gain_mean": self.gas_gain_mean,
            "collected_primary_electrons_mean": self.collected_primary_electrons_mean,
            "avalanche_electrons_mean": self.avalanche_electrons_mean,
            "avalanche_charge_c": self.avalanche_charge_c,
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


def gain_activation_argument(
    surface_field_v_per_m: float,
    gas: GasModel | str,
) -> float:
    """
    Compute the dimensionless gain-activation variable.

    Definition
    ----------
    x = max(E_surface / E_scale - 1, 0)

    where E_scale is the gas-specific gain onset field.
    """
    if surface_field_v_per_m < 0.0:
        raise ValueError(
            "surface_field_v_per_m must be >= 0, "
            f"got {surface_field_v_per_m!r}."
        )
    gas_model = resolve_gas(gas)
    ratio = surface_field_v_per_m / gas_model.gain_field_scale_v_per_m
    return max(ratio - 1.0, 0.0)


def estimate_gas_gain_from_surface_field(
    surface_field_v_per_m: float,
    gas: GasModel | str,
    *,
    use_gain_surrogate: bool = True,
) -> float:
    """
    Estimate the mean gas gain from the wire-surface electric field.

    Model
    -----
    If gain is disabled, the function returns 1.0.

    Otherwise:
        x = max(E_surface / E_scale - 1, 0)
        gain = min(exp(slope * x), gain_cap)

    The gain is never allowed below 1.0 in this deterministic Level 1 model.
    """
    if surface_field_v_per_m < 0.0:
        raise ValueError(
            "surface_field_v_per_m must be >= 0, "
            f"got {surface_field_v_per_m!r}."
        )

    if not use_gain_surrogate:
        return 1.0

    gas_model = resolve_gas(gas)
    x = gain_activation_argument(surface_field_v_per_m, gas_model)
    gain = math.exp(gas_model.gain_slope * x)
    gain = min(gain, gas_model.gain_cap)
    return max(gain, 1.0)


def estimate_gas_gain(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    use_gain_surrogate: bool = True,
) -> float:
    """
    Estimate mean gas gain from geometry plus gas properties.
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)
    surface_field = cylindrical_surface_field_v_per_m(geometry)
    return estimate_gas_gain_from_surface_field(
        surface_field,
        gas_model,
        use_gain_surrogate=use_gain_surrogate,
    )


def estimate_avalanche_electrons(
    collected_primary_electrons_mean: float,
    gas_gain_mean: float,
) -> float:
    """
    Convert collected primary electrons and gas gain into avalanche electrons.
    """
    if collected_primary_electrons_mean < 0.0:
        raise ValueError(
            "collected_primary_electrons_mean must be >= 0, "
            f"got {collected_primary_electrons_mean!r}."
        )
    if gas_gain_mean < 0.0:
        raise ValueError(f"gas_gain_mean must be >= 0, got {gas_gain_mean!r}.")
    return collected_primary_electrons_mean * gas_gain_mean


def estimate_avalanche_charge_c(avalanche_electrons_mean: float) -> float:
    """
    Convert avalanche electron count into total charge in Coulombs.
    """
    if avalanche_electrons_mean < 0.0:
        raise ValueError(
            "avalanche_electrons_mean must be >= 0, "
            f"got {avalanche_electrons_mean!r}."
        )
    return avalanche_electrons_mean * ELECTRON_CHARGE_C


def estimate_gain(
    geometry: GeometryModel,
    gas: GasModel | str,
    collected_primary_electrons_mean: float,
    *,
    use_gain_surrogate: bool = True,
) -> GainEstimate:
    """
    Produce a complete deterministic gain estimate.

    Parameters
    ----------
    geometry:
        Single-wire geometry model.
    gas:
        Gas model or built-in gas name.
    collected_primary_electrons_mean:
        Mean number of electrons reaching the multiplication region.
    use_gain_surrogate:
        If False, force unity gain.
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)

    if collected_primary_electrons_mean < 0.0:
        raise ValueError(
            "collected_primary_electrons_mean must be >= 0, "
            f"got {collected_primary_electrons_mean!r}."
        )

    surface_field = cylindrical_surface_field_v_per_m(geometry)
    activation = gain_activation_argument(surface_field, gas_model)
    gas_gain = estimate_gas_gain_from_surface_field(
        surface_field,
        gas_model,
        use_gain_surrogate=use_gain_surrogate,
    )
    avalanche_electrons = estimate_avalanche_electrons(
        collected_primary_electrons_mean,
        gas_gain,
    )
    avalanche_charge = estimate_avalanche_charge_c(avalanche_electrons)

    return GainEstimate(
        surface_field_v_per_m=surface_field,
        gain_activation_argument=activation,
        gas_gain_mean=gas_gain,
        collected_primary_electrons_mean=collected_primary_electrons_mean,
        avalanche_electrons_mean=avalanche_electrons,
        avalanche_charge_c=avalanche_charge,
        metadata={
            "gas_name": gas_model.name,
            "use_gain_surrogate": use_gain_surrogate,
            "gain_field_scale_v_per_m": gas_model.gain_field_scale_v_per_m,
            "gain_slope": gas_model.gain_slope,
            "gain_cap": gas_model.gain_cap,
        },
    )


def gain_summary(
    geometry: GeometryModel,
    gas: GasModel | str,
    collected_primary_electrons_mean: float,
    *,
    use_gain_surrogate: bool = True,
) -> dict[str, JSONValue]:
    """
    Return a JSON-friendly deterministic gain summary block.
    """
    estimate = estimate_gain(
        geometry,
        gas,
        collected_primary_electrons_mean,
        use_gain_surrogate=use_gain_surrogate,
    )
    return estimate.to_dict()


__all__ = [
    "ELECTRON_CHARGE_C",
    "GainEstimate",
    "estimate_avalanche_charge_c",
    "estimate_avalanche_electrons",
    "estimate_gain",
    "estimate_gas_gain",
    "estimate_gas_gain_from_surface_field",
    "gain_activation_argument",
    "gain_summary",
    "resolve_gas",
    "validate_gas",
]