from benchmark.law.shared.guards import LLMGuardGate
from benchmark.law.shared.http_app import main

if __name__ == "__main__":
    main("CGL", "chorusgraph", LLMGuardGate)
