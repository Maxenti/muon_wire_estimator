from __future__ import annotations

"""
Source-side data models for particle-driven ionization estimates.

This module introduces a lightweight, explicit configuration layer for
estimating ionization from different particle/source types without rewriting
the rest of the muon-wire-estimator pipeline.

Current intended source families
--------------------------------
- cosmic muon
- Sr-90 / Y-90 beta source

Design goals
------------
- standard-library only
- JSON-friendly
- deterministic and stochastic workflows can share the same config layer
- clear separation between source description and downstream detector response
- conservative validation with informative error messages

These models are intended to answer the source-side question:

    "What primary ionization is created in the gas by this source geometry and
    particle model?"

Downstream collection / gain / pulse estimation should consume the resulting
ionization summary rather than depend on the raw source configuration.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping


JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


SourceType = Literal["cosmic_muon", "sr90_beta"]
BetaSpectrumModel = Literal["fixed_energy", "sr90", "y90", "sr90_y90_combined"]
TrackLengthModel = Literal["fixed_length", "projected_length", "range_limited"]


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


def _ensure_non_empty(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")


def _ensure_literal(name: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of {{{allowed_text}}}, got {value!r}.")


def _metadata_from_mapping(value: Mapping[str, Any] | None) -> dict[str, JSONValue]:
    if value is None:
        return {}
    normalized: dict[str, JSONValue] = {}
    for key, item in value.items():
        normalized[str(key)] = _json_safe_value(item, path=str(key))
    return normalized


def _json_safe_value(value: Any, *, path: str) -> JSONValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_json_safe_value(item, path=f"{path}[]") for item in value]
    if isinstance(value, tuple):
        return [_json_safe_value(item, path=f"{path}[]") for item in value]
    if isinstance(value, dict):
        return {
            str(key): _json_safe_value(item, path=f"{path}.{key}")
            for key, item in value.items()
        }
    raise TypeError(
        f"Unsupported metadata value type at {path!r}: {type(value).__name__}."
    )


@dataclass(slots=True)
class ParticleSourceConfig:
    """
    Generic top-level source description.

    Parameters
    ----------
    source_type:
        Source family identifier.
    source_name:
        Human-readable source label.
    stochastic:
        Whether the source should be sampled stochastically.
    metadata:
        JSON-friendly metadata for provenance / reporting.
    """

    source_type: SourceType
    source_name: str
    stochastic: bool = False
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_literal(
            "source_type",
            self.source_type,
            {"cosmic_muon", "sr90_beta"},
        )
        _ensure_non_empty("source_name", self.source_name)

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "stochastic": self.stochastic,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class CosmicMuonSourceConfig:
    """
    Configuration for the existing cosmic-muon style source model.

    Parameters
    ----------
    muon_beta:
        Dimensionless beta = v/c.
    track_length_in_active_cm:
        Track length inside the active gas region.
    incidence_angle_deg:
        Optional descriptive incidence angle for reporting. The current
        simplified source model may not use it directly.
    metadata:
        JSON-friendly metadata.
    """

    muon_beta: float = 0.998
    track_length_in_active_cm: float = 5.0
    incidence_angle_deg: float = 0.0
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_positive(
            "muon_beta",
            self.muon_beta,
            allow_zero=False,
        )
        if self.muon_beta > 1.0:
            raise ValueError(f"muon_beta must be <= 1, got {self.muon_beta!r}.")
        _ensure_positive("track_length_in_active_cm", self.track_length_in_active_cm)
        # Angle may be any finite real number.
        if not isinstance(self.incidence_angle_deg, (int, float)):
            raise TypeError(
                "incidence_angle_deg must be numeric, "
                f"got {type(self.incidence_angle_deg).__name__}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "muon_beta": self.muon_beta,
            "track_length_in_active_cm": self.track_length_in_active_cm,
            "incidence_angle_deg": self.incidence_angle_deg,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class Sr90BetaSourceConfig:
    """
    Configuration for a reasonably defined Sr-90 / Y-90 beta source.

    Parameters
    ----------
    spectrum_model:
        Choice of beta-energy model.
    fixed_beta_energy_mev:
        Required when spectrum_model == 'fixed_energy'.
    include_sr90_branch:
        Whether the lower-energy Sr-90 beta branch is included.
    include_y90_branch:
        Whether the higher-energy Y-90 beta branch is included.
    source_activity_bq:
        Optional descriptive activity. Not required for single-event pulse
        estimation, but useful for reporting.
    collimated:
        Whether the source is treated as collimated.
    angular_spread_deg:
        Half-width angular spread for nontrivial source geometry models.
    track_length_model:
        Strategy for mapping beta transport into an active gas path length.
    metadata:
        JSON-friendly metadata.
    """

    spectrum_model: BetaSpectrumModel = "sr90_y90_combined"
    fixed_beta_energy_mev: float | None = None
    include_sr90_branch: bool = True
    include_y90_branch: bool = True
    source_activity_bq: float | None = None
    collimated: bool = False
    angular_spread_deg: float = 90.0
    track_length_model: TrackLengthModel = "range_limited"
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_literal(
            "spectrum_model",
            self.spectrum_model,
            {"fixed_energy", "sr90", "y90", "sr90_y90_combined"},
        )
        _ensure_literal(
            "track_length_model",
            self.track_length_model,
            {"fixed_length", "projected_length", "range_limited"},
        )

        if self.spectrum_model == "fixed_energy":
            if self.fixed_beta_energy_mev is None:
                raise ValueError(
                    "fixed_beta_energy_mev must be provided when "
                    "spectrum_model == 'fixed_energy'."
                )
            _ensure_positive("fixed_beta_energy_mev", self.fixed_beta_energy_mev)
        elif self.fixed_beta_energy_mev is not None:
            _ensure_positive("fixed_beta_energy_mev", self.fixed_beta_energy_mev)

        if not (self.include_sr90_branch or self.include_y90_branch):
            raise ValueError(
                "At least one of include_sr90_branch or include_y90_branch must be True."
            )

        if self.source_activity_bq is not None:
            _ensure_positive("source_activity_bq", self.source_activity_bq)
        _ensure_positive("angular_spread_deg", self.angular_spread_deg, allow_zero=True)

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "spectrum_model": self.spectrum_model,
            "fixed_beta_energy_mev": self.fixed_beta_energy_mev,
            "include_sr90_branch": self.include_sr90_branch,
            "include_y90_branch": self.include_y90_branch,
            "source_activity_bq": self.source_activity_bq,
            "collimated": self.collimated,
            "angular_spread_deg": self.angular_spread_deg,
            "track_length_model": self.track_length_model,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class SourceIonizationEstimate:
    """
    Summary of source-side ionization before detector collection/gain.

    Parameters
    ----------
    source_type:
        Source family identifier.
    source_name:
        Human-readable source label.
    deposited_energy_mev:
        Estimated deposited energy in the gas.
    primary_electrons_mean:
        Mean primary electrons created.
    track_length_in_active_cm:
        Effective track length in the active gas region.
    particle_kinetic_energy_mev:
        Representative kinetic energy for the particle.
    survival_to_active_region_probability:
        Optional source-side survival/acceptance factor prior to detector
        transport. This is distinct from detector drift/attachment survival.
    metadata:
        JSON-friendly metadata and intermediate source-side calculations.
    """

    source_type: SourceType
    source_name: str
    deposited_energy_mev: float
    primary_electrons_mean: float
    track_length_in_active_cm: float
    particle_kinetic_energy_mev: float | None = None
    survival_to_active_region_probability: float = 1.0
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_literal(
            "source_type",
            self.source_type,
            {"cosmic_muon", "sr90_beta"},
        )
        _ensure_non_empty("source_name", self.source_name)
        _ensure_positive("deposited_energy_mev", self.deposited_energy_mev, allow_zero=True)
        _ensure_positive(
            "primary_electrons_mean",
            self.primary_electrons_mean,
            allow_zero=True,
        )
        _ensure_positive(
            "track_length_in_active_cm",
            self.track_length_in_active_cm,
            allow_zero=True,
        )
        if self.particle_kinetic_energy_mev is not None:
            _ensure_positive(
                "particle_kinetic_energy_mev",
                self.particle_kinetic_energy_mev,
                allow_zero=True,
            )
        _ensure_fraction(
            "survival_to_active_region_probability",
            self.survival_to_active_region_probability,
        )

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "deposited_energy_mev": self.deposited_energy_mev,
            "primary_electrons_mean": self.primary_electrons_mean,
            "track_length_in_active_cm": self.track_length_in_active_cm,
            "particle_kinetic_energy_mev": self.particle_kinetic_energy_mev,
            "survival_to_active_region_probability": (
                self.survival_to_active_region_probability
            ),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class SourceEventSummary:
    """
    Event-level source summary for stochastic workflows.

    Parameters
    ----------
    event_index:
        Zero-based event index.
    source_type:
        Source family identifier.
    sampled_particle_energy_mev:
        Sampled source-particle kinetic energy.
    deposited_energy_mev:
        Deposited energy in active gas.
    created_primary_electrons:
        Created primary electron count or proxy.
    entered_active_region:
        Whether the particle/event reached the active gas region under the
        source-geometry/transport model.
    metadata:
        JSON-friendly metadata.
    """

    event_index: int
    source_type: SourceType
    sampled_particle_energy_mev: float
    deposited_energy_mev: float
    created_primary_electrons: float
    entered_active_region: bool = True
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.event_index < 0:
            raise ValueError(f"event_index must be >= 0, got {self.event_index!r}.")
        _ensure_literal(
            "source_type",
            self.source_type,
            {"cosmic_muon", "sr90_beta"},
        )
        _ensure_positive(
            "sampled_particle_energy_mev",
            self.sampled_particle_energy_mev,
            allow_zero=True,
        )
        _ensure_positive("deposited_energy_mev", self.deposited_energy_mev, allow_zero=True)
        _ensure_positive(
            "created_primary_electrons",
            self.created_primary_electrons,
            allow_zero=True,
        )

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "event_index": self.event_index,
            "source_type": self.source_type,
            "sampled_particle_energy_mev": self.sampled_particle_energy_mev,
            "deposited_energy_mev": self.deposited_energy_mev,
            "created_primary_electrons": self.created_primary_electrons,
            "entered_active_region": self.entered_active_region,
            "metadata": dict(self.metadata),
        }


def particle_source_config_from_mapping(data: Mapping[str, Any]) -> ParticleSourceConfig:
    """
    Construct a generic ParticleSourceConfig from a mapping.

    Expected keys
    -------------
    - source_type
    - source_name
    - stochastic
    - metadata
    """
    if not isinstance(data, Mapping):
        raise TypeError(f"data must be a mapping, got {type(data).__name__}.")
    return ParticleSourceConfig(
        source_type=str(data.get("source_type", "cosmic_muon")),  # type: ignore[arg-type]
        source_name=str(data.get("source_name", str(data.get("source_type", "source")))),
        stochastic=bool(data.get("stochastic", False)),
        metadata=_metadata_from_mapping(data.get("metadata")),
    )


def cosmic_muon_source_config_from_mapping(
    data: Mapping[str, Any],
) -> CosmicMuonSourceConfig:
    """
    Construct CosmicMuonSourceConfig from a mapping.
    """
    if not isinstance(data, Mapping):
        raise TypeError(f"data must be a mapping, got {type(data).__name__}.")
    return CosmicMuonSourceConfig(
        muon_beta=float(data.get("muon_beta", 0.998)),
        track_length_in_active_cm=float(data.get("track_length_in_active_cm", 5.0)),
        incidence_angle_deg=float(data.get("incidence_angle_deg", 0.0)),
        metadata=_metadata_from_mapping(data.get("metadata")),
    )


def sr90_beta_source_config_from_mapping(
    data: Mapping[str, Any],
) -> Sr90BetaSourceConfig:
    """
    Construct Sr90BetaSourceConfig from a mapping.
    """
    if not isinstance(data, Mapping):
        raise TypeError(f"data must be a mapping, got {type(data).__name__}.")
    fixed_energy_raw = data.get("fixed_beta_energy_mev")
    return Sr90BetaSourceConfig(
        spectrum_model=str(data.get("spectrum_model", "sr90_y90_combined")),  # type: ignore[arg-type]
        fixed_beta_energy_mev=(
            None if fixed_energy_raw is None else float(fixed_energy_raw)
        ),
        include_sr90_branch=bool(data.get("include_sr90_branch", True)),
        include_y90_branch=bool(data.get("include_y90_branch", True)),
        source_activity_bq=(
            None if data.get("source_activity_bq") is None
            else float(data["source_activity_bq"])
        ),
        collimated=bool(data.get("collimated", False)),
        angular_spread_deg=float(data.get("angular_spread_deg", 90.0)),
        track_length_model=str(data.get("track_length_model", "range_limited")),  # type: ignore[arg-type]
        metadata=_metadata_from_mapping(data.get("metadata")),
    )


__all__ = [
    "BetaSpectrumModel",
    "CosmicMuonSourceConfig",
    "JSONScalar",
    "JSONValue",
    "ParticleSourceConfig",
    "SourceEventSummary",
    "SourceIonizationEstimate",
    "SourceType",
    "Sr90BetaSourceConfig",
    "TrackLengthModel",
    "cosmic_muon_source_config_from_mapping",
    "particle_source_config_from_mapping",
    "sr90_beta_source_config_from_mapping",
]