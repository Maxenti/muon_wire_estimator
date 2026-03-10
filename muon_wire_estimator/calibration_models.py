"""
Schema models for Level 3 calibration records.

This module defines lightweight, validated dataclasses for loading and applying
external calibration information without breaking the default surrogate
estimator behavior.

The design goals are:

- standard-library-only
- explicit schema validation
- easy JSON serialization/deserialization
- partial override support
- clear distinction between default/surrogate and calibrated behavior
- future compatibility with Garfield++-derived tuning products

These models do not perform file I/O themselves. They only define structure,
validation, and conversion helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import JSONValue, dataclass_to_dict, merge_mappings


def _ensure_non_empty(name: str, value: str) -> None:
    """Validate that a required string is non-empty."""
    if not value or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")


def _ensure_positive(name: str, value: float, *, allow_zero: bool = False) -> None:
    """Validate positivity or non-negativity."""
    if allow_zero:
        if value < 0.0:
            raise ValueError(f"{name} must be >= 0, got {value!r}.")
        return
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0, got {value!r}.")


def _ensure_fraction(name: str, value: float) -> None:
    """Validate that a float lies in [0, 1]."""
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}.")


@dataclass(slots=True)
class GasCalibrationOverride:
    """
    Optional calibrated overrides for GasModel-like parameters.

    Any field set to None means "leave the default surrogate value unchanged".
    """

    pressure_atm: float | None = None
    temperature_k: float | None = None
    w_value_ev: float | None = None
    mean_energy_loss_mev_per_cm: float | None = None
    drift_velocity_m_per_s: float | None = None
    attachment_time_s: float | None = None
    collection_efficiency: float | None = None
    gain_field_scale_v_per_m: float | None = None
    gain_slope: float | None = None
    gain_cap: float | None = None
    fano_factor: float | None = None
    mean_cluster_size_electrons: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.pressure_atm is not None:
            _ensure_positive("pressure_atm", self.pressure_atm)
        if self.temperature_k is not None:
            _ensure_positive("temperature_k", self.temperature_k)
        if self.w_value_ev is not None:
            _ensure_positive("w_value_ev", self.w_value_ev)
        if self.mean_energy_loss_mev_per_cm is not None:
            _ensure_positive(
                "mean_energy_loss_mev_per_cm", self.mean_energy_loss_mev_per_cm
            )
        if self.drift_velocity_m_per_s is not None:
            _ensure_positive("drift_velocity_m_per_s", self.drift_velocity_m_per_s)
        if self.attachment_time_s is not None:
            _ensure_positive("attachment_time_s", self.attachment_time_s)
        if self.collection_efficiency is not None:
            _ensure_fraction("collection_efficiency", self.collection_efficiency)
        if self.gain_field_scale_v_per_m is not None:
            _ensure_positive(
                "gain_field_scale_v_per_m", self.gain_field_scale_v_per_m
            )
        if self.gain_slope is not None:
            _ensure_positive("gain_slope", self.gain_slope)
        if self.gain_cap is not None:
            _ensure_positive("gain_cap", self.gain_cap)
        if self.fano_factor is not None:
            _ensure_positive("fano_factor", self.fano_factor, allow_zero=True)
        if self.mean_cluster_size_electrons is not None:
            _ensure_positive(
                "mean_cluster_size_electrons", self.mean_cluster_size_electrons
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]

    def compact_dict(self) -> dict[str, JSONValue]:
        """Return only non-None overrides."""
        return {
            key: value
            for key, value in self.to_dict().items()
            if value is not None
        }


@dataclass(slots=True)
class GainCalibrationOverride:
    """
    Optional calibrated overrides for gain behavior.

    These fields allow Level 3 calibration to adjust the deterministic and
    stochastic gain layers without replacing the full package architecture.
    """

    use_calibrated_gain: bool = True
    mean_gain_scale: float | None = None
    mean_gain_offset: float | None = None
    fixed_mean_gain: float | None = None
    gain_shape_override: float | None = None
    field_scale_multiplier: float | None = None
    slope_multiplier: float | None = None
    cap_override: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.mean_gain_scale is not None:
            _ensure_positive("mean_gain_scale", self.mean_gain_scale, allow_zero=True)
        if self.mean_gain_offset is not None and self.mean_gain_offset < 0.0:
            raise ValueError(
                f"mean_gain_offset must be >= 0, got {self.mean_gain_offset!r}."
            )
        if self.fixed_mean_gain is not None:
            _ensure_positive("fixed_mean_gain", self.fixed_mean_gain, allow_zero=True)
        if self.gain_shape_override is not None:
            _ensure_positive("gain_shape_override", self.gain_shape_override)
        if self.field_scale_multiplier is not None:
            _ensure_positive("field_scale_multiplier", self.field_scale_multiplier)
        if self.slope_multiplier is not None:
            _ensure_positive("slope_multiplier", self.slope_multiplier)
        if self.cap_override is not None:
            _ensure_positive("cap_override", self.cap_override)

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]

    def compact_dict(self) -> dict[str, JSONValue]:
        """Return only non-None overrides plus explicit booleans."""
        return {
            key: value
            for key, value in self.to_dict().items()
            if value is not None
        }


@dataclass(slots=True)
class DriftCalibrationOverride:
    """
    Optional calibrated overrides for drift/attachment behavior.
    """

    drift_velocity_scale: float | None = None
    fixed_drift_velocity_m_per_s: float | None = None
    attachment_time_scale: float | None = None
    fixed_attachment_time_s: float | None = None
    collection_fraction_scale: float | None = None
    fixed_collection_fraction: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.drift_velocity_scale is not None:
            _ensure_positive(
                "drift_velocity_scale", self.drift_velocity_scale, allow_zero=True
            )
        if self.fixed_drift_velocity_m_per_s is not None:
            _ensure_positive(
                "fixed_drift_velocity_m_per_s", self.fixed_drift_velocity_m_per_s
            )
        if self.attachment_time_scale is not None:
            _ensure_positive(
                "attachment_time_scale", self.attachment_time_scale, allow_zero=True
            )
        if self.fixed_attachment_time_s is not None:
            _ensure_positive("fixed_attachment_time_s", self.fixed_attachment_time_s)
        if self.collection_fraction_scale is not None:
            _ensure_positive(
                "collection_fraction_scale",
                self.collection_fraction_scale,
                allow_zero=True,
            )
        if self.fixed_collection_fraction is not None:
            _ensure_fraction(
                "fixed_collection_fraction", self.fixed_collection_fraction
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]

    def compact_dict(self) -> dict[str, JSONValue]:
        """Return only non-None overrides."""
        return {
            key: value
            for key, value in self.to_dict().items()
            if value is not None
        }


@dataclass(slots=True)
class PulseCalibrationOverride:
    """
    Optional calibrated overrides for pulse/readout conversion.
    """

    width_scale: float | None = None
    fixed_width_s: float | None = None
    rise_time_scale: float | None = None
    fall_time_scale: float | None = None
    termination_ohm_override: float | None = None
    voltage_scale: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.width_scale is not None:
            _ensure_positive("width_scale", self.width_scale, allow_zero=True)
        if self.fixed_width_s is not None:
            _ensure_positive("fixed_width_s", self.fixed_width_s)
        if self.rise_time_scale is not None:
            _ensure_positive("rise_time_scale", self.rise_time_scale, allow_zero=True)
        if self.fall_time_scale is not None:
            _ensure_positive("fall_time_scale", self.fall_time_scale, allow_zero=True)
        if self.termination_ohm_override is not None:
            _ensure_positive(
                "termination_ohm_override", self.termination_ohm_override
            )
        if self.voltage_scale is not None:
            _ensure_positive("voltage_scale", self.voltage_scale, allow_zero=True)

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]

    def compact_dict(self) -> dict[str, JSONValue]:
        """Return only non-None overrides."""
        return {
            key: value
            for key, value in self.to_dict().items()
            if value is not None
        }


@dataclass(slots=True)
class CalibrationRecord:
    """
    Full Level 3 calibration schema.

    A record may partially override the default surrogate configuration for a
    particular gas and detector context. Missing blocks are interpreted as
    "use defaults".
    """

    calibration_name: str
    version: str
    source: str
    applies_to_gas: str | None = None
    gas_overrides: GasCalibrationOverride = field(
        default_factory=GasCalibrationOverride
    )
    gain_overrides: GainCalibrationOverride = field(
        default_factory=GainCalibrationOverride
    )
    drift_overrides: DriftCalibrationOverride = field(
        default_factory=DriftCalibrationOverride
    )
    pulse_overrides: PulseCalibrationOverride = field(
        default_factory=PulseCalibrationOverride
    )
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("calibration_name", self.calibration_name)
        _ensure_non_empty("version", self.version)
        _ensure_non_empty("source", self.source)
        if self.applies_to_gas is not None and not self.applies_to_gas.strip():
            raise ValueError("applies_to_gas must be None or a non-empty string.")
        if not isinstance(self.metadata, dict):
            raise TypeError(
                f"metadata must be a dict, got {type(self.metadata).__name__}."
            )
        self.metadata = {str(key): value for key, value in self.metadata.items()}

    @property
    def is_gas_specific(self) -> bool:
        """Return True if the record targets a specific gas."""
        return self.applies_to_gas is not None

    def applies_to(self, gas_name: str) -> bool:
        """Return True if the record applies to the given gas name."""
        if not gas_name or not gas_name.strip():
            raise ValueError("gas_name must be a non-empty string.")
        if self.applies_to_gas is None:
            return True
        return gas_name.strip() == self.applies_to_gas

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly full dictionary."""
        return dataclass_to_dict(self)  # type: ignore[return-value]

    def compact_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-friendly dictionary with empty override blocks pruned."""
        payload = {
            "calibration_name": self.calibration_name,
            "version": self.version,
            "source": self.source,
            "applies_to_gas": self.applies_to_gas,
            "gas_overrides": self.gas_overrides.compact_dict(),
            "gain_overrides": self.gain_overrides.compact_dict(),
            "drift_overrides": self.drift_overrides.compact_dict(),
            "pulse_overrides": self.pulse_overrides.compact_dict(),
            "metadata": dict(self.metadata),
        }
        return {
            key: value
            for key, value in payload.items()
            if value not in (None, {}, [])
        }

    def merged_metadata(self, extra: dict[str, JSONValue] | None = None) -> dict[str, JSONValue]:
        """Merge record metadata with optional extra metadata."""
        if extra is None:
            return dict(self.metadata)
        return merge_mappings(self.metadata, extra)


def gas_override_from_mapping(data: dict[str, JSONValue] | None) -> GasCalibrationOverride:
    """Build GasCalibrationOverride from a generic mapping."""
    if data is None:
        return GasCalibrationOverride()
    if not isinstance(data, dict):
        raise TypeError(
            f"gas_overrides must be a dict when provided, got {type(data).__name__}."
        )
    return GasCalibrationOverride(
        pressure_atm=_optional_float(data.get("pressure_atm")),
        temperature_k=_optional_float(data.get("temperature_k")),
        w_value_ev=_optional_float(data.get("w_value_ev")),
        mean_energy_loss_mev_per_cm=_optional_float(
            data.get("mean_energy_loss_mev_per_cm")
        ),
        drift_velocity_m_per_s=_optional_float(data.get("drift_velocity_m_per_s")),
        attachment_time_s=_optional_float(data.get("attachment_time_s")),
        collection_efficiency=_optional_float(data.get("collection_efficiency")),
        gain_field_scale_v_per_m=_optional_float(data.get("gain_field_scale_v_per_m")),
        gain_slope=_optional_float(data.get("gain_slope")),
        gain_cap=_optional_float(data.get("gain_cap")),
        fano_factor=_optional_float(data.get("fano_factor")),
        mean_cluster_size_electrons=_optional_float(
            data.get("mean_cluster_size_electrons")
        ),
        notes=_optional_str(data.get("notes")),
    )


def gain_override_from_mapping(
    data: dict[str, JSONValue] | None,
) -> GainCalibrationOverride:
    """Build GainCalibrationOverride from a generic mapping."""
    if data is None:
        return GainCalibrationOverride()
    if not isinstance(data, dict):
        raise TypeError(
            f"gain_overrides must be a dict when provided, got {type(data).__name__}."
        )
    return GainCalibrationOverride(
        use_calibrated_gain=bool(data.get("use_calibrated_gain", True)),
        mean_gain_scale=_optional_float(data.get("mean_gain_scale")),
        mean_gain_offset=_optional_float(data.get("mean_gain_offset")),
        fixed_mean_gain=_optional_float(data.get("fixed_mean_gain")),
        gain_shape_override=_optional_float(data.get("gain_shape_override")),
        field_scale_multiplier=_optional_float(data.get("field_scale_multiplier")),
        slope_multiplier=_optional_float(data.get("slope_multiplier")),
        cap_override=_optional_float(data.get("cap_override")),
        notes=_optional_str(data.get("notes")),
    )


def drift_override_from_mapping(
    data: dict[str, JSONValue] | None,
) -> DriftCalibrationOverride:
    """Build DriftCalibrationOverride from a generic mapping."""
    if data is None:
        return DriftCalibrationOverride()
    if not isinstance(data, dict):
        raise TypeError(
            f"drift_overrides must be a dict when provided, got {type(data).__name__}."
        )
    return DriftCalibrationOverride(
        drift_velocity_scale=_optional_float(data.get("drift_velocity_scale")),
        fixed_drift_velocity_m_per_s=_optional_float(
            data.get("fixed_drift_velocity_m_per_s")
        ),
        attachment_time_scale=_optional_float(data.get("attachment_time_scale")),
        fixed_attachment_time_s=_optional_float(data.get("fixed_attachment_time_s")),
        collection_fraction_scale=_optional_float(
            data.get("collection_fraction_scale")
        ),
        fixed_collection_fraction=_optional_float(data.get("fixed_collection_fraction")),
        notes=_optional_str(data.get("notes")),
    )


def pulse_override_from_mapping(
    data: dict[str, JSONValue] | None,
) -> PulseCalibrationOverride:
    """Build PulseCalibrationOverride from a generic mapping."""
    if data is None:
        return PulseCalibrationOverride()
    if not isinstance(data, dict):
        raise TypeError(
            f"pulse_overrides must be a dict when provided, got {type(data).__name__}."
        )
    return PulseCalibrationOverride(
        width_scale=_optional_float(data.get("width_scale")),
        fixed_width_s=_optional_float(data.get("fixed_width_s")),
        rise_time_scale=_optional_float(data.get("rise_time_scale")),
        fall_time_scale=_optional_float(data.get("fall_time_scale")),
        termination_ohm_override=_optional_float(data.get("termination_ohm_override")),
        voltage_scale=_optional_float(data.get("voltage_scale")),
        notes=_optional_str(data.get("notes")),
    )


def calibration_record_from_mapping(data: dict[str, JSONValue]) -> CalibrationRecord:
    """
    Build a CalibrationRecord from a generic mapping.
    """
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dict, got {type(data).__name__}.")
    try:
        calibration_name = str(data["calibration_name"])
        version = str(data["version"])
        source = str(data["source"])
    except KeyError as exc:
        raise KeyError(
            f"Missing required calibration field: {exc.args[0]!r}."
        ) from exc

    metadata_raw = data.get("metadata", {})
    if not isinstance(metadata_raw, dict):
        raise TypeError(
            f"metadata must be a dict when provided, got {type(metadata_raw).__name__}."
        )

    return CalibrationRecord(
        calibration_name=calibration_name,
        version=version,
        source=source,
        applies_to_gas=_optional_str(data.get("applies_to_gas")),
        gas_overrides=gas_override_from_mapping(_optional_mapping(data.get("gas_overrides"))),
        gain_overrides=gain_override_from_mapping(_optional_mapping(data.get("gain_overrides"))),
        drift_overrides=drift_override_from_mapping(_optional_mapping(data.get("drift_overrides"))),
        pulse_overrides=pulse_override_from_mapping(_optional_mapping(data.get("pulse_overrides"))),
        metadata={str(key): value for key, value in metadata_raw.items()},
    )


def _optional_float(value: JSONValue) -> float | None:
    """Return float(value) or None."""
    if value is None:
        return None
    return float(value)


def _optional_str(value: JSONValue) -> str | None:
    """Return str(value) or None."""
    if value is None:
        return None
    return str(value)


def _optional_mapping(value: JSONValue) -> dict[str, JSONValue] | None:
    """Return a string-keyed mapping or None."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError(f"Expected mapping or None, got {type(value).__name__}.")
    return {str(key): item for key, item in value.items()}


__all__ = [
    "CalibrationRecord",
    "DriftCalibrationOverride",
    "GainCalibrationOverride",
    "GasCalibrationOverride",
    "PulseCalibrationOverride",
    "calibration_record_from_mapping",
    "drift_override_from_mapping",
    "gain_override_from_mapping",
    "gas_override_from_mapping",
    "pulse_override_from_mapping",
]