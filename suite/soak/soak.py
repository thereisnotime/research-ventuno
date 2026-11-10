#!/usr/bin/env python3
"""Soak test: Qwen3-4B on the NPU (MBUF 256) answering requests nonstop until a deadline.

Logs one JSON line per request (latency, t/s, ok, pinned DMA-buf, temperatures). A request stuck for 5 min
counts as a wedge: it is logged, then the board is reset via sysrq (no kill of the NPU process). The unit
restarts after boot and carries on until the deadline in soak.deadline, then disables itself."""
import glob, json, os, subprocess, time, urllib.request

HOME = "/home/arduino/llm-bench/soak"
LLAMA = "/home/arduino/llama-npu"
MODEL = "/home/arduino/llm-models/Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf"
OUT, DL = f"{HOME}/soak.jsonl", f"{HOME}/soak.deadline"
if not os.path.exists(DL):  # 12 h from the first start
    open(DL, "w").write(str(time.time() + 12 * 3600))
DEADLINE = float(open(DL).read())
ENV = dict(os.environ, LD_LIBRARY_PATH=f"{LLAMA}/lib", ADSP_LIBRARY_PATH=f"{LLAMA}/lib",
           GGML_HEXAGON_DEVICES="4", GGML_HEXAGON_MBUF="256,256")
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


def log(row):
    row["ts"] = time.strftime("%F %T")
    open(OUT, "a").write(json.dumps(row) + "\n"); os.sync()


def pinned_mb():
    try:
        return round(sum(int(l.split()[0]) for l in open("/sys/kernel/debug/dma_buf/bufinfo") if l.strip()[:1].isdigit() and len(l.split()) > 3) / 2**20)
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


def reset(reason):
    log({"event": "wedge", "reason": reason, **temps(), "pinned_mb": pinned_mb()})
    for c in "sub":
        open("/proc/sysrq-trigger", "w").write(c); time.sleep(2)


def finish():
    log({"event": "deadline reached"})
    subprocess.run(["systemctl", "disable", "veni-soak"])
    raise SystemExit(0)


if time.time() > DEADLINE:
    finish()
if not os.path.exists(MODEL):
    subprocess.run(["curl", "-sSfL", "-o", MODEL + ".part", "https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf"], check=True)
    os.rename(MODEL + ".part", MODEL)
log({"event": "boot", "uptime_s": int(float(open("/proc/uptime").read().split()[0])), **temps(), "pinned_mb": pinned_mb()})
srv = subprocess.Popen([f"{LLAMA}/bin/llama-server", "-m", MODEL, "--alias", "m", "-dev", "HTP0,HTP1,HTP2,HTP3",
                        "-ngl", "99", "-fa", "on", "-t", "4", "-c", "4096", "--jinja", "--host", "0.0.0.0",
                        "--port", "8080", "--no-webui"], env=ENV, stdout=open(f"{HOME}/server.log", "a"),
                       stderr=subprocess.STDOUT)
t0 = time.time()
while True:
    try:
        if urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2).status == 200:
            break
    except Exception:
        pass
    if srv.poll() is not None:
        log({"event": "server exited", "rc": srv.returncode}); time.sleep(60); reset("server exit at load")
    if time.time() - t0 > 300:
        reset("load timeout")
    time.sleep(2)
log({"event": "loaded", "load_s": round(time.time() - t0, 1), "pinned_mb": pinned_mb()})
n = 0
while time.time() < DEADLINE:
    n += 1
    body = {"model": "m", "messages": [{"role": "user", "content": PROMPTS[n % len(PROMPTS)]}], "max_tokens": 384,
            "temperature": 0.7}
    if n % 7 == 0:
        body.update(messages=[{"role": "user", "content": "Set the bedroom light to 40%."}], tools=TOOLS)
    req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    s = time.time()
    try:
        r = json.load(urllib.request.urlopen(req, timeout=300))
        tm = r["timings"]
        log({"n": n, "ok": True, "lat_s": round(time.time() - s, 1), "gen_tps": round(tm["predicted_per_second"], 2),
             "pp_tps": round(tm["prompt_per_second"], 1), "tokens": tm["predicted_n"],
             "tool": bool(r["choices"][0]["message"].get("tool_calls")) if n % 7 == 0 else None,
             "pinned_mb": pinned_mb(), **temps()})
    except Exception as e:
        if srv.poll() is not None or time.time() - s >= 290:
            reset(f"request {n}: {e}")
        log({"n": n, "ok": False, "err": str(e)[:200], "lat_s": round(time.time() - s, 1), **temps()})
    time.sleep(2)
finish()
