# Muon Wire Estimator

A lightweight, production-ready Python package for estimating whether a single muon passing near a wire is likely to produce a measurable signal at a terminated readout.

This project refactors a baseline single-file estimator into a small, self-contained package with **three levels of realism**:

- **Level 1:** deterministic engineering estimate
- **Level 2:** stochastic repeated-event simulation
- **Level 3:** optional calibration-aware comparison infrastructure

The package is intentionally simple enough to run locally with the Python standard library only, while being structured so later Garfield++-derived calibration products can be dropped in without redesigning the whole codebase.

---

## What this estimator is

This estimator is a **physics-motivated engineering surrogate** for the question:

> Given a muon passing near a wire, a gas choice, a geometry, a voltage, and a simple scope/readout model, what signal amplitude should I expect, and is it plausibly visible?

It explicitly separates two signal concepts:

1. **Direct muon image pulse**
2. **Ordinary gas-avalanche pulse**

That distinction matters because those are not the same physical contribution, and in practice the quantity you usually care most about for ordinary gaseous-wire detection is the **avalanche pulse peak voltage into the termination**.

---

## What this estimator is not

This package is **not** a microscopic detector simulation.

It does **not** replace:

- Garfield++
- HEED/TrackHeed-level cluster formation
- AvalancheMicroscopic
- full electron transport with detailed diffusion
- detailed Shockley–Ramo current modeling
- electronics transfer-function simulation
- waveform digitizer modeling
- time-dependent ion-tail simulation
- field maps from full multi-wire geometry solvers

Instead, it gives a compact bridge between a very rough hand estimate and a future calibrated workflow.

---

## Which output to compare to oscilloscope measurements

For ordinary wire-signal visibility, the main quantity to compare against oscilloscope thresholds or measured amplitudes is usually:

- `avalanche_pulse.peak_voltage_v`

That is the best single engineering output in this package for asking:

- Is the signal likely above my trigger/discriminator threshold?
- Is the pulse plausibly visible on a 50 ohm terminated scope?
- How does changing gas, bias, geometry, or calibration shift the visible signal?

A secondary quantity you may also inspect is:

- `direct_pulse.peak_voltage_v`

but it should remain conceptually separate from the avalanche signal.

---

## Why air estimates are especially uncertain

Predictions in air are much more uncertain than predictions in a conventional detector gas.

That is because in air:

- attachment can be strong and environment-dependent
- humidity and impurities matter
- avalanche onset is less stable and less detector-like
- microscopic transport and multiplication behavior are less well represented by simple surrogates
- breakdown-related behavior can complicate interpretation

So if you use this package with `air_dry_1atm`, treat the result as a coarse plausibility estimate, not a precision prediction.

---

## Level overview

## Level 1: deterministic engineering estimate

Level 1 adds a compact deterministic pipeline with:

- gas registry and built-in gas definitions
- drift time estimate
- attachment survival estimate
- collection fraction estimate
- simple surface-field-based avalanche gain surrogate
- finite pulse-width conversion to peak current and peak voltage
- separate direct-image and avalanche pulse blocks

Main files:

- `muon_wire_estimator/gases.py`
- `muon_wire_estimator/geometry.py`
- `muon_wire_estimator/ionization.py`
- `muon_wire_estimator/drift.py`
- `muon_wire_estimator/gain.py`
- `muon_wire_estimator/pulse.py`
- `muon_wire_estimator/core.py`

Use this level when you want a fast mean estimate.

## Level 2: stochastic event simulation

Level 2 adds repeated-event simulation with:

- seeded deterministic RNG
- stochastic primary ionization sampling
- stochastic collection/survival sampling
- stochastic gain fluctuations
- repeated event generation
- threshold crossing studies
- summary statistics
- optional event list output

Main files:

- `muon_wire_estimator/randomness.py`
- `muon_wire_estimator/stochastic.py`
- `muon_wire_estimator/thresholds.py`
- `muon_wire_estimator/event_stats.py`

Use this level when you want event distributions rather than only a mean result.

## Level 3: calibration-aware infrastructure

Level 3 adds:

- calibration JSON schema dataclasses
- calibration file loading
- calibrated gain override support
- default-vs-calibrated comparison reports
- safe fallback to surrogate/default behavior
- future-friendly structure for Garfield++-derived replacement

Main files:

- `muon_wire_estimator/calibration_models.py`
- `muon_wire_estimator/calibration_loader.py`
- `muon_wire_estimator/calibrated_gain.py`
- `muon_wire_estimator/calibrated_core.py`
- `muon_wire_estimator/reporting.py`

Use this level when you want to compare the baseline surrogate against tuned/calibrated behavior.

---

## Package layout

```text
muon_wire_estimator/
├── __init__.py
├── models.py
├── gases.py
├── geometry.py
├── ionization.py
├── drift.py
├── gain.py
├── pulse.py
├── core.py
├── randomness.py
├── stochastic.py
├── thresholds.py
├── event_stats.py
├── calibration_models.py
├── calibration_loader.py
├── calibrated_gain.py
├── calibrated_core.py
└── reporting.py

scripts/
├── run_estimator.py
├── run_event_scan.py
└── compare_default_vs_calibrated.py

examples/
├── level1_example.json
├── level2_event_scan.json
└── level3_calibration.json

calibration/
└── default_surrogate_calibration.json
Requirements

Python 3.11+

No third-party dependencies

Running Level 1

Run the deterministic estimate:

python scripts/run_estimator.py --config examples/level1_example.json --pretty

Write to a file:

python scripts/run_estimator.py \
  --config examples/level1_example.json \
  --output out/level1_result.json \
  --pretty

List built-in gases:

python scripts/run_estimator.py --config examples/level1_example.json --list-gases
Level 1 output interpretation

The most important fields are typically:

gas_gain_mean

avalanche_charge_c

avalanche_pulse.peak_voltage_v

direct_pulse.peak_voltage_v

For ordinary signal visibility, focus primarily on:

avalanche_pulse.peak_voltage_v

Running Level 2

Run the stochastic repeated-event scan:

python scripts/run_event_scan.py --config examples/level2_event_scan.json --pretty

Write to a file:

python scripts/run_event_scan.py \
  --config examples/level2_event_scan.json \
  --output out/level2_scan.json \
  --pretty

Get a more compact report-style view:

python scripts/run_event_scan.py \
  --config examples/level2_event_scan.json \
  --report-view \
  --pretty
Level 2 output interpretation

Useful fields include:

mean_peak_voltage_v

median_peak_voltage_v

max_peak_voltage_v

fraction_above_threshold

That last one is especially useful when asking whether a signal is likely to be visible often enough above a chosen threshold.

Running Level 3

Run the default-vs-calibrated comparison:

python scripts/compare_default_vs_calibrated.py \
  --config examples/level3_calibration.json \
  --pretty

Write to a file:

python scripts/compare_default_vs_calibrated.py \
  --config examples/level3_calibration.json \
  --output out/level3_comparison.json \
  --pretty

Get only minimal status:

python scripts/compare_default_vs_calibrated.py \
  --config examples/level3_calibration.json \
  --status-only \
  --pretty

Show the loaded calibration record in the output:

python scripts/compare_default_vs_calibrated.py \
  --config examples/level3_calibration.json \
  --show-calibration \
  --pretty
Level 3 output interpretation

The main comparison quantity is again:

calibrated.avalanche_pulse.peak_voltage_v

and you compare it against:

default.avalanche_pulse.peak_voltage_v

The comparison report also includes gain ratios and voltage deltas so you can immediately see how much the calibration shifted the prediction.

Built-in gases

This package includes at least:

air_dry_1atm

ar_co2_70_30_1atm

These are intended as convenient built-ins, not definitive authoritative detector databases.

Typical workflow

A practical workflow is:

Use Level 1 to get a fast deterministic estimate.

Use Level 2 to study event-to-event spread and threshold crossing.

Use Level 3 to compare the baseline surrogate against tuned calibration values.

Replace placeholder calibration values with Garfield++-derived products later.

How future Garfield++ calibration fits in

The intended long-term workflow is:

Run Garfield++ studies for specific gas, geometry, voltage, and transport conditions.

Derive tuned effective parameters such as:

gain rescaling

gain onset shift

drift velocity correction

attachment correction

collection-fraction correction

pulse-width/electronics correction

Store those derived values in calibration JSON files compatible with:

CalibrationRecord

GasCalibrationOverride

GainCalibrationOverride

DriftCalibrationOverride

PulseCalibrationOverride

Re-run this package using the calibrated comparison path.

In other words, this repository is structured so the current surrogate layer can later become a front-end consumer of Garfield++-derived calibration products instead of being thrown away.

Suggested interpretation discipline

A good way to use this package is:

treat Level 1 as a plausibility estimator

treat Level 2 as a visibility/distribution estimator

treat Level 3 as the bridge toward calibrated detector-specific prediction

For serious detector conclusions, especially in air or near threshold, you should regard this package as one layer in a larger workflow rather than the final truth model.

Example files

examples/level1_example.json
Deterministic Level 1 configuration.

examples/level2_event_scan.json
Repeated-event Level 2 stochastic scan.

examples/level3_calibration.json
Default-vs-calibrated Level 3 comparison example.

calibration/default_surrogate_calibration.json
Example calibration record showing how future tuned values can be stored.

Status

This repository is designed to be:

understandable

deterministic

easy to run locally

straightforward to extend

ready for later calibration replacement

It is deliberately not a heavyweight simulation framework.