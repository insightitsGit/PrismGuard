"""In-process metrics for HTTP guard service."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class GuardMetrics:
    check_total: int = 0
    check_allow: int = 0
    check_block: int = 0
    scan_output_total: int = 0
    errors: int = 0
    gate_counts: Dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_check(self, *, decision: str, gate: str) -> None:
        with self._lock:
            self.check_total += 1
            if decision == "allow":
                self.check_allow += 1
            elif decision == "block":
                self.check_block += 1
            self.gate_counts[gate] = self.gate_counts.get(gate, 0) + 1

    def record_scan(self) -> None:
        with self._lock:
            self.scan_output_total += 1

    def record_error(self) -> None:
        with self._lock:
            self.errors += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "check_total": self.check_total,
                "check_allow": self.check_allow,
                "check_block": self.check_block,
                "scan_output_total": self.scan_output_total,
                "errors": self.errors,
                "resolution_gate_counts": dict(self.gate_counts),
            }

    def prometheus_text(self) -> str:
        snap = self.snapshot()
        lines = [
            "# HELP prismguard_check_total Input checks served.",
            "# TYPE prismguard_check_total counter",
            f"prismguard_check_total {snap['check_total']}",
            "# HELP prismguard_check_allow_total Allowed inputs.",
            "# TYPE prismguard_check_allow_total counter",
            f"prismguard_check_allow_total {snap['check_allow']}",
            "# HELP prismguard_check_block_total Blocked inputs.",
            "# TYPE prismguard_check_block_total counter",
            f"prismguard_check_block_total {snap['check_block']}",
            "# HELP prismguard_scan_output_total Output scans served.",
            "# TYPE prismguard_scan_output_total counter",
            f"prismguard_scan_output_total {snap['scan_output_total']}",
            "# HELP prismguard_errors_total Handler errors.",
            "# TYPE prismguard_errors_total counter",
            f"prismguard_errors_total {snap['errors']}",
        ]
        for gate, count in sorted(snap["resolution_gate_counts"].items()):
            safe = gate.replace('"', '\\"')
            lines.append(f'prismguard_resolution_gate_total{{gate="{safe}"}} {count}')
        return "\n".join(lines) + "\n"


_GLOBAL = GuardMetrics()


def get_metrics() -> GuardMetrics:
    return _GLOBAL
