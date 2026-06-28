#!/usr/bin/env python3
"""E1 — verifier-pruned fix-search figure: resolution lift + safety ledger.
Reads results/e1/e1_summary.json (copied from the live run). Every value from the file.
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(HERE, "results", "e1", "e1_summary.json")))
FIG = os.path.join(HERE, "figures")


def main():
    b = S["baselines"]; arms = S["arms"]
    # left: resolution rate (no-agent / single-shot / search_nohint / search_hint)
    labels = ["no-agent\n(E0)", "single-shot\n(E0)", "search\n(no hint)", "search\n(+hint)"]
    rates = [b["e0_no_agent"]["rate"], b["e0_single_shot"]["rate"],
             arms["search_nohint"]["resolve_rate"], arms["search_hint"]["resolve_rate"]]
    cis = [b["e0_no_agent"]["ci95"], b["e0_single_shot"]["ci95"],
           arms["search_nohint"]["resolve_ci95"], arms["search_hint"]["resolve_ci95"]]
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(len(labels))
    yerr = [[r - c[0] for r, c in zip(rates, cis)], [c[1] - r for r, c in zip(rates, cis)]]
    cols = ["#9aa0a6", "#d93025", "#188038", "#1a73e8"]
    axL.bar(x, rates, 0.6, yerr=yerr, capsize=5, color=cols)
    for xi, r in zip(x, rates): axL.text(xi, r + 0.03, f"{r:.2f}", ha="center", fontsize=9)
    axL.set_xticks(x); axL.set_xticklabels(labels, fontsize=8); axL.set_ylim(0, 1.15)
    axL.set_ylabel("resolution rate (out-of-band oracle)")
    axL.set_title("E1 — fix-search vs single-shot on bad_image_geo\n(does SEARCH crack the cascade single-shot failed?)",
                  fontsize=10, weight="bold")

    # right: safety ledger (per arm) — proposed / caught / false-allow / TNR
    keys = ["writes_proposed", "writes_caught_by_verifier", "false_allow_under_search", "tnr_violations"]
    klab = ["proposed", "caught", "false-allow", "TNR viol."]
    w = 0.38
    for i, arm in enumerate(["search_nohint", "search_hint"]):
        led = arms[arm]["safety_ledger"]
        vals = [led[k] for k in keys]
        axR.bar(np.arange(len(keys)) + (i - 0.5) * w, vals, w, label=arm,
                color=["#188038", "#1a73e8"][i])
        for xi, v in zip(np.arange(len(keys)) + (i - 0.5) * w, vals):
            axR.text(xi, v + 0.1, str(v), ha="center", fontsize=8)
    axR.set_xticks(np.arange(len(keys))); axR.set_xticklabels(klab, fontsize=8)
    axR.set_ylabel("count (summed over seeds)")
    axR.set_title("E1 — safety ledger under search\n(false-allow = verifier-safe but actually dangerous)",
                  fontsize=10, weight="bold")
    axR.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "e1_fix_search.png"), dpi=130, bbox_inches="tight")
    print("-> figures/e1_fix_search.png")


if __name__ == "__main__":
    main()
