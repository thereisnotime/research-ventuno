# Reproducing the tests on your own board

Everything in this repo was measured on one Arduino VENTUNO Q. This page lists what you need to run the same tests
on yours and compare. The scripts assume the default `arduino` user and these paths on the board:

| Path | What |
|---|---|
| `~/llama-npu/` | llama.cpp build with the Hexagon (NPU) backend: `bin/`, `lib/` |
| `~/llm-models/` | GGUF model files (the scripts download what is missing) |
| `~/llm-bench/suite/` | Main suite: `suite.py`, `queue.json`, results |
| `~/llm-bench/soak/` | Soak and coding tests: `soak.py`, `code_bench.py`, `plan.json`, `HumanEval.jsonl` |

If your paths differ, change the constants at the top of each script (`ROOT`, `MODELS`, `LLAMA`, `HOME`).

## 1. Check your board matches

Compare against [§2 of the README](../README.md#2-test-environment) and [environments.md](../reports/environments.md):

```bash
uname -r                                     # tested: 6.8.0-1089-qcom
cat /etc/os-release | grep -E 'VERSION=|BUILD_ID'
dpkg -l linux-firmware-dragonwing qcom-fastrpc1 arduino-app-cli | grep ^ii
ls /dev/fastrpc-cdsp* /dev/dma_heap/system   # the NPU device nodes
sudo cat /sys/kernel/debug/dma_buf/bufinfo | tail -1   # pinned NPU memory; the scripts log this
```

`linux-firmware-dragonwing 20260825` broke NPU memory mapping on our board; we run the 20260612 DSP firmware files
([board-notes.md](board-notes.md)). If your NPU fails every load with `fastrpc_mmap failed`, check this first.

## 2. Safety setup before long runs

The NPU can freeze the whole board ([§5](../README.md#5-stability-findings)). The unattended runs depend on:

- **Never kill a stuck NPU process** (`kill -9` on a process inside a fastrpc call can hang the kernel).
  Reset with sysrq instead, which is what the scripts do (Ubuntu's default `kernel.sysrq = 176` allows these three):

  ```bash
  sudo sh -c 'echo s > /proc/sysrq-trigger; sleep 2; echo u > /proc/sysrq-trigger; sleep 2; echo b > /proc/sysrq-trigger'
  ```

- **Hardware watchdog and hung-task panic**, so a frozen kernel reboots by itself:

  ```bash
  # /etc/systemd/system.conf
  RuntimeWatchdogSec=30s
  # /etc/sysctl.d/90-hung.conf
  kernel.hung_task_timeout_secs = 120
  kernel.hung_task_panic = 1
  kernel.panic = 10
  ```

  and add `watchdog.stop_on_reboot=0` to the kernel command line. Details and the reasons for each are in
  [stability-fixes.md](stability-fixes.md).

- **No real-time clock:** timestamps jump at every reboot. The scripts also log `uptime_s`; use that or the
  request number when you compare runs.

## 3. llama.cpp with the NPU backend

**Prebuilt (main results, build `7fe450e`):** release `v0.1-7fe450e` of
[ThinkOffApp/ventuno](https://github.com/ThinkOffApp/ventuno), file `pkg-linux-7fe450e.tgz`. Its
`build/install-on-ventuno.sh` untars into `~/llama-npu` and links the system `libcdsprpc.so`; no sudo needed.

**Build it yourself (newer build `d5bbcd1`, §4.6):** cross-compile on an x86 machine with Qualcomm's toolchain image,
following llama.cpp's `docs/backend/snapdragon` guide:

```bash
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp && git checkout d5bbcd1
docker run --rm -u $(id -u):$(id -g) -v $PWD:/w -w /w ghcr.io/snapdragon-toolchain/arm64-linux:v0.8 \
  sh -c 'cmake --preset arm64-linux-snapdragon-release -B build-snapdragon &&
         cmake --build build-snapdragon -j && cmake --install build-snapdragon --prefix pkg'
rsync -a pkg/ arduino@<board>:llama-npu-d5bbcd1/
```

**Smoke test on the board:**

```bash
D=~/llama-npu; export LD_LIBRARY_PATH=$D/lib ADSP_LIBRARY_PATH=$D/lib
export GGML_HEXAGON_DEVICES=4 GGML_HEXAGON_MBUF=256,256
$D/bin/llama-bench -m ~/llm-models/Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf \
  -dev HTP0/HTP1/HTP2/HTP3 -ngl 99 -t 4 -fa 1 -p 512 -n 128 -r 2
```

Expect roughly 445 t/s for `pp512` and 13 t/s for `tg128` ([Table 3](../README.md#44-llama-bench)).

**Server, as used in every test:**

```bash
taskset -c 0-3 $D/bin/llama-server -m ~/llm-models/Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf --alias m \
  -dev HTP0,HTP1,HTP2,HTP3 -ngl 99 -fa on -t 4 -c 4096 --jinja --host 0.0.0.0 --port 8080 --no-webui
```

Settings worth knowing:

| Setting | Value used | Why |
|---|---|---|
| `GGML_HEXAGON_DEVICES` / `-dev` | 4 sessions | One NPU session can address about 3.1 GiB; 4B models need several |
| `GGML_HEXAGON_MBUF` | `256,256` (from §4.11) | Removes the random `fastrpc_mmap failed` at load, no speed cost |
| `-c` | 4096 | 8192 runs out of NPU-mappable memory |
| `-np` | default (4 slots), `1` in the soak and coding tests | `-np 1` was the only setting with no freeze in a 4 h soak |
| `-t`, `taskset` | 4 threads on cores 0-3 | The A78 cores |
| CPU runs | `-dev none -ngl 0` | Same binary, no NPU |

Models are Q4_0 GGUFs; the exact URLs are in [`results/queue.json`](../results/queue.json) (`files` of each item).

## 4. Genie (Qualcomm's runtime) and Arduino App Lab

Genie bundles come with `arduino-app-cli`, or download one with Arduino's downloader container
([board-notes.md](board-notes.md#genie-llm-api-on-the-lan-2026-11-08)). Start the service with the tested settings:

```bash
sudo docker compose -f suite/genie-compose.yaml up -d
curl -s localhost:9001/v1/models            # ready when this answers; /health does not exist
```

Genie needs streamed requests and a fresh `user` value per request (see the comments in the compose file).
Starting Genie leaves NPU memory pinned, so reboot before going back to llama.cpp.

App Lab's own llama.cpp service (Gemma 4 E4B) is started from its shipped compose file, copied as tested in
[`suite/applab-llamacpp-service_compose.yaml`](../suite/applab-llamacpp-service_compose.yaml):

```bash
arduino-app-cli model install gemma-4-E4B_q4_0-it
sudo docker compose -p veni-applab -f /var/lib/arduino-app-cli/assets/0.13.2/services/arduino/llamacpp/service_compose.yaml up -d
curl -s localhost:9999/health
```

## 5. Main suite (tables in §4.1-4.5)

`suite/suite.py` runs a queue one item at a time as root, reboots itself when leaked NPU memory passes a limit, and
resumes after boot. A queue item:

```json
{"id": "qwen3-4b-2507.npu.server", "engine": "llama", "model": "qwen3-4b-2507", "kind": "server", "dev": "npu",
 "files": [["Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf",
            "https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf"]]}
```

`kind` is `server` (speed, tools, JSON, quiz, needle, optional `vision`) or `llamabench`; `engine` is `llama`,
`genie` or `applab`. Optional keys: `env`, `server_args`, `sessions`, `ctx`, `llama` (another build directory),
`mmproj`. Copy items from [`results/queue.json`](../results/queue.json) to rerun ours.

```bash
mkdir -p ~/llm-bench/suite ~/llm-models
cp suite/suite.py ~/llm-bench/suite/ && cp my-queue.json ~/llm-bench/suite/queue.json
sudo cp suite/veni-bench.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl enable --now veni-bench      # disables itself when the queue is done
tail -f ~/llm-bench/suite/driver.log
```

Then copy `results.jsonl` and `transcripts/` back into `results/` and regenerate the tables and figures:

```bash
python3 tools/build_docs.py && python3 tools/plots.py
```

## 6. Soak and coding tests (§4.11 and the coding section)

`suite/soak/soak.py` runs the phases in `plan.json` in order, each from a fresh boot. A soak phase sends requests
nonstop for `hours`; a `"kind": "code"` phase runs the coding test once per model and moves on. A request with no
reply for 5 minutes (7 for coding) is logged as a freeze and the board is reset by sysrq; the run then resumes.

```json
[
 {"name": "qwen3-4b.npu.np1", "hours": 4, "file": "Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf",
  "url": "https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf",
  "server_args": ["-np", "1"]},
 {"name": "code.qwen3-4b.npu", "kind": "code", "hours": 8, "file": "Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf",
  "url": "https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen_Qwen3-4B-Instruct-2507-Q4_0.gguf",
  "server_args": ["-np", "1"]},
 {"name": "genie.qwen3-4b", "hours": 12, "engine": "genie", "model": "qwen3_4b_instruct_2507"}
]
```

Phase keys: `dev` (`npu` default, or `cpu`), `env`, `server_args`, `llama` (build directory), `engine`
(`llama`, `genie`, `applab`), `model` (name sent to Genie or App Lab). Our full plan is
[`suite/soak/plan.json`](../suite/soak/plan.json).

```bash
mkdir -p ~/llm-bench/soak
cp suite/soak/soak.py suite/soak/code_bench.py my-plan.json ~/llm-bench/soak/
mv ~/llm-bench/soak/my-plan.json ~/llm-bench/soak/plan.json
curl -sSfL https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz \
  | gunzip > ~/llm-bench/soak/HumanEval.jsonl
sudo cp suite/soak/veni-soak.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl enable --now veni-soak      # disables itself after the last phase
tail -f ~/llm-bench/soak/soak-*.jsonl
```

Progress is kept in `plan_state.json`; delete it to start the plan from the beginning.

**The coding test on its own**, against any OpenAI-compatible server that is already running (no reboots, no
watchdog):

```bash
python3 code_bench.py 8080 m llama code-results.jsonl      # port, model name, engine (llama|genie|applab), output
```

It uses every 4th HumanEval task (41 tasks) in two variants: `hidden` (the model writes the function; HumanEval's
tests, which it never sees, decide) and `selftest` (the model also writes its own asserts, which are run against its
code and against the reference solution). Model code runs in a separate `python3 -I` process with a 10 s limit and
memory caps, but it is still untrusted code: run it on a test board, not a machine with anything you care about.

## 7. Probes

| Script | Measures | Run |
|---|---|---|
| [`suite/probes/bw.c`](../suite/probes/bw.c) | Memory bandwidth per thread count (§4.8) | `gcc -O3 -pthread bw.c -o bw && ./bw 4 256 5` (threads, MB per thread, reps) |
| [`suite/probes/genie_prefill.py`](../suite/probes/genie_prefill.py) | Genie prompt reading at 128/512/2048 tokens (§4.7) | `python3 genie_prefill.py` with Genie running |
| [`suite/probes/combo_parallel.py`](../suite/probes/combo_parallel.py) | Two models at once, NPU + CPU (§4.9) | see the script header |

## 8. Sharing your results

Open an issue or pull request with your `results.jsonl` lines (or soak/coding `.jsonl` files) and the output of
the commands in step 1. Differences in kernel, firmware or `qcom-fastrpc1` version are the most likely reason for
different freeze behaviour, so include them.
