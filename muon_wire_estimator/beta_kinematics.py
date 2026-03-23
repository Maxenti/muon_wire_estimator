from __future__ import annotations

"""
Relativistic kinematics helpers for beta-particle source modeling.

This module provides lightweight, standard-library-only utilities for
converting beta-particle kinetic energy into commonly needed kinematic
quantities for source-side ionization estimates.

Scope
-----
The functions here are intended for electrons/positrons in the energy range
relevant to Sr-90 / Y-90 beta emission and similar source-driven gas
ionization studies. The emphasis is on:

- clear formulas
- robust validation
- JSON-friendly summary objects
- compatibility with deterministic and stochastic source workflows

Conventions
-----------
All energies are expressed in MeV unless stated otherwise.

For an electron with kinetic energy T:

    E_total = T + m_e c^2
    p c     = sqrt(E_total^2 - (m_e c^2)^2)
    gamma   = E_total / (m_e c^2)
    beta    = p c / E_total

This module uses c = 1 units internally for energy-momentum relations, then
returns any derived SI velocities explicitly when requested.

Design goals
------------
- standard-library only
- deterministic
- no hidden global state
- easy to test
"""

import math
from dataclasses import dataclass
from typing import Any


SPEED_OF_LIGHT_M_PER_S = 299_792_458.0
ELECTRON_REST_MASS_MEV = 0.51099895
ELECTRON_REST_ENERGY_J = ELECTRON_REST_MASS_MEV * 1.0e6 * 1.602176634e-19
MEV_TO_J = 1.602176634e-13


JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


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


@dataclass(slots=True)
class BetaKinematics:
    """
    Compact relativistic kinematics summary for a beta particle.

    Parameters
    ----------
    kinetic_energy_mev:
        Particle kinetic energy in MeV.
    total_energy_mev:
        Total relativistic energy in MeV.
    momentum_mev_per_c:
        Relativistic momentum in MeV/c.
    gamma:
        Lorentz gamma factor.
    beta:
        Dimensionless velocity ratio v/c.
    velocity_m_per_s:
        Particle speed in m/s.
    momentum_si_kg_m_per_s:
        Relativistic momentum in SI units.
    metadata:
        Additional JSON-friendly metadata.
    """

    kinetic_energy_mev: float
    total_energy_mev: float
    momentum_mev_per_c: float
    gamma: float
    beta: float
    velocity_m_per_s: float
    momentum_si_kg_m_per_s: float
    metadata: dict[str, JSONValue]

    def __post_init__(self) -> None:
        _ensure_positive("kinetic_energy_mev", self.kinetic_energy_mev, allow_zero=True)
        _ensure_positive("total_energy_mev", self.total_energy_mev)
        _ensure_positive("momentum_mev_per_c", self.momentum_mev_per_c, allow_zero=True)
        _ensure_positive("gamma", self.gamma)
        _ensure_fraction("beta", self.beta)
        _ensure_positive("velocity_m_per_s", self.velocity_m_per_s, allow_zero=True)
        _ensure_positive(
            "momentum_si_kg_m_per_s",
            self.momentum_si_kg_m_per_s,
            allow_zero=True,
        )

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "kinetic_energy_mev": self.kinetic_energy_mev,
            "total_energy_mev": self.total_energy_mev,
            "momentum_mev_per_c": self.momentum_mev_per_c,
            "gamma": self.gamma,
            "beta": self.beta,
            "velocity_m_per_s": self.velocity_m_per_s,
            "momentum_si_kg_m_per_s": self.momentum_si_kg_m_per_s,
            "metadata": dict(self.metadata),
        }


def total_energy_mev(kinetic_energy_mev: float) -> float:
    """
    Return total relativistic energy in MeV.

    E_total = T + m_e c^2
    """
    _ensure_positive("kinetic_energy_mev", kinetic_energy_mev, allow_zero=True)
    return kinetic_energy_mev + ELECTRON_REST_MASS_MEV


def gamma_from_kinetic_energy(kinetic_energy_mev: float) -> float:
    """
    Return the Lorentz gamma factor from kinetic energy.
    """
    total = total_energy_mev(kinetic_energy_mev)
    return total / ELECTRON_REST_MASS_MEV


def momentum_mev_per_c(kinetic_energy_mev: float) -> float:
    """
    Return relativistic momentum in MeV/c.

    p c = sqrt(E_total^2 - (m_e c^2)^2)
    """
    total = total_energy_mev(kinetic_energy_mev)
    mass = ELECTRON_REST_MASS_MEV
    argument = total * total - mass * mass
    if argument < 0.0 and abs(argument) < 1.0e-15:
        argument = 0.0
    if argument < 0.0:
        raise ValueError(
            "Momentum argument became negative for kinetic energy "
            f"{kinetic_energy_mev!r} MeV."
        )
    return math.sqrt(argument)


def beta_from_kinetic_energy(kinetic_energy_mev: float) -> float:
    """
    Return the dimensionless speed beta = v/c.
    """
    total = total_energy_mev(kinetic_energy_mev)
    if total <= 0.0:
        raise ValueError(f"Computed non-positive total energy {total!r}.")
    p = momentum_mev_per_c(kinetic_energy_mev)
    beta = p / total
    # Guard against tiny numerical excursions above 1.
    if beta > 1.0 and beta - 1.0 < 1.0e-14:
        beta = 1.0
    _ensure_fraction("beta", beta)
    return beta


def velocity_m_per_s(kinetic_energy_mev: float) -> float:
    """
    Return particle speed in m/s.
    """
    return beta_from_kinetic_energy(kinetic_energy_mev) * SPEED_OF_LIGHT_M_PER_S


def momentum_si_kg_m_per_s(kinetic_energy_mev: float) -> float:
    """
    Return relativistic momentum in SI units.

    Conversion
    ----------
    If p is in MeV/c, then:

        p_SI = (p * MeV_to_J) / c
    """
    p_mev_per_c = momentum_mev_per_c(kinetic_energy_mev)
    return (p_mev_per_c * MEV_TO_J) / SPEED_OF_LIGHT_M_PER_S


def kinetic_energy_mev_from_beta(beta: float) -> float:
    """
    Invert beta -> kinetic energy in MeV.
    """
    _ensure_fraction("beta", beta)
    if beta == 1.0:
        raise ValueError("beta = 1.0 would imply infinite kinetic energy.")
    gamma = 1.0 / math.sqrt(1.0 - beta * beta)
    return (gamma - 1.0) * ELECTRON_REST_MASS_MEV


def kinetic_energy_mev_from_gamma(gamma: float) -> float:
    """
    Invert gamma -> kinetic energy in MeV.
    """
    _ensure_positive("gamma", gamma)
    if gamma < 1.0:
        raise ValueError(f"gamma must be >= 1, got {gamma!r}.")
    return (gamma - 1.0) * ELECTRON_REST_MASS_MEV


def kinetic_energy_mev_from_momentum_mev_per_c(p_mev_per_c: float) -> float:
    """
    Invert momentum (MeV/c) -> kinetic energy in MeV.
    """
    _ensure_positive("p_mev_per_c", p_mev_per_c, allow_zero=True)
    total = math.sqrt(
        p_mev_per_c * p_mev_per_c + ELECTRON_REST_MASS_MEV * ELECTRON_REST_MASS_MEV
    )
    return total - ELECTRON_REST_MASS_MEV


def beta_rigidity_like_mev_per_c(beta_value: float) -> float:
    """
    Return p = beta * gamma * m in MeV/c for an electron.

    This is sometimes useful in quick transport surrogates.
    """
    _ensure_fraction("beta_value", beta_value)
    if beta_value == 1.0:
        raise ValueError("beta_value = 1.0 would imply infinite momentum.")
    gamma = 1.0 / math.sqrt(1.0 - beta_value * beta_value)
    return beta_value * gamma * ELECTRON_REST_MASS_MEV


def build_beta_kinematics(
    kinetic_energy_mev: float,
    *,
    metadata: dict[str, JSONValue] | None = None,
) -> BetaKinematics:
    """
    Build a complete BetaKinematics summary from kinetic energy.
    """
    _ensure_positive("kinetic_energy_mev", kinetic_energy_mev, allow_zero=True)

    total = total_energy_mev(kinetic_energy_mev)
    gamma = gamma_from_kinetic_energy(kinetic_energy_mev)
    beta = beta_from_kinetic_energy(kinetic_energy_mev)
    momentum = momentum_mev_per_c(kinetic_energy_mev)
    velocity = velocity_m_per_s(kinetic_energy_mev)
    momentum_si = momentum_si_kg_m_per_s(kinetic_energy_mev)

    return BetaKinematics(
        kinetic_energy_mev=kinetic_energy_mev,
        total_energy_mev=total,
        momentum_mev_per_c=momentum,
        gamma=gamma,
        beta=beta,
        velocity_m_per_s=velocity,
        momentum_si_kg_m_per_s=momentum_si,
        metadata={} if metadata is None else dict(metadata),
    )


def beta_kinematics_from_mapping(data: dict[str, Any]) -> BetaKinematics:
    """
    Build BetaKinematics from a mapping containing at least
    ``kinetic_energy_mev``.
    """
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dictionary, got {type(data).__name__}.")
    if "kinetic_energy_mev" not in data:
        raise KeyError("Missing required field 'kinetic_energy_mev'.")
    metadata = data.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise TypeError(
            f"metadata must be a dictionary when provided, got {type(metadata).__name__}."
        )
    return build_beta_kinematics(
        float(data["kinetic_energy_mev"]),
        metadata={} if metadata is None else metadata,
    )


__all__ = [
    "BetaKinematics",
    "ELECTRON_REST_ENERGY_J",
    "ELECTRON_REST_MASS_MEV",
    "MEV_TO_J",
    "SPEED_OF_LIGHT_M_PER_S",
    "beta_from_kinetic_energy",
    "beta_kinematics_from_mapping",
    "beta_rigidity_like_mev_per_c",
    "build_beta_kinematics",
    "gamma_from_kinetic_energy",
    "kinetic_energy_mev_from_beta",
    "kinetic_energy_mev_from_gamma",
    "kinetic_energy_mev_from_momentum_mev_per_c",
    "momentum_mev_per_c",
    "momentum_si_kg_m_per_s",
    "total_energy_mev",
    "velocity_m_per_s",
]