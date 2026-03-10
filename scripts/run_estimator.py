#!/usr/bin/env python3
"""
CLI entrypoint for the Level 1 deterministic muon wire estimator.

This script reads a JSON configuration file, runs the deterministic estimator,
and writes the result either to stdout or to a JSON output file.

Example
-------
python scripts/run_estimator.py \
    --config examples/level1_example.json \
    --pretty

python scripts/run_estimator.py \
    --config examples/level1_example.json \
    --output out/result.json \
    --pretty
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from muon_wire_estimator import (
    config_from_mapping,
    estimate_from_config,
    list_builtin_gases,
    result_to_dict,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the Level 1 deterministic muon wire estimator from a JSON config."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the estimator JSON configuration file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON file path. Defaults to stdout.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output with indentation.",
    )
    parser.add_argument(
        "--list-gases",
        action="store_true",
        help="List built-in gas names and exit.",
    )
    return parser


def load_json_file(path: Path) -> dict[str, Any]:
    """
    Load a JSON object from disk.

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    ValueError
        If the file cannot be parsed into a top-level JSON object.
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file does not exist: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Configuration path is not a file: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Failed to read configuration file {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse JSON configuration file {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Top-level JSON in {path} must be an object/dictionary, got {type(data).__name__}."
        )

    return data


def write_json_output(
    data: dict[str, Any],
    *,
    output_path: Path | None,
    pretty: bool,
) -> None:
    """
    Write JSON either to stdout or to a file.
    """
    json_text = json.dumps(
        data,
        indent=2 if pretty else None,
        sort_keys=True,
    )
    if pretty:
        json_text += "\n"

    if output_path is None:
        sys.stdout.write(json_text)
        if not pretty:
            sys.stdout.write("\n")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(json_text, encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Failed to write output file {output_path}: {exc}") from exc


def print_builtin_gases() -> None:
    """Print the available built-in gas names."""
    for name in list_builtin_gases():
        print(name)


def main(argv: list[str] | None = None) -> int:
    """
    Run the CLI.

    Returns
    -------
    int
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_gases:
        print_builtin_gases()
        return 0

    try:
        config_data = load_json_file(args.config)
        config = config_from_mapping(config_data)
        result = estimate_from_config(config)
        result_dict = result_to_dict(result)
        write_json_output(
            result_dict,
            output_path=args.output,
            pretty=args.pretty,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())