from __future__ import annotations

"""
Bridge from beta-source ionization models into the existing detector-response
chain of muon_wire_estimator.

Purpose
-------
The beta-source modules estimate source-side quantities such as:

- representative / sampled beta energy
- deposited energy in gas
- created primary electrons

This file connects those source-side outputs to the already existing detector
logic for:

- drift / attachment
- collected electrons
- gas gain
- avalanche charge
- direct-image and avalanche pulse estimates

This keeps the beta-specific logic separate from the downstream detector model
while producing the same style of end-to-end outputs already used for the
cosmic-muon workflow.

Design goals
------------
- standard-library only
- conservative imports from existing package modules
- deterministic and event-level stochastic support
- JSON-friendly reporting
- explicit separation between source-side and detector-side quantities

Important note
--------------
The "direct" pulse block here is still computed using the existing direct-image
helper from the package geometry model. That is a convenient engineering bridge,
not a claim that the direct induced signal from a beta track is modeled with
full fidelity. The source-side created ionization and the detector-side
avalanche response are the primary quantities of interest.
"""

from dataclasses import dataclass
from typing import Any

from .beta_ionization import (
    estimate_beta_ionization,
    simulate_beta_source_event,
    source_event_summary_to_dict,
    source_ionization_estimate_to_dict,
)
from .drift import estimate_collected_primary_electrons, estimate_drift
from .gain import estimate_gain
from .gases import GasModel, get_gas
from .geometry import geometry_from_mapping
from .models import GeometryModel, JSONValue
from .pulse import build_avalanche_pulse, build_direct_image_pulse
from .randomness import SeededRNG, make_rng
from .source_geometry import (
    SourceGeometryConfig,
    source_geometry_from_mapping,
    summarize_source_geometry,
)
from .source_models import (
    SourceIonizationEstimate,
    Sr90BetaSourceConfig,
    sr90_beta_source_config_from_mapping,
)


def _normalize_metadata(value: dict[str, Any] | None) -> dict[str, JSONValue]:
    if value is None:
        return {}
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


def resolve_gas(gas: GasModel | str) -> GasModel:
    """
    Resolve either a GasModel object or a built-in gas name.
    """
    if isinstance(gas, GasModel):
        return gas
    if isinstance(gas, str):
        return get_gas(gas)
    raise TypeError(f"gas must be GasModel or str, got {type(gas).__name__}.")


@dataclass(slots=True)
class BetaDetectorChainConfig:
    """
    Top-level configuration for running a beta source through the detector chain.

    Parameters
    ----------
    geometry:
        Existing detector geometry model.
    gas_name:
        Built-in gas name.
    source:
        Beta source configuration.
    source_geometry:
        Source-to-detector geometry configuration.
    use_attachment:
        Whether detector-side attachment losses are enabled.
    use_gain_surrogate:
        Whether detector-side gas gain surrogate is enabled.
    include_direct_image_pulse:
        Whether to include the existing direct-image pulse estimate.
    include_avalanche_signal:
        Whether to include the avalanche-pulse estimate.
    direct_charge_efficiency:
        Direct-image scaling factor passed to the downstream direct-pulse model.
    avalanche_pulse_width_s:
        Optional override for avalanche pulse width.
    metadata:
        JSON-friendly metadata.
    """

    geometry: GeometryModel
    gas_name: str
    source: Sr90BetaSourceConfig
    source_geometry: SourceGeometryConfig
    use_attachment: bool = True
    use_gain_surrogate: bool = True
    include_direct_image_pulse: bool = True
    include_avalanche_signal: bool = True
    direct_charge_efficiency: float = 1.0
    avalanche_pulse_width_s: float | None = None
    metadata: dict[str, JSONValue] | None = None

    def __post_init__(self) -> None:
        if not self.gas_name or not self.gas_name.strip():
            raise ValueError("gas_name must be a non-empty string.")
        if not 0.0 <= self.direct_charge_efficiency <= 1.0:
            raise ValueError(
                "direct_charge_efficiency must be in [0, 1], got "
                f"{self.direct_charge_efficiency!r}."
            )
        if self.avalanche_pulse_width_s is not None and self.avalanche_pulse_width_s <= 0.0:
            raise ValueError(
                "avalanche_pulse_width_s must be > 0 when provided, got "
                f"{self.avalanche_pulse_width_s!r}."
            )
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "geometry": self.geometry.to_dict(),
            "gas_name": self.gas_name,
            "source": self.source.to_dict(),
            "source_geometry": self.source_geometry.to_dict(),
            "use_attachment": self.use_attachment,
            "use_gain_surrogate": self.use_gain_surrogate,
            "include_direct_image_pulse": self.include_direct_image_pulse,
            "include_avalanche_signal": self.include_avalanche_signal,
            "direct_charge_efficiency": self.direct_charge_efficiency,
            "avalanche_pulse_width_s": self.avalanche_pulse_width_s,
            "metadata": dict(self.metadata or {}),
        }


def beta_detector_chain_config_from_mapping(
    data: dict[str, Any],
) -> BetaDetectorChainConfig:
    """
    Construct BetaDetectorChainConfig from a JSON-style mapping.

    Expected structure
    ------------------
    {
      "gas_name": "...",
      "geometry": { ... existing GeometryModel mapping ... },
      "source": { ... Sr90BetaSourceConfig fields ... },
      "source_geometry": { ... SourceGeometryConfig fields ... },
      ...
    }
    """
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dictionary, got {type(data).__name__}.")

    if "geometry" not in data:
        raise KeyError("Missing required top-level field 'geometry'.")
    if "source" not in data:
        raise KeyError("Missing required top-level field 'source'.")
    if "source_geometry" not in data:
        raise KeyError("Missing required top-level field 'source_geometry'.")

    geometry_raw = data["geometry"]
    source_raw = data["source"]
    source_geometry_raw = data["source_geometry"]

    if not isinstance(geometry_raw, dict):
        raise TypeError(
            f"'geometry' must be a dictionary, got {type(geometry_raw).__name__}."
        )
    if not isinstance(source_raw, dict):
        raise TypeError(
            f"'source' must be a dictionary, got {type(source_raw).__name__}."
        )
    if not isinstance(source_geometry_raw, dict):
        raise TypeError(
            "'source_geometry' must be a dictionary, got "
            f"{type(source_geometry_raw).__name__}."
        )

    return BetaDetectorChainConfig(
        geometry=geometry_from_mapping(geometry_raw),
        gas_name=str(data.get("gas_name", "air_dry_1atm")),
        source=sr90_beta_source_config_from_mapping(source_raw),
        source_geometry=source_geometry_from_mapping(source_geometry_raw),
        use_attachment=bool(data.get("use_attachment", True)),
        use_gain_surrogate=bool(data.get("use_gain_surrogate", True)),
        include_direct_image_pulse=bool(data.get("include_direct_image_pulse", True)),
        include_avalanche_signal=bool(data.get("include_avalanche_signal", True)),
        direct_charge_efficiency=float(data.get("direct_charge_efficiency", 1.0)),
        avalanche_pulse_width_s=(
            None
            if data.get("avalanche_pulse_width_s") is None
            else float(data["avalanche_pulse_width_s"])
        ),
        metadata=_normalize_metadata(data.get("metadata")),
    )


def detector_response_from_created_primary_electrons(
    created_primary_electrons_mean: float,
    *,
    geometry: GeometryModel,
    gas: GasModel | str,
    use_attachment: bool = True,
    use_gain_surrogate: bool = True,
    include_direct_image_pulse: bool = True,
    include_avalanche_signal: bool = True,
    direct_charge_efficiency: float = 1.0,
    avalanche_pulse_width_s: float | None = None,
) -> dict[str, JSONValue]:
    """
    Run the downstream detector-response chain for a supplied primary-electron count.
    """
    if created_primary_electrons_mean < 0.0:
        raise ValueError(
            "created_primary_electrons_mean must be >= 0, got "
            f"{created_primary_electrons_mean!r}."
        )

    gas_model = resolve_gas(gas)

    drift = estimate_drift(
        geometry,
        gas_model,
        use_attachment=use_attachment,
    )

    collected_primary_electrons_mean = estimate_collected_primary_electrons(
        created_primary_electrons_mean,
        geometry,
        gas_model,
        use_attachment=use_attachment,
    )

    gain = estimate_gain(
        geometry,
        gas_model,
        collected_primary_electrons_mean,
        use_gain_surrogate=use_gain_surrogate,
    )

    direct_pulse = None
    if include_direct_image_pulse:
        # Use the same existing direct-image bridge used elsewhere in the package.
        # This is primarily retained for continuity with the current signal model.
        from .ionization import estimate_direct_image_charge_c

        direct_charge_c = estimate_direct_image_charge_c(
            geometry,
            gas_model,
            direct_charge_efficiency=direct_charge_efficiency,
        )
        direct_pulse = build_direct_image_pulse(direct_charge_c, geometry)

    avalanche_pulse = None
    if include_avalanche_signal:
        avalanche_pulse = build_avalanche_pulse(
            gain.avalanche_charge_c,
            geometry,
            override_width_s=avalanche_pulse_width_s,
        )

    return {
        "created_primary_electrons_mean": created_primary_electrons_mean,
        "drift": drift.to_dict(),
        "collected_primary_electrons_mean": collected_primary_electrons_mean,
        "gain": gain.to_dict(),
        "direct_pulse": None if direct_pulse is None else direct_pulse.to_dict(),
        "avalanche_pulse": (
            None if avalanche_pulse is None else avalanche_pulse.to_dict()
        ),
    }


def run_beta_detector_chain(
    config: BetaDetectorChainConfig,
) -> dict[str, JSONValue]:
    """
    Run a deterministic beta source through the downstream detector chain.
    """
    if not isinstance(config, BetaDetectorChainConfig):
        raise TypeError(
            "config must be BetaDetectorChainConfig, "
            f"got {type(config).__name__}."
        )

    gas_model = resolve_gas(config.gas_name)

    source_estimate: SourceIonizationEstimate = estimate_beta_ionization(
        source_config=config.source,
        gas=gas_model,
        source_geometry=config.source_geometry,
    )

    detector_chain = detector_response_from_created_primary_electrons(
        source_estimate.primary_electrons_mean,
        geometry=config.geometry,
        gas=gas_model,
        use_attachment=config.use_attachment,
        use_gain_surrogate=config.use_gain_surrogate,
        include_direct_image_pulse=config.include_direct_image_pulse,
        include_avalanche_signal=config.include_avalanche_signal,
        direct_charge_efficiency=config.direct_charge_efficiency,
        avalanche_pulse_width_s=config.avalanche_pulse_width_s,
    )

    return {
        "gas": gas_model.to_dict(),
        "source": config.source.to_dict(),
        "source_geometry": config.source_geometry.to_dict(),
        "source_geometry_summary": summarize_source_geometry(
            config.source_geometry
        ).to_dict(),
        "source_ionization": source_ionization_estimate_to_dict(source_estimate),
        "detector_chain": detector_chain,
        "config_snapshot": config.to_dict(),
        "metadata": dict(config.metadata or {}),
    }


def run_beta_detector_event(
    config: BetaDetectorChainConfig,
    *,
    event_index: int,
    rng: SeededRNG,
) -> dict[str, JSONValue]:
    """
    Simulate one stochastic beta-source event and propagate it through the detector chain.
    """
    if event_index < 0:
        raise ValueError(f"event_index must be >= 0, got {event_index!r}.")
    if not isinstance(rng, SeededRNG):
        raise TypeError(f"rng must be SeededRNG, got {type(rng).__name__}.")
    if not isinstance(config, BetaDetectorChainConfig):
        raise TypeError(
            "config must be BetaDetectorChainConfig, "
            f"got {type(config).__name__}."
        )

    gas_model = resolve_gas(config.gas_name)

    source_event = simulate_beta_source_event(
        event_index=event_index,
        source_config=config.source,
        gas=gas_model,
        source_geometry=config.source_geometry,
        rng=rng,
    )

    detector_chain = detector_response_from_created_primary_electrons(
        source_event.created_primary_electrons,
        geometry=config.geometry,
        gas=gas_model,
        use_attachment=config.use_attachment,
        use_gain_surrogate=config.use_gain_surrogate,
        include_direct_image_pulse=config.include_direct_image_pulse,
        include_avalanche_signal=config.include_avalanche_signal,
        direct_charge_efficiency=config.direct_charge_efficiency,
        avalanche_pulse_width_s=config.avalanche_pulse_width_s,
    )

    event_output: dict[str, JSONValue] = {
        "event_index": event_index,
        "source_event": source_event_summary_to_dict(source_event),
        "detector_chain": detector_chain,
    }

    avalanche_pulse = detector_chain.get("avalanche_pulse")
    if isinstance(avalanche_pulse, dict):
        event_output["peak_voltage_v"] = avalanche_pulse.get("peak_voltage_v")
        event_output["peak_current_a"] = avalanche_pulse.get("peak_current_a")
    else:
        event_output["peak_voltage_v"] = None
        event_output["peak_current_a"] = None

    return event_output


def run_beta_detector_event_scan(
    config: BetaDetectorChainConfig,
    *,
    n_events: int,
    random_seed: int,
    threshold_v: float = 1.0e-3,
    return_event_list: bool = False,
) -> dict[str, JSONValue]:
    """
    Run a stochastic beta-source event scan through the detector chain.

    Summary quantities are aligned with the style already used elsewhere in the
    estimator for scope-visibility studies.
    """
    if not isinstance(config, BetaDetectorChainConfig):
        raise TypeError(
            "config must be BetaDetectorChainConfig, "
            f"got {type(config).__name__}."
        )
    if n_events <= 0:
        raise ValueError(f"n_events must be > 0, got {n_events!r}.")
    if threshold_v < 0.0:
        raise ValueError(f"threshold_v must be >= 0, got {threshold_v!r}.")

    rng = make_rng(random_seed)

    event_records: list[dict[str, JSONValue]] = []
    peak_voltages: list[float] = []
    created_primary: list[float] = []
    source_energies: list[float] = []
    deposited_energies: list[float] = []
    entered_flags: list[float] = []

    for event_index in range(n_events):
        event = run_beta_detector_event(
            config,
            event_index=event_index,
            rng=rng,
        )

        source_event = event["source_event"]
        if not isinstance(source_event, dict):
            raise RuntimeError("source_event payload must be a dictionary.")

        created_value = source_event.get("created_primary_electrons")
        sampled_energy = source_event.get("sampled_particle_energy_mev")
        deposited_energy = source_event.get("deposited_energy_mev")
        entered_active_region = source_event.get("entered_active_region")

        if isinstance(created_value, (int, float)):
            created_primary.append(float(created_value))
        if isinstance(sampled_energy, (int, float)):
            source_energies.append(float(sampled_energy))
        if isinstance(deposited_energy, (int, float)):
            deposited_energies.append(float(deposited_energy))
        entered_flags.append(1.0 if bool(entered_active_region) else 0.0)

        peak_voltage = event.get("peak_voltage_v")
        if isinstance(peak_voltage, (int, float)):
            peak_voltages.append(float(peak_voltage))
        else:
            peak_voltages.append(0.0)

        if return_event_list:
            event_records.append(event)

    above_threshold = [1.0 if v >= threshold_v else 0.0 for v in peak_voltages]

    def mean(values: list[float]) -> float:
        return sum(values) / float(len(values)) if values else 0.0

    sorted_peak = sorted(peak_voltages)
    if sorted_peak:
        mid = len(sorted_peak) // 2
        if len(sorted_peak) % 2 == 1:
            median_peak = sorted_peak[mid]
        else:
            median_peak = 0.5 * (sorted_peak[mid - 1] + sorted_peak[mid])
    else:
        median_peak = 0.0

    return {
        "n_events": n_events,
        "random_seed": random_seed,
        "threshold_v": threshold_v,
        "gas_name": config.gas_name,
        "mean_sampled_particle_energy_mev": mean(source_energies),
        "mean_deposited_energy_mev": mean(deposited_energies),
        "mean_created_primary_electrons": mean(created_primary),
        "fraction_entering_active_region": mean(entered_flags),
        "min_peak_voltage_v": min(peak_voltages) if peak_voltages else 0.0,
        "mean_peak_voltage_v": mean(peak_voltages),
        "median_peak_voltage_v": median_peak,
        "max_peak_voltage_v": max(peak_voltages) if peak_voltages else 0.0,
        "fraction_above_threshold": mean(above_threshold),
        "config_snapshot": config.to_dict(),
        "source_geometry_summary": summarize_source_geometry(
            config.source_geometry
        ).to_dict(),
        "event_records": event_records if return_event_list else [],
    }


__all__ = [
    "BetaDetectorChainConfig",
    "beta_detector_chain_config_from_mapping",
    "detector_response_from_created_primary_electrons",
    "resolve_gas",
    "run_beta_detector_chain",
    "run_beta_detector_event",
    "run_beta_detector_event_scan",
]