from benchmark.law.shared.guards import NemoGuardrailsGate
from benchmark.law.shared.http_app import main

if __name__ == "__main__":
    main("LNL", "langgraph", NemoGuardrailsGate)
