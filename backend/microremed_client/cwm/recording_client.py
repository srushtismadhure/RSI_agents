"""A ChaosClient wrapper that records transitions around real cluster actions.

This subclasses the existing remote.client.ChaosClient and overrides the two
methods that actually change the world:

    inject_failure(...)  -> the fault / "chance" event   (Action kind="inject")
    execute_playbook(...) -> the remediation action       (Action kind="remediate")

Around each, it snapshots the cluster before and after and emits a Transition
to a sink. The existing remediation code (SoloGen / ThinkRemed) is given an
instance of this class instead of a plain ChaosClient, so NO existing file
needs to change to capture per-action transitions.

Read-only calls (check_status, execute_probe) are left untouched -- they are
observations, not transitions.
"""

from __future__ import annotations

import time
from typing import Optional

from remote.client import ChaosClient

from cwm.cluster_state import SnapshotFn, get_snapshot_fn
from cwm.schema import Action, State, Transition, TransitionWriter


class RecordingChaosClient(ChaosClient):
    def __init__(
        self,
        base_url: str,
        writer: TransitionWriter,
        snapshot_fn: Optional[SnapshotFn] = None,
        settle_seconds: float = 5.0,
    ):
        super().__init__(base_url)
        self._writer = writer
        self._snapshot = snapshot_fn or get_snapshot_fn("kubectl")
        self._settle = settle_seconds

        # Per-episode context, set by the collector via begin_episode().
        self._episode_id: str = "unset"
        self._env: str = "unknown"
        self._namespace: str = "default"
        self._fault_type: str = "unknown"
        self._target_pod: str = "unknown"
        self._step: int = 0

    # ------------------------------------------------------------------ #
    # Episode bookkeeping (called by the collector)
    # ------------------------------------------------------------------ #
    def begin_episode(
        self, episode_id: str, env: str, namespace: str, fault_type: str, target_pod: str
    ) -> None:
        self._episode_id = episode_id
        self._env = env
        self._namespace = namespace
        self._fault_type = fault_type
        self._target_pod = target_pod
        self._step = 0

    def _snapshot_state(self) -> State:
        return self._snapshot(self._namespace)

    def _record(
        self,
        state: State,
        action: Action,
        next_state: State,
        reward: float = 0.0,
        done: bool = False,
        info: Optional[dict] = None,
    ) -> None:
        self._writer.write(
            Transition(
                episode_id=self._episode_id,
                step=self._step,
                env=self._env,
                namespace=self._namespace,
                fault_type=self._fault_type,
                target_pod=self._target_pod,
                state=state,
                action=action,
                next_state=next_state,
                reward=reward,
                done=done,
                info=info or {},
            )
        )
        self._step += 1

    # ------------------------------------------------------------------ #
    # Overridden world-changing actions
    # ------------------------------------------------------------------ #
    def inject_failure(self, failure_type: str, target_pod: str, target_namespace: str) -> dict:
        state = self._snapshot_state()
        result = super().inject_failure(failure_type, target_pod, target_namespace)
        time.sleep(self._settle)
        next_state = self._snapshot_state()
        self._record(
            state,
            Action(kind="inject", method=failure_type, target=target_pod),
            next_state,
            reward=0.0,
            done=False,
            info={"server_result": result},
        )
        return result

    def execute_playbook(self, playbook: str) -> dict:
        state = self._snapshot_state()
        result = super().execute_playbook(playbook)
        time.sleep(self._settle)
        next_state = self._snapshot_state()

        # Reward/done are finalized by the collector after a check_status, but
        # we record a per-action reward proxy: all target pods healthy again.
        target_ok = all(
            p.ready for p in next_state.pods if p.app == self._target_pod
        ) if any(p.app == self._target_pod for p in next_state.pods) else False

        self._record(
            state,
            Action(kind="remediate", method="playbook", target=self._target_pod, payload=playbook),
            next_state,
            reward=1.0 if target_ok else 0.0,
            done=bool(target_ok),
            info={"server_result": result, "target_ready": target_ok},
        )
        return result
