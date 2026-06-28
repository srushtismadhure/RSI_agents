#!/usr/bin/env python3
"""E0 — attributed-recovery figure (live DOKS), separate from the auto-harness eval.

Reads the 3 counterfactual summaries and plots no-agent vs with-agent recovery per scenario
with the attributed delta + CI. Every value from results/e0/*.json.
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(HERE, "results", "e0"); FIG = os.path.join(HERE, "figures")
SC = [("scale_zero_geo", "scale-to-0 geo\n(structural)"),
      ("scale_zero_profile", "scale-to-0 profile\n(structural)"),
      ("bad_image_geo", "bad-image geo\n(non-trivial)")]

def main():
    rows = []
    for key, label in SC:
        d = json.load(open(os.path.join(R, key + "__attribution.json")))["summary"]
        rows.append((label, d["no_agent_recovery"]["rate"], d["with_agent_recovery"]["rate"],
                     d["attributed_delta"], d["attributed_delta_ci95"], d["attributable"]))
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(rows)); w = 0.36
    ax.bar(x - w/2, [r[1] for r in rows], w, label="no-agent (ambient)", color="#9aa0a6")
    ax.bar(x + w/2, [r[2] for r in rows], w, label="with-agent (DO llama3.3-70b)", color="#188038")
    for i, r in enumerate(rows):
        ax.text(i - w/2, r[1] + 0.02, f"{r[1]:.2f}", ha="center", fontsize=8)
        ax.text(i + w/2, r[2] + 0.02, f"{r[2]:.2f}", ha="center", fontsize=8)
        col = "#188038" if r[5] else "#d93025"
        ax.text(i, 1.07, f"Δ={r[3]:+.2f}\n[{r[4][0]:.2f},{r[4][1]:.2f}]", ha="center",
                fontsize=8, color=col, weight="bold")
    ax.set_xticks(x); ax.set_xticklabels([r[0] for r in rows], fontsize=9)
    ax.set_ylim(0, 1.25); ax.set_ylabel("recovery rate (out-of-band oracle)")
    ax.legend(loc="center right", fontsize=8)
    ax.set_title("E0 — attributed recovery on LIVE DOKS (agent-caused vs ambient)\n"
                 "out-of-band /hotels probe; Δ green=attributable, red=within noise", fontsize=11, weight="bold")
    ax.text(0.5, -0.13, "structural faults: agent recovers (Δ=+1.0, CI excludes 0). non-trivial bad-image: "
            "agent fails 0/15 -> no attributable signal (stop condition).", transform=ax.transAxes,
            ha="center", fontsize=7.5, color="#5f6368")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "e0_attributed_recovery.png"), dpi=130, bbox_inches="tight")
    print("-> figures/e0_attributed_recovery.png")

if __name__ == "__main__":
    main()
