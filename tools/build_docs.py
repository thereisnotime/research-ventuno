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
    ("olmoe-1b-7b", "llama", "npu"): "⚠️ bad at tools",
    ("phi-mini-moe", "llama", "npu"): "⚠️ bad at tools",
}
MEDALS = ["🥇", "🥈", "🥉"]


def load():
    rows = [json.loads(l) for l in open(RES)]
    return {r["id"]: r for r in rows}


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
            out = (fmt_calls(tcs) + " " + cell(txt, 160)).strip() if tcs else cell(txt)
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
         f"started {r.get('started')}.", ""]
    if r.get("error"):
        L += [f"> ❌ **Error:** `{cell(r['error'], 600)}`", ""]
    L += ["| Test | t/s |", "|---|---:|"]
    for k in ("pp512_d0", "tg128_d0", "pp512_d2048", "tg128_d2048"):
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
         "| Run | Kind | Model | Engine | Device | OK |", "|---|---|---|---|---|---|"]
    for r in R.values():
        L.append(f"| [{r['id']}]({r['id']}.md) | {r.get('kind')} | {r.get('model')} | {r.get('engine')} | "
                 f"{r.get('dev')} | {yn(r.get('ok'))} |")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- README tables

def summary_table(R):
    groups = {}
    for r in R.values():
        if not is_server(r):
            continue
        groups.setdefault((r["model"], r["engine"], r["dev"] if r["engine"] == "llama" else "npu (QNN)"), []).append(r)
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
    L = ["| Model | Pick | Engine | Device | Gen t/s | Prefill t/s | Tools | JSON | Quiz | Needle | Vision | s/image | Peak RAM MB |",
         "|---|---|---|---|---:|---:|---|---|---|---|---|---:|---:|"]
    for (model, eng, dev), b, v in rows:
        ok = bool(b.get("short_gen_tps"))
        sc = lambda s, t: medal(score_num(s), t, lambda n: s) if ok and s and score_num(s) > 0 else (s or "—")
        vis = "—"
        vs = "—"
        if v and score_num(v.get("vision_score")) > 0:
            vis = f"[{medal(score_num(v['vision_score']), m_vis, lambda n: v['vision_score'])}]({REP}/{v['id']}.md#vision)"
            vs = medal(v["vision_avg_s"], m_vs)
        L.append(" | ".join([
            f"| {runlink(b['id'], model)}", BADGES.get((model, eng, dev), ""), eng, dev,
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
    L = ["| Test | htp | Gen t/s | Prefill t/s | Load s | Needle | Tools | JSON | Quiz | Vision | s/image | Peak RAM MB | Note |",
         "|---|---|---:|---:|---:|---|---|---|---|---|---:|---:|---|"]
    for r in R.values():
        if not is_server(r):
            continue
        d = lambda k: "—" if r.get(k) is None else str(r[k])
        status = "❌ " if r.get("error") or not r.get("short_gen_tps") and not r.get("tools_score") else ""
        L.append(f"| {status}{runlink(r['id'])} | {r.get('htp_sessions', '—')} | {d('short_gen_tps')} | "
                 f"{d('long_prompt_tps')} | {d('load_s')} | {yn(r.get('needle_ok'))} | {d('tools_score')} | "
                 f"{yn(r.get('json_ok'))} | {d('quiz_score')} | {d('vision_score')} | {d('vision_avg_s')} | "
                 f"{d('peak_used_mb')} | {cell(r.get('error') or '', 60) if r.get('error') else ''} |")
    return "\n".join(L)


def bench_table(R):
    B = [r for r in R.values() if r.get("kind") == "llamabench"]
    ok = [r for r in B if r.get("tg128_d0")]
    m = {k: rank([r.get(k) for r in ok]) for k in ("pp512_d0", "tg128_d0", "pp512_d2048", "tg128_d2048")}
    L = ["| Test | htp | pp512 | tg128 | pp512 @2k | tg128 @2k | Note |", "|---|---|---:|---:|---:|---:|---|"]
    for r in B:
        st = "" if r.get("tg128_d0") else "❌ "
        L.append(f"| {st}{runlink(r['id'])} | {r.get('htp_sessions', '—')} | "
                 + " | ".join(medal(r.get(k), m[k]) for k in m)
                 + f" | {cell(r.get('error') or '', 60) if r.get('error') else ''} |")
    return "\n".join(L)


def replace_table(text, heading, table):
    i = text.index(heading)
    j = text.index("\n|", i) + 1
    k = j
    while k < len(text) and text[k] == "|":
        k = text.index("\n", k) + 1
    return text[:j] + table + "\n" + text[k:]


def main():
    R = load()
    os.makedirs(REP, exist_ok=True)
    for r in R.values():
        open(f"{REP}/{r['id']}.md", "w").write(run_page(r) if is_server(r) else bench_page(r))
    q, t = matrix_pages(R)
    open(f"{REP}/quiz.md", "w").write(q)
    open(f"{REP}/tools.md", "w").write(t)
    open(f"{REP}/index.md", "w").write(index_page(R))
    s = open("README.md").read()
    s = replace_table(s, "### 4.1 Summary: best run per model", summary_table(R))
    s = replace_table(s, "### 4.3 Server tests, every run", server_table(R))
    s = replace_table(s, "### 4.4 llama-bench", bench_table(R))
    open("README.md", "w").write(s)


if __name__ == "__main__":
    main()
