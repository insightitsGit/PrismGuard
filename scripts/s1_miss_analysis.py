#!/usr/bin/env python3
"""Analyze attack misses vs an expected-block prompt set (stack S1 quality track).

Input formats:
  - .txt one prompt per line (all expected block)
  - .jsonl {"text": "...", "expected": "block"|"allow"}
  - .yaml list of {text, expected?} (expected defaults to block)

Usage:
  python scripts/s1_miss_analysis.py --profile light --attacks path/to/s1.txt
  python scripts/s1_miss_analysis.py --profile heavy --attacks benchmark/law/data/legal_attacks_holdout.yaml

Prints FN (expected block, got allow/gray), FP (expected allow, got block), and gate histogram.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _load_cases(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml

        data = yaml.safe_load(text)
        cases: list[dict] = []
        if isinstance(data, dict):
            # holdout shape: attacks: [{prompt/text/...}]
            items = data.get("attacks") or data.get("entries") or data.get("prompts") or []
            if not items and "text" in data:
                items = [data]
        elif isinstance(data, list):
            items = data
        else:
            items = []
        for item in items:
            if isinstance(item, str):
                cases.append({"text": item, "expected": "block"})
            elif isinstance(item, dict):
                prompt = item.get("text") or item.get("prompt") or item.get("attack") or ""
                if not prompt:
                    continue
                exp = str(item.get("expected") or item.get("label") or "block").lower()
                if exp in ("attack", "inject", "injection", "1", "true"):
                    exp = "block"
                if exp in ("benign", "normal", "0", "false"):
                    exp = "allow"
                cases.append({"text": str(prompt), "expected": exp})
        return cases

    if path.suffix.lower() == ".jsonl":
        cases = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            cases.append(
                {
                    "text": str(obj.get("text") or obj.get("prompt")),
                    "expected": str(obj.get("expected") or "block").lower(),
                }
            )
        return cases

    # plain text — all expected block
    return [{"text": ln.strip(), "expected": "block"} for ln in text.splitlines() if ln.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="S1 / attack miss analysis")
    parser.add_argument("--profile", default="light", help="light|heavy|law_pilot|…")
    parser.add_argument("--attacks", required=True, help="txt / jsonl / yaml prompt file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from prismguard.runtime.factory import create_checker_for_app

    path = Path(args.attacks)
    cases = _load_cases(path)
    if not cases:
        print(f"No cases loaded from {path}", flush=True)
        return 2

    if args.profile == "law_pilot":
        checker = create_checker_for_app("law_pilot", use_onnx=True)
    else:
        checker = create_checker_for_app(args.profile)  # type: ignore[arg-type]

    mode = getattr(getattr(checker, "_config", None), "guard_model", None)
    classifier_mode = getattr(mode, "classifier_mode", "?") if mode else "?"

    fn: list[dict] = []
    fp: list[dict] = []
    tp = tn = 0
    gates: Counter[str] = Counter()

    for case in cases:
        result = checker.check(case["text"])
        gates[result.resolution_gate or "unknown"] += 1
        decision = result.decision
        expected = case["expected"]
        row = {
            "text": case["text"][:120],
            "expected": expected,
            "decision": decision,
            "resolution_gate": result.resolution_gate,
        }
        if expected == "block":
            if decision == "block":
                tp += 1
            else:
                fn.append(row)
        else:
            if decision == "block":
                fp.append(row)
            else:
                tn += 1

    precision = tp / (tp + len(fp)) if (tp + len(fp)) else 0.0
    recall = tp / (tp + len(fn)) if (tp + len(fn)) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    report = {
        "profile": args.profile,
        "classifier_mode": classifier_mode,
        "n": len(cases),
        "tp": tp,
        "tn": tn,
        "fp": len(fp),
        "fn": len(fn),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "gates": dict(gates),
        "false_negatives": fn,
        "false_positives": fp,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"profile={report['profile']} classifier_mode={report['classifier_mode']} "
            f"n={report['n']} F1={report['f1']} P={report['precision']} R={report['recall']}"
        )
        print(f"tp={tp} tn={tn} fp={len(fp)} fn={len(fn)}")
        print("gates:", dict(gates))
        if fn:
            print("\nFalse negatives (expected block):")
            for row in fn[:20]:
                print(f"  [{row['resolution_gate']}] {row['decision']}: {row['text']}")
        if fp:
            print("\nFalse positives (expected allow):")
            for row in fp[:20]:
                print(f"  [{row['resolution_gate']}] {row['decision']}: {row['text']}")
        print(
            "\nNext: add Tier-1/structural coverage for FN patterns, or retrain ONNX on "
            "exported feedback (PRISMGUARD_FEEDBACK_PERSIST=1 → prismguard feedback export)."
        )
    return 0 if not fn else 1


if __name__ == "__main__":
    raise SystemExit(main())
