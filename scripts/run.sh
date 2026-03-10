rm -rf sweep_outputs
mkdir -p sweep_outputs/deterministic sweep_outputs/stochastic

for cfg in sweep_configs/*.json; do
  base=$(basename "$cfg" .json)

  python scripts/run_estimator.py \
    --config "$cfg" \
    --output "sweep_outputs/deterministic/${base}.json" \
    --pretty

  python scripts/run_event_scan.py \
    --config "$cfg" \
    --output "sweep_outputs/stochastic/${base}.json" \
    --pretty
done

python scripts/plot_sweeps.py