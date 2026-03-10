"""
Ionization and primary-charge estimation helpers for the muon wire estimator.

This module provides lightweight, deterministic ionization calculations for the
Level 1 estimator. The intent is to preserve the spirit of the original
single-file script while separating out the pieces that later levels will
replace or augment with stochastic sampling and calibration.

Scope of this module
--------------------
- mean ionization energy loss in the active gas
- mean number of primary electron-ion pairs
- primary charge in Coulombs
- simple cluster-count surrogate for later stochastic use
- direct-image-pulse source charge estimate kept separate from avalanche logic

These functions are deliberately phenomenological. They are suitable for
engineering estimates and trend studies, not microscopic transport modeling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .gases import get_gas
from .geometry import direct_image_charge_sharing_factor, validate_geometry
from .models import GasModel, GeometryModel, JSONValue

ELECTRON_CHARGE_C = 1.602176634e-19
EV_PER_MEV = 1.0e6
CM_PER_M = 100.0


@dataclass(slots=True)
class IonizationEstimate:
    """
    Deterministic mean ionization estimate for one track segment.

    Attributes
    ----------
    track_length_m:
        Muon path length inside the active region used for ionization.
    energy_loss_mev:
        Mean energy loss across the active path in MeV.
    energy_loss_ev:
        Mean energy loss across the active path in eV.
    primary_electrons_mean:
        Mean number of produced primary electrons.
    primary_charge_c:
        Mean total primary ionization charge in Coulombs.
    mean_cluster_count:
        Mean number of primary clusters in a simple surrogate model.
    mean_electrons_per_cluster:
        Mean electrons per cluster in that surrogate model.
    metadata:
        JSON-friendly auxiliary information.
    """

    track_length_m: float
    energy_loss_mev: float
    energy_loss_ev: float
    primary_electrons_mean: float
    primary_charge_c: float
    mean_cluster_count: float
    mean_electrons_per_cluster: float
    metadata: dict[str, JSONValue]

    def __post_init__(self) -> None:
        if self.track_length_m < 0.0:
            raise ValueError(f"track_length_m must be >= 0, got {self.track_length_m!r}.")
        if self.energy_loss_mev < 0.0:
            raise ValueError(f"energy_loss_mev must be >= 0, got {self.energy_loss_mev!r}.")
        if self.energy_loss_ev < 0.0:
            raise ValueError(f"energy_loss_ev must be >= 0, got {self.energy_loss_ev!r}.")
        if self.primary_electrons_mean < 0.0:
            raise ValueError(
                f"primary_electrons_mean must be >= 0, got {self.primary_electrons_mean!r}."
            )
        if self.primary_charge_c < 0.0:
            raise ValueError(f"primary_charge_c must be >= 0, got {self.primary_charge_c!r}.")
        if self.mean_cluster_count < 0.0:
            raise ValueError(
                f"mean_cluster_count must be >= 0, got {self.mean_cluster_count!r}."
            )
        if self.mean_electrons_per_cluster <= 0.0:
            raise ValueError(
                "mean_electrons_per_cluster must be > 0, "
                f"got {self.mean_electrons_per_cluster!r}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "track_length_m": self.track_length_m,
            "energy_loss_mev": self.energy_loss_mev,
            "energy_loss_ev": self.energy_loss_ev,
            "primary_electrons_mean": self.primary_electrons_mean,
            "primary_charge_c": self.primary_charge_c,
            "mean_cluster_count": self.mean_cluster_count,
            "mean_electrons_per_cluster": self.mean_electrons_per_cluster,
            "metadata": dict(self.metadata),
        }


def validate_gas(gas: GasModel) -> GasModel:
    """Validate and return a gas model."""
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


def track_energy_loss_mev(track_length_m: float, gas: GasModel | str) -> float:
    """
    Estimate the mean muon energy loss over a given path length.

    Parameters
    ----------
    track_length_m:
        Path length through the active medium in meters.
    gas:
        Gas model or built-in gas name.

    Returns
    -------
    float
        Mean energy loss in MeV.
    """
    if track_length_m < 0.0:
        raise ValueError(f"track_length_m must be >= 0, got {track_length_m!r}.")
    gas_model = resolve_gas(gas)
    return gas_model.mean_energy_loss_mev_per_cm * track_length_m * CM_PER_M


def track_energy_loss_ev(track_length_m: float, gas: GasModel | str) -> float:
    """
    Estimate the mean muon energy loss over a given path length in eV.
    """
    return track_energy_loss_mev(track_length_m, gas) * EV_PER_MEV


def mean_primary_electrons_from_energy_loss(energy_loss_ev: float, gas: GasModel | str) -> float:
    """
    Convert mean energy loss into a mean number of primary electrons.

    The estimate uses the gas W-value:
        N_mean = DeltaE / W

    Parameters
    ----------
    energy_loss_ev:
        Mean energy deposition in eV.
    gas:
        Gas model or built-in gas name.
    """
    if energy_loss_ev < 0.0:
        raise ValueError(f"energy_loss_ev must be >= 0, got {energy_loss_ev!r}.")
    gas_model = resolve_gas(gas)
    return energy_loss_ev / gas_model.w_value_ev if energy_loss_ev > 0.0 else 0.0


def mean_primary_charge_c(primary_electrons_mean: float) -> float:
    """
    Convert a mean electron count into charge in Coulombs.
    """
    if primary_electrons_mean < 0.0:
        raise ValueError(
            f"primary_electrons_mean must be >= 0, got {primary_electrons_mean!r}."
        )
    return primary_electrons_mean * ELECTRON_CHARGE_C


def mean_cluster_count(primary_electrons_mean: float, gas: GasModel | str) -> float:
    """
    Estimate a mean number of primary clusters.

    This is a simple surrogate:
        N_clusters = N_electrons / <cluster size>

    It is included now because Level 2 stochastic sampling will naturally build
    on the same notion.
    """
    if primary_electrons_mean < 0.0:
        raise ValueError(
            f"primary_electrons_mean must be >= 0, got {primary_electrons_mean!r}."
        )
    gas_model = resolve_gas(gas)
    return (
        primary_electrons_mean / gas_model.mean_cluster_size_electrons
        if primary_electrons_mean > 0.0
        else 0.0
    )


def estimate_mean_ionization(
    geometry: GeometryModel,
    gas: GasModel | str,
) -> IonizationEstimate:
    """
    Produce a deterministic mean ionization estimate for the active track.

    Parameters
    ----------
    geometry:
        Detector/wire geometry model.
    gas:
        Gas model or built-in gas name.

    Returns
    -------
    IonizationEstimate
        Mean ionization summary for the active path segment.
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)

    track_length_m = geometry.track_length_in_active_m
    energy_mev = track_energy_loss_mev(track_length_m, gas_model)
    energy_ev = energy_mev * EV_PER_MEV
    primary_electrons = mean_primary_electrons_from_energy_loss(energy_ev, gas_model)
    primary_charge = mean_primary_charge_c(primary_electrons)
    clusters = mean_cluster_count(primary_electrons, gas_model)

    return IonizationEstimate(
        track_length_m=track_length_m,
        energy_loss_mev=energy_mev,
        energy_loss_ev=energy_ev,
        primary_electrons_mean=primary_electrons,
        primary_charge_c=primary_charge,
        mean_cluster_count=clusters,
        mean_electrons_per_cluster=gas_model.mean_cluster_size_electrons,
        metadata={
            "gas_name": gas_model.name,
            "w_value_ev": gas_model.w_value_ev,
            "mean_energy_loss_mev_per_cm": gas_model.mean_energy_loss_mev_per_cm,
        },
    )


def estimate_direct_image_charge_c(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    direct_charge_efficiency: float = 1.0,
) -> float:
    """
    Estimate the effective direct muon image-pulse source charge.

    Philosophy
    ----------
    This estimator intentionally keeps the direct image-pulse path separate from
    the ordinary avalanche signal. We use the produced primary ionization charge
    as a source scale and then apply:

    - a geometric coupling/sharing factor
    - an explicit user/configurable direct-charge efficiency

    This does not claim to be a rigorous Shockley-Ramo calculation. It is a
    compact engineering proxy to keep the direct path visible in outputs.

    Parameters
    ----------
    geometry:
        Geometry model.
    gas:
        Gas model or built-in gas name.
    direct_charge_efficiency:
        Extra dimensionless scale factor in [0, 1].

    Returns
    -------
    float
        Effective direct image source charge in Coulombs.
    """
    geometry = validate_geometry(geometry)
    gas_model = resolve_gas(gas)

    if not 0.0 <= direct_charge_efficiency <= 1.0:
        raise ValueError(
            "direct_charge_efficiency must be in [0, 1], "
            f"got {direct_charge_efficiency!r}."
        )

    ionization = estimate_mean_ionization(geometry, gas_model)
    sharing = direct_image_charge_sharing_factor(geometry)
    return ionization.primary_charge_c * sharing * direct_charge_efficiency


def ionization_summary(
    geometry: GeometryModel,
    gas: GasModel | str,
    *,
    direct_charge_efficiency: float = 1.0,
) -> dict[str, JSONValue]:
    """
    Return a JSON-friendly summary block for deterministic ionization outputs.
    """
    gas_model = resolve_gas(gas)
    ionization = estimate_mean_ionization(geometry, gas_model)
    direct_charge_c = estimate_direct_image_charge_c(
        geometry,
        gas_model,
        direct_charge_efficiency=direct_charge_efficiency,
    )

    return {
        "gas_name": gas_model.name,
        "track_length_m": ionization.track_length_m,
        "energy_loss_mev": ionization.energy_loss_mev,
        "energy_loss_ev": ionization.energy_loss_ev,
        "primary_electrons_mean": ionization.primary_electrons_mean,
        "primary_charge_c": ionization.primary_charge_c,
        "mean_cluster_count": ionization.mean_cluster_count,
        "mean_electrons_per_cluster": ionization.mean_electrons_per_cluster,
        "direct_image_source_charge_c": direct_charge_c,
        "direct_charge_efficiency": direct_charge_efficiency,
        "metadata": dict(ionization.metadata),
    }


def estimate_primary_statistics_proxy(
    geometry: GeometryModel,
    gas: GasModel | str,
) -> dict[str, JSONValue]:
    """
    Return simple deterministic statistics proxies useful for later stochastic levels.

    Included quantities
    -------------------
    - mean primary electron count
    - Fano-inspired variance proxy
    - standard deviation proxy
    - mean cluster count

    These are not used by Level 1 directly for sampling, but exposing them now
    keeps the later Level 2 implementation consistent with the same interfaces.
    """
    gas_model = resolve_gas(gas)
    ionization = estimate_mean_ionization(geometry, gas_model)

    variance = gas_model.fano_factor * ionization.primary_electrons_mean
    sigma = math.sqrt(variance) if variance > 0.0 else 0.0

    return {
        "gas_name": gas_model.name,
        "primary_electrons_mean": ionization.primary_electrons_mean,
        "primary_electrons_variance_proxy": variance,
        "primary_electrons_sigma_proxy": sigma,
        "mean_cluster_count": ionization.mean_cluster_count,
        "mean_electrons_per_cluster": ionization.mean_electrons_per_cluster,
        "fano_factor": gas_model.fano_factor,
    }


__all__ = [
    "CM_PER_M",
    "ELECTRON_CHARGE_C",
    "EV_PER_MEV",
    "IonizationEstimate",
    "estimate_direct_image_charge_c",
    "estimate_mean_ionization",
    "estimate_primary_statistics_proxy",
    "ionization_summary",
    "mean_cluster_count",
    "mean_primary_charge_c",
    "mean_primary_electrons_from_energy_loss",
    "resolve_gas",
    "track_energy_loss_ev",
    "track_energy_loss_mev",
    "validate_gas",
]