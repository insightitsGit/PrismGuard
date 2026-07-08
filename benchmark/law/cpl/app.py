from pathlib import Path

from benchmark.law.shared.guards import PrismGuardGate
from benchmark.law.shared.http_app import create_app, serve_app

app = create_app(stack_id="CPL", framework="chorusgraph", guard_factory=PrismGuardGate)

if __name__ == "__main__":
    serve_app(import_target=f"{Path(__file__).stem}:app")
