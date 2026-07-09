"""Holdout-only pipeline attribution: CPL vs CGL by resolution gate."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def holdout_attacks(rows: list[dict]) -> list[dict]:
    return [
        r
        for r in rows
        if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack"
    ]


def main() -> None:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("benchmark/law/results/verified")
    stacks = {s: holdout_attacks(load(base / f"{s}.jsonl")) for s in ("cpl", "cgl")}

    n = len(stacks["cpl"])
    print(f"Holdout attacks: n={n}\n")

    for sid in ("cpl", "cgl"):
        rows = stacks[sid]
        blocks = sum(1 for r in rows if r["decision"] == "block")
        print(f"{sid.upper()}: {blocks}/{len(rows)} blocked ({blocks/len(rows):.1%})")
        by_gate: dict[str, int] = defaultdict(int)
        for r in rows:
            if r["decision"] == "block":
                by_gate[r["resolution_gate"]] += 1
        for gate, count in sorted(by_gate.items(), key=lambda x: -x[1]):
            print(f"  {gate}: {count}")
        print()

    cpl_by_text = {r["input_text"]: r for r in stacks["cpl"]}
    cgl_by_text = {r["input_text"]: r for r in stacks["cgl"]}

    print("CPL blocks / CGL allows (PrismGuard-only wins):")
    wins = 0
    for text, cpl in cpl_by_text.items():
        cgl = cgl_by_text[text]
        if cpl["decision"] == "block" and cgl["decision"] == "allow":
            wins += 1
            print(f"  [{cpl['resolution_gate']}] {text[:100]}")
    print(f"  total: {wins}\n")

    print("CGL blocks / CPL allows (LLM Guard-only wins):")
    losses = 0
    for text, cgl in cgl_by_text.items():
        cpl = cpl_by_text[text]
        if cgl["decision"] == "block" and cpl["decision"] == "allow":
            losses += 1
            print(f"  [{cgl['resolution_gate']}] {text[:100]}")
    print(f"  total: {losses}\n")

    print("Both block:")
    both = sum(
        1
        for t in cpl_by_text
        if cpl_by_text[t]["decision"] == "block" and cgl_by_text[t]["decision"] == "block"
    )
    print(f"  {both}/{n}\n")

    print("Both allow:")
    neither = sum(
        1
        for t in cpl_by_text
        if cpl_by_text[t]["decision"] == "allow" and cgl_by_text[t]["decision"] == "allow"
    )
    print(f"  {neither}/{n}")


if __name__ == "__main__":
    main()
