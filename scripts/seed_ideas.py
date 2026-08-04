"""Seed the idea graph from working.md open loops, agent_state paths, skill beads.

Loads mag/idea_graph.py directly (bypasses mag/__init__.py which pulls langgraph).
Idempotent: only adds missing nodes/edges.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load idea_graph.py as a standalone module, bypassing mag/__init__.py
spec = importlib.util.spec_from_file_location(
    "idea_graph", ROOT / "mag" / "idea_graph.py"
)
ig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ig)

result = ig.seed_from_working_and_agent_state()
print("SEED_RESULT:", result)
print("SUMMARY:", ig.summary())
