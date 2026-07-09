# Advertisement benchmark results

Separate suites for honest external messaging:

- **attack-holdout** — cold attack detection (cite this for holdout block rate)
- **normal-holdout** — cold false-positive eval (cite this for benign pass rate)
- **normal-dev** — development/tuned benign set (do not cite as generalization)
- **law-full** — combined harness matching production benchmark shape
- **healthcare-domain** / **finance-domain** — domain pack overlays

See `ADVERTISEMENT_SUMMARY.md` for CPL headline table and `summary.json` for machine-readable output.
Each subdirectory has `comparison.json`, `COMPARISON_REPORT.md`, and per-stack `*.jsonl` traces.
