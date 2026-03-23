from __future__ import annotations

"""
Beta-particle ionization surrogates for the muon wire estimator.

This module provides a lightweight source-side ionization model for reasonably
defined beta particles, especially Sr-90 / Y-90 source electrons, so the
existing detector-response chain can be reused:

    source beta -> deposited energy in gas -> created primary electrons
                -> drift / attachment -> gain -> pulse

Scope
-----
This is an engineering estimator, not a full electron-transport Monte Carlo.
The model is designed to be:

- standard-library only
- deterministic or stochastic depending on source configuration
- explicit about assumptions
- easy to calibrate later

Main responsibilities
---------------------
- estimate a representative beta kinetic energy
- estimate active path length in gas
- estimate deposited energy in gas
- convert deposited energy to primary ionization
- provide both deterministic and event-level stochastic summaries

Modeling philosophy
-------------------
The beta source model is intentionally factorized into:

1. source-spectrum choice
2. source-to-active-region geometry acceptance
3. approximate active path length
4. approximate energy deposition in the gas
5. conversion to ion pairs via W-value

This allows downstream detector collection / gain / pulse code to remain
mostly unchanged.

Important limitation
--------------------
The deposited-energy model here is an approximate surrogate. It does not
attempt a detailed electron stopping-power or multiple-scattering simulation.
Instead it uses an energy-dependent effective stopping-power curve suitable for
rough comparisons between gases, wire geometries, and source placements.
"""

import math
from dataclasses import dataclass
from typing import Any

from .beta_kinematics import build_beta_kinematics
from .beta_spectrum import (
    SampledBetaEnergy,
    mean_beta_energy_mev_approx,
    sample_beta_energy,
)
from .gases import GasModel, get_gas
from .source_geometry import (
    SourceGeometryConfig,
    active_path_length_cm,
    source_geometry_from_mapping,
    source_survival_to_active_region_probability,
)
from .source_models import (
    JSONValue,
    SourceEventSummary,
    SourceIonizationEstimate,
    Sr90BetaSourceConfig,
    sr90_beta_source_config_from_mapping,
)
from .randomness import SeededRNG


def _ensure_positive(name: str, value: float, *, allow_zero: bool = False) -> None:
    if allow_zero:
        if value < 0.0:
            raise ValueError(f"{name} must be >= 0, got {value!r}.")
        return
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0, got {value!r}.")


def _ensure_non_negative_int(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value!r}.")


@dataclass(slots=True)
class BetaIonizationModel:
    """
    Parameters controlling the approximate beta energy-deposition surrogate.

    Parameters
    ----------
    reference_stopping_power_mev_per_cm:
        Effective stopping power at the reference energy.
    reference_energy_mev:
        Reference beta kinetic energy.
    low_energy_exponent:
        Controls the rise in stopping power at lower kinetic energies.
    minimum_stopping_power_mev_per_cm:
        Lower floor to avoid vanishing deposition at high energies.
    maximum_stopping_power_mev_per_cm:
        Upper cap to avoid pathological divergence at very low energies.
    notes:
        Optional human-readable model note.
    """

    reference_stopping_power_mev_per_cm: float
    reference_energy_mev: float
    low_energy_exponent: float = 0.7
    minimum_stopping_power_mev_per_cm: float = 0.001
    maximum_stopping_power_mev_per_cm: float = 0.05
    notes: str = ""

    def __post_init__(self) -> None:
        _ensure_positive(
            "reference_stopping_power_mev_per_cm",
            self.reference_stopping_power_mev_per_cm,
        )
        _ensure_positive("reference_energy_mev", self.reference_energy_mev)
        _ensure_positive("low_energy_exponent", self.low_energy_exponent)
        _ensure_positive(
            "minimum_stopping_power_mev_per_cm",
            self.minimum_stopping_power_mev_per_cm,
        )
        _ensure_positive(
            "maximum_stopping_power_mev_per_cm",
            self.maximum_stopping_power_mev_per_cm,
        )
        if (
            self.minimum_stopping_power_mev_per_cm
            > self.maximum_stopping_power_mev_per_cm
        ):
            raise ValueError(
                "minimum_stopping_power_mev_per_cm cannot exceed "
                "maximum_stopping_power_mev_per_cm."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "reference_stopping_power_mev_per_cm": self.reference_stopping_power_mev_per_cm,
            "reference_energy_mev": self.reference_energy_mev,
            "low_energy_exponent": self.low_energy_exponent,
            "minimum_stopping_power_mev_per_cm": self.minimum_stopping_power_mev_per_cm,
            "maximum_stopping_power_mev_per_cm": self.maximum_stopping_power_mev_per_cm,
            "notes": self.notes,
        }


def resolve_gas(gas: GasModel | str) -> GasModel:
    """
    Resolve either a GasModel object or a built-in gas name.
    """
    if isinstance(gas, GasModel):
        return gas
    if isinstance(gas, str):
        return get_gas(gas)
    raise TypeError(f"gas must be GasModel or str, got {type(gas).__name__}.")


def default_beta_ionization_model_for_gas(gas: GasModel | str) -> BetaIonizationModel:
    """
    Return a simple gas-specific beta energy-deposition surrogate.

    Design intent
    -------------
    This uses the gas's existing mean energy-loss scale as an anchor while
    allowing stronger stopping at lower beta energies than the nearly constant
    minimum-ionizing muon-like value. It is intentionally conservative and easy
    to calibrate later.

    The resulting model is not a precision stopping-power calculation. It is a
    transparent source-side surrogate for comparative detector studies.
    """
    gas_model = resolve_gas(gas)

    if gas_model.name == "air_dry_1atm":
        return BetaIonizationModel(
            reference_stopping_power_mev_per_cm=0.0030,
            reference_energy_mev=1.0,
            low_energy_exponent=0.75,
            minimum_stopping_power_mev_per_cm=0.0015,
            maximum_stopping_power_mev_per_cm=0.03,
            notes="Conservative beta stopping-power surrogate for dry air at 1 atm.",
        )

    if gas_model.name in {"ar_co2_70_30_1atm", "ar_co2_75_25_1atm"}:
        return BetaIonizationModel(
            reference_stopping_power_mev_per_cm=0.0045,
            reference_energy_mev=1.0,
            low_energy_exponent=0.80,
            minimum_stopping_power_mev_per_cm=0.0020,
            maximum_stopping_power_mev_per_cm=0.04,
            notes="Conservative beta stopping-power surrogate for Ar/CO2 at 1 atm.",
        )

    # Fallback generic gas surrogate.
    anchor = max(gas_model.mean_energy_loss_mev_per_cm, 1.0e-6)
    return BetaIonizationModel(
        reference_stopping_power_mev_per_cm=max(1.5 * anchor, 0.001),
        reference_energy_mev=1.0,
        low_energy_exponent=0.75,
        minimum_stopping_power_mev_per_cm=max(anchor, 0.0005),
        maximum_stopping_power_mev_per_cm=max(10.0 * anchor, 0.02),
        notes=(
            "Generic beta stopping-power surrogate derived from the gas-level "
            "mean_energy_loss_mev_per_cm anchor."
        ),
    )


def effective_beta_stopping_power_mev_per_cm(
    kinetic_energy_mev: float,
    gas: GasModel | str,
    *,
    model: BetaIonizationModel | None = None,
) -> float:
    """
    Estimate an effective beta stopping power in the gas.

    Surrogate form
    --------------
    A simple low-energy-enhanced power-law surrogate is used:

        S(T) = S_ref * (T_ref / max(T, T_floor))^alpha

    then clamped into [S_min, S_max].

    This captures the qualitative fact that lower-energy electrons tend to
    deposit energy more strongly per unit path in the gas.
    """
    _ensure_positive("kinetic_energy_mev", kinetic_energy_mev, allow_zero=True)
    gas_model = resolve_gas(gas)
    if model is None:
        model = default_beta_ionization_model_for_gas(gas_model)

    t_floor = max(kinetic_energy_mev, 0.01)
    raw = model.reference_stopping_power_mev_per_cm * (
        model.reference_energy_mev / t_floor
    ) ** model.low_energy_exponent

    return min(
        max(raw, model.minimum_stopping_power_mev_per_cm),
        model.maximum_stopping_power_mev_per_cm,
    )


def deposited_energy_mev_for_beta(
    kinetic_energy_mev: float,
    gas: GasModel | str,
    source_geometry: SourceGeometryConfig,
    *,
    model: BetaIonizationModel | None = None,
) -> float:
    """
    Estimate deposited energy in the active gas from a beta particle.

    Model
    -----
    The deposited energy is the lesser of:
    - stopping_power * active_path_length
    - available kinetic energy

    multiplied by the source-geometry survival/acceptance probability.

    This keeps the estimate conservative and avoids depositing more energy than
    the beta actually carries.
    """
    _ensure_positive("kinetic_energy_mev", kinetic_energy_mev, allow_zero=True)
    gas_model = resolve_gas(gas)

    survival = source_survival_to_active_region_probability(source_geometry)
    if survival <= 0.0 or kinetic_energy_mev <= 0.0:
        return 0.0

    path_length_cm = active_path_length_cm(source_geometry)
    stopping_power = effective_beta_stopping_power_mev_per_cm(
        kinetic_energy_mev,
        gas_model,
        model=model,
    )

    candidate = stopping_power * path_length_cm
    deposited = min(candidate, kinetic_energy_mev)
    return deposited * survival


def primary_electrons_from_deposited_energy(
    deposited_energy_mev: float,
    gas: GasModel | str,
) -> float:
    """
    Convert deposited energy into mean primary-electron count using the gas W-value.
    """
    _ensure_positive("deposited_energy_mev", deposited_energy_mev, allow_zero=True)
    gas_model = resolve_gas(gas)
    if deposited_energy_mev == 0.0:
        return 0.0
    return deposited_energy_mev * 1.0e6 / gas_model.w_value_ev


def estimate_beta_ionization(
    source_config: Sr90BetaSourceConfig,
    gas: GasModel | str,
    source_geometry: SourceGeometryConfig,
    *,
    seed_for_mean_energy: int = 12345,
    mean_energy_samples: int = 20000,
    model: BetaIonizationModel | None = None,
) -> SourceIonizationEstimate:
    """
    Deterministically estimate source-side ionization from a beta source config.

    Strategy
    --------
    - If the source uses fixed_energy, use it directly.
    - Otherwise estimate the representative mean beta energy by deterministic
      Monte Carlo sampling with a fixed seed.
    - Convert that representative energy into deposited energy and then into
      primary ionization.

    This makes the output deterministic while still reflecting the chosen
    source-spectrum model.
    """
    if not isinstance(source_config, Sr90BetaSourceConfig):
        raise TypeError(
            "source_config must be Sr90BetaSourceConfig, "
            f"got {type(source_config).__name__}."
        )

    gas_model = resolve_gas(gas)

    if source_config.spectrum_model == "fixed_energy":
        if source_config.fixed_beta_energy_mev is None:
            raise ValueError(
                "fixed_beta_energy_mev must be set for fixed_energy beta source."
            )
        representative_energy = source_config.fixed_beta_energy_mev
    else:
        representative_energy = mean_beta_energy_mev_approx(
            source_config.spectrum_model,
            fixed_beta_energy_mev=source_config.fixed_beta_energy_mev,
            sr90_weight=1.0 if source_config.include_sr90_branch else 0.0,
            y90_weight=1.0 if source_config.include_y90_branch else 0.0,
            seed=seed_for_mean_energy,
            n_samples=mean_energy_samples,
        )

    deposited_mev = deposited_energy_mev_for_beta(
        representative_energy,
        gas_model,
        source_geometry,
        model=model,
    )
    primary_electrons = primary_electrons_from_deposited_energy(
        deposited_mev,
        gas_model,
    )
    survival = source_survival_to_active_region_probability(source_geometry)

    stopping_power = effective_beta_stopping_power_mev_per_cm(
        representative_energy,
        gas_model,
        model=model,
    )
    kin = build_beta_kinematics(representative_energy)

    metadata: dict[str, JSONValue] = {
        "spectrum_model": source_config.spectrum_model,
        "fixed_beta_energy_mev": source_config.fixed_beta_energy_mev,
        "include_sr90_branch": source_config.include_sr90_branch,
        "include_y90_branch": source_config.include_y90_branch,
        "track_length_model": source_config.track_length_model,
        "source_geometry": source_geometry.to_dict(),
        "beta_kinematics": kin.to_dict(),
        "effective_beta_stopping_power_mev_per_cm": stopping_power,
        "beta_ionization_model": (
            default_beta_ionization_model_for_gas(gas_model).to_dict()
            if model is None
            else model.to_dict()
        ),
        "gas_name": gas_model.name,
        "gas_w_value_ev": gas_model.w_value_ev,
    }

    return SourceIonizationEstimate(
        source_type="sr90_beta",
        source_name="Sr-90 beta source",
        deposited_energy_mev=deposited_mev,
        primary_electrons_mean=primary_electrons,
        track_length_in_active_cm=active_path_length_cm(source_geometry),
        particle_kinetic_energy_mev=representative_energy,
        survival_to_active_region_probability=survival,
        metadata=metadata,
    )


def simulate_beta_source_event(
    event_index: int,
    source_config: Sr90BetaSourceConfig,
    gas: GasModel | str,
    source_geometry: SourceGeometryConfig,
    rng: SeededRNG,
    *,
    model: BetaIonizationModel | None = None,
) -> SourceEventSummary:
    """
    Simulate one stochastic beta-source event.

    The event-level summary includes:
    - sampled beta energy
    - source-geometry acceptance
    - deposited energy
    - created primary electrons
    """
    _ensure_non_negative_int("event_index", event_index)
    if not isinstance(source_config, Sr90BetaSourceConfig):
        raise TypeError(
            "source_config must be Sr90BetaSourceConfig, "
            f"got {type(source_config).__name__}."
        )
    if not isinstance(rng, SeededRNG):
        raise TypeError(f"rng must be SeededRNG, got {type(rng).__name__}.")

    gas_model = resolve_gas(gas)

    sampled_energy: SampledBetaEnergy = sample_beta_energy(
        source_config.spectrum_model,
        rng=rng,
        fixed_beta_energy_mev=source_config.fixed_beta_energy_mev,
        sr90_weight=1.0 if source_config.include_sr90_branch else 0.0,
        y90_weight=1.0 if source_config.include_y90_branch else 0.0,
    )

    survival_probability = source_survival_to_active_region_probability(source_geometry)
    entered_active_region = True
    if survival_probability < 1.0:
        entered_active_region = rng.bernoulli(survival_probability)

    if not entered_active_region:
        deposited_mev = 0.0
        created_primary_electrons = 0.0
        stopping_power = 0.0
    else:
        deposited_mev = deposited_energy_mev_for_beta(
            sampled_energy.kinetic_energy_mev,
            gas_model,
            source_geometry,
            model=model,
        )
        created_primary_electrons = primary_electrons_from_deposited_energy(
            deposited_mev,
            gas_model,
        )
        stopping_power = effective_beta_stopping_power_mev_per_cm(
            sampled_energy.kinetic_energy_mev,
            gas_model,
            model=model,
        )

    kin = build_beta_kinematics(sampled_energy.kinetic_energy_mev)

    metadata: dict[str, JSONValue] = {
        "sampled_beta": sampled_energy.to_dict(),
        "source_geometry": source_geometry.to_dict(),
        "beta_kinematics": kin.to_dict(),
        "effective_beta_stopping_power_mev_per_cm": stopping_power,
        "gas_name": gas_model.name,
    }

    return SourceEventSummary(
        event_index=event_index,
        source_type="sr90_beta",
        sampled_particle_energy_mev=sampled_energy.kinetic_energy_mev,
        deposited_energy_mev=deposited_mev,
        created_primary_electrons=created_primary_electrons,
        entered_active_region=entered_active_region,
        metadata=metadata,
    )


def source_ionization_estimate_to_dict(
    estimate: SourceIonizationEstimate,
) -> dict[str, JSONValue]:
    """
    Convert SourceIonizationEstimate to a JSON-friendly dictionary.
    """
    if not isinstance(estimate, SourceIonizationEstimate):
        raise TypeError(
            "estimate must be SourceIonizationEstimate, "
            f"got {type(estimate).__name__}."
        )
    return estimate.to_dict()


def source_event_summary_to_dict(
    summary: SourceEventSummary,
) -> dict[str, JSONValue]:
    """
    Convert SourceEventSummary to a JSON-friendly dictionary.
    """
    if not isinstance(summary, SourceEventSummary):
        raise TypeError(
            "summary must be SourceEventSummary, "
            f"got {type(summary).__name__}."
        )
    return summary.to_dict()


def estimate_beta_ionization_from_mapping(
    data: dict[str, Any],
    gas: GasModel | str,
) -> SourceIonizationEstimate:
    """
    Convenience helper to build beta source and source-geometry configs from a mapping.

    Expected structure
    ------------------
    {
      "source": { ... Sr90BetaSourceConfig fields ... },
      "source_geometry": { ... SourceGeometryConfig fields ... }
    }
    """
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dictionary, got {type(data).__name__}.")

    if "source" not in data:
        raise KeyError("Missing required top-level field 'source'.")
    if "source_geometry" not in data:
        raise KeyError("Missing required top-level field 'source_geometry'.")

    source_raw = data["source"]
    source_geometry_raw = data["source_geometry"]

    if not isinstance(source_raw, dict):
        raise TypeError(
            f"'source' must be a dictionary, got {type(source_raw).__name__}."
        )
    if not isinstance(source_geometry_raw, dict):
        raise TypeError(
            "'source_geometry' must be a dictionary, got "
            f"{type(source_geometry_raw).__name__}."
        )

    source_config = sr90_beta_source_config_from_mapping(source_raw)
    source_geometry = source_geometry_from_mapping(source_geometry_raw)

    return estimate_beta_ionization(source_config, gas, source_geometry)


__all__ = [
    "BetaIonizationModel",
    "default_beta_ionization_model_for_gas",
    "deposited_energy_mev_for_beta",
    "effective_beta_stopping_power_mev_per_cm",
    "estimate_beta_ionization",
    "estimate_beta_ionization_from_mapping",
    "primary_electrons_from_deposited_energy",
    "resolve_gas",
    "simulate_beta_source_event",
    "source_event_summary_to_dict",
    "source_ionization_estimate_to_dict",
]