"""
Calibrated gain helpers for the Level 3 muon wire estimator.

This module layers optional calibration behavior on top of the default
surrogate gain model. The philosophy is:

- keep the default deterministic gain estimate as the baseline
- allow external calibration records to override or rescale gain behavior
- remain safe and non-breaking when calibration is absent or incomplete
- clearly label whether outputs came from surrogate/default or calibrated logic

This module does not replace the entire estimator. It focuses on the gas-gain
part of the signal chain and is intended to be reused by calibrated_core.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .calibration_models import CalibrationRecord, GainCalibrationOverride
from .gain import GainEstimate, estimate_gain
from .gases import get_gas
from .models import GasModel, GeometryModel, JSONValue


@dataclass(slots=True)
class CalibratedGainEstimate:
    """
    Gain estimate that keeps both default and calibrated information visible.

    Attributes
    ----------
    default_gain:
        The unmodified Level 1 surrogate gain estimate.
    calibrated_gain_mean:
        Final gain mean after calibration logic is applied.
    calibrated_avalanche_electrons_mean:
        Mean avalanche electrons using the calibrated gain.
    calibrated_avalanche_charge_c:
        Mean avalanche charge using the calibrated gain.
    calibration_applied:
        Whether a calibration record actually modified the gain result.
    calibration_name:
        Name of the calibration record, if one was used.
    metadata:
        JSON-friendly auxiliary information.
    """

    default_gain: GainEstimate
    calibrated_gain_mean: float
    calibrated_avalanche_electrons_mean: float
    calibrated_avalanche_charge_c: float
    calibration_applied: bool
    calibration_name: str | None
    metadata: dict[str, JSONValue]

    def __post_init__(self) -> None:
        if not isinstance(self.default_gain, GainEstimate):
            raise TypeError(
                "default_gain must be a GainEstimate instance, "
                f"got {type(self.default_gain).__name__}."
            )
        if self.calibrated_gain_mean < 0.0:
            raise ValueError(
                "calibrated_gain_mean must be >= 0, "
                f"got {self.calibrated_gain_mean!r}."
            )
        if self.calibrated_avalanche_electrons_mean < 0.0:
            raise ValueError(
                "calibrated_avalanche_electrons_mean must be >= 0, "
                f"got {self.calibrated_avalanche_electrons_mean!r}."
            )
        if self.calibrated_avalanche_charge_c < 0.0:
            raise ValueError(
                "calibrated_avalanche_charge_c must be >= 0, "
                f"got {self.calibrated_avalanche_charge_c!r}."
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "default_gain": self.default_gain.to_dict(),
            "calibrated_gain_mean": self.calibrated_gain_mean,
            "calibrated_avalanche_electrons_mean": self.calibrated_avalanche_electrons_mean,
            "calibrated_avalanche_charge_c": self.calibrated_avalanche_charge_c,
            "calibration_applied": self.calibration_applied,
            "calibration_name": self.calibration_name,
            "metadata": dict(self.metadata),
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


def _apply_gain_override(
    default_gain_mean: float,
    override: GainCalibrationOverride,
) -> tuple[float, dict[str, JSONValue]]:
    """
    Apply gain-override logic to a default mean gain.

    Order of operations
    -------------------
    1. Start from default surrogate gain
    2. Optionally force a fixed_mean_gain
    3. Else optionally add mean_gain_offset
    4. Else optionally apply mean_gain_scale
    5. Clamp to >= 0
    """
    if default_gain_mean < 0.0:
        raise ValueError(
            f"default_gain_mean must be >= 0, got {default_gain_mean!r}."
        )
    if not isinstance(override, GainCalibrationOverride):
        raise TypeError(
            "override must be a GainCalibrationOverride instance, "
            f"got {type(override).__name__}."
        )

    metadata: dict[str, JSONValue] = {
        "default_gain_mean": default_gain_mean,
        "use_calibrated_gain": override.use_calibrated_gain,
    }

    if not override.use_calibrated_gain:
        metadata["calibration_mode"] = "disabled"
        return default_gain_mean, metadata

    if override.fixed_mean_gain is not None:
        calibrated = override.fixed_mean_gain
        metadata["calibration_mode"] = "fixed_mean_gain"
        metadata["fixed_mean_gain"] = override.fixed_mean_gain
        return max(calibrated, 0.0), metadata

    calibrated = default_gain_mean
    metadata["calibration_mode"] = "scaled_offset"

    if override.mean_gain_scale is not None:
        calibrated *= override.mean_gain_scale
        metadata["mean_gain_scale"] = override.mean_gain_scale

    if override.mean_gain_offset is not None:
        calibrated += override.mean_gain_offset
        metadata["mean_gain_offset"] = override.mean_gain_offset

    if override.cap_override is not None:
        calibrated = min(calibrated, override.cap_override)
        metadata["cap_override"] = override.cap_override

    return max(calibrated, 0.0), metadata


def calibration_applies_to_gas(
    calibration: CalibrationRecord | None,
    gas: GasModel | str,
) -> bool:
    """
    Return True if a calibration record is absent (fallback case) or applies
    to the provided gas.
    """
    if calibration is None:
        return False
    if not isinstance(calibration, CalibrationRecord):
        raise TypeError(
            "calibration must be CalibrationRecord or None, "
            f"got {type(calibration).__name__}."
        )
    gas_model = resolve_gas(gas)
    return calibration.applies_to(gas_model.name)


def estimate_calibrated_gain(
    geometry: GeometryModel,
    gas: GasModel | str,
    collected_primary_electrons_mean: float,
    *,
    calibration: CalibrationRecord | None = None,
    use_gain_surrogate: bool = True,
) -> CalibratedGainEstimate:
    """
    Estimate gain using the default surrogate and optional calibration override.

    Parameters
    ----------
    geometry:
        Geometry model.
    gas:
        Gas model or built-in gas name.
    collected_primary_electrons_mean:
        Mean number of electrons reaching the multiplication region.
    calibration:
        Optional calibration record.
    use_gain_surrogate:
        Whether to enable the default surrogate before calibration is applied.

    Returns
    -------
    CalibratedGainEstimate
        Object containing both default and calibrated gain information.
    """
    if collected_primary_electrons_mean < 0.0:
        raise ValueError(
            "collected_primary_electrons_mean must be >= 0, "
            f"got {collected_primary_electrons_mean!r}."
        )

    gas_model = resolve_gas(gas)
    default_gain = estimate_gain(
        geometry,
        gas_model,
        collected_primary_electrons_mean,
        use_gain_surrogate=use_gain_surrogate,
    )

    calibration_applied = False
    calibration_name: str | None = None
    metadata: dict[str, JSONValue] = {
        "gas_name": gas_model.name,
        "use_gain_surrogate": use_gain_surrogate,
        "source_mode": "default_surrogate",
    }

    calibrated_gain_mean = default_gain.gas_gain_mean

    if calibration is not None and calibration.applies_to(gas_model.name):
        calibrated_gain_mean, override_metadata = _apply_gain_override(
            default_gain.gas_gain_mean,
            calibration.gain_overrides,
        )
        calibration_applied = calibrated_gain_mean != default_gain.gas_gain_mean
        calibration_name = calibration.calibration_name
        metadata["source_mode"] = (
            "calibrated_override" if calibration_applied else "default_surrogate"
        )
        metadata["calibration_record"] = calibration.compact_dict()
        metadata["gain_override"] = override_metadata
    elif calibration is not None:
        metadata["source_mode"] = "default_surrogate_gas_mismatch"
        metadata["calibration_record"] = calibration.compact_dict()

    calibrated_avalanche_electrons_mean = (
        collected_primary_electrons_mean * calibrated_gain_mean
    )
    calibrated_avalanche_charge_c = calibrated_avalanche_electrons_mean * 1.602176634e-19

    return CalibratedGainEstimate(
        default_gain=default_gain,
        calibrated_gain_mean=calibrated_gain_mean,
        calibrated_avalanche_electrons_mean=calibrated_avalanche_electrons_mean,
        calibrated_avalanche_charge_c=calibrated_avalanche_charge_c,
        calibration_applied=calibration_applied,
        calibration_name=calibration_name,
        metadata=metadata,
    )


def calibrated_gain_summary(
    geometry: GeometryModel,
    gas: GasModel | str,
    collected_primary_electrons_mean: float,
    *,
    calibration: CalibrationRecord | None = None,
    use_gain_surrogate: bool = True,
) -> dict[str, JSONValue]:
    """
    Return a JSON-friendly calibrated gain summary block.
    """
    estimate = estimate_calibrated_gain(
        geometry,
        gas,
        collected_primary_electrons_mean,
        calibration=calibration,
        use_gain_surrogate=use_gain_surrogate,
    )
    return estimate.to_dict()


__all__ = [
    "CalibratedGainEstimate",
    "calibrated_gain_summary",
    "calibration_applies_to_gas",
    "estimate_calibrated_gain",
    "resolve_gas",
]