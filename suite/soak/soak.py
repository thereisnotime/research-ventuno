#!/usr/bin/env python3
"""Soak tests: one model answering requests nonstop for a set time, several configurations one after another.

The phases are listed in plan.json and run in order. Each phase starts from a fresh boot, logs one JSON line per
request (latency, t/s, ok, pinned DMA-buf, temperatures) to soak-<name>.jsonl and runs until its own deadline.
A request stuck for 5 min, or a server that dies, counts as a freeze: it is logged and the board is reset via sysrq
(never a kill of the NPU process). The unit restarts after boot and carries on with the same phase. When a phase's
time is up the next phase is selected and the board rebooted; after the last phase the unit disables itself."""
import glob, json, os, re, subprocess, threading, time, urllib.request

HOME = "/home/arduino/llm-bench/soak"
MODELS = "/home/arduino/llm-models"
PLAN, STATE = json.load(open(f"{HOME}/plan.json")), f"{HOME}/plan_state.json"
APPLAB_COMPOSE = "/var/lib/arduino-app-cli/assets/0.13.2/services/arduino/llamacpp/service_compose.yaml"
PROMPTS = [
    "Explain in detail how a home router handles NAT, DHCP, DNS and its firewall.",
    "Write a Python function that parses an ISO 8601 date and returns the weekday. Include tests.",
    'Return only JSON: {"room": str, "action": "on"|"off", "brightness": int} for: dim the kitchen lights to 30%.',
    "Summarise the causes of the First World War in five bullet points.",
    "The thermostat reads 19.5C, target 22C, outside -3C. What should the heating schedule be tonight and why?",
]
TOOLS = [{"type": "function", "function": {"name": "set_light", "description": "Set a light",
          "parameters": {"type": "object", "properties": {"room": {"type": "string"}, "brightness": {"type": "integer"}},
                         "required": ["room", "brightness"]}}}]

state = json.load(open(STATE)) if os.path.exists(STATE) else {"phase": 0}
P = PLAN[state["phase"]] if state["phase"] < len(PLAN) else None
OUT = f"{HOME}/soak-{P['name']}.jsonl" if P else f"{HOME}/soak-done.jsonl"


def log(row):
    row["ts"] = time.strftime("%F %T")
    row["uptime_s"] = int(float(open("/proc/uptime").read().split()[0]))
    open(OUT, "a").write(json.dumps(row) + "\n"); os.sync()


def pinned_mb():
    try:
        for line in open("/sys/kernel/debug/dma_buf/bufinfo"):
            m = re.match(r"Total \d+ objects, (\d+) bytes", line)
            if m:
                return int(m.group(1)) // 1048576
    except Exception:
        return None


def temps():
    t = {}
    for z in glob.glob("/sys/class/thermal/thermal_zone*"):
        try:
            n = open(f"{z}/type").read().strip()
            if n.startswith(("cpu", "nsp", "cdsp", "ddr", "gpu", "aoss-0")):
                t[n] = int(open(f"{z}/temp").read()) // 1000
        except Exception:
            pass
    return {"max_c": max(t.values(), default=None), "nsp_c": max((v for k, v in t.items() if "nsp" in k), default=None),
            "cpu_c": max((v for k, v in t.items() if k.startswith("cpu")), default=None)}


def reboot():
    for c in "sub":
        open("/proc/sysrq-trigger", "w").write(c); time.sleep(2)


def reset(reason):
    log({"event": "wedge", "reason": reason, **temps(), "pinned_mb": pinned_mb()})
    reboot()


def save_state():
    json.dump(state, open(STATE, "w")); os.sync()


if P is None:
    subprocess.run(["systemctl", "disable", "veni-soak"])
    raise SystemExit(0)
if "deadline" not in state:
    state["deadline"] = time.time() + P["hours"] * 3600
    save_state()
if time.time() > state["deadline"]:
    # Phase over: move on and reboot, so the next phase starts with a clean NPU
    log({"event": "deadline reached"})
    state = {"phase": state["phase"] + 1}
    save_state()
    if state["phase"] >= len(PLAN):
        subprocess.run(["systemctl", "disable", "veni-soak"])
        raise SystemExit(0)
    reboot()

engine = P.get("engine", "llama")
port = {"llama": 8080, "genie": 9001, "applab": 9999}[engine]
log({"event": "boot", "phase": P, **temps(), "pinned_mb": pinned_mb()})
# Only the engine under test may hold the NPU
if engine != "genie":
    subprocess.run(["docker", "compose", "-f", "/opt/genie/compose.yaml", "stop"], capture_output=True)
if engine != "applab":
    subprocess.run(["docker", "compose", "-p", "veni-applab", "-f", APPLAB_COMPOSE, "stop"], capture_output=True)
srv = None
if engine == "llama":
    model = f"{MODELS}/{P['file']}"
    if not os.path.exists(model):
        subprocess.run(["curl", "-sSfL", "-o", model + ".part", P["url"]], check=True)
        os.rename(model + ".part", model)
    llama = P.get("llama", "/home/arduino/llama-npu")
    env = dict(os.environ, LD_LIBRARY_PATH=f"{llama}/lib", ADSP_LIBRARY_PATH=f"{llama}/lib",
               GGML_HEXAGON_DEVICES="4", GGML_HEXAGON_MBUF="256,256", **P.get("env", {}))
    dev = ["-dev", "HTP0,HTP1,HTP2,HTP3", "-ngl", "99"] if P.get("dev", "npu") == "npu" else ["-dev", "none", "-ngl", "0"]
    srv = subprocess.Popen([f"{llama}/bin/llama-server", "-m", model, "--alias", "m", *dev, "-fa", "on", "-t", "4",
                            "-c", "4096", "--jinja", "--host", "0.0.0.0", "--port", str(port), "--no-webui",
                            *P.get("server_args", [])],
                           env=env, stdout=open(f"{HOME}/server-{P['name']}.log", "a"), stderr=subprocess.STDOUT)
elif engine == "genie":
    subprocess.run(["docker", "compose", "-f", "/opt/genie/compose.yaml", "up", "-d"], capture_output=True)
else:
    subprocess.run(["docker", "compose", "-p", "veni-applab", "-f", APPLAB_COMPOSE, "up", "-d"], capture_output=True)

t0 = time.time()
while True:
    try:
        if urllib.request.urlopen(f"http://127.0.0.1:{port}/{'v1/models' if engine == 'genie' else 'health'}",
                                  timeout=2).status == 200:
            break
    except Exception:
        pass
    if srv is not None and srv.poll() is not None:
        log({"event": "server exited", "rc": srv.returncode}); time.sleep(60); reset("server exit at load")
    if time.time() - t0 > 300:
        reset("load timeout")
    time.sleep(2)
log({"event": "up", "load_s": round(time.time() - t0, 1), "pinned_mb": pinned_mb()})

if P.get("kind") == "code":
    # Coding test instead of a soak: every task once, then on to the next phase. A task that hangs the board is
    # logged as a wedge row, so the resumed run after the reset skips it
    import code_bench
    done = {(r["variant"], r["task"]) for r in map(json.loads, open(OUT)) if "variant" in r}
    dog = [None]

    def arm():
        def fire():
            v, t = code_bench.CURRENT or ("?", "?")
            log({"variant": v, "task": t, "wedge": True, "hidden": False})
            reset(f"code {v} {t}: watchdog, no reply in 420 s")
        dog[0] = threading.Timer(420, fire); dog[0].daemon = True; dog[0].start()

    def row(r):
        dog[0].cancel(); log(r); arm()

    arm()
    code_bench.run(port, P.get("model", "m"), engine, row, done)
    dog[0].cancel()
    state["deadline"] = 0; save_state()
    os.execv("/usr/bin/python3", ["python3", __file__])


def request(n):
    """One streamed request. Returns (latency, ttft, tokens, gen t/s, tool call made)."""
    body = {"model": P.get("model", "m"), "messages": [{"role": "user", "content": PROMPTS[n % len(PROMPTS)]}],
            "max_tokens": 384, "temperature": 0.7, "stream": True, "user": f"soak-{time.time_ns()}"}
    if engine != "genie":
        body["chat_template_kwargs"] = {"enable_thinking": False}
    if n % 7 == 0:
        body.update(messages=[{"role": "user", "content": "Set the bedroom light to 40%."}], tools=TOOLS)
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    s = time.time(); first = None; chunks = 0; tool = False; timings = None
    with urllib.request.urlopen(req, timeout=300) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            d = json.loads(line[5:])
            timings = d.get("timings") or timings
            for c in d.get("choices") or []:
                dl = c.get("delta") or {}
                if dl.get("content") or dl.get("tool_calls"):
                    first = first or time.time()
                    chunks += 1
                tool = tool or bool(dl.get("tool_calls"))
    end = time.time()
    if timings:
        tokens, tps = timings["predicted_n"], timings["predicted_per_second"]
    else:                                 # Genie sends no timings: one streamed chunk per token
        tokens, tps = chunks, (chunks - 1) / (end - first) if first and end > first and chunks > 1 else None
    return end - s, (first - s) if first else None, tokens, tps, tool


n = state.get("n", 0)
fails = 0
while time.time() < state["deadline"]:
    n += 1
    s = time.time()
    # urlopen's timeout is per socket read, and a wedged server can leave the read blocked for hours: a wall-clock
    # watchdog resets regardless of what the socket is doing
    state["n"] = n
    dog = threading.Timer(300, lambda: (save_state(), reset(f"request {n}: watchdog, no reply in 300 s")))
    dog.daemon = True; dog.start()
    try:
        lat, ttft, tokens, tps, tool = request(n)
        dog.cancel()
        fails = 0
        log({"n": n, "ok": True, "lat_s": round(lat, 1), "ttft_s": round(ttft, 2) if ttft else None,
             "gen_tps": round(tps, 2) if tps else None, "tokens": tokens, "tool": tool if n % 7 == 0 else None,
             "pinned_mb": pinned_mb(), **temps()})
    except Exception as e:
        dog.cancel()
        fails += 1
        log({"n": n, "ok": False, "err": str(e)[:200], "lat_s": round(time.time() - s, 1), **temps()})
        if (srv is not None and srv.poll() is not None) or time.time() - s >= 290 or fails >= 3:
            state["n"] = n; save_state()
            reset(f"request {n}: {e}")
    if n % 20 == 0:
        state["n"] = n; save_state()
    time.sleep(2)
state["n"] = n; save_state()
os.execv("/usr/bin/python3", ["python3", __file__])   # handles the deadline: next phase or done
