"""Code World Model (CWM) pipeline for MicroRemed.

Stage 1 (implemented): collect structured (state, action) -> next_state
transitions from real inject-and-remediate episodes into a JSONL dataset.

Stage 2 (spec only, see world_model_spec.py): synthesize a code world model
from those transitions via LLM code generation + test-driven refinement, then
plan with it.
"""

from cwm.schema import State, Pod, Action, Transition, TransitionWriter

__all__ = ["State", "Pod", "Action", "Transition", "TransitionWriter"]
