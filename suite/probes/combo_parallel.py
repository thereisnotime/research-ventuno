#!/usr/bin/env python3
"""Two models at once: Qwen3-4B on the NPU and LFM2-8B-A1B on the CPU, each in its own llama-server.

Measures each server alone, then both generating at the same time, with the same core pinning in every phase
so the numbers are comparable: the NPU server's host threads on the A55 cores (4-7), the CPU model on the A78
cores (0-3). Run only when the suite is idle. Writes one JSON line per phase to combo_parallel.jsonl."""
import json, os, subprocess, threading, time, urllib.request

HOME = "/home/arduino"
MODELS = f"{HOME}/llm-models"
LLAMA = f"{HOME}/llama-npu-b12244"
OUT = f"{HOME}/llm-bench/tops/combo_parallel.jsonl"
NPU_M = ("Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf",
         "https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf")
CPU_M = ("LiquidAI_LFM2-8B-A1B-Q4_0.gguf",
         "https://huggingface.co/LiquidAI/LFM2-8B-A1B-GGUF/resolve/main/LFM2-8B-A1B-Q4_0.gguf")
ENV = dict(os.environ, LD_LIBRARY_PATH=f"{LLAMA}/lib", ADSP_LIBRARY_PATH=f"{LLAMA}/lib", GGML_HEXAGON_DEVICES="4")
PROMPT = "Explain in detail how a home router handles NAT, DHCP, DNS and its firewall."


def ensure(name, url):
    if not os.path.exists(f"{MODELS}/{name}"):
        subprocess.run(["curl", "-sSL", "-o", f"{MODELS}/{name}.part", url], check=True)
        os.rename(f"{MODELS}/{name}.part", f"{MODELS}/{name}")


def server(port, model, cores, dev):
    cmd = ["taskset", "-c", cores, f"{LLAMA}/bin/llama-server", "-m", f"{MODELS}/{model}", "--alias", "m",
           *dev, "-fa", "on", "-t", "4", "-c", "4096", "--host", "127.0.0.1", "--port", str(port), "--no-webui"]
    p = subprocess.Popen(cmd, env=ENV, stdout=open(f"{OUT}.{port}.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(300):
        try:
            if urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2).status == 200:
                return p
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"server on {port} did not come up")


def gen(port, n=256):
    body = {"model": "m", "messages": [{"role": "user", "content": PROMPT}], "max_tokens": n, "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=600))
    return r["timings"]["predicted_per_second"]


def phase(name, ports, reps=3):
    res = {p: [] for p in ports}
    for _ in range(reps):
        ts = [threading.Thread(target=lambda p=p: res[p].append(gen(p))) for p in ports]
        [t.start() for t in ts]
        [t.join() for t in ts]
    row = {"phase": name, **{f"port{p}_gen_tps": round(sum(v) / len(v), 2) for p, v in res.items()}}
    row["total_tps"] = round(sum(row[f"port{p}_gen_tps"] for p in ports), 2)
    print(json.dumps(row), flush=True)
    open(OUT, "a").write(json.dumps(row) + "\n")


ensure(*NPU_M)
ensure(*CPU_M)
npu = server(8080, NPU_M[0], "4-7", ["-dev", "HTP0,HTP1,HTP2,HTP3", "-ngl", "99"])
cpu = server(8081, CPU_M[0], "0-3", ["-dev", "none", "-ngl", "0"])
gen(8080, 16), gen(8081, 16)               # warm-up
phase("npu_alone (qwen3-4b, host on A55)", [8080])
phase("cpu_alone (lfm2-8b-a1b, A78)", [8081])
phase("both_at_once", [8080, 8081])
free = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout.split("\n")[1].split()
open(OUT, "a").write(json.dumps({"phase": "ram", "used_mb": int(free[2]), "total_mb": int(free[1])}) + "\n")
print("ram used MB", free[2])
# Leave the NPU server running: stopping a process with a live fastrpc session can hang; the caller reboots via sysrq
cpu.terminate()
