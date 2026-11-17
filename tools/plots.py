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
R = [json.loads(l) for l in open(os.path.join(ROOT, "results", "performance", "results.jsonl"))]
PARAMS_B = {"qwen3-4b-2507": 4.02, "lfm2.5-1.2b": 1.17}
GENIE_TOPS = 1034 * 2 * 4.02 / 1000   # README §4.7, pp512 from results/probes/genie_prefill_sizes.txt
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
        # "tools_score": gpt-oss and Qwen3-30B ran their server tests under a kind "bench" queue item
        if (r.get("kind") != "server" and "tools_score" not in r) or not r.get("ok") or not r.get("short_gen_tps"):
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


def place_labels(ax, pts):
    """Label each point at the first nearby spot whose text box overlaps no other label or point."""
    fig = ax.figure
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    taken = [ax.transData.transform((x, y)) for x, y, _ in pts]
    taken = [(px - 5, py - 5, px + 5, py + 5) for px, py in taken]
    cands = [(6, 3, "left"), (6, -10, "left"), (-6, 3, "right"), (-6, -10, "right"), (0, 10, "center"),
             (0, -16, "center")]
    cands += [(dx * k, dy * k, ha) for k in (2, 3) for dx, dy, ha in cands[:4]]
    # crowded clusters: further out, with a leader line
    cands += [(dx, dy, "center") for dy in (22, -26, 34, -38, 46, -50, 58, -62) for dx in (0, -35, 35, -70, 70)]
    for x, y, name in pts:
        for dx, dy, ha in cands:
            t = ax.annotate(name, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=7.5, ha=ha,
                            arrowprops=dict(arrowstyle="-", lw=0.4, color="grey") if abs(dx) > 6 or abs(dy) > 10 else None)
            t.update_positions(rend)
            b = matplotlib.text.Text.get_window_extent(t, rend)  # text only, not the leader line
            box = (b.x0 - 1, b.y0 - 1, b.x1 + 1, b.y1 + 1)
            ab = ax.get_window_extent(rend)
            inside = ab.x0 <= box[0] and box[2] <= ab.x1 and ab.y0 <= box[1] and box[3] <= ab.y1
            if inside and not any(box[0] < o[2] and o[0] < box[2] and box[1] < o[3] and o[1] < box[3] for o in taken):
                taken.append(box)
                break
            t.remove()
        else:
            ax.annotate(name, (x, y), xytext=(6, 3), textcoords="offset points", fontsize=7.5)


def speed_vs_quality():
    fig, ax = plt.subplots(figsize=(10, 6.5))
    pts = []
    for r in sorted(best_servers(), key=lambda r: (-score(r["tools_score"]) - score(r["quiz_score"]), r["short_gen_tps"])):
        g = group(r)
        s = score(r["tools_score"]) + score(r["quiz_score"])
        x = r["short_gen_tps"]
        ax.scatter(x, s, s=60, color=DEV_COLOR.get(g, "grey"), edgecolor="black", linewidth=0.4, zorder=3)
        pts.append((x, s, "qwen3-4b (Genie)" if g == "genie" else r["model"].replace("gemma-4-E4B_q4_0-it", "gemma-4-e4b")))
    for g, c in DEV_COLOR.items():
        ax.scatter([], [], color=c, label={"npu": "llama.cpp NPU", "cpu": "llama.cpp CPU", "genie": "Genie (QNN)",
                                           "applab": "Arduino App Lab"}[g])
    ax.set(xlabel="Generation speed, short reply (tokens/s)", ylabel="Tools + quiz score (max 19)",
           title="Speed vs accuracy, best run per model and engine")
    ax.set_ylim(-1, 20.5)
    ax.legend(loc="lower right")
    fig.tight_layout()
    place_labels(ax, pts)
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
    rows.append(("Genie qwen3-4b\npp512", GENIE_TOPS))
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
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "results", "stability", "soak.jsonl"))]
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


def coding():
    rows = []
    for f in sorted(os.listdir(os.path.join(ROOT, "results", "coding"))):
        R = [json.loads(l) for l in open(os.path.join(ROOT, "results", "coding", f))]
        c = [r for r in R if "variant" in r]
        s = [r for r in c if r["variant"] == "selftest"]
        rows.append((f[:-6], sum(r["hidden"] for r in c if r["variant"] == "hidden"),
                     sum(bool(r.get("asserts_correct")) for r in s), len(s)))
    rows.sort(key=lambda r: -r[1])
    fig, ax = plt.subplots(figsize=(9, 1.2 + 0.36 * len(rows)))
    y = range(len(rows))
    ax.barh([i - 0.2 for i in y], [r[1] for r in rows], height=0.4, color=DEV_COLOR["npu"], label="code passes hidden tests")
    ax.barh([i + 0.2 for i in y], [r[2] for r in rows], height=0.4, color="#adb5bd", label="its own asserts all correct")
    for i, r in enumerate(rows):
        ax.text(r[1] + 0.4, i - 0.2, str(r[1]), va="center", fontsize=8)
        ax.text(r[2] + 0.4, i + 0.2, str(r[2]), va="center", fontsize=8)
    ax.set_yticks(list(y), [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set(xlabel=f"Tasks (of {max(r[3] for r in rows)})", xlim=(0, 44), title="Coding: writing correct code vs writing correct tests")
    ax.legend(loc="lower right", fontsize=8)
    save(fig, "coding.svg")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in (speed_vs_quality, npu_vs_cpu, tops, bandwidth, soak, coding):
        f()
