"""Stage 2 SPEC (not yet implemented) -- the code world model interface.

This file defines the target API that a *synthesized* world model must satisfy,
plus the outline of the synthesis loop. It mirrors the OpenSpiel-style API from
the "Code World Models for General Game Playing" talk, specialized to
microservice remediation:

    apply_action(state, action) -> next_state          (transition model  f)
    observation(state)          -> observation         (observation model)
    is_terminal(state)          -> bool                (episode done?)
    legal_actions(state)        -> list[Action]        (valid remediations)
    resample_history(obs_history, action_history) -> full action list
                                                       (imputation, for the
                                                        partially observed case)

Stage 1 produces the transitions.jsonl that this stage consumes. Implementing
the body below is the "CWM later" work; the collector is what runs now.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from cwm.schema import Action, State, Transition


class CodeWorldModel(ABC):
    """Interface a synthesized world model must implement to be planner-ready."""

    @abstractmethod
    def apply_action(self, state: State, action: Action) -> State:
        """Transition model f: deterministic given resolved chance events."""

    @abstractmethod
    def observation(self, state: State) -> dict[str, Any]:
        """Player-visible projection (closed-deck view)."""

    @abstractmethod
    def is_terminal(self, state: State) -> bool:
        """True once the fault is remediated (or the episode is otherwise done)."""

    @abstractmethod
    def legal_actions(self, state: State) -> list[Action]:
        """Candidate remediation actions available from `state`."""

    def resample_history(
        self, obs_history: list[dict[str, Any]], action_history: list[Action]
    ) -> list[Action]:
        """Imputation model: fill in unobserved actions consistent with the
        observation history. Default: identity (fully observed). Override for
        partially observable settings (IS-MCTS planning)."""
        return action_history


# --------------------------------------------------------------------------- #
# Synthesis loop outline (to implement)
# --------------------------------------------------------------------------- #
def build_unit_tests(transitions: list[Transition]) -> list[dict[str, Any]]:
    """Turn recorded transitions into pass/fail assertions for a candidate model.

    For each transition we can assert (per the talk's open-deck evaluation):
      * apply_action(state, action) == next_state
      * observation(state)         == recorded observation
    The candidate model's score is (# assertions passed / # total).

    TODO(stage2): emit concrete, runnable assertions.
    """
    raise NotImplementedError("Stage 2: build_unit_tests")


def synthesize(
    nl_description: str,
    transitions: list[Transition],
    *,
    max_iterations: int = 20,
) -> CodeWorldModel:
    """Evolve a CodeWorldModel from a natural-language env description + data.

    Outline (matches the talk):
      1. Prompt the LLM to generate code implementing the CodeWorldModel API.
      2. Score it against build_unit_tests(transitions); collect failing tests.
      3. Feed score + failing tests back to the LLM to refine.
      4. Keep candidates in a tree; pick the next node to expand via Thompson
         sampling over (score, visit_count).
      5. Stop at max_iterations or once all tests pass; return the best model.

    TODO(stage2): implement the code-generation + tree-search refinement loop.
    """
    raise NotImplementedError("Stage 2: synthesize")
