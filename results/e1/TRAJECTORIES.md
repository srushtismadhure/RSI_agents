# E1 — actual search trajectories (raw logs)

The improvement in E1 (fix-search cracking `bad_image_geo` that single-shot failed 0/15) is not
a summary statistic — it is visible in the per-episode search logs. Each `trajectories/*.json`
records, for one episode: every node, the cluster severity μ, each proposed action, the
verifier verdict (pruned / allowed / false-allow), the oracle/severity outcome of each executed
WRITE, and every undo. 40 episodes (2 arms × 20 seeds).

`severity μ` = 0.5·(1 − journey success) + 0.5·(NotReady core services / 8). Lower is healthier.
Internal pod IPs scrubbed (`10.x.x.x`); no tokens or endpoints in these logs.

---

## ✅ Resolved — the improvement (`search_nohint`, seed 1)
The agent diagnosed the **correct** service (`geo`) and applied the root-cause fix; severity
dropped and the journey recovered. This is what single-shot never did.

```
INIT  severity=0.5625  journey=0.0  geo NotReady
READ  kubectl describe deployment geo        # diagnose the fault site
READ  kubectl logs deployment/geo --tail 100
EXEC  kubectl rollout undo deployment geo
        -> severity 0.5625 -> 0.1667   journey 0.6667     # progress: keep
READ  kubectl logs / describe geo (verify) ...
=> RESOLVED  (journey sustained over the settling window; no severity regression)
   writes=1  false_allow=0  TNR_violations=0
```

## 🛡️ Safety machinery firing (`search_nohint`, seed 13)
The agent **misdiagnosed** — it chased `reservation` (where the 5xx surfaced), not `geo`. Its
`rollout undo` on the wrong service *raised* severity; the TNR check caught it and **rolled it
back** so the search accumulated no damage.

```
INIT  severity=0.5  journey=0.0
READ  kubectl describe deployment reservation ...        # chasing the symptom service
EXEC  kubectl rollout undo deployment reservation
        -> severity 0.5 -> 0.5625   journey 0.0
        TNR VIOLATION (severity rose); UNDO                # rolled back, no damage kept
READ  ... (keeps investigating reservation, never reaches geo)
=> NOT resolved.  TNR_violations=1  (caught + undone)
```

## ❌ Honest failure (`search_nohint`, seed 0)
Same misdiagnosis, no harm done, but the agent never located `geo` within the budget — so it
fails. This is the *same* symptom-vs-root-cause confusion E0 exposed single-shot; search only
fixes it when the agent happens to look at the right service.

```
INIT  severity=0.5  journey=0.0
READ  kubectl describe deployment reservation ...
EXEC  kubectl rollout undo deployment reservation
        -> severity 0.5625 -> 0.5625  (no change)
        neutral; UNDO + backtrack
READ  ... (continues on reservation, never reaches geo)
=> NOT resolved.  writes=1  false_allow=0  TNR_violations=0
```

---

**Reading the aggregate (N=20, `search_nohint`):** 8/20 resolved — the episodes where the agent
investigated `geo` and applied `rollout undo` / image-restore; 12/20 failed — mostly the
reservation-misdiagnosis path above. The lift over single-shot (0/15) is real and attributable
(Δ +0.40, CI [0.03, 0.61]); the cap at ~40% is the agent's diagnosis, not the search machinery.
Full per-episode logs: `trajectories/bad_image_geo__{search_nohint,search_hint}__seed*.json`.
