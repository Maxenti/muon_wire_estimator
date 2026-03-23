from __future__ import annotations

"""
Beta-spectrum helpers for Sr-90 / Y-90 source modeling.

This module provides lightweight, standard-library-only tools for working with
reasonably defined beta-particle source spectra in the muon wire estimator.

Scope
-----
The goal is not to reproduce a full nuclear-data-quality decay simulation.
Instead, this module provides transparent, deterministic utilities that are
good enough for source-side ionization estimates and event generation.

Supported spectrum families
---------------------------
- fixed-energy beta
- Sr-90 beta branch
- Y-90 beta branch
- combined Sr-90 + Y-90 source mixture

Modeling notes
--------------
For allowed beta decays, a simple spectral shape can be approximated by

    f(T) ∝ p * E * (T_max - T)^2

where:
- T is kinetic energy
- E = T + m_e c^2 is total energy
- p c = sqrt(E^2 - (m_e c^2)^2)

This is the classic phase-space-like shape for an allowed beta decay, without
adding a Fermi-function Coulomb correction. That omission is deliberate here:
the aim is a lightweight engineering estimator, not a precision decay package.

Sampling strategy
-----------------
This module uses deterministic rejection sampling with Python's standard
library RNG. The implementation is intended for typical event counts in the
O(10^2) to O(10^5) range and should remain practical for estimator workflows.

Conventions
-----------
All beta energies are kinetic energies in MeV.
"""

import math
from dataclasses import dataclass
from typing import Iterable, Literal

from .source_models import BetaSpectrumModel
from .randomness import SeededRNG, make_rng


ELECTRON_REST_MASS_MEV = 0.51099895

# Endpoint energies in MeV for the two branches.
# These are standard approximate endpoint kinetic energies commonly quoted for:
# - Sr-90 -> Y-90 beta decay
# - Y-90 -> Zr-90 beta decay
SR90_BETA_ENDPOINT_MEV = 0.546
Y90_BETA_ENDPOINT_MEV = 2.280

# In secular equilibrium, Y-90 activity closely tracks the parent activity.
# A 50/50 branch-choice model is a reasonable simple source surrogate when
# both branches are intended to be present in a long-lived source.
DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT = 0.5


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


@dataclass(slots=True)
class BetaBranch:
    """
    Description of a single beta-emitting branch.

    Parameters
    ----------
    name:
        Human-readable branch label.
    endpoint_energy_mev:
        Kinetic-energy endpoint for the beta branch.
    branch_weight:
        Relative weight used only when combining multiple branches into a source
        mixture. Does not need to be normalized a priori.
    notes:
        Optional descriptive note.
    """

    name: str
    endpoint_energy_mev: float
    branch_weight: float = 1.0
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string.")
        _ensure_positive("endpoint_energy_mev", self.endpoint_energy_mev)
        _ensure_positive("branch_weight", self.branch_weight, allow_zero=True)

    def to_dict(self) -> dict[str, str | float]:
        return {
            "name": self.name,
            "endpoint_energy_mev": self.endpoint_energy_mev,
            "branch_weight": self.branch_weight,
            "notes": self.notes,
        }


@dataclass(slots=True)
class SampledBetaEnergy:
    """
    Result of sampling a beta energy from a named spectrum family.

    Parameters
    ----------
    spectrum_model:
        Spectrum family used.
    branch_name:
        Name of the specific branch chosen for the sample.
    kinetic_energy_mev:
        Sampled beta kinetic energy in MeV.
    endpoint_energy_mev:
        Endpoint kinetic energy of the chosen branch in MeV.
    metadata:
        Small JSON-friendly metadata dictionary.
    """

    spectrum_model: BetaSpectrumModel
    branch_name: str
    kinetic_energy_mev: float
    endpoint_energy_mev: float
    metadata: dict[str, str | float | bool]

    def __post_init__(self) -> None:
        _ensure_literal(
            "spectrum_model",
            self.spectrum_model,
            {"fixed_energy", "sr90", "y90", "sr90_y90_combined"},
        )
        if not self.branch_name or not self.branch_name.strip():
            raise ValueError("branch_name must be a non-empty string.")
        _ensure_positive("kinetic_energy_mev", self.kinetic_energy_mev, allow_zero=True)
        _ensure_positive("endpoint_energy_mev", self.endpoint_energy_mev)
        if self.kinetic_energy_mev > self.endpoint_energy_mev + 1.0e-12:
            raise ValueError(
                "kinetic_energy_mev cannot exceed endpoint_energy_mev, got "
                f"{self.kinetic_energy_mev!r} > {self.endpoint_energy_mev!r}."
            )

    def to_dict(self) -> dict[str, str | float | bool | dict[str, str | float | bool]]:
        return {
            "spectrum_model": self.spectrum_model,
            "branch_name": self.branch_name,
            "kinetic_energy_mev": self.kinetic_energy_mev,
            "endpoint_energy_mev": self.endpoint_energy_mev,
            "metadata": dict(self.metadata),
        }


def sr90_branch() -> BetaBranch:
    """
    Return the canonical Sr-90 beta branch.
    """
    return BetaBranch(
        name="sr90",
        endpoint_energy_mev=SR90_BETA_ENDPOINT_MEV,
        branch_weight=1.0,
        notes="Sr-90 beta branch with approximate endpoint kinetic energy.",
    )


def y90_branch() -> BetaBranch:
    """
    Return the canonical Y-90 beta branch.
    """
    return BetaBranch(
        name="y90",
        endpoint_energy_mev=Y90_BETA_ENDPOINT_MEV,
        branch_weight=1.0,
        notes="Y-90 beta branch with approximate endpoint kinetic energy.",
    )


def combined_sr90_y90_branches(
    *,
    sr90_weight: float = DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT,
    y90_weight: float = DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT,
) -> list[BetaBranch]:
    """
    Return a simple combined Sr-90/Y-90 source mixture.

    The default 50/50 weighting is a practical surrogate for a mature source
    where both activities contribute comparably.
    """
    _ensure_positive("sr90_weight", sr90_weight, allow_zero=True)
    _ensure_positive("y90_weight", y90_weight, allow_zero=True)
    if sr90_weight == 0.0 and y90_weight == 0.0:
        raise ValueError("At least one branch weight must be > 0.")

    sr = sr90_branch()
    yr = y90_branch()
    sr.branch_weight = sr90_weight
    yr.branch_weight = y90_weight
    return [sr, yr]


def beta_total_energy_mev(kinetic_energy_mev: float) -> float:
    """
    Return the total beta energy (including rest mass) in MeV.
    """
    _ensure_positive("kinetic_energy_mev", kinetic_energy_mev, allow_zero=True)
    return kinetic_energy_mev + ELECTRON_REST_MASS_MEV


def beta_momentum_mev_over_c(kinetic_energy_mev: float) -> float:
    """
    Return beta momentum in MeV/c.
    """
    _ensure_positive("kinetic_energy_mev", kinetic_energy_mev, allow_zero=True)
    total = beta_total_energy_mev(kinetic_energy_mev)
    mass = ELECTRON_REST_MASS_MEV
    argument = total * total - mass * mass
    if argument < 0.0 and abs(argument) < 1.0e-15:
        argument = 0.0
    if argument < 0.0:
        raise ValueError(
            f"Momentum argument became negative for kinetic_energy_mev={kinetic_energy_mev!r}."
        )
    return math.sqrt(argument)


def allowed_beta_shape_unnormalized(
    kinetic_energy_mev: float,
    endpoint_energy_mev: float,
) -> float:
    """
    Return an unnormalized allowed-beta spectral density.

    Shape used
    ----------
    f(T) ∝ p * E * (T_max - T)^2

    where:
    - T is kinetic energy
    - E is total energy
    - p is momentum in MeV/c
    """
    _ensure_positive("endpoint_energy_mev", endpoint_energy_mev)
    if kinetic_energy_mev < 0.0:
        raise ValueError(
            f"kinetic_energy_mev must be >= 0, got {kinetic_energy_mev!r}."
        )
    if kinetic_energy_mev > endpoint_energy_mev:
        return 0.0

    total = beta_total_energy_mev(kinetic_energy_mev)
    momentum = beta_momentum_mev_over_c(kinetic_energy_mev)
    available = endpoint_energy_mev - kinetic_energy_mev
    return momentum * total * available * available


def estimate_allowed_beta_shape_peak(
    endpoint_energy_mev: float,
    *,
    n_grid: int = 2048,
) -> float:
    """
    Estimate the peak value of the allowed-beta shape on a grid.

    This is used for rejection sampling.
    """
    _ensure_positive("endpoint_energy_mev", endpoint_energy_mev)
    if n_grid < 16:
        raise ValueError(f"n_grid must be >= 16, got {n_grid!r}.")

    best = 0.0
    for i in range(n_grid + 1):
        t = endpoint_energy_mev * i / n_grid
        best = max(best, allowed_beta_shape_unnormalized(t, endpoint_energy_mev))
    return best


def sample_allowed_beta_energy_mev(
    endpoint_energy_mev: float,
    rng: SeededRNG,
    *,
    max_trials: int = 100000,
) -> float:
    """
    Sample beta kinetic energy from the allowed-beta approximation.

    Parameters
    ----------
    endpoint_energy_mev:
        Beta endpoint kinetic energy.
    rng:
        Deterministic RNG wrapper.
    max_trials:
        Safety cap for rejection sampling iterations.
    """
    _ensure_positive("endpoint_energy_mev", endpoint_energy_mev)
    if max_trials <= 0:
        raise ValueError(f"max_trials must be > 0, got {max_trials!r}.")
    if not isinstance(rng, SeededRNG):
        raise TypeError(f"rng must be a SeededRNG, got {type(rng).__name__}.")

    peak = estimate_allowed_beta_shape_peak(endpoint_energy_mev)
    if peak <= 0.0:
        return 0.0

    for _ in range(max_trials):
        trial_energy = rng.uniform(0.0, endpoint_energy_mev)
        trial_y = rng.uniform(0.0, peak)
        if trial_y <= allowed_beta_shape_unnormalized(trial_energy, endpoint_energy_mev):
            return trial_energy

    raise RuntimeError(
        "Failed to sample allowed beta energy within max_trials. "
        "This suggests a numerical or configuration issue."
    )


def sample_branch_by_weight(
    branches: Iterable[BetaBranch],
    rng: SeededRNG,
) -> BetaBranch:
    """
    Sample a beta branch from relative branch weights.
    """
    if not isinstance(rng, SeededRNG):
        raise TypeError(f"rng must be a SeededRNG, got {type(rng).__name__}.")

    branch_list = list(branches)
    if not branch_list:
        raise ValueError("branches must be non-empty.")

    weights = [branch.branch_weight for branch in branch_list]
    total = sum(weights)
    if total <= 0.0:
        raise ValueError("At least one branch must have positive weight.")

    index = rng.choice_index_from_weights(weights)
    return branch_list[index]


def sample_sr90_beta_energy(
    rng: SeededRNG,
) -> SampledBetaEnergy:
    """
    Sample a kinetic energy from the Sr-90 branch.
    """
    if not isinstance(rng, SeededRNG):
        raise TypeError(f"rng must be a SeededRNG, got {type(rng).__name__}.")

    branch = sr90_branch()
    energy = sample_allowed_beta_energy_mev(branch.endpoint_energy_mev, rng)
    return SampledBetaEnergy(
        spectrum_model="sr90",
        branch_name=branch.name,
        kinetic_energy_mev=energy,
        endpoint_energy_mev=branch.endpoint_energy_mev,
        metadata={
            "sampler": "allowed_beta_rejection",
            "branch_weight": branch.branch_weight,
        },
    )


def sample_y90_beta_energy(
    rng: SeededRNG,
) -> SampledBetaEnergy:
    """
    Sample a kinetic energy from the Y-90 branch.
    """
    if not isinstance(rng, SeededRNG):
        raise TypeError(f"rng must be a SeededRNG, got {type(rng).__name__}.")

    branch = y90_branch()
    energy = sample_allowed_beta_energy_mev(branch.endpoint_energy_mev, rng)
    return SampledBetaEnergy(
        spectrum_model="y90",
        branch_name=branch.name,
        kinetic_energy_mev=energy,
        endpoint_energy_mev=branch.endpoint_energy_mev,
        metadata={
            "sampler": "allowed_beta_rejection",
            "branch_weight": branch.branch_weight,
        },
    )


def sample_combined_sr90_y90_beta_energy(
    rng: SeededRNG,
    *,
    sr90_weight: float = DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT,
    y90_weight: float = DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT,
) -> SampledBetaEnergy:
    """
    Sample from a combined Sr-90/Y-90 source mixture.
    """
    if not isinstance(rng, SeededRNG):
        raise TypeError(f"rng must be a SeededRNG, got {type(rng).__name__}.")

    branches = combined_sr90_y90_branches(
        sr90_weight=sr90_weight,
        y90_weight=y90_weight,
    )
    chosen = sample_branch_by_weight(branches, rng)
    energy = sample_allowed_beta_energy_mev(chosen.endpoint_energy_mev, rng)
    return SampledBetaEnergy(
        spectrum_model="sr90_y90_combined",
        branch_name=chosen.name,
        kinetic_energy_mev=energy,
        endpoint_energy_mev=chosen.endpoint_energy_mev,
        metadata={
            "sampler": "allowed_beta_rejection",
            "branch_weight": chosen.branch_weight,
            "sr90_weight": sr90_weight,
            "y90_weight": y90_weight,
        },
    )


def fixed_beta_energy_sample(
    kinetic_energy_mev: float,
) -> SampledBetaEnergy:
    """
    Return a deterministic fixed-energy beta sample.

    Useful for deterministic scans or reference points.
    """
    _ensure_positive("kinetic_energy_mev", kinetic_energy_mev, allow_zero=True)
    return SampledBetaEnergy(
        spectrum_model="fixed_energy",
        branch_name="fixed_energy",
        kinetic_energy_mev=kinetic_energy_mev,
        endpoint_energy_mev=kinetic_energy_mev if kinetic_energy_mev > 0.0 else 1.0e-30,
        metadata={
            "sampler": "fixed_value",
        },
    )


def sample_beta_energy(
    spectrum_model: BetaSpectrumModel,
    *,
    rng: SeededRNG | None = None,
    fixed_beta_energy_mev: float | None = None,
    sr90_weight: float = DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT,
    y90_weight: float = DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT,
) -> SampledBetaEnergy:
    """
    Generic dispatcher for beta-energy sampling.

    Parameters
    ----------
    spectrum_model:
        One of the supported beta spectrum families.
    rng:
        Deterministic RNG. Required for non-fixed spectra.
    fixed_beta_energy_mev:
        Used only when spectrum_model == 'fixed_energy'.
    sr90_weight, y90_weight:
        Relative branch weights for the combined source model.
    """
    _ensure_literal(
        "spectrum_model",
        spectrum_model,
        {"fixed_energy", "sr90", "y90", "sr90_y90_combined"},
    )

    if spectrum_model == "fixed_energy":
        if fixed_beta_energy_mev is None:
            raise ValueError(
                "fixed_beta_energy_mev must be provided when spectrum_model == 'fixed_energy'."
            )
        return fixed_beta_energy_sample(fixed_beta_energy_mev)

    if rng is None:
        raise ValueError("rng must be provided for stochastic beta spectrum sampling.")

    if spectrum_model == "sr90":
        return sample_sr90_beta_energy(rng)
    if spectrum_model == "y90":
        return sample_y90_beta_energy(rng)
    return sample_combined_sr90_y90_beta_energy(
        rng,
        sr90_weight=sr90_weight,
        y90_weight=y90_weight,
    )


def mean_beta_energy_mev_approx(
    spectrum_model: BetaSpectrumModel,
    *,
    fixed_beta_energy_mev: float | None = None,
    sr90_weight: float = DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT,
    y90_weight: float = DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT,
    seed: int = 12345,
    n_samples: int = 20000,
) -> float:
    """
    Estimate the mean beta kinetic energy by Monte Carlo sampling.

    This is intentionally simple and deterministic for a fixed seed. It is
    useful for deterministic source-side surrogates when a representative
    mean beta energy is needed from a chosen spectrum model.
    """
    if n_samples <= 0:
        raise ValueError(f"n_samples must be > 0, got {n_samples!r}.")
    rng = make_rng(seed)
    total = 0.0
    for _ in range(n_samples):
        sample = sample_beta_energy(
            spectrum_model,
            rng=rng,
            fixed_beta_energy_mev=fixed_beta_energy_mev,
            sr90_weight=sr90_weight,
            y90_weight=y90_weight,
        )
        total += sample.kinetic_energy_mev
    return total / float(n_samples)


__all__ = [
    "BetaBranch",
    "DEFAULT_SR90_Y90_COMBINED_BRANCH_WEIGHT",
    "ELECTRON_REST_MASS_MEV",
    "SR90_BETA_ENDPOINT_MEV",
    "SampledBetaEnergy",
    "Y90_BETA_ENDPOINT_MEV",
    "allowed_beta_shape_unnormalized",
    "beta_momentum_mev_over_c",
    "beta_total_energy_mev",
    "combined_sr90_y90_branches",
    "estimate_allowed_beta_shape_peak",
    "fixed_beta_energy_sample",
    "mean_beta_energy_mev_approx",
    "sample_allowed_beta_energy_mev",
    "sample_beta_energy",
    "sample_branch_by_weight",
    "sample_combined_sr90_y90_beta_energy",
    "sample_sr90_beta_energy",
    "sample_y90_beta_energy",
    "sr90_branch",
    "y90_branch",
]