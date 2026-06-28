"""Trajectory schema for the MicroRemed Code World Model pipeline.

A trajectory is a sequence of transitions. Each transition mirrors the
(state, action) -> (next_state, observation, reward, done) shape that a code
world model is trained to reproduce:

    apply_action(state, action) -> next_state
    observation(state)          -> observation   (player-visible subset)

For microservice remediation the "state" is a structured snapshot of the
cluster (see cluster_state.py), the "action" is either the injected fault
(a chance/env event) or a remediation playbook proposed by the agent.

Everything serializes to plain JSON so transitions can be streamed to a
``.jsonl`` file (one transition per line) and read back without any custom
deserializer.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
@dataclass
class Pod:
    """A single pod as seen in a cluster snapshot."""

    name: str
    app: Optional[str]        # value of the `app` label, used as the service id
    phase: str                # Pending / Running / Succeeded / Failed / Unknown
    ready: bool               # all containers ready
    restarts: int             # summed container restart count
    node: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Pod":
        return cls(**d)


@dataclass
class State:
    """Structured snapshot of the cluster at one instant (the world state)."""

    namespace: str
    pods: list[Pod] = field(default_factory=list)
    captured_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "pods": [p.to_dict() for p in self.pods],
            "captured_at": self.captured_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "State":
        return cls(
            namespace=d["namespace"],
            pods=[Pod.from_dict(p) for p in d.get("pods", [])],
            captured_at=d.get("captured_at", 0.0),
        )

    def observation(self, hidden_fault: bool = True) -> dict[str, Any]:
        """Player-visible projection of the state (partial observability).

        Mirrors the talk's open-deck / closed-deck distinction: the injected
        fault is the "hidden" variable. The observation exposes pod health that
        an SRE/agent could read (phase, readiness, restarts) but omits the
        ground-truth fault label, which the world model must *infer*.
        """
        return {
            "namespace": self.namespace,
            "pods": [
                {"app": p.app, "phase": p.phase, "ready": p.ready, "restarts": p.restarts}
                for p in self.pods
            ],
        }


# --------------------------------------------------------------------------- #
# Action
# --------------------------------------------------------------------------- #
@dataclass
class Action:
    """An action applied to the world.

    kind:
        "inject"    chance/env event: a fault is injected (target_pod, fault)
        "remediate" agent action: an Ansible playbook is executed
        "stop"      the chaos experiment is stopped
        "restore"   the environment is restored from the original manifest
    """

    kind: str
    method: Optional[str] = None     # remediation method (SoloGen / ThinkRemed) or fault type
    target: Optional[str] = None     # target pod / service
    payload: Optional[str] = None    # playbook YAML or chaos spec, when applicable

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Action":
        return cls(**d)


# --------------------------------------------------------------------------- #
# Transition
# --------------------------------------------------------------------------- #
@dataclass
class Transition:
    episode_id: str
    step: int
    env: str
    namespace: str
    fault_type: str
    target_pod: str
    state: State
    action: Action
    next_state: State
    reward: float = 0.0
    done: bool = False
    info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "step": self.step,
            "env": self.env,
            "namespace": self.namespace,
            "fault_type": self.fault_type,
            "target_pod": self.target_pod,
            "state": self.state.to_dict(),
            "action": self.action.to_dict(),
            "next_state": self.next_state.to_dict(),
            "observation": self.state.observation(),
            "next_observation": self.next_state.observation(),
            "reward": self.reward,
            "done": self.done,
            "info": self.info,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Transition":
        return cls(
            episode_id=d["episode_id"],
            step=d["step"],
            env=d["env"],
            namespace=d["namespace"],
            fault_type=d["fault_type"],
            target_pod=d["target_pod"],
            state=State.from_dict(d["state"]),
            action=Action.from_dict(d["action"]),
            next_state=State.from_dict(d["next_state"]),
            reward=d.get("reward", 0.0),
            done=d.get("done", False),
            info=d.get("info", {}),
        )


# --------------------------------------------------------------------------- #
# Writer
# --------------------------------------------------------------------------- #
class TransitionWriter:
    """Append-only JSONL sink. One JSON object per line, flushed per write so a
    crashed/interrupted collection run still yields a valid partial dataset."""

    def __init__(self, path: str):
        import os

        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")
        self.count = 0

    def write(self, transition: Transition) -> None:
        self._fh.write(json.dumps(transition.to_dict(), ensure_ascii=False) + "\n")
        self._fh.flush()
        self.count += 1

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()

    def __enter__(self) -> "TransitionWriter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def read_transitions(path: str) -> list[Transition]:
    """Load a ``.jsonl`` transition file back into Transition objects."""
    out: list[Transition] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(Transition.from_dict(json.loads(line)))
    return out
