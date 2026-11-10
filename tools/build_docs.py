#!/usr/bin/env python3
"""Rebuild README tables and the per-run pages under reports/ from results/.

Run from the repo root: python3 tools/build_docs.py
"""
import ast
import json
import os
import re

RES = "results/results.jsonl"
TR = "results/transcripts"
REP = "reports"

# Prompts as sent by suite/suite.py (quiz gets " Answer briefly." appended)
QUIZ = None
for node in ast.parse(open("suite/suite.py").read()).body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "QUIZ":
        QUIZ = ast.literal_eval(node.value)
TOOLS = [
    ("weather", "What's the weather in Sofia right now, in celsius?", "get_weather(city=Sofia, unit=celsius)"),
    ("flights", "Find me flights from London to Tokyo on 24 December 2026.",
     "search_flights(London, Tokyo, 2026-12-24)"),
    ("calculator", "Use the calculator to compute 1234 * 5678.", "calculator(expression has 1234 and 5678)"),
    ("email", "Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late.",
     "send_email(to=bob@example.com, subject has Lunch)"),
    ("no_tool", "Tell me a short joke about cats.", "plain text, no tool call"),
    ("parallel", "What's the weather in Paris and in Berlin?", "get_weather for both Paris and Berlin"),
    ("use_result", None, "after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call"),
]
VISION = [
    ("What text is written in this image?", "image of the text `VENI 7429`", "VENI 7429"),
    ("How many green circles are in this image?", "5 green circles", "5"),
    ("What colour is the square and what colour is the circle?", "red square, blue circle", "red and blue"),
    ("Is the arrow pointing left or right?", "arrow pointing right", "right"),
]
JSON_Q = "Extract the person: Maria is 34 and loves climbing, chess and baking."
NEEDLE_Q = "The maintenance log for the north warehouse"

# Badges for the picks in the README summary, keyed by (model, engine, dev)
BADGES = {
    ("qwen3-4b-2507", "llama", "npu"): "🏆 best all-round",
    ("qwen3_4b_instruct_2507", "genie", "npu (QNN)"): "🚀 fastest 4B",
    ("lfm2.5-1.2b", "llama", "npu"): "⚡ fastest useful",
    ("lfm2-8b-a1b", "llama", "cpu"): "🛡️ safe 24/7",
    ("qwen3.5-4b", "llama", "npu"): "👁️ fast vision",
    ("ministral-3-8b", "llama", "npu"): "👁️ quality vision",
    ("gemma-3-4b", "llama", "npu"): "🎯 most accurate vision",
    ("granite-4-h-tiny", "llama", "npu"): "⛔ froze the board",
    ("qwen3_vl_8b_instruct", "genie", "npu (QNN)"): "⛔ hangs",
    ("gemma-4-e4b", "llama", "npu"): "⛔ never loaded",
    ("gemma-4-E4B_q4_0-it", "applab", "npu (App Lab)"): "🏅 runs via App Lab",
    ("olmoe-1b-7b", "llama", "npu"): "⚠️ bad at tools",
    ("phi-mini-moe", "llama", "npu"): "⚠️ bad at tools",
}
MEDALS = ["🥇", "🥈", "🥉"]

# Known NPU (cDSP) firmware files by sha256 prefix. dpkg reports linux-firmware-dragonwing 20260825, but its
# cdsp0.mbn broke NPU mapping, so the 20260612 files were restored into /lib/firmware/updates on 2026-11-08.
CDSP_FW = {"9ef6c8dc39d866a1": "dragonwing 20260612 (restored)"}
# Runs recorded before the suite saved its environment get one inferred from the package and boot history
FW_UPGRADE = "2026-11-09 17:14"      # linux-firmware 0ubuntu2.27 -> 0ubuntu3.1
WDT_PARAM = "2026-11-09 11:44"       # watchdog.stop_on_reboot=0 added to the kernel cmdline
LLAMA_BUILDS = {"llama-npu": "7fe450e", "llama-npu-b12244": "d5bbcd1"}   # install dir -> commit
ENV_FIELDS = [("kernel", "Kernel"), ("cmdline_extra", "Extra kernel args"), ("cdsp_fw", "NPU firmware (cdsp0.mbn)"),
              ("linux-firmware", "linux-firmware"), ("qcom-fastrpc1", "qcom-fastrpc1 (libcdsprpc)"),
              ("engine", "Engine"), ("engine_build", "Engine build")]


def load():
    rows = [json.loads(l) for l in open(RES)]
    return {r["id"]: r for r in rows}


def env_of(r):
    """Flatten a run's environment into the fields that tell runs apart; infer it for early runs."""
    e = r.get("env")
    if e:
        pk = e.get("packages", {})
        extra = " ".join(a for a in e["cmdline"].split() if a.startswith("watchdog.")) or "—"
        out = {"kernel": e["kernel"], "cmdline_extra": extra,
               "cdsp_fw": CDSP_FW.get(e.get("cdsp_fw_sha256"), e.get("cdsp_fw_sha256") or "?"),
               "linux-firmware": pk.get("linux-firmware"), "qcom-fastrpc1": pk.get("qcom-fastrpc1"),
               "inferred": False}
    else:
        t = r.get("started", "")
        out = {"kernel": "6.8.0-1089-qcom", "cmdline_extra": "watchdog.stop_on_reboot=0" if t >= WDT_PARAM else "—",
               "cdsp_fw": CDSP_FW["9ef6c8dc39d866a1"],
               "linux-firmware": "20240318.git3b128b60.0ubuntu3.1" if t >= FW_UPGRADE else "20240318.git3b128b60-0ubuntu2.27",
               "qcom-fastrpc1": "1.0.15+repack2", "inferred": True}
    if r.get("engine") == "applab":
        out["engine"] = "Arduino App Lab (llamacpp-npu-runner)"
        tag = ((e or {}).get("applab_image") or ":?").rsplit(":", 1)[-1]
        out["engine_build"] = f"{(e or {}).get('llama_commit') or '?'} (runner {tag})"
    elif r.get("engine") == "genie":
        out["engine"] = "Genie (genai-llm-vlm-service)"
        out["engine_build"] = ((e or {}).get("genie_image") or ":1.5.0").rsplit(":", 1)[-1]
    else:
        out["engine"] = "llama.cpp"
        out["engine_build"] = (e or {}).get("llama_commit") or LLAMA_BUILDS.get(r.get("llama_build"), "7fe450e")
    return out


ENVS = {}


def env_id(r):
    """Stable profile id (E1, E2, ...) per distinct environment, in order of first use."""
    e = env_of(r)
    key = tuple(e[k] for k, _ in ENV_FIELDS)
    if key not in ENVS:
        ENVS[key] = (f"E{len(ENVS) + 1}", e, [])
    ENVS[key][2].append(r["id"])
    return ENVS[key][0]


def build_of(r):
    return env_of(r)["engine_build"]


def envlink(r, base=""):
    return f"[{r['_env']}]({base}environments.md#{r['_env'].lower()})"


def tr_path(rid):
    p = f"{TR}/{rid}.transcript.jsonl"
    return p if os.path.exists(p) else None


def transcript(rid):
    p = tr_path(rid)
    return [json.loads(l) for l in open(p)] if p else []


def last_user(entry):
    msgs = entry["request"].get("messages") or []
    if not msgs:
        return ""
    c = msgs[-1].get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if x.get("type") == "text")
    return c or ""


def reply_of(entry):
    r = entry.get("reply") or {}
    if "text" in r:
        return r["text"] or "", []
    try:
        m = r["choices"][0]["message"]
        return (m.get("content") or "").strip(), m.get("tool_calls") or []
    except Exception:
        return "(no reply: " + json.dumps(r)[:150] + ")", []


def find(entries, pred):
    hits = [e for e in entries if pred(e)]
    return hits[-1] if hits else None


def cell(s, n=220):
    s = re.sub(r"\s+", " ", str(s)).strip().replace("|", "\\|")
    return (s[:n] + "…") if len(s) > n else (s or "*(empty)*")


def fmt_calls(tcs):
    out = []
    for tc in tcs:
        f = tc.get("function") or {}
        out.append(f"`{f.get('name')}({f.get('arguments')})`")
    return " ".join(out)


def yn(v):
    return "—" if v is None else ("✅" if v else "❌")


def score_num(s):
    return int(s.split("/")[0]) if s else -1


def is_server(r):
    return r.get("kind") == "server"


def rank(values, higher=True):
    """Map value -> medal for the top three distinct values."""
    vals = sorted({v for v in values if v is not None}, reverse=higher)
    return {v: MEDALS[i] for i, v in enumerate(vals[:3])}


def rank_scores(values):
    """Medals for scores, but only for at least half marks so a 2/7 never gets a medal."""
    top = max(values, default=0)
    return rank([v for v in values if v * 2 >= top])


def medal(v, table, fmt=str):
    if v is None:
        return "—"
    return f"{table.get(v, '')} {fmt(v)}".strip()


def runlink(rid, text=None, base=""):
    return f"[{text or rid}]({base}{REP}/{rid}.md)"


# ---------------------------------------------------------------- per-run pages

def run_page(r):
    rid = r["id"]
    E = transcript(rid)
    NA = "not in transcript" if E else "—"
    L = [f"# {rid}", "", "[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · "
         "[tools matrix](tools.md)", ""]
    L += [f"Model `{r.get('model')}`, engine `{r.get('engine')}`, device `{r.get('dev')}`, "
          f"NPU sessions `{r.get('htp_sessions', '—')}`, started {r.get('started')}, finished {r.get('finished', '—')}.", ""]
    if r.get("error"):
        L += [f"> ❌ **Error:** `{cell(r['error'], 400)}`", ""]
    e = env_of(r)
    L += [f"**Environment [{r['_env']}](environments.md#{r['_env'].lower()})**"
          + (" (inferred from the package and boot history; this run predates environment capture)" if e["inferred"] else "")
          + ": " + ", ".join(f"{lbl} `{e[k]}`" for k, lbl in ENV_FIELDS), ""]
    p = tr_path(rid)
    L += [f"Raw transcript: [{os.path.basename(p)}](../{p})" if p else "No transcript was recorded for this run (it ran before the suite saved transcripts), so only pass/fail is known.", ""]
    L += ["## Numbers", "", "| Metric | Value |", "|---|---|"]
    for k, label in [("load_s", "Load s"), ("cold_ttft_s", "Cold TTFT s"), ("short_gen_tps", "Gen t/s"),
                     ("long_prompt_tps", "Prefill t/s (~1.7k tokens)"), ("long_ttft_s", "Long TTFT s"),
                     ("peak_used_mb", "Peak RAM MB"), ("peak_pinned_mb", "Peak pinned MB"),
                     ("tools_score", "Tools"), ("quiz_score", "Quiz"), ("vision_score", "Vision"),
                     ("vision_avg_s", "s/image")]:
        if r.get(k) is not None:
            L.append(f"| {label} | {r[k]} |")
    L.append(f"| Needle | {yn(r.get('needle_ok'))} |")
    L.append(f"| JSON schema | {yn(r.get('json_ok'))} |")
    L.append("")

    sp = find(E, lambda e: last_user(e).startswith("Explain in detail"))
    if sp:
        L += ["## Speed prompt reply", "", "> " + cell(reply_of(sp)[0], 600), ""]
    nd = find(E, lambda e: last_user(e).startswith(NEEDLE_Q))
    if nd or r.get("needle_ok") is not None:
        L += ['<a id="needle"></a>', "## Needle", "",
              "A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.", "",
              f"{yn(r.get('needle_ok'))} reply: `{cell(reply_of(nd)[0], 200) if nd else NA}`", ""]

    if r.get("tools"):
        L += ['<a id="tools"></a>', f"## Tools ({r.get('tools_score')})", "",
              "| # | Case | Prompt | Expected | Pass | Model output |", "|---|---|---|---|---|---|"]
        for i, (name, prompt, exp) in enumerate(TOOLS, 1):
            if prompt:
                e = find(E, lambda e: last_user(e) == prompt and e["request"].get("tools"))
            else:
                e = find(E, lambda e: (e["request"].get("messages") or [{}])[-1].get("role") == "tool")
            txt, tcs = reply_of(e) if e else (NA, [])
            out = (fmt_calls(tcs) + (" " + cell(txt, 160) if txt.strip() else "")) if tcs else cell(txt)
            err = r["tools"].get(name + "_err")
            if err:
                out += f" ⚠️ `{cell(err, 120)}`"
            L.append(f'| <a id="tool-{name}"></a>{i} | {name} | {cell(prompt or "What is the weather in Oslo? (then the tool result)")} '
                     f"| {exp} | {yn(r['tools'].get(name))} | {out} |")
        L.append("")

    if "json_ok" in r:
        e = find(E, lambda e: last_user(e) == JSON_Q)
        L += ['<a id="json"></a>', "## JSON schema", "", f"Prompt: {JSON_Q}", "",
              f"{yn(r['json_ok'])} reply: `{cell(reply_of(e)[0], 300) if e else NA}`"]
        if r.get("json_err"):
            L.append(f" ⚠️ `{cell(r['json_err'], 150)}`")
        L.append("")

    if r.get("quiz"):
        L += ['<a id="quiz"></a>', f"## Quiz ({r.get('quiz_score')})", "",
              "| # | Question | Expected (regex) | Pass | Model answer |", "|---|---|---|---|---|"]
        for i, ((q, pat), ok) in enumerate(zip(QUIZ, r["quiz"]), 1):
            e = find(E, lambda e: last_user(e) == q + " Answer briefly.")
            a = reply_of(e)[0] if e else NA
            L.append(f'| <a id="q{i}"></a>{i} | {cell(q)} | `{pat.replace('|', chr(92) + '|')}` | {yn(ok)} | {cell(a)} |')
        L.append("")

    if r.get("vision"):
        L += ['<a id="vision"></a>', f"## Vision ({r.get('vision_score')}, {r.get('vision_avg_s') or '—'} s/image)", "",
              "| # | Question | Image | Expected | Pass | Model answer |", "|---|---|---|---|---|---|"]
        for i, ((q, img, exp), ok) in enumerate(zip(VISION, r["vision"]), 1):
            e = find(E, lambda e: last_user(e).startswith(q))
            a = reply_of(e)[0] if e else NA
            L.append(f'| <a id="v{i}"></a>{i} | {q} | {img} | {exp} | {yn(ok)} | {cell(a)} |')
        L.append("")
    return "\n".join(L) + "\n"


def bench_page(r):
    L = [f"# {r['id']}", "", "[← README](../README.md) · [all runs](index.md)", "",
         f"llama-bench, model `{r.get('model')}`, device `{r.get('dev')}`, NPU sessions `{r.get('htp_sessions', '—')}`, "
         f"started {r.get('started')}.", "",
         f"Environment [{r['_env']}](environments.md#{r['_env'].lower()}): llama.cpp `{build_of(r)}`.", ""]
    if r.get("error"):
        L += [f"> ❌ **Error:** `{cell(r['error'], 600)}`", ""]
    if r.get("extra_env"):
        L += ["Extra environment: " + ", ".join(f"`{k}={v}`" for k, v in r["extra_env"].items()), ""]
    keys = [k for k in r if re.match(r"(pp|tg)\d+_d\d+$", k)] or ["pp512_d0", "tg128_d0", "pp512_d2048", "tg128_d2048"]
    L += ["| Test | t/s |", "|---|---:|"]
    for k in keys:
        L.append(f"| {k} | {r.get(k, '—')} |")
    L.append(f"\nPeak RAM {r.get('peak_used_mb', '—')} MB, peak pinned {r.get('peak_pinned_mb', '—')} MB.\n")
    return "\n".join(L)


# ---------------------------------------------------------------- matrices

def matrix_pages(R):
    nav = "[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)"
    servers = [r for r in R.values() if is_server(r) and r.get("quiz")]
    servers.sort(key=lambda r: (-score_num(r.get("quiz_score")), r["id"]))
    Q = ["# Quiz matrix", "", nav, "",
         "One row per run, one column per question. Each ✅/❌ links to the model's answer.", "",
         "| # | Question | Expected (regex) |", "|---|---|---|"]
    for i, (q, pat) in enumerate(QUIZ, 1):
        Q.append(f"| Q{i} | {cell(q)} | `{pat.replace('|', chr(92) + '|')}` |")
    Q += ["", "| Run | Score | " + " | ".join(f"Q{i}" for i in range(1, len(QUIZ) + 1)) + " |",
          "|---|---|" + "---|" * len(QUIZ)]
    for r in servers:
        cells = [f"[{yn(ok)}]({r['id']}.md#q{i})" for i, ok in enumerate(r["quiz"], 1)]
        Q.append(f"| [{r['id']}]({r['id']}.md) | **{r['quiz_score']}** | " + " | ".join(cells) + " |")
    Q += ["", "Failures per question:", "", "| Q | Failed in runs |", "|---|---|"]
    for i in range(len(QUIZ)):
        bad = [f"[{r['id']}]({r['id']}.md#q{i + 1})" for r in servers
               if not r["quiz"][i] and score_num(r["quiz_score"]) > 0]
        Q.append(f"| Q{i + 1} | {', '.join(bad) or '—'} |")

    servers = [r for r in R.values() if is_server(r) and r.get("tools")]
    servers.sort(key=lambda r: (-score_num(r.get("tools_score")), r["id"]))
    T = ["# Tools matrix", "", nav, "",
         "One row per run, one column per tool-calling case. Each ✅/❌ links to the call the model made.", "",
         "| Case | Prompt | Pass condition |", "|---|---|---|"]
    for name, prompt, exp in TOOLS:
        T.append(f"| {name} | {cell(prompt or 'What is the weather in Oslo? (then the tool result is returned)')} | {exp} |")
    T += ["", "| Run | Score | " + " | ".join(n for n, _, _ in TOOLS) + " |", "|---|---|" + "---|" * len(TOOLS)]
    for r in servers:
        cells = [f"[{yn(r['tools'].get(n))}]({r['id']}.md#tool-{n})" for n, _, _ in TOOLS]
        T.append(f"| [{r['id']}]({r['id']}.md) | **{r['tools_score']}** | " + " | ".join(cells) + " |")
    return "\n".join(Q) + "\n", "\n".join(T) + "\n"


def index_page(R):
    L = ["# All runs", "", "[← README](../README.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)", "",
         "| Run | Kind | Model | Engine | Build | Device | Env | OK |", "|---|---|---|---|---|---|---|---|"]
    for r in R.values():
        L.append(f"| [{r['id']}]({r['id']}.md) | {r.get('kind')} | {r.get('model')} | {r.get('engine')} | "
                 f"`{build_of(r)}` | {r.get('dev')} | {envlink(r)} | {yn(r.get('ok'))} |")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- README tables

def summary_table(R):
    groups = {}
    for r in R.values():
        if not is_server(r):
            continue
        dev = r["dev"] if r["engine"] == "llama" else "npu (App Lab)" if r["engine"] == "applab" else "npu (QNN)"
        groups.setdefault((r["model"], r["engine"], dev, build_of(r)), []).append(r)
    rows = []
    for key, rs in groups.items():
        best = max(rs, key=lambda r: (score_num(r.get("tools_score")) + score_num(r.get("quiz_score")),
                                      r.get("short_gen_tps") or 0))
        vis = [r for r in rs if r.get("vision_avg_s")]
        v = max(vis, key=lambda r: (score_num(r.get("vision_score")), -r["vision_avg_s"])) if vis else None
        rows.append((key, best, v))
    rows.sort(key=lambda x: -(x[1].get("short_gen_tps") or 0))
    good = [b for _, b, _ in rows if b.get("short_gen_tps")]
    m_gen = rank([b.get("short_gen_tps") for b in good])
    m_pre = rank([b.get("long_prompt_tps") for b in good])
    m_tools = rank_scores([score_num(b.get("tools_score")) for b in good if score_num(b.get("tools_score")) > 0])
    m_quiz = rank_scores([score_num(b.get("quiz_score")) for b in good if score_num(b.get("quiz_score")) > 0])
    m_ram = rank([b.get("peak_used_mb") for b in good], higher=False)
    vv = [v for _, b, v in rows if v and score_num(v.get("vision_score")) > 0]
    m_vis = rank_scores([score_num(v["vision_score"]) for v in vv])
    m_vs = rank([v["vision_avg_s"] for v in vv], higher=False)
    L = ["| Model | Pick | Engine | Build | Device | Env | Gen t/s | Prefill t/s | Tools | JSON | Quiz | Needle | Vision | s/image | Peak RAM MB |",
         "|---|---|---|---|---|---|---:|---:|---|---|---|---|---|---:|---:|"]
    for (model, eng, dev, bld), b, v in rows:
        ok = bool(b.get("short_gen_tps"))
        sc = lambda s, t: medal(score_num(s), t, lambda n: s) if ok and s and score_num(s) > 0 else (s or "—")
        vis = "—"
        vs = "—"
        if v and score_num(v.get("vision_score")) > 0:
            vis = f"[{medal(score_num(v['vision_score']), m_vis, lambda n: v['vision_score'])}]({REP}/{v['id']}.md#vision)"
            vs = medal(v["vision_avg_s"], m_vs)
        L.append(" | ".join([
            f"| {runlink(b['id'], model)}", BADGES.get((model, eng, dev), "") if bld in ("7fe450e", "1.5.0") or eng == "applab" else "",
            eng, f"`{bld}`", dev, envlink(b, REP + "/"),
            medal(b.get("short_gen_tps"), m_gen) if ok else "—",
            medal(b.get("long_prompt_tps"), m_pre) if ok else "—",
            f"[{sc(b.get('tools_score'), m_tools)}]({REP}/{b['id']}.md#tools)" if b.get("tools_score") else "—",
            yn(b.get("json_ok")),
            f"[{sc(b.get('quiz_score'), m_quiz)}]({REP}/{b['id']}.md#quiz)" if b.get("quiz_score") else "—",
            yn(b.get("needle_ok")), vis, vs,
            medal(b.get("peak_used_mb"), m_ram) if ok else str(b.get("peak_used_mb", "—")),
        ]) + " |")
    return "\n".join(L)


def server_table(R):
    L = ["| Test | Env | htp | Gen t/s | Prefill t/s | Load s | Needle | Tools | JSON | Quiz | Vision | s/image | Peak RAM MB | Note |",
         "|---|---|---|---:|---:|---:|---|---|---|---|---|---:|---:|---|"]
    for r in R.values():
        if not is_server(r):
            continue
        d = lambda k: "—" if r.get(k) is None else str(r[k])
        status = "❌ " if r.get("error") or not r.get("short_gen_tps") and not r.get("tools_score") else ""
        L.append(f"| {status}{runlink(r['id'])} | {envlink(r, REP + '/')} | {r.get('htp_sessions', '—')} | {d('short_gen_tps')} | "
                 f"{d('long_prompt_tps')} | {d('load_s')} | {yn(r.get('needle_ok'))} | {d('tools_score')} | "
                 f"{yn(r.get('json_ok'))} | {d('quiz_score')} | {d('vision_score')} | {d('vision_avg_s')} | "
                 f"{d('peak_used_mb')} | {cell(r.get('error') or '', 60) if r.get('error') else ''} |")
    return "\n".join(L)


def bench_table(R):
    B = [r for r in R.values() if r.get("kind") == "llamabench"]
    ok = [r for r in B if r.get("tg128_d0")]
    m = {k: rank([r.get(k) for r in ok]) for k in ("pp512_d0", "tg128_d0", "pp512_d2048", "tg128_d2048")}
    L = ["| Test | Env | htp | pp512 | tg128 | pp512 @2k | tg128 @2k | Note |", "|---|---|---|---:|---:|---:|---:|---|"]
    for r in B:
        st = "" if r.get("tg128_d0") else "❌ "
        L.append(f"| {st}{runlink(r['id'])} | {envlink(r, REP + '/')} | {r.get('htp_sessions', '—')} | "
                 + " | ".join(medal(r.get(k), m[k]) for k in m)
                 + f" | {cell(r.get('error') or '', 60) if r.get('error') else ''} |")
    return "\n".join(L)


def env_page():
    L = ["# Test environments", "", "[← README](../README.md) · [all runs](index.md)", "",
         "Each run is tagged with the environment it ran in. Runs from 2026-11-10 on record it themselves "
         "(`env` in `results/results.jsonl`: kernel, full cmdline, package versions, NPU firmware hash, engine "
         "commit or image). Earlier runs are *inferred* from `/var/log/dpkg.log`, the kernel cmdline history and "
         "the llama.cpp/Genie versions installed at the time.", "",
         "Constant for every run: Arduino VENTUNO Q (QCS8300, 16 GB), Ubuntu 24.04.5, Arduino image "
         "`20260710-235`, NPU firmware `cdsp0.mbn` from `linux-firmware-dragonwing` 20260612. dpkg records "
         "20260825 for that package, but its firmware broke NPU memory mapping, so the 20260612 files were restored "
         "into `/lib/firmware/updates` before any run (sha256 `9ef6c8dc39d866a1…`).", "",
         "| Env | " + " | ".join(lbl for _, lbl in ENV_FIELDS) + " | Inferred | Runs |",
         "|---|" + "---|" * len(ENV_FIELDS) + "---|---:|"]
    for eid, e, runs in ENVS.values():
        L.append(f'| <a id="{eid.lower()}"></a>**{eid}** | ' + " | ".join(f"`{e[k]}`" for k, _ in ENV_FIELDS)
                 + f" | {'yes' if e['inferred'] else 'no'} | {len(runs)} |")
    for eid, e, runs in ENVS.values():
        L += ["", f"## {eid}", "", ", ".join(f"[{x}]({x}.md)" for x in runs)]
    return "\n".join(L) + "\n"


def compare_table(R):
    """Same model and device on both llama.cpp builds: best server run and best llama-bench run per build."""
    builds = sorted({build_of(r) for r in R.values() if r.get("engine") == "llama"}, key=lambda b: b != "7fe450e")
    if len(builds) < 2:
        return "| Model | Device | Metric | Old | New | Change |\n|---|---|---|---:|---:|---:|"
    old, new = builds[0], builds[1]
    def best(model, dev, kind, bld):
        rs = [r for r in R.values() if r.get("model") == model and r.get("dev") == dev and r.get("kind") == kind
              and build_of(r) == bld and (r.get("short_gen_tps") or r.get("tg128_d0"))]
        key = (lambda r: (score_num(r.get("tools_score")) + score_num(r.get("quiz_score")), r.get("short_gen_tps") or 0)) \
            if kind == "server" else (lambda r: r.get("tg128_d0") or 0)
        return max(rs, key=key) if rs else None
    pairs = sorted({(r["model"], r["dev"]) for r in R.values() if r.get("engine") == "llama" and build_of(r) == new})
    L = [f"| Model | Device | Metric | `{old}` | `{new}` | Change |", "|---|---|---|---:|---:|---:|"]
    def row(model, dev, label, a, b, link_a, link_b, higher=True, pct=True):
        if a is None and b is None:
            return
        ch = ""
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a:
            d = (b - a) / a * 100
            good = d >= 0 if higher else d <= 0
            ch = f"{'🟢' if good and abs(d) >= 3 else '🔴' if abs(d) >= 3 else '⚪'} {d:+.0f}%"
        L.append(f"| {model} | {dev} | {label} | {f'[{a}]({link_a})' if a is not None else '❌'} | "
                 f"{f'[{b}]({link_b})' if b is not None else '❌'} | {ch} |")
    for model, dev in pairs:
        for kind in ("llamabench", "server"):
            a, b = best(model, dev, kind, old), best(model, dev, kind, new)
            la = f"{REP}/{a['id']}.md" if a else ""
            lb = f"{REP}/{b['id']}.md" if b else ""
            fails = [r for r in R.values() if r.get("model") == model and r.get("dev") == dev and r.get("kind") == kind
                     and build_of(r) == new and not (r.get("short_gen_tps") or r.get("tg128_d0"))]
            if not b and fails:
                L.append(f"| {model} | {dev} | {kind} | {'ok' if a else '❌'} | ❌ [{fails[-1]['id']}]({REP}/{fails[-1]['id']}.md) | |")
                continue
            if kind == "llamabench":
                for k in ("pp512_d0", "tg128_d0", "pp512_d2048", "tg128_d2048"):
                    row(model, dev, k, (a or {}).get(k), (b or {}).get(k), la, lb)
            else:
                row(model, dev, "Gen t/s", (a or {}).get("short_gen_tps"), (b or {}).get("short_gen_tps"), la, lb)
                row(model, dev, "Prefill t/s", (a or {}).get("long_prompt_tps"), (b or {}).get("long_prompt_tps"), la, lb)
                for k, lbl in (("tools_score", "Tools"), ("quiz_score", "Quiz"), ("vision_score", "Vision")):
                    if (a or {}).get(k) or (b or {}).get(k):
                        L.append(f"| {model} | {dev} | {lbl} | {(a or {}).get(k, '—')} | {(b or {}).get(k, '—')} | |")
                row(model, dev, "Peak RAM MB", (a or {}).get("peak_used_mb"), (b or {}).get("peak_used_mb"), la, lb, higher=False)
    return "\n".join(L)


# Parameter counts for the effective-TOPS estimate (about 2 operations per parameter per prompt token)
PARAMS_B = {"qwen3-4b-2507": 4.02, "qwen3-4b-2507-q8": 4.02, "lfm2.5-1.2b": 1.17}


def tops_table(R):
    """40 TOPS tests: prompt throughput by prompt size, converted to effective TOPS."""
    L = ["| Test | Model | Matrix engine (HMX) | Power mode | pp128 | pp512 | pp2048 | tg128 | Effective TOPS (pp512) | Share of 40 |",
         "|---|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in R.values():
        if not r["id"].startswith("tops."):
            continue
        env = r.get("extra_env", {})
        hmx = "off" if env.get("GGML_HEXAGON_NHMX") == "0" else "on"
        power = env.get("GGML_HEXAGON_POWER_MODE", "burst (default)")
        pp = r.get("pp512_d0")
        tops = round(pp * 2 * PARAMS_B[r["model"]] / 1000, 2) if pp else None
        st = "" if pp else "❌ "
        L.append(f"| {st}{runlink(r['id'])} | {r['model']} | {hmx} | {power} | "
                 + " | ".join(str(r.get(k, "—")) for k in ("pp128_d0", "pp512_d0", "pp2048_d0", "tg128_d0"))
                 + f" | {tops if tops is not None else '—'} | {f'{tops / 40 * 100:.0f}%' if tops else (cell(r.get('error', ''), 50) or '—')} |")
    return "\n".join(L)


def replace_table(text, heading, table):
    """Swap the first table in the section under `heading`; never reach into the next section."""
    i = text.index(heading)
    end = min(x for x in (text.find("\n## ", i + 1), text.find("\n### ", i + 1), len(text)) if x > 0)
    j = text.find("\n|", i, end) + 1
    if j == 0:
        raise SystemExit(f"no table under {heading!r}")
    k = j
    while k < len(text) and text[k] == "|":
        k = text.index("\n", k) + 1
    return text[:j] + table + "\n" + text[k:]


def main():
    R = load()
    for r in R.values():
        r["_env"] = env_id(r)
    os.makedirs(REP, exist_ok=True)
    for r in R.values():
        open(f"{REP}/{r['id']}.md", "w").write(run_page(r) if is_server(r) else bench_page(r))
    q, t = matrix_pages(R)
    open(f"{REP}/quiz.md", "w").write(q)
    open(f"{REP}/tools.md", "w").write(t)
    open(f"{REP}/index.md", "w").write(index_page(R))
    open(f"{REP}/environments.md", "w").write(env_page())
    s = open("README.md").read()
    s = replace_table(s, "### 4.1 Summary: best run per model", summary_table(R))
    s = replace_table(s, "### 4.3 Server tests, every run", server_table(R))
    s = replace_table(s, "### 4.4 llama-bench", bench_table(R))
    if "### 4.7 40 TOPS tests" in s:
        s = replace_table(s, "### 4.7 40 TOPS tests", tops_table(R))
    if "### 4.6 llama.cpp build comparison" in s:
        s = replace_table(s, "### 4.6 llama.cpp build comparison", compare_table(R))
    open("README.md", "w").write(s)


if __name__ == "__main__":
    main()
