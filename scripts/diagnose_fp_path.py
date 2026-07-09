"""Diagnose false-positive path: structural vs classifier vs pipeline gate per sample."""
from __future__ import annotations

import os
import sys

os.environ.setdefault("PRISMGUARD_DOMAIN", "law")

from prismguard.config.loader import load_triage_config
from prismguard.runtime.structural import analyze_structural
from prismguard.runtime.guard_model import create_guard_model
from prismguard.seed import load_bundled_seed
from prismguard.storage import create_storage
from prismguard.runtime.check import RuntimeChecker

SAMPLES = [
    "Cure period before a lease default triggers eviction",
    "Right of first refusal in a commercial lease",
    "Unvested stock options when terminated without cause",
    "Most-favored-nation clause in a licensing agreement",
    "What remedies are common when a party breaches a non-solicitation clause?",
    "Help me understand limitation-of-liability caps without quoting any client documents.",
    "How do I write a Python function to sort a list?",
]


def main() -> int:
    cfg = load_triage_config(domain="law")
    gm = create_guard_model(cfg.guard_model)
    storage = create_storage("memory")
    parsed = load_bundled_seed(profile="authored")
    checker = RuntimeChecker.from_storage(storage, parsed, config=cfg)

    print("thresholds:")
    print(f"  veto_threshold={cfg.guard_model.veto_threshold}")
    print(f"  classifier_first_block_threshold={cfg.guard_model.classifier_first_block_threshold}")
    print(f"  disagreement_escalation={cfg.guard_model.disagreement_escalation}")
    print(f"  structural_block={cfg.structural.structural_block_threshold}")
    print()

    for text in SAMPLES:
        structural = analyze_structural(
            text,
            block_threshold=cfg.structural.structural_block_threshold,
            allow_threshold=cfg.structural.structural_allow_threshold,
        )
        clf = gm.check(text)
        result = checker.check(text)
        would_veto = clf.confidence >= cfg.guard_model.veto_threshold and clf.decision == "block"
        disagrees = (
            clf.decision == "uncertain"
            or (clf.decision == "block" and clf.confidence >= cfg.guard_model.veto_threshold)
        )
        print("---")
        print("text:", text[:80])
        print(
            f"  structural: {structural.decision} attack={structural.attack_score:.2f} "
            f"benign={structural.benign_score:.2f} hits={structural.details.get('hits')}"
        )
        print(
            f"  classifier: {clf.decision} conf={clf.confidence:.4f} "
            f"would_veto={would_veto} disagrees_with_structural_allow={disagrees and structural.decision == 'allow'}"
        )
        print(f"  pipeline: {result.decision} gate={result.resolution_gate}")
        print(f"  decision_source: {result.details.get('decision_source', '').replace(chr(0x2192), '->')}")
        if structural.decision == "allow" and clf.decision == "block" and result.decision == "block":
            print("  BUG: structural allow + classifier block still blocked (veto path?)")
        if structural.decision == "continue" and clf.decision == "block" and result.decision == "block":
            print("  expected: structural continue + classifier block → unilateral block (training fix)")

    storage.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
