"""
Top-level deterministic estimator orchestration for the muon wire estimator.

This module assembles the Level 1 deterministic pipeline from the lower-level
helpers:

- gas lookup
- geometry summary
- ionization estimate
- drift / attachment estimate
- avalanche gain estimate
- pulse conversion
- compact JSON-friendly reporting

The design keeps the two signal paths separate:

1. direct muon image pulse
2. ordinary gas-avalanche pulse

This preserves the baseline estimator spirit while making the nonzero-field
path more realistic and modular.
"""

from __future__ import annotations

from typing import Any

from .drift import estimate_collected_primary_electrons, estimate_drift
from .gain import estimate_gain
from .gases import get_gas, list_builtin_gases
from .geometry import geometry_from_mapping, geometry_summary, validate_geometry
from .ionization import (
    estimate_direct_image_charge_c,
    estimate_mean_ionization,
    estimate_primary_statistics_proxy,
)
from .models import (
    DeterministicEstimate,
    EstimatorConfig,
    GasModel,
    GeometryModel,
    JSONValue,
)
from .pulse import build_avalanche_pulse, build_direct_image_pulse


ESTIMATOR_VERSION = "level1-deterministic-1.0"


def resolve_gas(gas: GasModel | str) -> GasModel:
    """
    Resolve a gas model instance or built-in gas name.
    """
    if isinstance(gas, GasModel):
        return gas
    if isinstance(gas, str):
        return get_gas(gas)
    raise TypeError(f"gas must be GasModel or str, got {type(gas).__name__}.")


def build_estimator_config(
    geometry: GeometryModel,
    *,
    gas_name: str = "air_dry_1atm",
    include_direct_image_pulse: bool = True,
    include_avalanche_signal: bool = True,
    use_attachment: bool = True,
    use_gain_surrogate: bool = True,
    direct_charge_efficiency: float = 1.0,
    avalanche_pulse_width_s: float | None = None,
    output_event_details: bool = False,
    metadata: dict[str, JSONValue] | None = None,
) -> EstimatorConfig:
    """
    Build a validated EstimatorConfig.
    """
    return EstimatorConfig(
        geometry=validate_geometry(geometry),
        gas_name=gas_name,
        include_direct_image_pulse=include_direct_image_pulse,
        include_avalanche_signal=include_avalanche_signal,
        use_attachment=use_attachment,
        use_gain_surrogate=use_gain_surrogate,
        direct_charge_efficiency=direct_charge_efficiency,
        avalanche_pulse_width_s=avalanche_pulse_width_s,
        output_event_details=output_event_details,
        metadata={} if metadata is None else dict(metadata),
    )


def estimate_from_config(config: EstimatorConfig) -> DeterministicEstimate:
    """
    Run the full deterministic Level 1 estimator from a validated config.
    """
    if not isinstance(config, EstimatorConfig):
        raise TypeError(
            f"config must be an EstimatorConfig instance, got {type(config).__name__}."
        )

    geometry = validate_geometry(config.geometry)
    gas = get_gas(config.gas_name)

    ionization = estimate_mean_ionization(geometry, gas)
    drift = estimate_drift(
        geometry,
        gas,
        use_attachment=config.use_attachment,
    )

    collected_primary_electrons_mean = estimate_collected_primary_electrons(
        ionization.primary_electrons_mean,
        geometry,
        gas,
        use_attachment=config.use_attachment,
    )

    gain = estimate_gain(
        geometry,
        gas,
        collected_primary_electrons_mean,
        use_gain_surrogate=config.use_gain_surrogate,
    )

    direct_pulse = None
    if config.include_direct_image_pulse:
        direct_charge_c = estimate_direct_image_charge_c(
            geometry,
            gas,
            direct_charge_efficiency=config.direct_charge_efficiency,
        )
        direct_pulse = build_direct_image_pulse(direct_charge_c, geometry)

    avalanche_pulse = None
    if config.include_avalanche_signal:
        avalanche_pulse = build_avalanche_pulse(
            gain.avalanche_charge_c,
            geometry,
            override_width_s=config.avalanche_pulse_width_s,
        )

    notes: list[str] = [
        "Deterministic Level 1 estimate using phenomenological gas, drift, gain, and pulse surrogates.",
        "Direct muon image pulse and ordinary gas-avalanche pulse are reported separately.",
    ]
    if gas.name == "air_dry_1atm":
        notes.append(
            "Air predictions are especially uncertain because attachment and avalanche behavior are highly environment-dependent."
        )
    if not config.use_attachment:
        notes.append("Attachment losses were disabled by configuration.")
    if not config.use_gain_surrogate:
        notes.append("Gas gain surrogate was disabled; unity gain was used.")
    if not config.include_direct_image_pulse:
        notes.append("Direct muon image pulse block was omitted by configuration.")
    if not config.include_avalanche_signal:
        notes.append("Gas-avalanche pulse block was omitted by configuration.")

    metadata: dict[str, JSONValue] = {
        "estimator_version": ESTIMATOR_VERSION,
        "config": config.to_dict(),
        "geometry_summary": geometry_summary(geometry),
        "ionization_summary": ionization.to_dict(),
        "drift_summary": drift.to_dict(),
        "gain_summary": gain.to_dict(),
        "primary_statistics_proxy": estimate_primary_statistics_proxy(geometry, gas),
        "available_builtin_gases": list_builtin_gases(),
    }

    return DeterministicEstimate(
        estimator_version=ESTIMATOR_VERSION,
        geometry=geometry,
        gas=gas,
        created_primary_electrons_mean=ionization.primary_electrons_mean,
        collected_primary_electrons_mean=collected_primary_electrons_mean,
        drift_time_s=drift.drift_time_s,
        attachment_survival_fraction=drift.attachment_survival_fraction,
        collection_fraction_total=drift.collection_fraction_total,
        gas_gain_mean=gain.gas_gain_mean,
        avalanche_electrons_mean=gain.avalanche_electrons_mean,
        avalanche_charge_c=gain.avalanche_charge_c,
        direct_pulse=direct_pulse,
        avalanche_pulse=avalanche_pulse,
        notes=notes,
        metadata=metadata,
    )


def estimate(
    geometry: GeometryModel,
    *,
    gas: GasModel | str = "air_dry_1atm",
    include_direct_image_pulse: bool = True,
    include_avalanche_signal: bool = True,
    use_attachment: bool = True,
    use_gain_surrogate: bool = True,
    direct_charge_efficiency: float = 1.0,
    avalanche_pulse_width_s: float | None = None,
    output_event_details: bool = False,
    metadata: dict[str, JSONValue] | None = None,
) -> DeterministicEstimate:
    """
    Convenience wrapper to run the deterministic estimate directly.

    Parameters
    ----------
    geometry:
        Valid GeometryModel.
    gas:
        GasModel instance or built-in gas name.
    include_direct_image_pulse:
        Whether to compute/report the direct image pulse.
    include_avalanche_signal:
        Whether to compute/report the avalanche pulse.
    use_attachment:
        Whether to apply attachment losses in drift/collection.
    use_gain_surrogate:
        Whether to apply the Level 1 gas-gain surrogate.
    direct_charge_efficiency:
        Scaling factor applied only to the direct-image source charge.
    avalanche_pulse_width_s:
        Optional override for the avalanche pulse width used in peak estimation.
    output_event_details:
        Reserved Level 1 config flag for interface consistency.
    metadata:
        Optional JSON-friendly config metadata.
    """
    gas_model = resolve_gas(gas)
    config = build_estimator_config(
        geometry,
        gas_name=gas_model.name,
        include_direct_image_pulse=include_direct_image_pulse,
        include_avalanche_signal=include_avalanche_signal,
        use_attachment=use_attachment,
        use_gain_surrogate=use_gain_surrogate,
        direct_charge_efficiency=direct_charge_efficiency,
        avalanche_pulse_width_s=avalanche_pulse_width_s,
        output_event_details=output_event_details,
        metadata=metadata,
    )
    return estimate_from_config(config)


def result_to_dict(result: DeterministicEstimate) -> dict[str, JSONValue]:
    """
    Convert a DeterministicEstimate into a JSON-friendly dictionary.
    """
    if not isinstance(result, DeterministicEstimate):
        raise TypeError(
            "result must be a DeterministicEstimate instance, "
            f"got {type(result).__name__}."
        )
    return result.to_dict()


def estimate_to_dict(
    geometry: GeometryModel,
    *,
    gas: GasModel | str = "air_dry_1atm",
    include_direct_image_pulse: bool = True,
    include_avalanche_signal: bool = True,
    use_attachment: bool = True,
    use_gain_surrogate: bool = True,
    direct_charge_efficiency: float = 1.0,
    avalanche_pulse_width_s: float | None = None,
    output_event_details: bool = False,
    metadata: dict[str, JSONValue] | None = None,
) -> dict[str, JSONValue]:
    """
    Run the estimate and return a JSON-friendly dictionary.
    """
    result = estimate(
        geometry,
        gas=gas,
        include_direct_image_pulse=include_direct_image_pulse,
        include_avalanche_signal=include_avalanche_signal,
        use_attachment=use_attachment,
        use_gain_surrogate=use_gain_surrogate,
        direct_charge_efficiency=direct_charge_efficiency,
        avalanche_pulse_width_s=avalanche_pulse_width_s,
        output_event_details=output_event_details,
        metadata=metadata,
    )
    return result.to_dict()


def config_from_mapping(data: dict[str, Any]) -> EstimatorConfig:
    """
    Build an EstimatorConfig from a generic mapping, suitable for CLI JSON input.

    Required structure
    ------------------
    {
      "geometry": {...},
      "gas_name": "air_dry_1atm",
      ...
    }
    """
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dictionary, got {type(data).__name__}.")

    if "geometry" not in data:
        raise KeyError("Missing required top-level field 'geometry'.")

    geometry_raw = data["geometry"]
    if not isinstance(geometry_raw, dict):
        raise TypeError(
            "The 'geometry' field must be a dictionary compatible with GeometryModel."
        )

    geometry = geometry_from_mapping(geometry_raw)

    return EstimatorConfig(
        geometry=geometry,
        gas_name=str(data.get("gas_name", "air_dry_1atm")),
        include_direct_image_pulse=bool(data.get("include_direct_image_pulse", True)),
        include_avalanche_signal=bool(data.get("include_avalanche_signal", True)),
        use_attachment=bool(data.get("use_attachment", True)),
        use_gain_surrogate=bool(data.get("use_gain_surrogate", True)),
        direct_charge_efficiency=float(data.get("direct_charge_efficiency", 1.0)),
        avalanche_pulse_width_s=(
            None
            if data.get("avalanche_pulse_width_s") is None
            else float(data["avalanche_pulse_width_s"])
        ),
        output_event_details=bool(data.get("output_event_details", False)),
        metadata=(
            {}
            if data.get("metadata") is None
            else _validate_json_mapping(data["metadata"], field_name="metadata")
        ),
    )


def estimate_from_mapping(data: dict[str, Any]) -> DeterministicEstimate:
    """
    Build config from a mapping and run the deterministic estimate.
    """
    config = config_from_mapping(data)
    return estimate_from_config(config)


def estimate_from_mapping_to_dict(data: dict[str, Any]) -> dict[str, JSONValue]:
    """
    Build config from a mapping, run the estimate, and return a JSON-friendly dict.
    """
    return estimate_from_mapping(data).to_dict()


def _validate_json_mapping(value: Any, *, field_name: str) -> dict[str, JSONValue]:
    """
    Validate that a value is a dictionary with string-like keys.

    This helper is intentionally lightweight because the project only needs
    JSON-friendly metadata, not a heavy schema layer at Level 1.
    """
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dictionary, got {type(value).__name__}.")
    normalized: dict[str, JSONValue] = {}
    for key, item in value.items():
        normalized[str(key)] = item
    return normalized


__all__ = [
    "ESTIMATOR_VERSION",
    "build_estimator_config",
    "config_from_mapping",
    "estimate",
    "estimate_from_config",
    "estimate_from_mapping",
    "estimate_from_mapping_to_dict",
    "estimate_to_dict",
    "resolve_gas",
    "result_to_dict",
]