# Code World Model (CWM) pipeline for MicroRemed

Adapts the "Code World Models for General Game Playing" approach to
microservice remediation. Two stages:

```
Stage 1 (now):    real episodes ──► trajectory collector ──► transitions.jsonl
                  (state, action) → (next_state, observation, reward, done)

Stage 2 (later):  transitions.jsonl + NL env description
                      ──► LLM code-synth + test-driven tree-search refinement
                      ──► world_model.py  ──► planner (MCTS / IS-MCTS)
```

The key idea from the talk: instead of using the LLM as the policy every step,
**synthesize a world model in code** and plan with it. To do that you first need
**transition data** — not the chat transcripts the existing
`inject_and_remediate.py` saves, but structured `(state, action) → next_state`
tuples. Stage 1 produces exactly that.

## What "state" and "action" mean here

| Game concept (talk)        | Microservice mapping (this pipeline)                       |
| -------------------------- | ---------------------------------------------------------- |
| state                      | structured cluster snapshot (pods: phase/ready/restarts)   |
| chance / env event         | fault injection (`Action(kind="inject")`)                  |
| agent action               | remediation playbook (`Action(kind="remediate")`)          |
| observation (closed-deck)  | pod health minus the hidden ground-truth fault label       |
| reward / terminal          | target service healthy again                               |

## Files

| File                     | Role                                                              |
| ------------------------ | ----------------------------------------------------------------- |
| `schema.py`              | `State` / `Pod` / `Action` / `Transition` + JSONL read/write      |
| `cluster_state.py`       | snapshot the real cluster (`kubectl`) → `State`                   |
| `recording_client.py`    | `ChaosClient` subclass that records transitions around actions    |
| `collect_trajectories.py`| Stage 1 CLI: drive episodes, write `transitions.jsonl`            |
| `world_model_spec.py`    | Stage 2 SPEC: world-model API + synthesis-loop outline (stubs)    |

Nothing in the existing MicroRemed client is modified — the collector reuses
`ChaosClient`, `envs.env`, and `methods.remediate`, and captures transitions by
**wrapping** the client (`recording_client.py`).

## Running Stage 1 (infra-dependent)

Collection reads the real cluster, so it needs the full stack up:

- MicroRemed-Server reachable at `--server-url`
- a Kubernetes cluster with the target env deployed
- `kubectl` on PATH with access to that cluster (the snapshot backend)
- `LLM_API_KEY` set (the remediation agent calls an LLM)

```bash
export LLM_API_KEY=...
cd backend/microremed_client
python3 -m cwm.collect_trajectories \
    --env train-ticket --namespace train-ticket \
    --server-url http://127.0.0.1:5000 \
    --model qwen-plus --remediate-method SoloGen \
    --experiment-path experiments/easy.txt \
    --out data/trajectories/train-ticket.jsonl
```

Output: one JSON object per line, e.g.

```json
{"episode_id":"ts-order-service_cpu-stress_1a2b3c4d","step":0,
 "action":{"kind":"inject","method":"cpu-stress","target":"ts-order-service"},
 "state":{...},"next_state":{...},"observation":{...},"reward":0.0,"done":false}
```

If the cluster is only reachable server-side, add a `/cluster_state` endpoint to
MicroRemed-Server and pass a custom `snapshot_fn` (see `cluster_state.py`); the
default `kubectl` backend assumes the collector host can reach the cluster.

## Stage 2 (the "CWM later" part)

`world_model_spec.py` defines the target `CodeWorldModel` API and the synthesis
loop outline (generate code → score against unit tests built from the
transitions → refine via Thompson-sampling tree search). Implementing those two
`NotImplementedError` bodies is the next milestone, consuming the
`transitions.jsonl` produced by Stage 1.

## Known issue worth fixing before a real run

`methods/remediate.py` imports `methods.CoRA.coordinator`, but the package is
named `ThinkRemed` (no `CoRA/` dir exists). Importing `methods.remediate` will
raise `ModuleNotFoundError`. The collector imports it lazily so the rest of the
`cwm` package loads fine, but a real collection run with `--remediate-method`
will hit this until `remediate.py` is corrected.
