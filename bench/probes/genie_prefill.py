#!/usr/bin/env python3
"""Time Genie's prompt reading: time to first streamed token for prompts of increasing length.

Prefill rate = extra prompt tokens / extra time-to-first-token between sizes, so the fixed overhead cancels out.
Streaming only and a unique `user` per request (Genie kills its model on non-streaming requests and groups
sessions by user + messages)."""
import json, sys, time, urllib.request

URL = "http://127.0.0.1:9001/v1/chat/completions"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3_4b_instruct_2507"
FILL = ("The maintenance log for the north warehouse lists routine inspections of the loading docks, "
        "the forklift batteries, the fire doors and the sprinkler valves, all marked as passed. ")

def ttft(words):
    text = (FILL * (words // len(FILL.split()) + 1))
    msg = " ".join(text.split()[:words]) + "\nReply with the single word OK."
    body = {"model": MODEL, "messages": [{"role": "user", "content": msg}], "stream": True, "max_tokens": 4,
            "temperature": 0, "user": f"prefill-{time.time_ns()}", "stream_options": {"include_usage": True}}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time(); first = None; usage = None
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            d = json.loads(line[5:])
            if d.get("usage"):
                usage = d["usage"]
            for c in d.get("choices") or []:
                if first is None and (c.get("delta") or {}).get("content"):
                    first = time.time() - t0
    return first, (usage or {}).get("prompt_tokens")

# Word counts that give 128, 512 and 2048 prompt tokens with the Qwen3 tokenizer (message text only)
SIZES = {128: 99, 512: 406, 2048: 1634}
ttft(50)   # warm-up, includes the model load
rows = []
for tokens, words in SIZES.items():
    ts = sorted(ttft(words)[0] for _ in range(3))
    t = ts[1]                                     # median of 3
    rows.append((words, tokens, t))
    print(f"tokens={tokens} words={words} ttft_s={t:.3f} (runs {', '.join(f'{x:.3f}' for x in ts)}) "
          f"pp_tps_incl_overhead={tokens / t:.0f}", flush=True)
for (w0, n0, t0), (w1, n1, t1) in zip(rows, rows[1:]):
    if n0 and n1 and t1 > t0:
        print(f"prefill {n0}->{n1} tokens: {(n1 - n0) / (t1 - t0):.0f} t/s")
