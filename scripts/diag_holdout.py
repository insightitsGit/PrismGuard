"""Diagnose holdout attack resolution paths."""
from __future__ import annotations

import yaml
from pathlib import Path

from benchmark.law.shared.guards import PrismGuardGate
from prismguard.config.loader import load_triage_config
from prismguard.runtime.normalize import normalize_prompt
from prismguard.runtime.structural import analyze_structural, has_suspicious_segments
from prismguard.taxonomy.mapping import build_mapping_from_parsed_seed
from prismguard.seed import load_bundled_seed

holdout = yaml.safe_load(Path("benchmark/law/data/legal_attacks_holdout.yaml").read_text())
cfg = load_triage_config()
engine = build_mapping_from_parsed_seed(load_bundled_seed(profile="authored"))

print("=" * 72)
print("HOLDOUT ATTACK ROOT-CAUSE ANALYSIS")
print("=" * 72)

attacks = [e for e in holdout["entries"] if e["category_slug"] != "benign_adjacent"]
gate = PrismGuardGate()

for e in attacks:
    text = e["text"]
    norm = normalize_prompt(text)
    tier1 = engine.match_tier1(norm)
    struct = analyze_structural(
        norm,
        block_threshold=cfg.structural.structural_block_threshold,
        allow_threshold=cfg.structural.structural_allow_threshold,
    )
    susp = has_suspicious_segments(norm, floor=cfg.embedding.suspicious_ngram_floor)
    outcome = gate.check(text)

    print(f"\n[{e['category_slug']}]")
    print(f"  TEXT: {text[:90]}...")
    print(f"  tier1: {tier1.rule_id if tier1 else None}")
    print(f"  structural: decision={struct.decision} attack={struct.attack_score:.2f} benign={struct.benign_score:.2f} hits={struct.details.get('hits')}")
    print(f"  suspicious_segments: {susp}")
    if not susp and struct.decision == "continue":
        print("  >>> BYPASS: no_suspicious_segments -> ALLOW without embed/classifier")
    print(f"  FINAL: {outcome.decision} @ {outcome.resolution_gate} (clf_calls={outcome.guard_classifier_calls}, {outcome.latency_ms:.2f}ms)")
