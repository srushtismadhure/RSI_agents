"""Capture a structured cluster snapshot -> cwm.schema.State.

Infra-dependent: this reads the *real* cluster. Two backends are supported via
a pluggable snapshot function:

  * "kubectl" (default) -- shell out to `kubectl get pods -n <ns> -o json`.
    Requires kubectl on PATH with a kubeconfig that can reach the cluster the
    MicroRemed-Server is managing.

  * a custom callable -- pass your own `snapshot_fn(namespace) -> State` if the
    cluster is only reachable from the server side (e.g. add a `/cluster_state`
    endpoint to MicroRemed-Server and call it through ChaosClient). The server
    does not expose such an endpoint today; this hook is where it would plug in.
"""

from __future__ import annotations

import json
import subprocess
from typing import Callable

from cwm.schema import Pod, State


class ClusterStateError(RuntimeError):
    pass


def _pod_from_kubectl_item(item: dict) -> Pod:
    meta = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})

    labels = meta.get("labels", {}) or {}
    container_statuses = status.get("containerStatuses", []) or []

    ready = bool(container_statuses) and all(
        cs.get("ready", False) for cs in container_statuses
    )
    restarts = sum(int(cs.get("restartCount", 0)) for cs in container_statuses)

    return Pod(
        name=meta.get("name", "<unknown>"),
        app=labels.get("app"),
        phase=status.get("phase", "Unknown"),
        ready=ready,
        restarts=restarts,
        node=spec.get("nodeName"),
    )


def kubectl_snapshot(namespace: str, kubectl_bin: str = "kubectl") -> State:
    """Snapshot all pods in `namespace` via kubectl."""
    cmd = [kubectl_bin, "get", "pods", "-n", namespace, "-o", "json"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
    except FileNotFoundError as e:
        raise ClusterStateError(
            f"`{kubectl_bin}` not found on PATH. Install kubectl or pass a custom "
            f"snapshot_fn that reaches the cluster another way."
        ) from e
    except subprocess.TimeoutExpired as e:
        raise ClusterStateError(f"kubectl timed out: {' '.join(cmd)}") from e

    if proc.returncode != 0:
        raise ClusterStateError(
            f"kubectl failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
        )

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ClusterStateError(f"could not parse kubectl JSON output: {e}") from e

    pods = [_pod_from_kubectl_item(item) for item in payload.get("items", [])]
    return State(namespace=namespace, pods=pods)


# Type of a snapshot backend: namespace -> State
SnapshotFn = Callable[[str], State]


def get_snapshot_fn(backend: str = "kubectl", **kwargs) -> SnapshotFn:
    """Resolve a snapshot backend by name. Extend here for a server-side backend."""
    if backend == "kubectl":
        kubectl_bin = kwargs.get("kubectl_bin", "kubectl")
        return lambda ns: kubectl_snapshot(ns, kubectl_bin=kubectl_bin)
    raise ValueError(f"unknown snapshot backend: {backend!r}")
