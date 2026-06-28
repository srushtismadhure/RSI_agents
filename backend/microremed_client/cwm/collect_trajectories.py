"""Stage 1 entrypoint: collect transition trajectories from real episodes.

This drives the same inject -> remediate -> verify -> restore loop as
inject_and_remediate.py, but swaps in a RecordingChaosClient so every
world-changing call emits a (state, action, next_state) Transition to a
JSONL dataset that Stage 2 (the code world model) consumes.

It deliberately does NOT modify inject_and_remediate.py; it is a parallel
collector that reuses the same building blocks (ChaosClient, envs.env,
methods.remediate).

Prerequisites (infra-dependent collection):
  * MicroRemed-Server reachable at --server-url
  * a Kubernetes cluster with the target env deployed
  * kubectl on PATH with access to that cluster (the snapshot backend)
  * LLM_API_KEY set (the remediation agent calls an LLM)

Example:
  export LLM_API_KEY=...
  python3 -m cwm.collect_trajectories \
      --env train-ticket --namespace train-ticket \
      --server-url http://127.0.0.1:5000 \
      --model qwen-plus --remediate-method SoloGen \
      --experiment-path experiments/easy.txt \
      --out data/trajectories/train-ticket.jsonl
"""

from __future__ import annotations

import argparse
import os
import time
import uuid

from envs.env import get_random_failure, get_random_service

from cwm.cluster_state import get_snapshot_fn
from cwm.recording_client import RecordingChaosClient
from cwm.schema import TransitionWriter


def _load_failure_list(path: str | None):
    if path and os.path.exists(path):
        with open(path, "r") as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
    return None


def collect(args) -> None:
    # remediate is imported lazily: methods.* pulls in models.llm which requires
    # LLM_API_KEY at import time, so we only touch it once we are actually
    # collecting (and after the user has set up the infra).
    from methods.remediate import remediate

    snapshot_fn = get_snapshot_fn("kubectl", kubectl_bin=args.kubectl_bin)
    target_env = args.env or "default-env"

    failure_list = _load_failure_list(args.experiment_path)
    total = len(failure_list) if failure_list else args.experiments

    print(f"[collect] env={target_env} ns={args.namespace} total_episodes={total}")
    print(f"[collect] writing transitions -> {args.out}")

    with TransitionWriter(args.out) as writer:
        client = RecordingChaosClient(
            base_url=args.server_url,
            writer=writer,
            snapshot_fn=snapshot_fn,
            settle_seconds=args.settle_seconds,
        )

        episode_no = 1
        injected_episodes = 0
        while episode_no <= total:
            fault_type = (
                failure_list[episode_no - 1] if failure_list else get_random_failure(target_env)
            )
            target_pod = get_random_service(target_env, fault_type)
            episode_id = f"{target_pod}_{fault_type}_{uuid.uuid4().hex[:8]}"
            client.begin_episode(episode_id, target_env, args.namespace, fault_type, target_pod)

            print(f"\n=== episode {episode_no}/{total} :: {episode_id} ===")

            # Ensure the target service is healthy before we inject.
            if not client.check_status(args.namespace, f"app={target_pod}", "pod-fail"):
                print("[collect] target unhealthy, redeploying env and retrying")
                client.deploy_env(target_env)
                continue

            # --- inject (recorded as a chance/env transition) ---
            injection_status = client.inject_failure(fault_type, target_pod, args.namespace)
            if not injection_status:
                print("[collect] injection failed, skipping episode")
                episode_no += 1
                continue

            # Wait for the fault to take hold.
            start = time.time()
            injected = False
            while time.time() - start <= args.injection_timeout:
                if not client.check_status(args.namespace, f"app={target_pod}", fault_type, 5):
                    injected = True
                    break
                time.sleep(args.wait_interval)
            if not injected:
                print("[collect] injection did not take effect, stopping & skipping")
                client.stop_injection(fault_type, args.namespace)
                episode_no += 1
                continue

            injected_episodes += 1

            # --- remediate (each execute_playbook is recorded as an action) ---
            remediate(
                client=client,
                runtime_envs="This microservice system runs on k3s.",
                namespace=args.namespace,
                root_cause=target_pod,
                failure_category=fault_type,
                remediate_method=args.remediate_method,
            )

            success = bool(client.check_status(args.namespace, f"app={target_pod}", fault_type))
            print(f"[collect] episode result: success={success}")

            # --- cleanup ---
            client.stop_injection(fault_type, args.namespace)
            client.restore_by_original_manifest(args.namespace, target_pod, args.manifest_path)
            time.sleep(args.settle_seconds)

            episode_no += 1

        print(
            f"\n[collect] done. episodes_with_injection={injected_episodes} "
            f"transitions_written={writer.count} file={args.out}"
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Collect CWM transition trajectories.")
    # Mirrors inject_and_remediate.py's surface so existing run configs port over.
    p.add_argument("--experiments", type=int, default=20)
    p.add_argument("--namespace", type=str, default="default")
    p.add_argument("--wait-interval", type=int, default=10)
    p.add_argument("--injection-timeout", type=int, default=60)
    p.add_argument("--env", type=str, default="train-ticket")
    p.add_argument("--manifest-path", type=str, default="envs/source-config/train-ticket-config.yaml")
    p.add_argument("--remediate-method", type=str, default="SoloGen", help="SoloGen / ThinkRemed")
    p.add_argument("--experiment-path", type=str, default=None)
    p.add_argument("--model", type=str, default="")
    p.add_argument("--server-url", type=str, required=True)
    # CWM-specific
    p.add_argument("--out", type=str, default="data/trajectories/transitions.jsonl",
                   help="Output JSONL path for collected transitions.")
    p.add_argument("--kubectl-bin", type=str, default="kubectl",
                   help="kubectl binary used for cluster snapshots.")
    p.add_argument("--settle-seconds", type=float, default=5.0,
                   help="Seconds to wait after an action before snapshotting next_state.")
    return p


if __name__ == "__main__":
    collect(build_parser().parse_args())
