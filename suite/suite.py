#!/usr/bin/env python3
"""VENI overnight LLM suite. Runs as root from veni-bench.service, one item at a time.

State lives in /home/arduino/llm-bench/suite/: queue.json (items), state.json (done/failed, reboots),
results.jsonl (one line per finished item), logs/<id>.log (server/bench output).
Reboots when leaked DMA-buf passes REBOOT_MB and resumes after boot; capped at MAX_REBOOTS.
"""
import base64, io, json, os, re, statistics, subprocess, sys, threading, time, urllib.request

ROOT = os.environ.get("SUITE_ROOT", "/home/arduino/llm-bench/suite")
MODELS = "/home/arduino/llm-models"
LLAMA = "/home/arduino/llama-npu"
REBOOT_MB = 1200
MAX_REBOOTS = 60
PORT = {"llama": 8080, "genie": 9001}
KEEP = {"Qwen_Qwen3-8B-Q4_0.gguf"}
LENV = dict(os.environ, LD_LIBRARY_PATH=f"{LLAMA}/lib", ADSP_LIBRARY_PATH=f"{LLAMA}/lib",
            GGML_HEXAGON_DEVICES="1")  # was 4; 1 session since 2026-11-09 to test the hangs
NPU = ["-dev", "HTP0", "-ngl", "99"]


def htp(item):
    """Per-item NPU session count: 8B+ models can't map their weights on a single session."""
    n = int(item.get("sessions", 4))
    return n, dict(LENV, GGML_HEXAGON_DEVICES=str(n)), ["-dev", ",".join(f"HTP{i}" for i in range(n)), "-ngl", "99"]
CPU = ["-dev", "none", "-ngl", "0"]


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(f"{ROOT}/driver.log", "a") as f:
        f.write(line + "\n")


def jload(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def jsave(p, d):
    json.dump(d, open(p + ".tmp", "w"), indent=1)
    os.replace(p + ".tmp", p)


def pinned_mb():
    for line in open("/sys/kernel/debug/dma_buf/bufinfo"):
        m = re.match(r"Total \d+ objects, (\d+) bytes", line)
        if m:
            return int(m.group(1)) // 1048576
    return 0


def meminfo():
    d = {}
    for line in open("/proc/meminfo"):
        k, v = line.split(":")
        d[k] = int(v.split()[0]) // 1024
    return d


class Sampler(threading.Thread):
    """Peak RAM used (total - available) and peak pinned DMA-buf while an item runs."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop_ev = threading.Event()
        self.peak_used = 0
        self.peak_pinned = 0

    def run(self):
        while not self.stop_ev.is_set():
            m = meminfo()
            self.peak_used = max(self.peak_used, m["MemTotal"] - m["MemAvailable"])
            self.peak_pinned = max(self.peak_pinned, pinned_mb())
            time.sleep(0.5)


# ---------------------------------------------------------------- downloads

def ensure(files):
    for name, url in files:
        p = f"{MODELS}/{name}"
        if os.path.exists(p) and not os.path.exists(p + ".part"):
            continue
        log(f"download {name}")
        open(p + ".part", "w").close()
        r = subprocess.run(["curl", "-sfL", "--retry", "5", "-C", "-", "-o", p, url])
        if r.returncode:
            raise RuntimeError(f"download failed {name} rc={r.returncode}")
        os.remove(p + ".part")
        subprocess.run(["chown", "arduino:arduino", p])


def cleanup(queue, state):
    """Delete GGUFs no pending item needs."""
    pending = [i for i in queue if i["id"] not in state["done"]]
    needed = {n for i in pending for n, _ in i.get("files", [])}
    for f in os.listdir(MODELS):
        if f.endswith(".gguf") and f not in needed and f not in KEEP:
            log(f"delete {f}")
            os.remove(f"{MODELS}/{f}")


# ---------------------------------------------------------------- servers

def wait_health(url, proc, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc is not None and proc.poll() is not None:
            return None
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status == 200:
                    return time.time() - t0
        except Exception:
            pass
        time.sleep(2)
    return None


def start_server(item, logf):
    if item["engine"] == "genie":
        subprocess.run(["docker", "compose", "-f", "/opt/genie/compose.yaml", "up", "-d"],
                       stdout=logf, stderr=logf)
        # Genie loads the model on first request; health only means the API is up
        return None, wait_health("http://127.0.0.1:9001/v1/models", None, 120)
    m = item["files"][0][0]
    cmd = ["taskset", "-c", "0-3", f"{LLAMA}/bin/llama-server", "-m", f"{MODELS}/{m}",
           "--alias", item["model"], *(htp(item)[2] if item["dev"] == "npu" else CPU),
           "-fa", "on", "-t", "4", "-c", str(item.get("ctx", 4096)), "--jinja",
           "--host", "0.0.0.0", "--port", "8080", "--no-webui"]
    if item.get("mmproj"):
        # Image encoder on CPU: on the NPU it fails to map its ~800 MB buffer (fastrpc_mmap)
        cmd += ["--mmproj", f"{MODELS}/{item['mmproj']}", "--no-mmproj-offload"]
    proc = subprocess.Popen(cmd, env=htp(item)[1], stdout=logf, stderr=subprocess.STDOUT)
    return proc, wait_health("http://127.0.0.1:8080/health", proc)


def stop_server(item, proc, logf):
    if item["engine"] == "genie":
        subprocess.run(["docker", "compose", "-f", "/opt/genie/compose.yaml", "stop"],
                       stdout=logf, stderr=logf)
        return
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(60)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(30)


# ---------------------------------------------------------------- client

def transcript(item, body, reply):
    """Every request and reply, so failed cases can be read back later (images elided)."""
    def strip(m):
        if isinstance(m.get("content"), list):
            m = dict(m, content=[c if c.get("type") != "image_url" else {"type": "image_url", "image_url": "<elided>"}
                                 for c in m["content"]])
        return m
    rec = {"t": time.strftime("%T"), "request": dict(body, messages=[strip(m) for m in body["messages"]]),
           "reply": reply}
    with open(f"{ROOT}/logs/{item['id']}.transcript.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")


def chat(item, messages, stream=False, timeout=600, **kw):
    body = {"model": item["model"], "messages": messages, "stream": stream,
            "max_tokens": kw.pop("max_tokens", 512), "temperature": 0}
    if item["engine"] == "llama":
        # Hybrid thinkers (Qwen3) answer directly; reasoning is out of scope for this suite
        body["chat_template_kwargs"] = {"enable_thinking": False}
    else:
        # Genie groups requests into sessions by user + messages; repeated prompts pile into one
        # history whose eviction/fact extraction crashes the LLM process. One session per request.
        body["user"] = f"suite-{time.time_ns()}"
    body.update(kw)
    req = urllib.request.Request(f"http://127.0.0.1:{PORT[item['engine']]}/v1/chat/completions",
                                 json.dumps(body).encode(), {"Content-Type": "application/json"})
    if not stream and item["engine"] == "genie":
        body["stream"] = True
        req = urllib.request.Request(req.full_url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        text, calls = "", {}
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                for line in r:
                    line = line.decode().strip()
                    if not line.startswith("data:") or line == "data: [DONE]":
                        continue
                    for c in json.loads(line[5:]).get("choices", []):
                        dl = c.get("delta") or {}
                        text += dl.get("content") or ""
                        for tc in dl.get("tool_calls") or []:
                            cur = calls.setdefault(tc.get("index", 0), {"type": "function", "function": {"name": "", "arguments": ""}})
                            cur["id"] = tc.get("id", cur.get("id"))
                            f = tc.get("function") or {}
                            cur["function"]["name"] += f.get("name") or ""
                            cur["function"]["arguments"] += f.get("arguments") or ""
        except Exception as e:
            transcript(item, body, {"error": str(e)[:300]})
            raise
        msg = {"role": "assistant", "content": text}
        if calls:
            msg["tool_calls"] = [calls[k] for k in sorted(calls)]
        resp = {"choices": [{"message": msg}]}
        transcript(item, body, resp)
        return resp
    if not stream:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.load(r)
        except Exception as e:
            transcript(item, body, {"error": str(e)[:300]})
            raise
        transcript(item, body, resp)
        return resp
    t0 = time.time()
    first = last = None
    chunks = 0
    usage = timings = None
    text = ""
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            d = json.loads(line[5:])
            usage = d.get("usage") or usage
            timings = d.get("timings") or timings
            for c in d.get("choices", []):
                piece = (c.get("delta") or {}).get("content")
                if piece:
                    chunks += 1
                    text += piece
                    last = time.time()
                    first = first or last
    res = {"ttft_s": round(first - t0, 3) if first else None, "text": text}
    transcript(item, body, {"text": text, "usage": usage, "timings": timings})
    if timings:
        res.update(prompt_n=timings.get("prompt_n"), prompt_tps=round(timings["prompt_per_second"], 2),
                   gen_n=timings.get("predicted_n"), gen_tps=round(timings["predicted_per_second"], 2))
    else:
        n = (usage or {}).get("completion_tokens") or chunks
        res.update(prompt_n=(usage or {}).get("prompt_tokens"), gen_n=n,
                   gen_tps=round((n - 1) / (last - first), 2) if first and last > first else None)
        if res["prompt_n"] and res["ttft_s"]:
            res["prompt_tps"] = round(res["prompt_n"] / res["ttft_s"], 2)
    return res


def msg_text(resp):
    m = resp["choices"][0]["message"]
    return (m.get("content") or "").strip(), m.get("tool_calls") or []


# ---------------------------------------------------------------- tests

FILLER = ("The maintenance log for the north warehouse lists routine inspections of the loading docks, "
          "conveyor belts, fire doors and lighting. Each entry notes the inspector, the date and any "
          "follow-up work. Most entries report no issues beyond worn rubber seals and dusty sensors. ")


def test_speed(item):
    out = {}
    short = "Explain in detail how a home router handles NAT, DHCP, DNS and its firewall."
    runs = [chat(item, [{"role": "user", "content": short}], stream=True, max_tokens=256) for _ in range(4)]
    out["cold_ttft_s"] = runs[0]["ttft_s"]
    warm = runs[1:]
    for k in ("ttft_s", "prompt_tps", "gen_tps"):
        vals = [r.get(k) for r in warm if r.get(k)]
        out[f"short_{k}"] = round(statistics.median(vals), 2) if vals else None
    out["short_gen_n"] = warm[-1].get("gen_n")
    # Long prompt (~2.5k tokens) with a needle: prefill speed + retrieval in one go
    hay = FILLER * 34
    cut = len(hay) * 2 // 3
    needle = " Note from the night shift: the spare key for the server room is in locker 4417. "
    doc = hay[:cut] + needle + hay[cut:]
    q = doc + "\n\nQuestion: which locker holds the spare key for the server room? Answer with the number only."
    r = chat(item, [{"role": "user", "content": q}], stream=True, max_tokens=24)
    out.update(long_prompt_n=r.get("prompt_n"), long_ttft_s=r["ttft_s"], long_prompt_tps=r.get("prompt_tps"),
               needle_ok="4417" in r["text"])
    return out


TOOLS = [
    {"type": "function", "function": {"name": "get_weather", "description": "Current weather for a city",
     "parameters": {"type": "object", "properties": {"city": {"type": "string"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "search_flights", "description": "Search flights",
     "parameters": {"type": "object", "properties": {"origin": {"type": "string"},
                    "destination": {"type": "string"}, "date": {"type": "string", "description": "YYYY-MM-DD"}},
                    "required": ["origin", "destination", "date"]}}},
    {"type": "function", "function": {"name": "calculator", "description": "Evaluate an arithmetic expression",
     "parameters": {"type": "object", "properties": {"expression": {"type": "string"}},
                    "required": ["expression"]}}},
    {"type": "function", "function": {"name": "send_email", "description": "Send an email",
     "parameters": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"},
                    "body": {"type": "string"}}, "required": ["to", "subject", "body"]}}},
]


def _calls(resp):
    _, tcs = msg_text(resp)
    out = []
    for tc in tcs:
        f = tc.get("function", {})
        try:
            args = json.loads(f.get("arguments") or "{}")
        except Exception:
            args = None
        out.append((f.get("name"), args))
    return out


def test_tools(item):
    U = lambda s: [{"role": "user", "content": s}]
    cases = {}

    def run(name, msgs, check):
        try:
            resp = chat(item, msgs, tools=TOOLS, max_tokens=300)
            cases[name] = bool(check(resp))
        except Exception as e:
            cases[name] = False
            cases[name + "_err"] = str(e)[:120]

    lc = lambda v: str(v or "").lower()
    run("weather", U("What's the weather in Sofia right now, in celsius?"),
        lambda r: any(n == "get_weather" and a and "sofia" in lc(a.get("city")) and a.get("unit") == "celsius"
                      for n, a in _calls(r)))
    run("flights", U("Find me flights from London to Tokyo on 24 December 2026."),
        lambda r: any(n == "search_flights" and a and "london" in lc(a.get("origin"))
                      and "tokyo" in lc(a.get("destination")) and a.get("date") == "2026-12-24" for n, a in _calls(r)))
    run("calculator", U("Use the calculator to compute 1234 * 5678."),
        lambda r: any(n == "calculator" and a and "1234" in lc(a.get("expression")) and "5678" in lc(a.get("expression"))
                      for n, a in _calls(r)))
    run("email", U("Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late."),
        lambda r: any(n == "send_email" and a and lc(a.get("to")) == "bob@example.com" and "lunch" in lc(a.get("subject"))
                      for n, a in _calls(r)))
    run("no_tool", U("Tell me a short joke about cats."),
        lambda r: not _calls(r) and len(msg_text(r)[0]) > 10)
    run("parallel", U("What's the weather in Paris and in Berlin?"),
        lambda r: {lc(a.get("city")).split(",")[0] for n, a in _calls(r) if n == "get_weather" and a} >= {"paris", "berlin"})
    # Real two-step flow with the model's own call id: Genie tracks pending calls server-side and
    # times out (408) on a made-up id
    try:
        first = chat(item, U("What's the weather in Oslo?"), tools=TOOLS, max_tokens=300)
        tc = ((first.get("choices") or [{}])[0].get("message") or {}).get("tool_calls") or []
        tc = [c for c in tc if (c.get("function") or {}).get("name") == "get_weather"][:1]
    except Exception as e:
        tc = []
        cases["use_result_err"] = "first call: " + str(e)[:100]
    if tc:
        cid = tc[0].get("id") or "call_1"
        hist = U("What's the weather in Oslo?") + [
            {"role": "assistant", "content": None, "tool_calls": [dict(tc[0], id=cid)]},
            {"role": "tool", "tool_call_id": cid, "content": json.dumps({"temp_c": 7, "condition": "light rain"})}]
        run("use_result", hist, lambda r: not _calls(r) and "7" in msg_text(r)[0] and "rain" in msg_text(r)[0].lower())
    else:
        cases["use_result"] = False
        cases.setdefault("use_result_err", "no get_weather call to answer")
    score = sum(v for k, v in cases.items() if not k.endswith("_err"))
    return {"tools_score": f"{score}/7", "tools": cases}


def test_json(item):
    schema = {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"},
              "hobbies": {"type": "array", "items": {"type": "string"}}}, "required": ["name", "age", "hobbies"]}
    try:
        r = chat(item, [{"role": "user", "content": "Extract the person: Maria is 34 and loves climbing, chess and baking."}],
                 response_format={"type": "json_schema", "json_schema": {"name": "person", "schema": schema}},
                 max_tokens=200)
        d = json.loads(msg_text(r)[0])
        ok = d.get("name", "").lower().startswith("maria") and d.get("age") == 34 and len(d.get("hobbies", [])) == 3
        return {"json_ok": bool(ok)}
    except Exception as e:
        return {"json_ok": False, "json_err": str(e)[:120]}


QUIZ = [
    ("What is 17 * 23?", r"\b391\b"),
    ("A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)?", r"17:15"),
    ("What is the capital of Australia?", r"canberra"),
    ("How many times does the letter r appear in the word strawberry?", r"\b(3|three)\b"),
    ("Sort these numbers ascending: 5, 2, 9, 1", r"1\D+2\D+5\D+9"),
    ("Alice is older than Bob. Bob is older than Carol. Who is the youngest?", r"carol"),
    ("Translate 'good morning' into Spanish.", r"buenos d[ií]as"),
    ("What number comes next: 2, 6, 12, 20, 30, ?", r"\b42\b"),
    ("What is the chemical symbol for gold?", r"\bau\b"),
    ("A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost?", r"\b(5|five)\b"),
    ("In what year did World War II end?", r"1945"),
    ("Write the word 'stressed' backwards.", r"desserts"),
]


def test_quiz(item):
    res = []
    for q, pat in QUIZ:
        try:
            a, _ = msg_text(chat(item, [{"role": "user", "content": q + " Answer briefly."}], max_tokens=200))
            res.append(bool(re.search(pat, a.lower())))
        except Exception:
            res.append(False)
    return {"quiz_score": f"{sum(res)}/{len(res)}", "quiz": res}


def _img(draw_fn):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (448, 448), "white")
    d = ImageDraw.Draw(im)
    draw_fn(d, ImageFont)
    b = io.BytesIO()
    im.save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def test_vision(item):
    def font(F, size):
        for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",):
            if os.path.exists(p):
                return F.truetype(p, size)
        return F.load_default()

    imgs = [
        ("What text is written in this image? Reply with the text only.",
         _img(lambda d, F: d.text((40, 180), "VENI 7429", fill="black", font=font(F, 72))), r"veni\s*7429"),
        ("How many green circles are in this image? Answer with a number.",
         _img(lambda d, F: [d.ellipse((30 + 80 * i, 190, 90 + 80 * i, 250), fill="green") for i in range(5)]), r"\b(5|five)\b"),
        ("What colour is the square and what colour is the circle?",
         _img(lambda d, F: (d.rectangle((40, 140, 200, 300), fill="red"), d.ellipse((250, 140, 410, 300), fill="blue"))),
         r"(?=.*red)(?=.*blue)"),
        ("Is the arrow pointing left or right? Answer with one word.",
         _img(lambda d, F: (d.rectangle((80, 200, 300, 248), fill="black"),
                            d.polygon([(300, 150), (400, 224), (300, 298)], fill="black"))), r"\bright\b"),
    ]
    res = []
    times = []
    for q, url, pat in imgs:
        try:
            t0 = time.time()
            a, _ = msg_text(chat(item, [{"role": "user", "content": [
                {"type": "text", "text": q}, {"type": "image_url", "image_url": {"url": url}}]}], max_tokens=60))
            times.append(time.time() - t0)
            res.append(bool(re.search(pat, a.lower())))
        except Exception as e:
            res.append(False)
            log(f"vision err {str(e)[:100]}")
    return {"vision_score": f"{sum(res)}/{len(res)}", "vision": res,
            "vision_avg_s": round(statistics.mean(times), 1) if times else None}


# ---------------------------------------------------------------- items

def run_llamabench(item, logf):
    m = item["files"][0][0]
    dev = ["-dev", "/".join(f"HTP{i}" for i in range(htp(item)[0])), "-ngl", "99"] if item["dev"] == "npu" else ["-dev", "none", "-ngl", "0"]
    cmd = ["taskset", "-c", "0-3", f"{LLAMA}/bin/llama-bench", "-m", f"{MODELS}/{m}", *dev, "-fa", "1", "-t", "4",
           "-p", "512", "-n", "128", "-d", item.get("depths", "0,2048"), "-r", "3", "-o", "json"]
    p = subprocess.Popen(cmd, env=htp(item)[1], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        so, se = p.communicate(timeout=900)
    except subprocess.TimeoutExpired:
        # Killing a process stuck on the NPU risks freezing the board: leave it, stop the suite
        log(f"{item['id']} over 15 min, NPU likely wedged; not killing, stopping suite")
        subprocess.run(["systemctl", "disable", "veni-bench"])
        os._exit(3)
    r = subprocess.CompletedProcess(cmd, p.returncode, so, se)
    logf.write(r.stderr[-20000:])
    if r.returncode:
        raise RuntimeError(f"llama-bench rc={r.returncode}: {r.stderr.strip().splitlines()[-1:]}")
    out = {}
    for row in json.loads(r.stdout):
        kind = "pp512" if row["n_prompt"] else "tg128"
        out[f"{kind}_d{row['n_depth']}"] = round(row["avg_ts"], 2)
    return out


ENV_PKGS = ["linux-image-{kernel}", "linux-firmware", "linux-firmware-dragonwing", "qcom-fastrpc1", "arduino-app-cli"]


def env_snapshot(item):
    """Everything under the model that can change a result: kernel, boot args, firmware, NPU userspace, engine build."""
    sh = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
    kernel = os.uname().release
    env = {"kernel": kernel, "cmdline": open("/proc/cmdline").read().strip(),
           "packages": {}, "cdsp_fw_sha256": sh("sha256sum /lib/firmware/updates/qcom/qcs8300/cdsp0.mbn | cut -c1-16")}
    for pkg in ENV_PKGS:
        pkg = pkg.format(kernel=kernel)
        env["packages"][pkg] = sh(f"dpkg-query -W -f='${{Version}}' {pkg} 2>/dev/null") or None
    if item["engine"] == "llama":
        env["llama_build"] = os.path.basename(LLAMA)
        v = sh(f"LD_LIBRARY_PATH={LLAMA}/lib {LLAMA}/bin/llama-server --version 2>&1")
        m = re.search(r"commit ([0-9a-f]+)", v)
        env["llama_commit"] = m.group(1) if m else None
        env["llama_version"] = (re.search(r"version: (\S+)", v) or [None, None])[1]
    else:
        env["genie_image"] = sh("grep -m1 'image:' /opt/genie/compose.yaml | awk '{print $2}'")
    return env


def run_item(item):
    # Optional per-item llama.cpp build, e.g. "llama": "/home/arduino/llama-npu-b12244"
    global LLAMA, LENV
    LLAMA = item.get("llama", "/home/arduino/llama-npu")
    LENV = dict(LENV, LD_LIBRARY_PATH=f"{LLAMA}/lib", ADSP_LIBRARY_PATH=f"{LLAMA}/lib")
    os.makedirs(f"{ROOT}/logs", exist_ok=True)
    ensure(item.get("files", []))
    res = {"id": item["id"], "engine": item["engine"], "model": item["model"], "dev": item.get("dev"),
           "kind": item["kind"], "htp_sessions": htp(item)[0] if item.get("dev") == "npu" else 0, "started": time.strftime("%F %T"), "pinned_before_mb": pinned_mb(), "llama_build": os.path.basename(LLAMA), "env": env_snapshot(item)}
    s = Sampler()
    s.start()
    with open(f"{ROOT}/logs/{item['id']}.log", "a") as logf:
        try:
            if item["kind"] == "llamabench":
                res.update(run_llamabench(item, logf))
            else:
                proc, load_s = start_server(item, logf)
                # A wedged server (Granite H Tiny spun 20 min on one request) must not stall the night
                guard = threading.Timer(1800, lambda: proc and proc.kill())
                guard.start()
                try:
                    if load_s is None:
                        raise RuntimeError("server did not become healthy")
                    res["load_s"] = round(load_s, 1)
                    res.update(test_speed(item))
                    res.update(test_tools(item))
                    res.update(test_json(item))
                    res.update(test_quiz(item))
                    if item.get("vision"):
                        res.update(test_vision(item))
                finally:
                    guard.cancel()
                    stop_server(item, proc, logf)
            res["ok"] = True
        except Exception as e:
            res["ok"] = False
            res["error"] = str(e)[:300]
    time.sleep(5)
    s.stop_ev.set()
    s.join()
    res.update(peak_used_mb=s.peak_used, peak_pinned_mb=s.peak_pinned, pinned_after_mb=pinned_mb(),
               finished=time.strftime("%F %T"))
    return res


def main():
    queue = jload(f"{ROOT}/queue.json", [])
    state = jload(f"{ROOT}/state.json", {"done": {}, "reboots": 0})
    while True:
        queue = jload(f"{ROOT}/queue.json", queue)  # picks up items added while running
        pending = [i for i in queue if i["id"] not in state["done"]]
        if not pending:
            log("queue finished")
            break
        item = pending[0]
        p = pinned_mb()
        # fresh: items that need the whole NPU (8B+) reboot unless almost nothing is pinned
        if p > (200 if item.get("fresh") else REBOOT_MB):
            if state["reboots"] >= MAX_REBOOTS:
                log(f"pinned {p} MB but reboot cap reached, stopping")
                break
            if state.get("last_reboot_item") == item["id"]:
                # Fresh boot and still over the limit: record and move on instead of looping
                log(f"pinned {p} MB right after reboot, skipping {item['id']}")
                state["done"][item["id"]] = "skipped-pinned"
                jsave(f"{ROOT}/state.json", state)
                continue
            state["reboots"] += 1
            state["last_reboot_item"] = item["id"]
            jsave(f"{ROOT}/state.json", state)
            log(f"pinned {p} MB > {REBOOT_MB}, reboot {state['reboots']}/{MAX_REBOOTS}")
            # Hard reset via sysrq: a normal reboot tears down fastrpc and can hang there forever
            os.sync()
            for k in "sub":
                with open("/proc/sysrq-trigger", "w") as f:
                    f.write(k)
                time.sleep(2)
            time.sleep(600)
            return
        # Mark as started first: an item that hangs the board is never retried after the reboot
        state["done"][item["id"]] = "started"
        jsave(f"{ROOT}/state.json", state)
        log(f"start {item['id']} (pinned {p} MB)")
        res = run_item(item)
        with open(f"{ROOT}/results.jsonl", "a") as f:
            f.write(json.dumps(res) + "\n")
        state["done"][item["id"]] = "ok" if res["ok"] else "failed"
        if not res["ok"] and item["kind"] == "llamabench" and "depths" not in item:
            # depth 2048 needs more NPU mapping than the model alone; retry at depth 0 on a fresh boot
            queue = jload(f"{ROOT}/queue.json", queue)
            if not any(i["id"] == item["id"] + ".d0" for i in queue):
                queue.append(dict(item, id=item["id"] + ".d0", depths="0", fresh=True))
                jsave(f"{ROOT}/queue.json", queue)
        jsave(f"{ROOT}/state.json", state)
        log(f"end {item['id']} ok={res['ok']} {res.get('error', '')}")
        cleanup(queue, state)
    subprocess.run(["systemctl", "disable", "veni-bench.service"])
    subprocess.run(["chown", "-R", "arduino:arduino", ROOT])


if __name__ == "__main__":
    main()
