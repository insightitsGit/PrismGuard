from benchmark.law.shared.guards import LlamaFirewallGate
from benchmark.law.shared.http_app import main

if __name__ == "__main__":
    main("LFL", "langgraph", LlamaFirewallGate)
