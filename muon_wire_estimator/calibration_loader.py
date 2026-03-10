"""
Calibration loading helpers for the Level 3 muon wire estimator.

This module handles JSON-based calibration record loading and validation while
keeping file I/O separate from the calibration schema dataclasses.

Goals
-----
- standard-library-only
- robust file/path/error handling
- explicit schema validation
- safe fallback behavior for absent or incompatible calibration
- future-friendly layout for Garfield++-derived calibration products
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .calibration_models import CalibrationRecord, calibration_record_from_mapping
from .models import JSONValue


def load_calibration_mapping(path: str | Path) -> dict[str, Any]:
    """
    Load a calibration JSON file as a top-level dictionary.

    Parameters
    ----------
    path:
        Path to the calibration JSON file.

    Returns
    -------
    dict[str, Any]
        Parsed JSON mapping.

    Raises
    ------
    FileNotFoundError
        If the file does not exist or is not a regular file.
    ValueError
        If the file content cannot be decoded as a top-level JSON object.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Calibration file does not exist: {resolved}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Calibration path is not a file: {resolved}")

    try:
        raw = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Failed to read calibration file {resolved}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse calibration JSON file {resolved}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Top-level calibration JSON in {resolved} must be an object/dictionary, "
            f"got {type(data).__name__}."
        )
    return data


def load_calibration_record(path: str | Path) -> CalibrationRecord:
    """
    Load and validate a CalibrationRecord from disk.
    """
    mapping = load_calibration_mapping(path)
    return calibration_record_from_mapping(mapping)


def maybe_load_calibration_record(path: str | Path | None) -> CalibrationRecord | None:
    """
    Load a calibration record if a path is provided, otherwise return None.

    This helper is convenient for optional calibration workflows.
    """
    if path is None:
        return None
    return load_calibration_record(path)


def calibration_record_to_dict(record: CalibrationRecord) -> dict[str, JSONValue]:
    """
    Convert a CalibrationRecord to a JSON-friendly full dictionary.
    """
    if not isinstance(record, CalibrationRecord):
        raise TypeError(
            "record must be a CalibrationRecord instance, "
            f"got {type(record).__name__}."
        )
    return record.to_dict()


def calibration_record_to_compact_dict(
    record: CalibrationRecord,
) -> dict[str, JSONValue]:
    """
    Convert a CalibrationRecord to a JSON-friendly compact dictionary.
    """
    if not isinstance(record, CalibrationRecord):
        raise TypeError(
            "record must be a CalibrationRecord instance, "
            f"got {type(record).__name__}."
        )
    return record.compact_dict()


def record_applies_to_gas(record: CalibrationRecord, gas_name: str) -> bool:
    """
    Return True if the calibration record applies to the requested gas.
    """
    if not isinstance(record, CalibrationRecord):
        raise TypeError(
            "record must be a CalibrationRecord instance, "
            f"got {type(record).__name__}."
        )
    return record.applies_to(gas_name)


def load_matching_calibration_record(
    path: str | Path,
    gas_name: str,
    *,
    allow_mismatch: bool = True,
) -> CalibrationRecord | None:
    """
    Load a calibration record and optionally require that it applies to a gas.

    Parameters
    ----------
    path:
        Calibration file path.
    gas_name:
        Gas name to test compatibility against.
    allow_mismatch:
        If True, return None when the record does not apply.
        If False, raise ValueError on mismatch.
    """
    record = load_calibration_record(path)
    if record.applies_to(gas_name):
        return record
    if allow_mismatch:
        return None
    raise ValueError(
        f"Calibration record {record.calibration_name!r} does not apply to gas "
        f"{gas_name!r}."
    )


def calibration_loader_summary(
    path: str | Path,
    *,
    gas_name: str | None = None,
) -> dict[str, JSONValue]:
    """
    Load a calibration file and return a compact JSON-friendly summary.
    """
    record = load_calibration_record(path)
    applies = None if gas_name is None else record.applies_to(gas_name)

    return {
        "path": str(Path(path)),
        "calibration_name": record.calibration_name,
        "version": record.version,
        "source": record.source,
        "applies_to_gas": record.applies_to_gas,
        "queried_gas_name": gas_name,
        "applies_to_query": applies,
        "record": record.compact_dict(),
    }


__all__ = [
    "calibration_loader_summary",
    "calibration_record_to_compact_dict",
    "calibration_record_to_dict",
    "load_calibration_mapping",
    "load_calibration_record",
    "load_matching_calibration_record",
    "maybe_load_calibration_record",
    "record_applies_to_gas",
]