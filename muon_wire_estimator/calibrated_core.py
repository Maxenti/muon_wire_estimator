"""
Top-level calibrated estimator orchestration for Level 3.

This module layers optional calibration behavior on top of the default
deterministic estimator. The guiding philosophy is:

- always compute the default/surrogate estimate
- optionally load/apply a calibration record
- keep calibrated vs default behavior explicitly labeled
- degrade safely to default behavior if calibration is absent/incomplete
- preserve the same overall estimator structure and outputs

The calibrated path currently focuses on the gain block first, while leaving
geometry/ionization/drift/pulse structure compatible with future Garfield++-
derived tuning products.
"""

from __future__ import annotations

from dataclasses import dataclass

from .calibrated_gain import CalibratedGainEstimate, estimate_calibrated_gain
from .calibration_loader import maybe_load_calibration_record
from .calibration_models import CalibrationRecord
from .core import (
    ESTIMATOR_VERSION,
    build_estimator_config,
    estimate_from_config,
    resolve_gas,
)
from .drift import estimate_collected_primary_electrons
from .gases import get_gas
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


CALIBRATED_ESTIMATOR_VERSION = f"{ESTIMATOR_VERSION}+level3-calibrated-1.0"


@dataclass(slots=True)
class CalibratedDeterministicEstimate:
    """
    Combined default and calibrated deterministic estimate.

    Attributes
    ----------
    default_estimate:
        The original deterministic Level 1 estimate.
    calibrated_result:
        A DeterministicEstimate-like object reflecting calibrated gain behavior.
    calibrated_gain:
        Detailed calibrated gain block.
    calibration_record:
        The applied calibration record, if any.
    calibration_applied:
        Whether a compatible record was provided and changed the gain behavior.
    metadata:
        JSON-friendly extra reporting metadata.
    """

    default_estimate: DeterministicEstimate
    calibrated_result: DeterministicEstimate
    calibrated_gain: CalibratedGainEstimate
    calibration_record: CalibrationRecord | None
    calibration_applied: bool
    metadata: dict[str, JSONValue]

    def __post_init__(self) -> None:
        if not isinstance(self.default_estimate, DeterministicEstimate):
            raise TypeError(
                "default_estimate must be a DeterministicEstimate instance, "
                f"got {type(self.default_estimate).__name__}."
            )
        if not isinstance(self.calibrated_result, DeterministicEstimate):
            raise TypeError(
                "calibrated_result must be a DeterministicEstimate instance, "
                f"got {type(self.calibrated_result).__name__}."
            )
        if not isinstance(self.calibrated_gain, CalibratedGainEstimate):
            raise TypeError(
                "calibrated_gain must be a CalibratedGainEstimate instance, "
                f"got {type(self.calibrated_gain).__name__}."
            )
        if self.calibration_record is not None and not isinstance(
            self.calibration_record, CalibrationRecord
        ):
            raise TypeError(
                "calibration_record must be CalibrationRecord or None, "
                f"got {type(self.calibration_record).__name__}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "default_estimate": self.default_estimate.to_dict(),
            "calibrated_result": self.calibrated_result.to_dict(),
            "calibrated_gain": self.calibrated_gain.to_dict(),
            "calibration_record": (
                None if self.calibration_record is None else self.calibration_record.to_dict()
            ),
            "calibration_applied": self.calibration_applied,
            "metadata": dict(self.metadata),
        }


def build_calibrated_estimator_config(
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
    Build the same config structure as the default estimator.

    This wrapper exists mainly for naming clarity in the calibrated layer.
    """
    return build_estimator_config(
        geometry,
        gas_name=gas_name,
        include_direct_image_pulse=include_direct_image_pulse,
        include_avalanche_signal=include_avalanche_signal,
        use_attachment=use_attachment,
        use_gain_surrogate=use_gain_surrogate,
        direct_charge_efficiency=direct_charge_efficiency,
        avalanche_pulse_width_s=avalanche_pulse_width_s,
        output_event_details=output_event_details,
        metadata=metadata,
    )


def estimate_calibrated_from_config(
    config: EstimatorConfig,
    *,
    calibration: CalibrationRecord | None = None,
) -> CalibratedDeterministicEstimate:
    """
    Run the calibrated deterministic estimator from a validated config.

    The default Level 1 estimate is always computed first. Then the gain block
    is optionally replaced with a calibrated version if a compatible record is
    provided.
    """
    if not isinstance(config, EstimatorConfig):
        raise TypeError(
            f"config must be an EstimatorConfig instance, got {type(config).__name__}."
        )

    geometry = validate_geometry(config.geometry)
    gas = get_gas(config.gas_name)

    default_estimate = estimate_from_config(config)

    ionization = estimate_mean_ionization(geometry, gas)
    collected_primary_electrons_mean = estimate_collected_primary_electrons(
        ionization.primary_electrons_mean,
        geometry,
        gas,
        use_attachment=config.use_attachment,
    )

    calibrated_gain = estimate_calibrated_gain(
        geometry,
        gas,
        collected_primary_electrons_mean,
        calibration=calibration,
        use_gain_surrogate=config.use_gain_surrogate,
    )

    direct_pulse = default_estimate.direct_pulse
    if config.include_direct_image_pulse and direct_pulse is None:
        direct_charge_c = estimate_direct_image_charge_c(
            geometry,
            gas,
            direct_charge_efficiency=config.direct_charge_efficiency,
        )
        direct_pulse = build_direct_image_pulse(direct_charge_c, geometry)

    calibrated_avalanche_pulse = None
    if config.include_avalanche_signal:
        calibrated_avalanche_pulse = build_avalanche_pulse(
            calibrated_gain.calibrated_avalanche_charge_c,
            geometry,
            override_width_s=config.avalanche_pulse_width_s,
        )

    notes = list(default_estimate.notes)
    if calibration is None:
        notes.append("No calibration record was supplied; calibrated output falls back to default behavior.")
    elif calibration.applies_to(gas.name):
        notes.append(
            f"Calibration record {calibration.calibration_name!r} was evaluated for gas {gas.name!r}."
        )
        if calibrated_gain.calibration_applied:
            notes.append("Calibrated gain overrides were applied.")
        else:
            notes.append("Calibration record was compatible but did not modify the default gain result.")
    else:
        notes.append(
            f"Calibration record {calibration.calibration_name!r} did not apply to gas {gas.name!r}; default behavior was retained."
        )

    calibrated_metadata: dict[str, JSONValue] = {
        "estimator_version": CALIBRATED_ESTIMATOR_VERSION,
        "default_estimator_version": default_estimate.estimator_version,
        "config": config.to_dict(),
        "geometry_summary": geometry_summary(geometry),
        "primary_statistics_proxy": estimate_primary_statistics_proxy(geometry, gas),
        "calibrated_gain": calibrated_gain.to_dict(),
        "calibration_applied": calibrated_gain.calibration_applied,
        "calibration_name": calibrated_gain.calibration_name,
        "calibration_record": None if calibration is None else calibration.compact_dict(),
        "calibration_mode": (
            "none"
            if calibration is None
            else "applied"
            if calibrated_gain.calibration_applied
            else "compatible_no_change"
            if calibration.applies_to(gas.name)
            else "gas_mismatch"
        ),
    }

    calibrated_result = DeterministicEstimate(
        estimator_version=CALIBRATED_ESTIMATOR_VERSION,
        geometry=geometry,
        gas=gas,
        created_primary_electrons_mean=default_estimate.created_primary_electrons_mean,
        collected_primary_electrons_mean=default_estimate.collected_primary_electrons_mean,
        drift_time_s=default_estimate.drift_time_s,
        attachment_survival_fraction=default_estimate.attachment_survival_fraction,
        collection_fraction_total=default_estimate.collection_fraction_total,
        gas_gain_mean=calibrated_gain.calibrated_gain_mean,
        avalanche_electrons_mean=calibrated_gain.calibrated_avalanche_electrons_mean,
        avalanche_charge_c=calibrated_gain.calibrated_avalanche_charge_c,
        direct_pulse=direct_pulse,
        avalanche_pulse=calibrated_avalanche_pulse,
        notes=notes,
        metadata=calibrated_metadata,
    )

    return CalibratedDeterministicEstimate(
        default_estimate=default_estimate,
        calibrated_result=calibrated_result,
        calibrated_gain=calibrated_gain,
        calibration_record=calibration,
        calibration_applied=calibrated_gain.calibration_applied,
        metadata={
            "gas_name": gas.name,
            "calibration_name": calibrated_gain.calibration_name,
            "calibration_applied": calibrated_gain.calibration_applied,
        },
    )


def estimate_calibrated(
    geometry: GeometryModel,
    *,
    gas: GasModel | str = "air_dry_1atm",
    calibration: CalibrationRecord | None = None,
    include_direct_image_pulse: bool = True,
    include_avalanche_signal: bool = True,
    use_attachment: bool = True,
    use_gain_surrogate: bool = True,
    direct_charge_efficiency: float = 1.0,
    avalanche_pulse_width_s: float | None = None,
    output_event_details: bool = False,
    metadata: dict[str, JSONValue] | None = None,
) -> CalibratedDeterministicEstimate:
    """
    Convenience wrapper to run the calibrated deterministic estimator directly.
    """
    gas_model = resolve_gas(gas)
    config = build_calibrated_estimator_config(
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
    return estimate_calibrated_from_config(config, calibration=calibration)


def estimate_calibrated_with_optional_file(
    geometry: GeometryModel,
    *,
    gas: GasModel | str = "air_dry_1atm",
    calibration_path: str | None = None,
    include_direct_image_pulse: bool = True,
    include_avalanche_signal: bool = True,
    use_attachment: bool = True,
    use_gain_surrogate: bool = True,
    direct_charge_efficiency: float = 1.0,
    avalanche_pulse_width_s: float | None = None,
    output_event_details: bool = False,
    metadata: dict[str, JSONValue] | None = None,
) -> CalibratedDeterministicEstimate:
    """
    Convenience wrapper that loads a calibration record from disk if provided.
    """
    calibration = maybe_load_calibration_record(calibration_path)
    return estimate_calibrated(
        geometry,
        gas=gas,
        calibration=calibration,
        include_direct_image_pulse=include_direct_image_pulse,
        include_avalanche_signal=include_avalanche_signal,
        use_attachment=use_attachment,
        use_gain_surrogate=use_gain_surrogate,
        direct_charge_efficiency=direct_charge_efficiency,
        avalanche_pulse_width_s=avalanche_pulse_width_s,
        output_event_details=output_event_details,
        metadata=metadata,
    )


def calibrated_result_to_dict(
    result: CalibratedDeterministicEstimate,
) -> dict[str, JSONValue]:
    """
    Convert a CalibratedDeterministicEstimate into a JSON-friendly dictionary.
    """
    if not isinstance(result, CalibratedDeterministicEstimate):
        raise TypeError(
            "result must be a CalibratedDeterministicEstimate instance, "
            f"got {type(result).__name__}."
        )
    return result.to_dict()


def calibrated_config_from_mapping(data: dict[str, JSONValue]) -> EstimatorConfig:
    """
    Build an EstimatorConfig from a generic mapping, suitable for calibrated CLI use.
    """
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dictionary, got {type(data).__name__}.")

    geometry_raw = data.get("geometry")
    if not isinstance(geometry_raw, dict):
        raise TypeError(
            "The 'geometry' field must be a dictionary compatible with GeometryModel."
        )

    geometry = geometry_from_mapping(geometry_raw)

    metadata = data.get("metadata")
    if metadata is None:
        normalized_metadata: dict[str, JSONValue] = {}
    elif isinstance(metadata, dict):
        normalized_metadata = {str(key): value for key, value in metadata.items()}
    else:
        raise TypeError(
            f"metadata must be a dictionary when provided, got {type(metadata).__name__}."
        )

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
        metadata=normalized_metadata,
    )


def estimate_calibrated_from_mapping(
    data: dict[str, JSONValue],
    *,
    calibration: CalibrationRecord | None = None,
) -> CalibratedDeterministicEstimate:
    """
    Build calibrated config from a mapping and run the calibrated estimate.
    """
    config = calibrated_config_from_mapping(data)
    return estimate_calibrated_from_config(config, calibration=calibration)


def estimate_calibrated_from_mapping_to_dict(
    data: dict[str, JSONValue],
    *,
    calibration: CalibrationRecord | None = None,
) -> dict[str, JSONValue]:
    """
    Build calibrated config from a mapping, run the estimate, and return a dict.
    """
    return estimate_calibrated_from_mapping(data, calibration=calibration).to_dict()


__all__ = [
    "CALIBRATED_ESTIMATOR_VERSION",
    "CalibratedDeterministicEstimate",
    "build_calibrated_estimator_config",
    "calibrated_config_from_mapping",
    "calibrated_result_to_dict",
    "estimate_calibrated",
    "estimate_calibrated_from_config",
    "estimate_calibrated_from_mapping",
    "estimate_calibrated_from_mapping_to_dict",
    "estimate_calibrated_with_optional_file",
]