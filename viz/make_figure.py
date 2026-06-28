#!/usr/bin/env python3
"""Auto-Harness SRE eval — 6-panel figure, every bar from a real result file in ../results.

Integrity: no numeric literals for bars; each panel reads its JSON. Honest captions flag
SUSPECT/committed data. Panel 6 derives lift Δ + CIs from Panel 2's per-incident data.
Run:  python3 viz/make_figure.py   (from publish/)
"""
import json, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)
def L(f): return json.load(open(os.path.join(R, f)))
BLUE, GREEN, GREY, RED, AMBER = "#1a73e8", "#188038", "#9aa0a6", "#d93025", "#f9ab00"
T_4 = 2.776  # t(0.975, df=4) for n=5 paired incidents


def _bars(ax, labels, groups, colors, title, ylabel="mean reward", ylim=1.05, note=None):
    import numpy as np
    x = np.arange(len(labels)); k = len(groups); w = 0.8 / k
    for i, (gname, vals) in enumerate(groups):
        b = ax.bar(x + (i - (k - 1) / 2) * w, vals, w, label=gname, color=colors[i])
        for xi, v in zip(x + (i - (k - 1) / 2) * w, vals):
            if v is not None: ax.text(xi, v + 0.02, f"{v:.2f}", ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8, rotation=15)
    ax.set_ylim(0, ylim); ax.set_ylabel(ylabel, fontsize=8)
    ax.set_title(title, fontsize=9, weight="bold")
    if k > 1: ax.legend(fontsize=7)
    if note: ax.text(0.5, -0.28, note, transform=ax.transAxes, ha="center", fontsize=6.5,
                     color=RED, wrap=True)


def panel1_env(ax):
    d = L("env_quality.json"); m = d["by_model"]
    labels = list(m.keys()); vals = [m[k] for k in labels]
    _bars(ax, [k.replace("claude-", "") for k in labels], [("one-shot diagnosis", vals)], [BLUE],
          f"1. ENV QUALITY — one-shot diagnosis ({d['n_tasks']} HUD tasks)",
          note="real HUD eval (mean reward); base model, no harness")


def panel2_frontier(ax):
    d = L("frontier.json"); ms = d["models"]
    labels = [m["model"].replace("claude-", "").replace("-pro", "") for m in ms]
    base = [m["baseline_mean"] for m in ms]; rex = [m["rex_mean"] for m in ms]
    _bars(ax, labels, [("baseline", base), ("+REx", rex)], [GREY, GREEN],
          "2. FRONTIER SWEEP — baseline vs +REx (5 incidents)",
          note="SUSPECT: committed file has rex=0.86 for ALL models; contradicts Panel 1 (opus 0.50). Re-run required.")


def panel3_curriculum(ax):
    d = L("curriculum.json"); hard = d.get("hard", {})
    models = list(hard.keys())[:5]
    base = [hard[m].get("baseline_mean") for m in models]
    rex = [hard[m].get("rex_mean") for m in models]
    _bars(ax, [m.replace("claude-", "").replace("-pro", "") for m in models],
          [("baseline", base), ("+REx", rex)], [GREY, GREEN],
          "3. CURRICULUM — HARD cascades, baseline vs +REx",
          note="hard-cascade means from curriculum.json (committed)")


def panel4_ablation(ax):
    h = L("ablation_haiku.json")["aggregate"]; g = L("ablation_glm.json")["aggregate"]
    arms = ["zero_shot", "best_of_n", "retry_realistic", "rex_no_oracle", "rex"]
    val = lambda agg, a: (agg[a]["mean"] if isinstance(agg[a], dict) else agg[a])
    _bars(ax, arms, [("haiku", [val(h, a) for a in arms]), ("glm-5p2", [val(g, a) for a in arms])],
          [BLUE, AMBER], "4. FAIR-CONTROL ABLATION (honest)",
          note="haiku: rex 0.69 -> rex_no_oracle 0.25 ~ zero_shot 0.24 (COLLAPSES); glm: partial dependence")


def panel5_synth(ax):
    v1 = L("harness_synth_v1.json")["table"]
    seed = v1["seed (empty)"]["heldout"]["accuracy"]
    synth = v1["synthesized"]["heldout"]["accuracy"]
    hand = v1["hand-written is_safe"]["heldout"]["accuracy"]
    # v2 synthesized accuracy (different key shape)
    try:
        v2 = L("harness_synth_v2.json"); t2 = v2.get("heldout_table") or {}
        synth2 = next((x.get("accuracy") for k, x in t2.items() if "synth" in k.lower()), None)
    except Exception:
        synth2 = None
    labels = ["seed", "synth-v1", "synth-v2", "hand-written"]
    vals = [seed, synth, synth2, hand]
    cols = [GREY, GREEN, GREEN, BLUE]
    import numpy as np
    x = np.arange(len(labels))
    for xi, v, c in zip(x, vals, cols):
        if v is not None: ax.bar(xi, v, 0.6, color=c); ax.text(xi, v + 0.02, f"{v:.2f}", ha="center", fontsize=7)
        else: ax.text(xi, 0.05, "NEEDS\nDATA", ha="center", fontsize=7, color=RED)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8); ax.set_ylim(0, 1.05)
    ax.set_ylabel("held-out accuracy", fontsize=8)
    ax.set_title("5. SYNTHESIZED VERIFIER — held-out accuracy", fontsize=9, weight="bold")
    ax.text(0.5, -0.22, "REx-synthesized vs hand-written is_safe. NOTE: synth false-allow 0.385 >> hand 0.154 (safety).",
            transform=ax.transAxes, ha="center", fontsize=6.5, color=RED)


def panel6_lift(ax):
    d = L("frontier.json"); ms = d["models"]; scn = d["scenarios"]
    labels, deltas, errs, noisy = [], [], [], []
    for m in ms:
        diffs = [m["per_scenario"][s][1] - m["per_scenario"][s][0] for s in scn]
        n = len(diffs); mean = sum(diffs) / n
        var = sum((x - mean) ** 2 for x in diffs) / (n - 1) if n > 1 else 0.0
        ci = T_4 * math.sqrt(var / n)
        labels.append(m["model"].replace("claude-", "").replace("-pro", ""))
        deltas.append(mean); errs.append(ci); noisy.append(mean - ci <= 0)
    order = sorted(range(len(deltas)), key=lambda i: -deltas[i])
    labels = [labels[i] for i in order]; deltas = [deltas[i] for i in order]
    errs = [errs[i] for i in order]; noisy = [noisy[i] for i in order]
    import numpy as np
    x = np.arange(len(labels))
    ax.bar(x, deltas, 0.6, yerr=errs, capsize=4,
           color=[GREY if nz else GREEN for nz in noisy])
    for xi, dv, nz in zip(x, deltas, noisy):
        ax.text(xi, dv + 0.01, f"{dv:+.2f}" + ("*" if nz else ""), ha="center", fontsize=7)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8, rotation=15)
    ax.set_ylabel("REx lift Δ (mean over incidents)", fontsize=8)
    ax.set_title("6. REx LIFT per model (Δ = +REx − baseline)", fontsize=9, weight="bold")
    ax.text(0.5, -0.28, "* CI includes 0 = within noise. Derived from Panel 2 (SUSPECT source).",
            transform=ax.transAxes, ha="center", fontsize=6.5, color=RED)


PANELS = [("panel_1_env_quality", panel1_env), ("panel_2_frontier_sweep", panel2_frontier),
          ("panel_3_curriculum", panel3_curriculum), ("panel_4_ablation", panel4_ablation),
          ("panel_5_synth_verifier", panel5_synth), ("panel_6_rex_lift", panel6_lift)]


def main():
    # individual panels
    for name, fn in PANELS:
        fig, ax = plt.subplots(figsize=(5, 4))
        fn(ax); fig.tight_layout()
        fig.savefig(os.path.join(FIG, name + ".png"), dpi=130, bbox_inches="tight")
        plt.close(fig)
    # combined 3x2
    fig, axs = plt.subplots(3, 2, figsize=(13, 14))
    for (name, fn), ax in zip(PANELS, axs.flat):
        fn(ax)
    fig.suptitle("Auto-Harness for SRE — evaluation (base policy FIXED; only the verifier is learned)",
                 fontsize=13, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(os.path.join(FIG, "all_evals.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("figures ->", FIG)
    for f in sorted(os.listdir(FIG)):
        print("  ", f)


if __name__ == "__main__":
    main()
