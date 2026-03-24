"""
Built-in gas definitions and registry helpers for the muon wire estimator.

This module provides lightweight phenomenological gas models suitable for the
Level 1 deterministic estimator and later stochastic/calibrated extensions.
The values here are intentionally pragmatic surrogates rather than microscopic
transport calculations. They are designed to be:

- readable
- easily overridden later by calibration files
- safe for local/offline use
- explicit about uncertainty, especially for air

The registry includes at minimum:
- air_dry_1atm
- ar_co2_70_30_1atm
- ar_co2_75_25_1atm
"""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .models import GasModel


def _build_builtin_gases() -> dict[str, GasModel]:
    """
    Construct the immutable baseline gas registry.

    Notes on philosophy
    -------------------
    These parameters are not claimed to be Garfield++-accurate. They are
    compact surrogate settings chosen so the estimator has reasonable trends:

    - dry air at 1 atm:
      lower drift speed, appreciable attachment risk, conservative gain behavior
    - Ar/CO2 70/30 at 1 atm:
      faster drift, negligible attachment in this simplified picture,
      easier avalanche development than air
    - Ar/CO2 75/25 at 1 atm:
      very similar to 70/30 but with slightly more argon content, so in this
      surrogate picture it is treated as marginally easier to avalanche

    Future Level 3 calibration files can override any of these defaults.
    """
    gases = {
        "air_dry_1atm": GasModel(
            name="air_dry_1atm",
            pressure_atm=1.0,
            temperature_k=293.15,
            w_value_ev=34.0,
            mean_energy_loss_mev_per_cm=0.0019,
            drift_velocity_m_per_s=5.0e4,
            attachment_time_s=80.0e-9,
            collection_efficiency=0.70,
            gain_field_scale_v_per_m=9.0e6,
            gain_slope=0.22,
            gain_cap=2.0e3,
            fano_factor=0.25,
            mean_cluster_size_electrons=1.8,
            notes=(
                "Highly uncertain surrogate for dry air at 1 atm. "
                "Air is attachment-prone and avalanche predictions should be "
                "treated as qualitative unless externally calibrated."
            ),
        ),
        "ar_co2_70_30_1atm": GasModel(
            name="ar_co2_70_30_1atm",
            pressure_atm=1.0,
            temperature_k=293.15,
            w_value_ev=27.0,
            mean_energy_loss_mev_per_cm=0.0024,
            drift_velocity_m_per_s=5.5e4,
            attachment_time_s=None,
            collection_efficiency=0.95,
            gain_field_scale_v_per_m=4.5e6,
            gain_slope=0.85,
            gain_cap=1.0e5,
            fano_factor=0.17,
            mean_cluster_size_electrons=2.4,
            notes=(
                "Phenomenological Ar/CO2 70/30 surrogate intended for simple "
                "single-wire engineering estimates before Garfield-based tuning."
            ),
        ),
        "ar_co2_75_25_1atm": GasModel(
            name="ar_co2_75_25_1atm",
            pressure_atm=1.0,
            temperature_k=293.15,
            w_value_ev=28.0,
            mean_energy_loss_mev_per_cm=0.0024,
            drift_velocity_m_per_s=5.6e4,
            attachment_time_s=None,
            collection_efficiency=0.95,
            gain_field_scale_v_per_m=4.2e6,
            gain_slope=0.90,
            gain_cap=1.0e5,
            fano_factor=0.17,
            mean_cluster_size_electrons=2.5,
            notes=(
                "Phenomenological Ar/CO2 75/25 surrogate intended for simple "
                "single-wire engineering estimates before Garfield-based tuning. "
                "Compared with the 70/30 surrogate, this preset assumes slightly "
                "easier avalanche development from the higher argon fraction while "
                "keeping transport behavior broadly similar."
            ),
        ),
    }
    return gases


_BUILTIN_GASES: dict[str, GasModel] = _build_builtin_gases()


def list_builtin_gases() -> list[str]:
    """Return the sorted list of built-in gas registry keys."""
    return sorted(_BUILTIN_GASES.keys())


def iter_builtin_gases() -> Iterable[GasModel]:
    """
    Iterate over copies of built-in gas models in sorted name order.

    Copies are returned to prevent accidental mutation of registry state.
    """
    for key in list_builtin_gases():
        yield replace(_BUILTIN_GASES[key])


def has_gas(name: str) -> bool:
    """Return True if a named gas exists in the built-in registry."""
    if not name or not name.strip():
        return False
    return name.strip() in _BUILTIN_GASES


def get_gas(name: str) -> GasModel:
    """
    Return a copy of a named gas model from the registry.

    Parameters
    ----------
    name:
        Registry key such as ``air_dry_1atm``, ``ar_co2_70_30_1atm``, or
        ``ar_co2_75_25_1atm``.

    Raises
    ------
    KeyError
        If the requested gas name is not registered.
    """
    key = name.strip()
    if key not in _BUILTIN_GASES:
        available = ", ".join(list_builtin_gases())
        raise KeyError(
            f"Unknown gas {name!r}. Available built-in gases: {available}."
        )
    return replace(_BUILTIN_GASES[key])


def require_gas(name: str) -> GasModel:
    """
    Alias for :func:`get_gas` with a slightly more intention-revealing name.
    """
    return get_gas(name)


def register_gas(
    registry: dict[str, GasModel] | None,
    gas: GasModel,
    *,
    overwrite: bool = False,
) -> dict[str, GasModel]:
    """
    Register a gas in a caller-provided registry.

    This helper is meant for local extension by scripts or later calibration
    infrastructure without mutating the built-in registry.

    Parameters
    ----------
    registry:
        Existing mutable registry dictionary. If None, a new empty registry is
        created.
    gas:
        The gas model to insert.
    overwrite:
        If False, trying to replace an existing entry raises ``KeyError``.

    Returns
    -------
    dict[str, GasModel]
        The registry containing the inserted gas.
    """
    target = {} if registry is None else dict(registry)
    key = gas.name.strip()
    if not key:
        raise ValueError("gas.name must be a non-empty string.")
    if key in target and not overwrite:
        raise KeyError(
            f"Gas {key!r} is already present in the target registry. "
            "Pass overwrite=True to replace it."
        )
    target[key] = replace(gas)
    return target


def merged_registry(
    extra_gases: dict[str, GasModel] | None = None,
    *,
    overwrite: bool = True,
) -> dict[str, GasModel]:
    """
    Return a new registry consisting of built-ins plus optional extra gases.

    Parameters
    ----------
    extra_gases:
        Additional gas definitions to merge.
    overwrite:
        Whether extra gases may replace built-in entries with the same key.
    """
    registry = {name: replace(gas) for name, gas in _BUILTIN_GASES.items()}
    if not extra_gases:
        return registry

    for key, gas in extra_gases.items():
        normalized = key.strip()
        if not normalized:
            raise ValueError("Gas registry keys must be non-empty strings.")
        if normalized != gas.name.strip():
            raise ValueError(
                f"Registry key {normalized!r} does not match GasModel.name "
                f"{gas.name!r}."
            )
        if normalized in registry and not overwrite:
            raise KeyError(
                f"Gas {normalized!r} already exists in merged registry and "
                "overwrite=False."
            )
        registry[normalized] = replace(gas)
    return registry


def gas_to_dict(gas: GasModel) -> dict[str, object]:
    """
    Convert a gas model into a plain dictionary.

    This wrapper gives callers a simple import location for JSON-friendly gas
    snapshots without needing to know the dataclass internals.
    """
    return gas.to_dict()


def describe_gas(name: str) -> dict[str, object]:
    """
    Return a JSON-friendly dictionary for a named built-in gas.
    """
    return get_gas(name).to_dict()


__all__ = [
    "describe_gas",
    "gas_to_dict",
    "get_gas",
    "has_gas",
    "iter_builtin_gases",
    "list_builtin_gases",
    "merged_registry",
    "register_gas",
    "require_gas",
]