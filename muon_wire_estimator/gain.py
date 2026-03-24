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
Two gain modes are supported:

1. "phenomenological_capped" (default)
   The original Level 1 field-activation surrogate:

       x = max(E_surface / E_scale - 1, 0)
       gain = min(exp(slope * x), gain_cap)

2. "diethorn_like"
   A hand-calculation style cylindrical proportional-counter surrogate:

       ln(M) = (V / ln(b/a)) * (ln 2 / DeltaV) * ln(V / V0)

   with

       V0 = p * a * ln(b/a) * (E_min / p)

   using geometry-aware quantities:
   - V: applied bias voltage
   - a: sense-wire radius
   - b: effective outer radius
   - p: gas pressure

Notes
-----
- The diethorn-like mode is geometry-based, not field-only.
- In this Level 1 implementation, air-like gases still return unity gain in
  "diethorn_like" mode to stay consistent with the earlier hand calculations
  that treated air as direct-primary only rather than a stable proportional
  avalanche medium.
- The original phenomenological mode remains the default to preserve backward
  compatibility.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .gases import get_gas
from .geometry import cylindrical_surface_field_v_per_m, validate_geometry
from .models import GasModel, GeometryModel, JSONValue


ELECTRON_CHARGE_C = 1.602176634e-19

GAIN_MODEL_PHENOMENOLOGICAL_CAPPED = "phenomenological_capped"
GAIN_MODEL_DIETHORN_LIKE = "diethorn_like"

DEFAULT_GAIN_MODEL = GAIN_MODEL_PHENOMENOLOGICAL_CAPPED

DIETHORN_DEFAULT_DELTA_V = 35.0
DIETHORN_DEFAULT_E_MIN_OVER_P_V_PER_CM_TORR = 50.0


@dataclass(slots=True)
class GainEstimate:
    """
    Deterministic avalanche-gain estimate for a single configuration.

    Attributes
    ----------
    surface_field_v_per_m:
        Cylindrical surface electric field at the sense-wire radius.
    gain_activation_argument:
        Dimensionless gain-activation variable used by the selected surrogate.
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


def validate_gain_model(gain_model: str) -> str:
    """Validate and normalize the gain-model selector."""
    if not isinstance(gain_model, str):
        raise TypeError(
            f"gain_model must be a str, got {type(gain_model).__name__}."
        )
    normalized = gain_model.strip().lower()
    allowed = {
        GAIN_MODEL_PHENOMENOLOGICAL_CAPPED,
        GAIN_MODEL_DIETHORN_LIKE,
    }
    if normalized not in allowed:
        raise ValueError(
            "gain_model must be one of "
            f"{sorted(allowed)!r}, got {gain_model!r}."
        )
    return normalized


def _pressure_torr(gas_model: GasModel) -> float:
    """Return gas pressure in Torr."""
    pressure_atm = float(getattr(gas_model, "pressure_atm", 1.0))
    if pressure_atm <= 0.0:
        raise ValueError(
            f"gas pressure_atm must be > 0, got {pressure_atm!r}."
        )
    return pressure_atm * 760.0


def _geometry_log_b_over_a(geometry: GeometryModel) -> float:
    """Return ln(b/a) for the single-wire cylindrical model."""
    geometry = validate_geometry(geometry)
    a_m = geometry.sense_wire_radius_m
    b_m = geometry.effective_outer_radius_m
    if a_m <= 0.0:
        raise ValueError(
            f"sense_wire_radius_m must be > 0, got {a_m!r}."
        )
    if b_m <= 0.0:
        raise ValueError(
            f"effective_outer_radius_m must be > 0, got {b_m!r}."
        )
    if b_m <= a_m:
        raise ValueError(
            "effective_outer_radius_m must be > sense_wire_radius_m, "
            f"got b={b_m!r}, a={a_m!r}."
        )
    return math.log(b_m / a_m)


def _diethorn_v0_v(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    e_min_over_p_v_per_cm_torr: float = DIETHORN_DEFAULT_E_MIN_OVER_P_V_PER_CM_TORR,
) -> float:
    """
    Compute the Diethorn-like threshold voltage parameter V0.

    Uses:
        V0 = p * a * ln(b/a) * (E_min / p)

    with:
    - p in Torr
    - a in cm
    - E_min/p in V / (cm * Torr)
    """
    if e_min_over_p_v_per_cm_torr <= 0.0:
        raise ValueError(
            "e_min_over_p_v_per_cm_torr must be > 0, "
            f"got {e_min_over_p_v_per_cm_torr!r}."
        )

    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)

    a_cm = geometry.sense_wire_radius_m * 100.0
    if a_cm <= 0.0:
        raise ValueError(f"sense_wire_radius_m must be > 0, got {a_cm!r} cm.")

    log_b_over_a = _geometry_log_b_over_a(geometry)
    pressure_torr = _pressure_torr(gas_model)

    return pressure_torr * a_cm * log_b_over_a * e_min_over_p_v_per_cm_torr


def _is_air_like_gas(gas_model: GasModel) -> bool:
    """Heuristic used to keep air in unity-gain mode for the hand-calculation path."""
    return "air" in gas_model.name.lower()


def diethorn_activation_argument(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    e_min_over_p_v_per_cm_torr: float = DIETHORN_DEFAULT_E_MIN_OVER_P_V_PER_CM_TORR,
) -> float:
    """
    Compute a non-negative activation variable for the Diethorn-like mode.

    Definition
    ----------
    x = max(V / V0 - 1, 0)
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)

    if geometry.bias_voltage_v < 0.0:
        raise ValueError(
            f"bias_voltage_v must be >= 0, got {geometry.bias_voltage_v!r}."
        )

    if _is_air_like_gas(gas_model):
        return 0.0

    v0_v = _diethorn_v0_v(
        geometry,
        gas_model,
        e_min_over_p_v_per_cm_torr=e_min_over_p_v_per_cm_torr,
    )
    if v0_v <= 0.0:
        return 0.0
    return max((geometry.bias_voltage_v / v0_v) - 1.0, 0.0)


def gain_activation_argument(
    surface_field_v_per_m: float,
    gas: GasModel | str,
) -> float:
    """
    Compute the dimensionless gain-activation variable for the original
    phenomenological capped mode.

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
    gain_model: str = DEFAULT_GAIN_MODEL,
) -> float:
    """
    Estimate the mean gas gain from the wire-surface electric field.

    This helper only supports the original field-only phenomenological mode.
    The Diethorn-like mode needs full geometry and must be evaluated through
    `estimate_gas_gain(...)` or `estimate_gain(...)`.
    """
    gain_model = validate_gain_model(gain_model)

    if gain_model != GAIN_MODEL_PHENOMENOLOGICAL_CAPPED:
        raise ValueError(
            "estimate_gas_gain_from_surface_field only supports "
            f"{GAIN_MODEL_PHENOMENOLOGICAL_CAPPED!r}. "
            "Use estimate_gas_gain(...) or estimate_gain(...) for "
            f"{GAIN_MODEL_DIETHORN_LIKE!r}."
        )

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


def estimate_diethorn_like_gain(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    use_gain_surrogate: bool = True,
    delta_v: float = DIETHORN_DEFAULT_DELTA_V,
    e_min_over_p_v_per_cm_torr: float = DIETHORN_DEFAULT_E_MIN_OVER_P_V_PER_CM_TORR,
    apply_gain_cap: bool = False,
) -> float:
    """
    Estimate mean gas gain using the hand-calculation / Diethorn-like surrogate.

    For air-like gases in this Level 1 framework, the function returns unity
    gain to remain consistent with the earlier hand calculations that treated
    air as direct-primary only rather than a stable proportional avalanche gas.
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)

    if delta_v <= 0.0:
        raise ValueError(f"delta_v must be > 0, got {delta_v!r}.")
    if e_min_over_p_v_per_cm_torr <= 0.0:
        raise ValueError(
            "e_min_over_p_v_per_cm_torr must be > 0, "
            f"got {e_min_over_p_v_per_cm_torr!r}."
        )
    if geometry.bias_voltage_v < 0.0:
        raise ValueError(
            f"bias_voltage_v must be >= 0, got {geometry.bias_voltage_v!r}."
        )

    if not use_gain_surrogate:
        return 1.0

    if _is_air_like_gas(gas_model):
        return 1.0

    log_b_over_a = _geometry_log_b_over_a(geometry)
    v0_v = _diethorn_v0_v(
        geometry,
        gas_model,
        e_min_over_p_v_per_cm_torr=e_min_over_p_v_per_cm_torr,
    )
    if geometry.bias_voltage_v <= 0.0 or geometry.bias_voltage_v <= v0_v:
        return 1.0

    ln_m = (
        (geometry.bias_voltage_v / log_b_over_a)
        * (math.log(2.0) / delta_v)
        * math.log(geometry.bias_voltage_v / v0_v)
    )

    if ln_m <= 0.0:
        return 1.0

    gain = math.exp(ln_m)
    if apply_gain_cap:
        gain = min(gain, gas_model.gain_cap)
    return max(gain, 1.0)


def estimate_gas_gain(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    use_gain_surrogate: bool = True,
    gain_model: str = DEFAULT_GAIN_MODEL,
    diethorn_delta_v: float = DIETHORN_DEFAULT_DELTA_V,
    diethorn_e_min_over_p_v_per_cm_torr: float = DIETHORN_DEFAULT_E_MIN_OVER_P_V_PER_CM_TORR,
    diethorn_apply_gain_cap: bool = False,
) -> float:
    """
    Estimate mean gas gain from geometry plus gas properties.
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)
    gain_model = validate_gain_model(gain_model)

    if gain_model == GAIN_MODEL_PHENOMENOLOGICAL_CAPPED:
        surface_field = cylindrical_surface_field_v_per_m(geometry)
        return estimate_gas_gain_from_surface_field(
            surface_field,
            gas_model,
            use_gain_surrogate=use_gain_surrogate,
            gain_model=gain_model,
        )

    return estimate_diethorn_like_gain(
        geometry,
        gas_model,
        use_gain_surrogate=use_gain_surrogate,
        delta_v=diethorn_delta_v,
        e_min_over_p_v_per_cm_torr=diethorn_e_min_over_p_v_per_cm_torr,
        apply_gain_cap=diethorn_apply_gain_cap,
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
    gain_model: str = DEFAULT_GAIN_MODEL,
    diethorn_delta_v: float = DIETHORN_DEFAULT_DELTA_V,
    diethorn_e_min_over_p_v_per_cm_torr: float = DIETHORN_DEFAULT_E_MIN_OVER_P_V_PER_CM_TORR,
    diethorn_apply_gain_cap: bool = False,
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
    gain_model:
        Gain model selector. Supported values:
        - "phenomenological_capped"
        - "diethorn_like"
    diethorn_delta_v:
        DeltaV parameter for the Diethorn-like mode.
    diethorn_e_min_over_p_v_per_cm_torr:
        E_min/p parameter for the Diethorn-like mode.
    diethorn_apply_gain_cap:
        If True, also apply the gas-model gain cap in Diethorn-like mode.
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)
    gain_model = validate_gain_model(gain_model)

    if collected_primary_electrons_mean < 0.0:
        raise ValueError(
            "collected_primary_electrons_mean must be >= 0, "
            f"got {collected_primary_electrons_mean!r}."
        )

    surface_field = cylindrical_surface_field_v_per_m(geometry)

    if gain_model == GAIN_MODEL_PHENOMENOLOGICAL_CAPPED:
        activation = gain_activation_argument(surface_field, gas_model)
    else:
        activation = diethorn_activation_argument(
            geometry,
            gas_model,
            e_min_over_p_v_per_cm_torr=diethorn_e_min_over_p_v_per_cm_torr,
        )

    gas_gain = estimate_gas_gain(
        geometry,
        gas_model,
        use_gain_surrogate=use_gain_surrogate,
        gain_model=gain_model,
        diethorn_delta_v=diethorn_delta_v,
        diethorn_e_min_over_p_v_per_cm_torr=diethorn_e_min_over_p_v_per_cm_torr,
        diethorn_apply_gain_cap=diethorn_apply_gain_cap,
    )
    avalanche_electrons = estimate_avalanche_electrons(
        collected_primary_electrons_mean,
        gas_gain,
    )
    avalanche_charge = estimate_avalanche_charge_c(avalanche_electrons)

    metadata: dict[str, JSONValue] = {
        "gas_name": gas_model.name,
        "use_gain_surrogate": use_gain_surrogate,
        "gain_model": gain_model,
        "gain_field_scale_v_per_m": gas_model.gain_field_scale_v_per_m,
        "gain_slope": gas_model.gain_slope,
        "gain_cap": gas_model.gain_cap,
    }

    if gain_model == GAIN_MODEL_DIETHORN_LIKE:
        metadata.update(
            {
                "diethorn_delta_v": diethorn_delta_v,
                "diethorn_e_min_over_p_v_per_cm_torr": diethorn_e_min_over_p_v_per_cm_torr,
                "diethorn_apply_gain_cap": diethorn_apply_gain_cap,
                "diethorn_log_b_over_a": _geometry_log_b_over_a(geometry),
                "diethorn_v0_v": _diethorn_v0_v(
                    geometry,
                    gas_model,
                    e_min_over_p_v_per_cm_torr=diethorn_e_min_over_p_v_per_cm_torr,
                ),
                "diethorn_air_unity_gain_mode": _is_air_like_gas(gas_model),
            }
        )

    return GainEstimate(
        surface_field_v_per_m=surface_field,
        gain_activation_argument=activation,
        gas_gain_mean=gas_gain,
        collected_primary_electrons_mean=collected_primary_electrons_mean,
        avalanche_electrons_mean=avalanche_electrons,
        avalanche_charge_c=avalanche_charge,
        metadata=metadata,
    )


def gain_summary(
    geometry: GeometryModel,
    gas: GasModel | str,
    collected_primary_electrons_mean: float,
    *,
    use_gain_surrogate: bool = True,
    gain_model: str = DEFAULT_GAIN_MODEL,
    diethorn_delta_v: float = DIETHORN_DEFAULT_DELTA_V,
    diethorn_e_min_over_p_v_per_cm_torr: float = DIETHORN_DEFAULT_E_MIN_OVER_P_V_PER_CM_TORR,
    diethorn_apply_gain_cap: bool = False,
) -> dict[str, JSONValue]:
    """
    Return a JSON-friendly deterministic gain summary block.
    """
    estimate = estimate_gain(
        geometry,
        gas,
        collected_primary_electrons_mean,
        use_gain_surrogate=use_gain_surrogate,
        gain_model=gain_model,
        diethorn_delta_v=diethorn_delta_v,
        diethorn_e_min_over_p_v_per_cm_torr=diethorn_e_min_over_p_v_per_cm_torr,
        diethorn_apply_gain_cap=diethorn_apply_gain_cap,
    )
    return estimate.to_dict()


__all__ = [
    "DEFAULT_GAIN_MODEL",
    "DIETHORN_DEFAULT_DELTA_V",
    "DIETHORN_DEFAULT_E_MIN_OVER_P_V_PER_CM_TORR",
    "ELECTRON_CHARGE_C",
    "GAIN_MODEL_DIETHORN_LIKE",
    "GAIN_MODEL_PHENOMENOLOGICAL_CAPPED",
    "GainEstimate",
    "diethorn_activation_argument",
    "estimate_avalanche_charge_c",
    "estimate_avalanche_electrons",
    "estimate_diethorn_like_gain",
    "estimate_gain",
    "estimate_gas_gain",
    "estimate_gas_gain_from_surface_field",
    "gain_activation_argument",
    "gain_summary",
    "resolve_gas",
    "validate_gas",
    "validate_gain_model",
]