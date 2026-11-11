#!/usr/bin/env python3
"""Draw the report figures from results/ into docs/figures/ (SVG).

Run from the repo root after tools/build_docs.py: python3 tools/plots.py
Needs matplotlib. Every figure is drawn from the raw result files, nothing is typed in by hand except the
advertised 40 TOPS and the Genie prefill figure measured in §4.7."""
import json, os, re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "figures")
R = [json.loads(l) for l in open(os.path.join(ROOT, "results", "results.jsonl"))]
PARAMS_B = {"qwen3-4b-2507": 4.02, "lfm2.5-1.2b": 1.17}
GENIE_TOPS = 10.4                      # README §4.7, from results/probes/genie_prefill_qwen3-4b.txt
DEV_COLOR = {"npu": "#d9480f", "cpu": "#1c7ed6", "genie": "#7048e8", "applab": "#2b8a3e"}

plt.rcParams.update({"figure.dpi": 110, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "svg.fonttype": "none"})


def score(s):
    """'7/7' -> 7.0; anything else -> None."""
    m = re.match(r"(\d+)/(\d+)", str(s or ""))
    return int(m.group(1)) if m else None


def group(r):
    if r.get("engine") == "genie":
        return "genie"
    if r.get("engine") == "applab":
        return "applab"
    return r.get("dev")


def best_servers():
    """Best finished server run per (model, group), by tools+quiz then generation speed."""
    best = {}
    for r in R:
        if r.get("kind") != "server" or not r.get("ok") or not r.get("short_gen_tps"):
            continue
        t, q = score(r.get("tools_score")), score(r.get("quiz_score"))
        if t is None or q is None:
            continue
        k = (r["model"], group(r))
        key = (t + q, r["short_gen_tps"])
        if k not in best or key > best[k][0]:
            best[k] = (key, r)
    return [v[1] for v in best.values()]


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), format="svg")
    plt.close(fig)
    print("wrote", f"docs/figures/{name}")


def speed_vs_quality():
    fig, ax = plt.subplots(figsize=(10, 6.5))
    placed = []                                   # label positions, to stagger labels of points that overlap
    for r in sorted(best_servers(), key=lambda r: (r["short_gen_tps"], r["model"])):
        g = group(r)
        s = score(r["tools_score"]) + score(r["quiz_score"])
        x = r["short_gen_tps"]
        ax.scatter(x, s, s=60, color=DEV_COLOR.get(g, "grey"), edgecolor="black", linewidth=0.4, zorder=3)
        dy = 4
        while any(abs(px - x) < 3.2 and abs(py - (s + dy / 30)) < 0.3 for px, py in placed):
            dy += 9
        placed.append((x, s + dy / 30))
        name = "qwen3-4b (Genie)" if g == "genie" else r["model"]
        ax.annotate(name, (x, s), xytext=(5, dy), textcoords="offset points", fontsize=7.5,
                    arrowprops=dict(arrowstyle="-", lw=0.4, color="grey") if dy > 4 else None)
    for g, c in DEV_COLOR.items():
        ax.scatter([], [], color=c, label={"npu": "llama.cpp NPU", "cpu": "llama.cpp CPU", "genie": "Genie (QNN)",
                                           "applab": "Arduino App Lab"}[g])
    ax.set(xlabel="Generation speed, short reply (tokens/s)", ylabel="Tools + quiz score (max 19)",
           title="Speed vs accuracy, best run per model and engine")
    ax.legend(loc="lower right")
    save(fig, "speed-vs-quality.svg")


def npu_vs_cpu():
    runs = {(r["model"], group(r)): r for r in best_servers()}
    models = sorted({m for m, g in runs if g == "npu"} & {m for m, g in runs if g == "cpu"})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 0.9 * len(models) + 1.8), sharey=True)
    y = range(len(models))
    for ax, key, label in ((a1, "short_gen_tps", "Generation (tokens/s)"), (a2, "long_prompt_tps", "Prompt reading, long prompt (tokens/s)")):
        for off, dev in ((-0.2, "npu"), (0.2, "cpu")):
            ax.barh([i + off for i in y], [runs[(m, dev)].get(key) or 0 for m in models], height=0.4,
                    color=DEV_COLOR[dev], label=dev.upper())
        ax.set_xlabel(label)
    for ax, key in ((a1, "short_gen_tps"), (a2, "long_prompt_tps")):
        for off, dev in ((-0.2, "npu"), (0.2, "cpu")):
            for i, m in enumerate(models):
                v = runs[(m, dev)].get(key) or 0
                ax.text(v, i + off, f" {v:.0f}" if v >= 100 else f" {v:.1f}", va="center", fontsize=8)
    a1.set_yticks(list(y), models)
    a1.invert_yaxis()
    a1.legend()
    fig.suptitle("NPU vs CPU, same model (llama.cpp): generation is close, prompt reading is not")
    save(fig, "npu-vs-cpu.svg")


def tops():
    rows = []
    for r in R:
        if r["id"].startswith("tops.") and r.get("pp512_d0") and r["model"] in PARAMS_B:
            env = r.get("extra_env", {})
            tag = "HMX off" if env.get("GGML_HEXAGON_NHMX") == "0" else env.get("GGML_HEXAGON_POWER_MODE", "HMX on")
            rows.append((f"llama.cpp {r['model']}\n{tag}", r["pp512_d0"] * 2 * PARAMS_B[r["model"]] / 1000))
    rows.append(("Genie qwen3-4b", GENIE_TOPS))
    rows.append(("Advertised", 40.0))
    fig, ax = plt.subplots(figsize=(9, 4.8))
    names, vals = zip(*rows)
    colors = ["#adb5bd" if n == "Advertised" else DEV_COLOR["genie"] if n.startswith("Genie") else DEV_COLOR["npu"]
              for n in names]
    bars = ax.barh(names, vals, color=colors)
    for b, v in zip(bars, vals):
        ax.text(v + 0.4, b.get_y() + b.get_height() / 2, f"{v:.1f} ({v / 40:.0%})", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set(xlabel="Effective TOPS during prompt reading (2 ops per parameter per token)", xlim=(0, 46),
           title="Measured NPU throughput vs the advertised 40 TOPS")
    save(fig, "tops.svg")


def bandwidth():
    best = {}
    for l in open(os.path.join(ROOT, "results", "probes", "memory_bandwidth.txt")):
        m = re.match(r"(\w+) threads=(\d+) ([\d.]+) GB/s", l.strip())
        if m:
            k = (m.group(1), int(m.group(2)))
            best[k] = max(best.get(k, 0), float(m.group(3)))
    fig, ax = plt.subplots(figsize=(7, 4))
    for op, c in (("read", "#1c7ed6"), ("copy", "#d9480f")):
        pts = sorted((t, v) for (o, t), v in best.items() if o == op)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=c, label=op)
    # A 4B Q4_0 model reads about 2.3 GB of weights per generated token
    ax.axhline(30, ls="--", color="grey")
    ax.text(1, 30.6, "≈ 30 GB/s ceiling → ~13 t/s for a 2.3 GB model", fontsize=8, color="grey")
    ax.set(xlabel="CPU threads", ylabel="GB/s", ylim=(0, 36), xticks=sorted({t for _, t in best}),
           title="Measured memory bandwidth (best of repeated runs)")
    ax.legend()
    save(fig, "memory-bandwidth.svg")


def soak():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "results", "soak", "soak.jsonl"))]
    # The board has no RTC, so wall-clock time jumps at each reboot: plot by cumulative request number instead
    x, gen, temp, freezes, i = [], [], [], [], 0
    for r in rows:
        if r.get("event") == "wedge":
            freezes.append(i)
        if r.get("ok") and r.get("tokens", 0) > 200:
            i += 1
            x.append(i); gen.append(r["gen_tps"]); temp.append(r["max_c"])
        elif r.get("ok"):
            i += 1
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x, gen, ".", ms=2, color=DEV_COLOR["npu"], label="generation t/s (answers > 200 tokens)")
    ax.set(xlabel="Request number", ylabel="tokens/s", ylim=(0, 16),
           title="12-hour soak, Qwen3-4B on the NPU with MBUF 256: 1766 requests, 2 freezes")
    t = ax.twinx()
    t.plot(x, temp, color="#495057", lw=0.8, label="max temperature °C")
    t.set(ylabel="°C", ylim=(20, 60))
    t.grid(False)
    for f in freezes:
        ax.axvline(f, color="red", lw=1.2)
    ax.plot([], [], color="red", label="freeze → sysrq reset")
    ax.plot([], [], color="#495057", label="max temperature °C")
    ax.legend(loc="lower right", fontsize=8)
    save(fig, "soak.svg")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in (speed_vs_quality, npu_vs_cpu, tops, bandwidth, soak):
        f()
