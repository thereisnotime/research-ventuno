# Local LLM inference on the Arduino VENTUNO Q: an empirical evaluation of NPU and CPU backends

- **Hardware:** Arduino VENTUNO Q (Qualcomm QCS8300, Hexagon NPU, 16 GB LPDDR)
- **Engines:** llama.cpp (Hexagon/HTP and CPU backends), Qualcomm Genie (QNN)
- **Data collected:** 2026-11-08 to 2026-11-10 · **Status:** complete for the models listed; see §6 for open items

## Abstract

This repository reports an evaluation of small open-weight language models (1.2B to 9B parameters, 4-bit) running
locally on the Arduino VENTUNO Q, a single-board computer built on the Qualcomm QCS8300 SoC. About twenty models and
configurations were tested on three inference paths: llama.cpp with the Hexagon NPU backend, llama.cpp on the Arm
CPU, and Qualcomm's Genie runtime. Each was measured for throughput (prompt processing and generation), memory use,
tool-calling accuracy (7 cases), structured JSON output, a 12-question reasoning quiz, long-context retrieval and,
where supported, image understanding (4 synthetic images). The best overall result was Qwen3-4B-Instruct-2507 on
the NPU (7/7 tools, 12/12 quiz, 12.6 tokens/s); the fastest usable model was LFM2.5-1.2B (29 tokens/s generation,
1264 tokens/s prompt processing). The NPU path was not stable: driver-level wedges occurred at random across model
sizes and in two cases froze the whole board, which is documented together with the mitigations used to finish the
run unattended. Against the advertised "up to 40 dense TOPS" for LLMs, prompt processing with llama.cpp reached about
3.5 TOPS (9%) on two different models, with the NPU's matrix engine carrying all of it; Qualcomm's own runtime
reached about 10.4 TOPS (26%). Generation is limited by memory: the board delivers about 28-30 GB/s, and the NPU
already generates at that limit, so the CPU nearly matches it. All raw requests, responses and per-test results are published so every figure can be traced to the
model output it came from.

## 1. Motivation

The VENTUNO Q is marketed as an edge-AI board: eight Arm cores, 16 GB of RAM and a Hexagon NPU at the price of a
small PC. The intended use here is an always-on, LAN-only assistant for home automation that must (a) call tools
reliably, (b) read short text and simple images, and (c) answer at interactive speed, without cloud services or a
discrete GPU. Vendor material does not answer the practical questions this raises:

1. Which model and which engine (Genie or llama.cpp's Hexagon backend) give the best accuracy per unit of latency?
2. How large is the NPU's advantage over the CPU, for prompt processing and for generation?
3. Is the NPU stack stable enough for 24/7 operation, and if not, what are the failure modes and recovery options?
4. How much of the advertised "up to 40 dense TOPS of NPU acceleration for vision models, LLMs, and multi-modal
   AI inference" is usable for LLMs? (Vendor claims and archived sources: [docs/sources.md](docs/sources.md).)

## 2. Test environment

- Board: Arduino VENTUNO Q, SoC Qualcomm QCS8300 "Monaco" (DT model `Monaco Monza addons`), 16 GB RAM
- OS: Ubuntu 24.04.5 LTS (noble), Arduino image `BUILD_ID=20260710-235`
- Kernel: `6.8.0-1089-qcom #94-Ubuntu SMP PREEMPT_DYNAMIC Wed Sep 23 2026` (aarch64), 1078 still installed;
  cmdline adds `watchdog.stop_on_reboot=0` (from 2026-11-09)
- NPU kernel side: in-tree `fastrpc` (drivers/misc/fastrpc.ko), `qcom_q6v5_pas` remoteproc, `qcom_wdt`, `efi_pstore`
- DSP firmware (remoteproc, running): `qcom/qcs8300/cdsp0.mbn`, `adsp.mbn`, `gpdsp0.mbn`;
  packages `linux-firmware-dragonwing 20260825`, `linux-firmware 20240318...0ubuntu2.27`
- NPU userspace: `qcom-fastrpc1 1.0.15+repack2` (libcdsprpc), unsigned PD shell `/usr/lib/dsp/cdsp/fastrpc_shell_unsigned_3`
- llama.cpp: upstream `7fe450e`, ggml 0.25.1, Hexagon backend (`libggml-hexagon`, HTP libs v73/v75/v79/v81),
  4 HTP sessions (`GGML_HEXAGON_DEVICES=4`, `-dev HTP0/HTP1/HTP2/HTP3`), `-c 4096`, `-fa 1`, `-t 4` pinned to cores 0-3
- Genie: arduino-app-cli 0.14.1, bundles `qwen3_4b_instruct_2507`, `qwen3_8b`, `qwen3_vl_8b_instruct` (`genie-w4a16-qualcomm_qcs8275`)
- Arduino meta: `arduino-ventunoq 0.2.0` (0.4.0 available but pulls `arduino-cloud-connector`, held back)

Kernel check (2026-11-09): 1089 is the newest `linux-qcom` in noble and Arduino's repo; there is no newer kernel
to try. Its changelog already carries the known fastrpc fixes (dma_buf leak in `fastrpc_map_lookup`,
CVE-2025-68252; map leak in `fastrpc_put_args`; use-after-free races; DMA address corruption) plus
`PENDING` Qualcomm patches. So the leak and wedges we hit are still unfixed upstream bugs, not a missing update.

### 2.1 Environment per run

Every run is tagged with an environment profile (`E1`, `E2`, …) that fingerprints everything under the model:
kernel and boot arguments, NPU firmware hash, `linux-firmware` and `qcom-fastrpc1` versions, and the engine
build (llama.cpp commit or Genie image). The **Env** and **Build** columns in every table link to
[reports/environments.md](reports/environments.md), which lists each profile in full and the runs that used it.
Runs from 2026-11-10 on record their environment themselves; earlier runs are inferred from the package and
boot history and are marked as such.

## 3. Method

Each configuration ran as one queued item on an otherwise idle board, one at a time, driven by
[`suite/suite.py`](suite/suite.py). Server tests talk to an OpenAI-compatible endpoint (llama-server or Genie) at
temperature 0 with model "thinking" disabled. Context 4096, flash attention on, 4 threads pinned to cores 0-3.

| Test | What is measured | Pass condition |
|---|---|---|
| Speed | Generation t/s for a 256-token reply; cold and warm time-to-first-token | — |
| Prefill / needle | Prompt t/s on a ~1.7k-token log with one buried fact | Fact (code `4417`) returned |
| Tools | 7 cases: single call, argument formatting, no-call, parallel calls, use of a tool result ([details](reports/tools.md)) | Correct function and arguments |
| JSON | Schema-constrained extraction (`response_format: json_schema`) | Valid JSON, correct fields |
| Quiz | 12 short arithmetic, logic, language and knowledge questions ([details](reports/quiz.md)) | Answer matches a regex |
| Vision | 4 generated 448×448 images: OCR, counting, colours, direction | Answer matches a regex |
| llama-bench | `pp512` / `tg128` at context depth 0 and 2048 | — |

Memory is sampled during each test (peak used RAM and peak pinned NPU memory). When pinned NPU memory leaked above a
threshold, or the NPU wedged, the runner hard-reset the board (sysrq) and resumed the queue.

**Reading the tables.** 🥇 🥈 🥉 mark the best three distinct values per column (ties share a medal; lower is
better for RAM and s/image; score medals require at least half marks). ✅ pass, ❌ fail, — not measured. ❌ before a
run name means the run produced no measurements. Pick badges: 🏆 best all-round, 🚀 fastest 4B, ⚡ fastest useful,
🛡️ CPU-only (no NPU risk), 👁️ vision pick, 🎯 most accurate vision, ⚠️ weak, ⛔ avoid. Every model and run name links
to a page with the exact prompts and replies; see also the [quiz matrix](reports/quiz.md), the
[tools matrix](reports/tools.md) and the [list of all runs](reports/index.md).

## 4. Results

### 4.1 Summary: best run per model

Table 1. Each model's run with the highest tools+quiz score (wedged or crashed runs lose automatically). Medals only count runs that produced numbers. Vision = best run with the image encoder working. `—` = never produced a valid result.

| Model | Pick | Engine | Build | Device | Env | Gen t/s | Prefill t/s | Tools | JSON | Quiz | Needle | Vision | s/image | Peak RAM MB |
|---|---|---|---|---|---|---:|---:|---|---|---|---|---|---:|---:|
| [lfm2.5-1.2b](reports/lfm2.5-1.2b.npu.server.b12244.md) |  | llama | `d5bbcd1` | npu | [E5](reports/environments.md#e5) | 🥇 29.88 | 🥇 1317.85 | [🥈 6/7](reports/lfm2.5-1.2b.npu.server.b12244.md#tools) | ✅ | [🥉 10/12](reports/lfm2.5-1.2b.npu.server.b12244.md#quiz) | ✅ | — | — | 🥇 2382 |
| [lfm2-vl-1.6b](reports/lfm2-vl-1.6b.npu.server.md) |  | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | 🥈 29.51 | 🥉 1233.42 | [2/7](reports/lfm2-vl-1.6b.npu.server.md#tools) | ✅ | [🥉 10/12](reports/lfm2-vl-1.6b.npu.server.md#quiz) | ✅ | [🥈 3/4](reports/lfm2-vl-1.6b.npu.server.md#vision) | 🥈 5.1 | 🥉 3976 |
| [lfm2.5-1.2b](reports/lfm2.5-1.2b.npu.server.md) | ⚡ fastest useful | llama | `7fe450e` | npu | [E3](reports/environments.md#e3) | 🥉 29.13 | 🥈 1263.86 | [🥈 6/7](reports/lfm2.5-1.2b.npu.server.md#tools) | ✅ | [🥉 10/12](reports/lfm2.5-1.2b.npu.server.md#quiz) | ✅ | — | — | 🥈 2504 |
| [olmoe-1b-7b](reports/olmoe-1b-7b.npu.server.md) | ⚠️ bad at tools | llama | `7fe450e` | npu | [E3](reports/environments.md#e3) | 28.76 | 567.83 | [1/7](reports/olmoe-1b-7b.npu.server.md#tools) | ✅ | [7/12](reports/olmoe-1b-7b.npu.server.md#quiz) | ❌ | — | — | 7371 |
| [lfm2-8b-a1b](reports/lfm2-8b-a1b.cpu.server.tr.md) | 🛡️ safe 24/7 | llama | `7fe450e` | cpu | [E3](reports/environments.md#e3) | 24.7 | 49.0 | [🥈 6/7](reports/lfm2-8b-a1b.cpu.server.tr.md#tools) | ✅ | [🥉 10/12](reports/lfm2-8b-a1b.cpu.server.tr.md#quiz) | ✅ | — | — | 5430 |
| [lfm2-8b-a1b](reports/lfm2-8b-a1b.npu.server.b12244.md) |  | llama | `d5bbcd1` | npu | [E5](reports/environments.md#e5) | 24.23 | 550.86 | [🥉 5/7](reports/lfm2-8b-a1b.npu.server.b12244.md#tools) | ✅ | [🥉 10/12](reports/lfm2-8b-a1b.npu.server.b12244.md#quiz) | ✅ | — | — | 6480 |
| [lfm2-8b-a1b](reports/lfm2-8b-a1b.npu.server.tr.md) |  | llama | `7fe450e` | npu | [E3](reports/environments.md#e3) | 23.97 | 511.4 | [🥈 6/7](reports/lfm2-8b-a1b.npu.server.tr.md#tools) | ✅ | [🥉 10/12](reports/lfm2-8b-a1b.npu.server.tr.md#quiz) | ✅ | — | — | 6597 |
| [phi-mini-moe](reports/phi-mini-moe.npu.server.md) | ⚠️ bad at tools | llama | `7fe450e` | npu | [E3](reports/environments.md#e3) | 18.63 | 352.77 | [1/7](reports/phi-mini-moe.npu.server.md#tools) | ❌ | [8/12](reports/phi-mini-moe.npu.server.md#quiz) | ❌ | — | — | 7306 |
| [qwen3_4b_instruct_2507](reports/genie-qwen3-4b.server.fix5.md) | 🚀 fastest 4B | genie | `1.5.0` | npu (QNN) | [E4](reports/environments.md#e4) | 16.45 | — | [🥈 6/7](reports/genie-qwen3-4b.server.fix5.md#tools) | ❌ | [🥉 10/12](reports/genie-qwen3-4b.server.fix5.md#quiz) | ✅ | — | — | 7752 |
| [phi-4-mini](reports/phi-4-mini.npu.server.md) |  | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | 14.04 | 456.92 | [2/7](reports/phi-4-mini.npu.server.md#tools) | ✅ | [9/12](reports/phi-4-mini.npu.server.md#quiz) | ✅ | — | — | 5429 |
| [gemma-3-4b](reports/gemma-3-4b.npu.server.md) | 🎯 most accurate vision | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | 13.26 | 445.78 | [1/7](reports/gemma-3-4b.npu.server.md#tools) | ✅ | [🥇 12/12](reports/gemma-3-4b.npu.server.md#quiz) | ✅ | [🥇 4/4](reports/gemma-3-4b.npu.server.md#vision) | 27.7 | 7048 |
| [qwen3-4b-2507](reports/qwen3-4b-2507.npu.server.tr.md) | 🏆 best all-round | llama | `7fe450e` | npu | [E3](reports/environments.md#e3) | 12.79 | 395.46 | [🥇 7/7](reports/qwen3-4b-2507.npu.server.tr.md#tools) | ✅ | [🥇 12/12](reports/qwen3-4b-2507.npu.server.tr.md#quiz) | ✅ | — | — | 5405 |
| [qwen3-4b-2507](reports/qwen3-4b-2507.npu.server.b12244.md) |  | llama | `d5bbcd1` | npu | [E5](reports/environments.md#e5) | 12.71 | 402.2 | [🥇 7/7](reports/qwen3-4b-2507.npu.server.b12244.md#tools) | ✅ | [🥇 12/12](reports/qwen3-4b-2507.npu.server.b12244.md#quiz) | ✅ | — | — | 5287 |
| [qwen3-vl-4b](reports/qwen3-vl-4b.npu.server.md) |  | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | 12.55 | 385.69 | [🥇 7/7](reports/qwen3-vl-4b.npu.server.md#tools) | ✅ | [🥈 11/12](reports/qwen3-vl-4b.npu.server.md#quiz) | ✅ | [🥈 3/4](reports/qwen3-vl-4b.npu.server.vfix2.md#vision) | 🥉 9.8 | 6800 |
| [qwen3.5-4b](reports/qwen3.5-4b.npu.server.b12244.md) |  | llama | `d5bbcd1` | npu | [E5](reports/environments.md#e5) | 10.6 | 372.61 | [🥇 7/7](reports/qwen3.5-4b.npu.server.b12244.md#tools) | ✅ | [🥈 11/12](reports/qwen3.5-4b.npu.server.b12244.md#quiz) | ✅ | [🥈 3/4](reports/qwen3.5-4b.npu.server.b12244.md#vision) | 21.2 | 8890 |
| [gemma-4-e4b](reports/gemma-4-e4b.npu.server.md) | ⛔ never loaded | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | 10.47 | — | [0/7](reports/gemma-4-e4b.npu.server.md#tools) | ❌ | [0/12](reports/gemma-4-e4b.npu.server.md#quiz) | ❌ | — | — | 9007 |
| [qwen3-4b-2507](reports/qwen3-4b-2507.cpu.server.tr.md) |  | llama | `7fe450e` | cpu | [E3](reports/environments.md#e3) | 10.0 | 27.81 | [🥇 7/7](reports/qwen3-4b-2507.cpu.server.tr.md#tools) | ✅ | [🥈 11/12](reports/qwen3-4b-2507.cpu.server.tr.md#quiz) | ✅ | — | — | 4482 |
| [qwen3-4b-2507](reports/qwen3-4b-2507.cpu.server.b12244.md) |  | llama | `d5bbcd1` | cpu | [E5](reports/environments.md#e5) | 9.84 | 22.02 | [🥇 7/7](reports/qwen3-4b-2507.cpu.server.b12244.md#tools) | ✅ | [🥈 11/12](reports/qwen3-4b-2507.cpu.server.b12244.md#quiz) | ✅ | — | — | 4290 |
| [qwen3.5-4b](reports/qwen3.5-4b.npu.server.md) | 👁️ fast vision | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | 8.59 | 151.21 | [🥇 7/7](reports/qwen3.5-4b.npu.server.md#tools) | ✅ | [🥈 11/12](reports/qwen3.5-4b.npu.server.md#quiz) | ✅ | [🥈 3/4](reports/qwen3.5-4b.npu.server.md#vision) | 🥇 3.9 | 9557 |
| [qwen3-8b](reports/qwen3-8b.npu.server.md) |  | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | 7.64 | 250.26 | [🥇 7/7](reports/qwen3-8b.npu.server.md#tools) | ✅ | [🥉 10/12](reports/qwen3-8b.npu.server.md#quiz) | ✅ | — | — | 7370 |
| [qwen3-vl-8b](reports/qwen3-vl-8b.npu.server.md) |  | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | 7.57 | 246.36 | [🥇 7/7](reports/qwen3-vl-8b.npu.server.md#tools) | ✅ | [🥈 11/12](reports/qwen3-vl-8b.npu.server.md#quiz) | ✅ | — | — | 9079 |
| [ministral-3-8b](reports/ministral-3-8b.npu.server.vfix3.md) | 👁️ quality vision | llama | `7fe450e` | npu | [E3](reports/environments.md#e3) | 7.07 | 216.55 | [🥇 7/7](reports/ministral-3-8b.npu.server.vfix3.md#tools) | ✅ | [🥈 11/12](reports/ministral-3-8b.npu.server.vfix3.md#quiz) | ✅ | [🥈 3/4](reports/ministral-3-8b.npu.server.vfix3.md#vision) | 14.3 | 8531 |
| [qwen3.5-9b](reports/qwen3.5-9b.npu.server.md) |  | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | 5.83 | 99.5 | [🥇 7/7](reports/qwen3.5-9b.npu.server.md#tools) | ✅ | [🥉 10/12](reports/qwen3.5-9b.npu.server.md#quiz) | ✅ | [🥉 2/4](reports/qwen3.5-9b.npu.server.md#vision) | 10.1 | 12188 |
| [granite-4-h-tiny](reports/granite-4-h-tiny.npu.server.md) | ⛔ froze the board | llama | `7fe450e` | npu | [E1](reports/environments.md#e1) | — | — | — | — | — | — | — | — | 8582 |
| [qwen3_4b_instruct_2507-genie-w4a16-qualcomm_qcs8275](reports/genie-qwen3-4b.server.md) |  | genie | `1.5.0` | npu (QNN) | [E4](reports/environments.md#e4) | — | — | — | — | — | — | — | — | 2032 |
| [qwen3_vl_8b_instruct-genie-w4a16-qualcomm_qcs8275](reports/genie-qwen3-vl-8b.server.md) |  | genie | `1.5.0` | npu (QNN) | [E4](reports/environments.md#e4) | — | — | — | — | — | — | — | — | 886 |
| [qwen3_vl_8b_instruct](reports/genie-qwen3-vl-8b.server.fix.md) | ⛔ hangs | genie | `1.5.0` | npu (QNN) | [E4](reports/environments.md#e4) | — | — | [0/7](reports/genie-qwen3-vl-8b.server.fix.md#tools) | ❌ | [0/12](reports/genie-qwen3-vl-8b.server.fix.md#quiz) | ❌ | — | — | 9561 |
| [ministral-3-8b](reports/ministral-3-8b.npu.server.b12244.md) |  | llama | `d5bbcd1` | npu | [E5](reports/environments.md#e5) | — | — | — | — | — | — | — | — | 7545 |
| [gemma-4-e4b](reports/gemma-4-e4b.npu.server.b12244.md) |  | llama | `d5bbcd1` | npu | [E5](reports/environments.md#e5) | — | — | — | — | — | — | — | — | 10370 |
| [qwen3-vl-8b](reports/qwen3-vl-8b.npu.server.b12244.md) |  | llama | `d5bbcd1` | npu | [E5](reports/environments.md#e5) | — | — | — | — | — | — | — | — | 8478 |

### 4.2 Recommendations

| Use case | Configuration | Evidence |
|---|---|---|
| 🏆 General assistant (tools + reasoning) | Qwen3-4B-Instruct-2507, llama.cpp, NPU | 7/7 tools, 12/12 quiz, 12.6 t/s, 6.3 GB |
| 🚀 Same model, higher throughput | Qwen3-4B-Instruct-2507, Genie | 16.5 t/s, 6/7 tools, 10/12 quiz; no JSON-schema support |
| ⚡ Lowest latency | LFM2.5-1.2B, llama.cpp, NPU | 29 t/s, 1264 t/s prefill, 6/7 tools, 2.5 GB |
| 🛡️ No NPU (stability first) | LFM2-8B-A1B, llama.cpp, CPU | 24.5 t/s, 6/7 tools, no NPU involvement |
| 👁️ Vision, speed | Qwen3.5-4B, NPU + CPU image encoder | 3/4 images, 3.9 s/image, 7/7 tools |
| 👁️ Vision, quality | Ministral 3 8B, NPU + CPU image encoder | 3/4 images, 14.3 s/image, 7/7 tools, 11/12 quiz |
| 🎯 Vision, accuracy | Gemma 3 4B | 4/4 images, but 27.7 s/image and 1/7 tools |

Not recommended on this board: dense 8-9B models (slower without accuracy gains over the 4B models), Granite 4
(froze the board), OLMoE-1B-7B and Phi-mini-MoE (fast but 1/7 tool calls), Genie Qwen3-VL-8B (hangs on a
~1.7k-token prompt).

### 4.3 Server tests, every run

Table 2. All llama-server and Genie runs. Gen = short-reply generation t/s; Prefill = t/s on the ~1.7k-token prompt;
`htp` = number of NPU sessions.

| Test | Env | htp | Gen t/s | Prefill t/s | Load s | Needle | Tools | JSON | Quiz | Vision | s/image | Peak RAM MB | Note |
|---|---|---|---:|---:|---:|---|---|---|---|---|---:|---:|---|
| [qwen3-4b-2507.npu.server](reports/qwen3-4b-2507.npu.server.md) | [E1](reports/environments.md#e1) | — | 12.55 | 394.97 | 6.1 | ✅ | 7/7 | ✅ | 12/12 | — | — | 6287 |  |
| [qwen3-4b-2507.cpu.server](reports/qwen3-4b-2507.cpu.server.md) | [E1](reports/environments.md#e1) | — | 9.93 | 27.88 | 8.0 | ✅ | 7/7 | ✅ | 11/12 | — | — | 5406 |  |
| [qwen3-8b.npu.server](reports/qwen3-8b.npu.server.md) | [E1](reports/environments.md#e1) | — | 7.64 | 250.26 | 58.2 | ✅ | 7/7 | ✅ | 10/12 | — | — | 7370 |  |
| [lfm2-8b-a1b.npu.server](reports/lfm2-8b-a1b.npu.server.md) | [E1](reports/environments.md#e1) | — | 23.5 | 511.43 | 8.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 6673 |  |
| [lfm2-8b-a1b.cpu.server](reports/lfm2-8b-a1b.cpu.server.md) | [E1](reports/environments.md#e1) | — | 24.54 | 49.22 | 8.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 5492 |  |
| ❌ [granite-4-h-tiny.npu.server](reports/granite-4-h-tiny.npu.server.md) | [E1](reports/environments.md#e1) | — | — | — | 54.1 | — | — | — | — | — | — | 8582 | [Errno 104] Connection reset by peer |
| [phi-4-mini.npu.server](reports/phi-4-mini.npu.server.md) | [E1](reports/environments.md#e1) | — | 14.04 | 456.92 | 6.1 | ✅ | 2/7 | ✅ | 9/12 | — | — | 5429 |  |
| [gemma-3-4b.npu.server](reports/gemma-3-4b.npu.server.md) | [E1](reports/environments.md#e1) | — | 13.26 | 445.78 | 18.1 | ✅ | 1/7 | ✅ | 12/12 | 4/4 | 27.7 | 7048 |  |
| [qwen3-vl-4b.npu.server](reports/qwen3-vl-4b.npu.server.md) | [E1](reports/environments.md#e1) | — | 12.55 | 385.69 | 6.0 | ✅ | 7/7 | ✅ | 11/12 | 0/4 | — | 6800 |  |
| [lfm2-vl-1.6b.npu.server](reports/lfm2-vl-1.6b.npu.server.md) | [E1](reports/environments.md#e1) | — | 29.51 | 1233.42 | 4.0 | ✅ | 2/7 | ✅ | 10/12 | 3/4 | 5.1 | 3976 |  |
| [qwen3-vl-8b.npu.server](reports/qwen3-vl-8b.npu.server.md) | [E1](reports/environments.md#e1) | — | 7.57 | 246.36 | 10.2 | ✅ | 7/7 | ✅ | 11/12 | 0/4 | — | 9079 |  |
| [qwen3.5-4b.npu.server](reports/qwen3.5-4b.npu.server.md) | [E1](reports/environments.md#e1) | — | 8.59 | 151.21 | 8.1 | ✅ | 7/7 | ✅ | 11/12 | 3/4 | 3.9 | 9557 |  |
| [qwen3.5-9b.npu.server](reports/qwen3.5-9b.npu.server.md) | [E1](reports/environments.md#e1) | — | 5.83 | 99.5 | 34.1 | ✅ | 7/7 | ✅ | 10/12 | 2/4 | 10.1 | 12188 |  |
| [gemma-4-e4b.npu.server](reports/gemma-4-e4b.npu.server.md) | [E1](reports/environments.md#e1) | — | 10.47 | — | 28.1 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | — | 9007 |  |
| [ministral-3-8b.npu.server](reports/ministral-3-8b.npu.server.md) | [E2](reports/environments.md#e2) | — | 6.83 | 216.51 | 8.1 | ✅ | 7/7 | ✅ | 11/12 | 0/4 | — | 8677 |  |
| [lfm2.5-1.2b.npu.server](reports/lfm2.5-1.2b.npu.server.md) | [E3](reports/environments.md#e3) | — | 29.13 | 1263.86 | 2.1 | ✅ | 6/7 | ✅ | 10/12 | — | — | 2504 |  |
| [phi-mini-moe.npu.server](reports/phi-mini-moe.npu.server.md) | [E3](reports/environments.md#e3) | — | 18.63 | 352.77 | 8.0 | ❌ | 1/7 | ❌ | 8/12 | — | — | 7306 |  |
| [olmoe-1b-7b.npu.server](reports/olmoe-1b-7b.npu.server.md) | [E3](reports/environments.md#e3) | — | 28.76 | 567.83 | 8.0 | ❌ | 1/7 | ✅ | 7/12 | — | — | 7371 |  |
| ❌ [genie-qwen3-4b.server](reports/genie-qwen3-4b.server.md) | [E4](reports/environments.md#e4) | — | — | — | 10.2 | — | — | — | — | — | — | 2032 | HTTP Error 400: |
| ❌ [genie-qwen3-vl-8b.server](reports/genie-qwen3-vl-8b.server.md) | [E4](reports/environments.md#e4) | — | — | — | 4.2 | — | — | — | — | — | — | 886 | HTTP Error 400: |
| [qwen3-4b-2507.cpu.server.rerun](reports/qwen3-4b-2507.cpu.server.rerun.md) | [E3](reports/environments.md#e3) | 1 | 3.33 | 27.75 | 14.1 | ✅ | 7/7 | ✅ | 11/12 | — | — | 4225 |  |
| ❌ [qwen3-8b.npu.server.rerun](reports/qwen3-8b.npu.server.rerun.md) | [E3](reports/environments.md#e3) | 1 | — | — | — | — | — | — | — | — | — | 6341 | server did not become healthy |
| ❌ [lfm2-8b-a1b.npu.server.rerun](reports/lfm2-8b-a1b.npu.server.rerun.md) | [E3](reports/environments.md#e3) | 1 | — | — | — | — | — | — | — | — | — | 5820 | server did not become healthy |
| [lfm2-8b-a1b.cpu.server.rerun](reports/lfm2-8b-a1b.cpu.server.rerun.md) | [E3](reports/environments.md#e3) | 1 | 7.81 | 49.06 | 4.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 6163 |  |
| ❌ [qwen3-4b-2507.npu.server.s1](reports/qwen3-4b-2507.npu.server.s1.md) | [E3](reports/environments.md#e3) | 1 | — | — | — | — | — | — | — | — | — | 4274 | server did not become healthy |
| [genie-qwen3-4b.server.fix](reports/genie-qwen3-4b.server.fix.md) | [E4](reports/environments.md#e4) | 0 | 17.31 | — | 4.2 | ✅ | 0/7 | ❌ | 0/12 | — | — | 11785 |  |
| [genie-qwen3-vl-8b.server.fix](reports/genie-qwen3-vl-8b.server.fix.md) | [E4](reports/environments.md#e4) | 0 | — | — | 6.2 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | — | 9561 |  |
| ❌ [qwen3-vl-4b.npu.server.vfix](reports/qwen3-vl-4b.npu.server.vfix.md) | [E3](reports/environments.md#e3) | 1 | — | — | — | — | — | — | — | — | — | 4311 | server did not become healthy |
| ❌ [qwen3-vl-8b.npu.server.vfix](reports/qwen3-vl-8b.npu.server.vfix.md) | [E3](reports/environments.md#e3) | 4 | — | — | — | — | — | — | — | — | — | 892 | server did not become healthy |
| ❌ [ministral-3-8b.npu.server.vfix](reports/ministral-3-8b.npu.server.vfix.md) | [E3](reports/environments.md#e3) | 4 | — | — | — | — | — | — | — | — | — | 886 | server did not become healthy |
| ❌ [gemma-4-e4b.npu.server.vfix](reports/gemma-4-e4b.npu.server.vfix.md) | [E3](reports/environments.md#e3) | 1 | — | — | — | — | — | — | — | — | — | 6878 | server did not become healthy |
| [genie-qwen3-4b.server.fix2](reports/genie-qwen3-4b.server.fix2.md) | [E4](reports/environments.md#e4) | 0 | 17.06 | — | 6.2 | ✅ | 0/7 | ❌ | 0/12 | — | — | 11508 |  |
| [genie-qwen3-vl-8b.server.fix2](reports/genie-qwen3-vl-8b.server.fix2.md) | [E4](reports/environments.md#e4) | 0 | — | — | 4.2 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | 4.2 | 9730 |  |
| [qwen3-vl-4b.npu.server.vfix2](reports/qwen3-vl-4b.npu.server.vfix2.md) | [E3](reports/environments.md#e3) | 4 | 12.27 | 386.42 | 6.1 | ✅ | 7/7 | ✅ | 11/12 | 3/4 | 9.8 | 6418 |  |
| [genie-qwen3-4b.server.fix3](reports/genie-qwen3-4b.server.fix3.md) | [E4](reports/environments.md#e4) | 0 | 16.3 | — | 6.2 | ✅ | 0/7 | ❌ | 0/12 | — | — | 11347 |  |
| [genie-qwen3-vl-8b.server.fix3](reports/genie-qwen3-vl-8b.server.fix3.md) | [E4](reports/environments.md#e4) | 0 | — | — | 6.3 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | 4.2 | 9679 |  |
| [qwen3-vl-8b.npu.server.vfix3](reports/qwen3-vl-8b.npu.server.vfix3.md) | [E3](reports/environments.md#e3) | 4 | 7.54 | 246.7 | 99.0 | ✅ | 2/7 | ❌ | 0/12 | 0/4 | — | 8469 |  |
| [ministral-3-8b.npu.server.vfix3](reports/ministral-3-8b.npu.server.vfix3.md) | [E3](reports/environments.md#e3) | 4 | 7.07 | 216.55 | 10.1 | ✅ | 7/7 | ✅ | 11/12 | 3/4 | 14.3 | 8531 |  |
| ❌ [gemma-4-e4b.npu.server.vfix3](reports/gemma-4-e4b.npu.server.vfix3.md) | [E3](reports/environments.md#e3) | 4 | — | — | — | — | — | — | — | — | — | 8090 | server did not become healthy |
| [genie-qwen3-4b.server.fix4](reports/genie-qwen3-4b.server.fix4.md) | [E4](reports/environments.md#e4) | 0 | 16.33 | — | 6.2 | ✅ | 0/7 | ❌ | 0/12 | — | — | 11601 |  |
| [genie-qwen3-vl-8b.server.fix4](reports/genie-qwen3-vl-8b.server.fix4.md) | [E4](reports/environments.md#e4) | 0 | — | — | 4.2 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | 4.3 | 9703 |  |
| [genie-qwen3-4b.server.fix5](reports/genie-qwen3-4b.server.fix5.md) | [E4](reports/environments.md#e4) | 0 | 16.45 | — | 76.6 | ✅ | 6/7 | ❌ | 10/12 | — | — | 7752 |  |
| [genie-qwen3-vl-8b.server.fix5](reports/genie-qwen3-vl-8b.server.fix5.md) | [E4](reports/environments.md#e4) | 0 | — | — | 6.3 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | 4.0 | 9704 |  |
| [qwen3-4b-2507.npu.server.tr](reports/qwen3-4b-2507.npu.server.tr.md) | [E3](reports/environments.md#e3) | 4 | 12.79 | 395.46 | 6.1 | ✅ | 7/7 | ✅ | 12/12 | — | — | 5405 |  |
| [qwen3-4b-2507.cpu.server.tr](reports/qwen3-4b-2507.cpu.server.tr.md) | [E3](reports/environments.md#e3) | 0 | 10.0 | 27.81 | 4.0 | ✅ | 7/7 | ✅ | 11/12 | — | — | 4482 |  |
| [lfm2-8b-a1b.npu.server.tr](reports/lfm2-8b-a1b.npu.server.tr.md) | [E3](reports/environments.md#e3) | 4 | 23.97 | 511.4 | 8.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 6597 |  |
| [lfm2-8b-a1b.cpu.server.tr](reports/lfm2-8b-a1b.cpu.server.tr.md) | [E3](reports/environments.md#e3) | 0 | 24.7 | 49.0 | 10.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 5430 |  |
| ❌ [qwen3-4b-2507.npu.server.b12244.s1](reports/qwen3-4b-2507.npu.server.b12244.s1.md) | [E5](reports/environments.md#e5) | 1 | — | — | — | — | — | — | — | — | — | 4355 | server did not become healthy |
| [qwen3-4b-2507.npu.server.b12244](reports/qwen3-4b-2507.npu.server.b12244.md) | [E5](reports/environments.md#e5) | 4 | 12.71 | 402.2 | 4.1 | ✅ | 7/7 | ✅ | 12/12 | — | — | 5287 |  |
| [lfm2.5-1.2b.npu.server.b12244](reports/lfm2.5-1.2b.npu.server.b12244.md) | [E5](reports/environments.md#e5) | 4 | 29.88 | 1317.85 | 2.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 2382 |  |
| [lfm2-8b-a1b.npu.server.b12244](reports/lfm2-8b-a1b.npu.server.b12244.md) | [E5](reports/environments.md#e5) | 4 | 24.23 | 550.86 | 6.0 | ✅ | 5/7 | ✅ | 10/12 | — | — | 6480 |  |
| [qwen3.5-4b.npu.server.b12244](reports/qwen3.5-4b.npu.server.b12244.md) | [E5](reports/environments.md#e5) | 4 | 10.6 | 372.61 | 6.0 | ✅ | 7/7 | ✅ | 11/12 | 3/4 | 21.2 | 8890 |  |
| ❌ [ministral-3-8b.npu.server.b12244](reports/ministral-3-8b.npu.server.b12244.md) | [E5](reports/environments.md#e5) | 4 | — | — | — | — | — | — | — | — | — | 7545 | server did not become healthy |
| ❌ [gemma-4-e4b.npu.server.b12244](reports/gemma-4-e4b.npu.server.b12244.md) | [E5](reports/environments.md#e5) | 4 | — | — | — | — | — | — | — | — | — | 10370 | server did not become healthy |
| ❌ [qwen3-vl-8b.npu.server.b12244](reports/qwen3-vl-8b.npu.server.b12244.md) | [E5](reports/environments.md#e5) | 4 | — | — | 6.0 | — | — | — | — | — | — | 8478 | [Errno 104] Connection reset by peer |
| [qwen3-4b-2507.cpu.server.b12244](reports/qwen3-4b-2507.cpu.server.b12244.md) | [E5](reports/environments.md#e5) | 0 | 9.84 | 22.02 | 6.0 | ✅ | 7/7 | ✅ | 11/12 | — | — | 4290 |  |
| ❌ [combo.c1.qwen3-8b.ngl28](reports/combo.c1.qwen3-8b.ngl28.md) | [E3](reports/environments.md#e3) | 4 | — | — | 32.2 | — | — | — | — | — | — | 6998 | [Errno 104] Connection reset by peer |
| [combo.c2.qwen3-8b.ngl20](reports/combo.c2.qwen3-8b.ngl20.md) | [E3](reports/environments.md#e3) | 3 | 0.89 | 24.66 | 62.6 | ✅ | 7/7 | ✅ | 10/12 | — | — | 7255 |  |
| [combo.c3.qwen3-4b.spec4](reports/combo.c3.qwen3-4b.spec4.md) | [E5](reports/environments.md#e5) | 4 | 12.53 | 401.19 | 14.0 | ✅ | 7/7 | ✅ | 12/12 | — | — | 5926 |  |
| [combo.c4.qwen3-4b.spec8](reports/combo.c4.qwen3-4b.spec8.md) | [E5](reports/environments.md#e5) | 4 | 12.44 | 400.64 | 6.0 | ✅ | 7/7 | ✅ | 7/12 | — | — | 5740 |  |

### 4.4 llama-bench

Table 3. `pp512` / `tg128` throughput in tokens/s at context depth 0 and 2048.

| Test | Env | htp | pp512 | tg128 | pp512 @2k | tg128 @2k | Note |
|---|---|---|---:|---:|---:|---:|---|
| [qwen3-4b-2507.npu.bench](reports/qwen3-4b-2507.npu.bench.md) | [E1](reports/environments.md#e1) | — | 441.41 | 12.99 | 330.31 | 9.19 |  |
| [qwen3-4b-2507.cpu.bench](reports/qwen3-4b-2507.cpu.bench.md) | [E1](reports/environments.md#e1) | — | 33.59 | 10.2 | 20.77 | 5.1 |  |
| ❌ [qwen3-8b.npu.bench](reports/qwen3-8b.npu.bench.md) | [E1](reports/environments.md#e1) | — | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [lfm2-8b-a1b.npu.bench](reports/lfm2-8b-a1b.npu.bench.md) | [E1](reports/environments.md#e1) | — | 555.4 | 24.9 | 536.24 | 22.39 |  |
| [lfm2-8b-a1b.cpu.bench](reports/lfm2-8b-a1b.cpu.bench.md) | [E1](reports/environments.md#e1) | — | 50.52 | 25.09 | 46.72 | 7.82 |  |
| ❌ [granite-4-h-tiny.npu.bench](reports/granite-4-h-tiny.npu.bench.md) | [E1](reports/environments.md#e1) | — | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [phi-4-mini.npu.bench](reports/phi-4-mini.npu.bench.md) | [E1](reports/environments.md#e1) | — | 502.45 | 13.73 | 398.25 | 10.51 |  |
| ❌ [gemma-3-4b.npu.bench](reports/gemma-3-4b.npu.bench.md) | [E1](reports/environments.md#e1) | — | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [qwen3-vl-4b.npu.bench](reports/qwen3-vl-4b.npu.bench.md) | [E1](reports/environments.md#e1) | — | 430.88 | 13.0 | 323.27 | 9.16 |  |
| [lfm2-vl-1.6b.npu.bench](reports/lfm2-vl-1.6b.npu.bench.md) | [E1](reports/environments.md#e1) | — | 🥉 1440.54 | 27.87 | 🥉 1254.22 | 🥈 26.59 |  |
| [qwen3-vl-8b.npu.bench](reports/qwen3-vl-8b.npu.bench.md) | [E1](reports/environments.md#e1) | — | 263.45 | 7.79 | 218.88 | 6.25 |  |
| [qwen3.5-4b.npu.bench](reports/qwen3.5-4b.npu.bench.md) | [E1](reports/environments.md#e1) | — | 159.97 | 8.79 | 153.63 | 8.51 |  |
| ❌ [qwen3.5-9b.npu.bench](reports/qwen3.5-9b.npu.bench.md) | [E1](reports/environments.md#e1) | — | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| ❌ [gemma-4-e4b.npu.bench](reports/gemma-4-e4b.npu.bench.md) | [E1](reports/environments.md#e1) | — | — | — | — | — | llama-bench rc=-6: ['warning: 360\t../csu/libc-start.c: No s… |
| ❌ [granite-4.2-8b.npu.bench](reports/granite-4.2-8b.npu.bench.md) | [E1](reports/environments.md#e1) | — | — | — | — | — | llama-bench rc=-9: ['ggml-hex: device 3: HTP3 (phys=0, virt=… |
| [llama-3.2-3b.npu.bench](reports/llama-3.2-3b.npu.bench.md) | [E2](reports/environments.md#e2) | — | 593.74 | 16.54 | 467.02 | 12.58 |  |
| [lfm2.5-1.2b.npu.bench](reports/lfm2.5-1.2b.npu.bench.md) | [E3](reports/environments.md#e3) | — | 1438.99 | 🥉 29.47 | 🥈 1261.92 | 🥉 25.74 |  |
| [phi-mini-moe.npu.bench](reports/phi-mini-moe.npu.bench.md) | [E3](reports/environments.md#e3) | — | 411.07 | 18.35 | 326.34 | 11.82 |  |
| [olmoe-1b-7b.npu.bench](reports/olmoe-1b-7b.npu.bench.md) | [E3](reports/environments.md#e3) | — | 639.39 | 🥇 30.45 | 583.62 | 17.61 |  |
| ❌ [gemma-3-4b.npu.bench.d0](reports/gemma-3-4b.npu.bench.d0.md) | [E3](reports/environments.md#e3) | 1 | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| ❌ [qwen3-4b-2507.npu.bench.b12244.s1](reports/qwen3-4b-2507.npu.bench.b12244.s1.md) | [E5](reports/environments.md#e5) | 1 | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [qwen3-4b-2507.npu.bench.b12244](reports/qwen3-4b-2507.npu.bench.b12244.md) | [E5](reports/environments.md#e5) | 4 | 445.53 | 9.69 | 334.96 | 9.21 |  |
| ❌ [qwen3-8b.npu.bench.b12244](reports/qwen3-8b.npu.bench.b12244.md) | [E5](reports/environments.md#e5) | 4 | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| ❌ [qwen3-4b-2507.npu.bench.b12244.s1.d0](reports/qwen3-4b-2507.npu.bench.b12244.s1.d0.md) | [E5](reports/environments.md#e5) | 1 | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [lfm2.5-1.2b.npu.bench.b12244](reports/lfm2.5-1.2b.npu.bench.b12244.md) | [E5](reports/environments.md#e5) | 4 | 🥈 1461.56 | 🥈 30.31 | 🥇 1270.59 | 🥇 27.23 |  |
| [lfm2-8b-a1b.npu.bench.b12244](reports/lfm2-8b-a1b.npu.bench.b12244.md) | [E5](reports/environments.md#e5) | 4 | 595.55 | 24.26 | 562.52 | 22.39 |  |
| [qwen3.5-4b.npu.bench.b12244](reports/qwen3.5-4b.npu.bench.b12244.md) | [E5](reports/environments.md#e5) | 4 | 398.98 | 11.09 | 383.81 | 10.36 |  |
| ❌ [gemma-4-e4b.npu.bench.b12244](reports/gemma-4-e4b.npu.bench.b12244.md) | [E5](reports/environments.md#e5) | 4 | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [qwen3-4b-2507.cpu.bench.b12244](reports/qwen3-4b-2507.cpu.bench.b12244.md) | [E5](reports/environments.md#e5) | 0 | 30.57 | 10.22 | 20.48 | 5.08 |  |
| [qwen3-8b.npu.bench.b12244.d0](reports/qwen3-8b.npu.bench.b12244.d0.md) | [E5](reports/environments.md#e5) | 4 | 269.82 | 7.99 | — | — |  |
| [tops.t1.qwen3-4b-q4.hmx](reports/tops.t1.qwen3-4b-q4.hmx.md) | [E5](reports/environments.md#e5) | 4 | 445.23 | 13.13 | — | — |  |
| [tops.t2.qwen3-4b-q4.nohmx](reports/tops.t2.qwen3-4b-q4.nohmx.md) | [E5](reports/environments.md#e5) | 4 | 24.81 | 12.99 | — | — |  |
| [tops.t3.qwen3-4b-q4.balanced](reports/tops.t3.qwen3-4b-q4.balanced.md) | [E5](reports/environments.md#e5) | 4 | 444.99 | 12.86 | — | — |  |
| ❌ [tops.t4.qwen3-4b-q8.hmx](reports/tops.t4.qwen3-4b-q8.hmx.md) | [E5](reports/environments.md#e5) | 4 | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [tops.t5.lfm2.5-1.2b.hmx](reports/tops.t5.lfm2.5-1.2b.hmx.md) | [E5](reports/environments.md#e5) | 4 | 🥇 1463.7 | 20.73 | — | — |  |
| [tops.t5b.lfm2.5-1.2b.nohmx](reports/tops.t5b.lfm2.5-1.2b.nohmx.md) | [E5](reports/environments.md#e5) | 4 | 104.24 | 28.91 | — | — |  |
| ❌ [gemma-4-e4b.npu.bench.b12244.d0](reports/gemma-4-e4b.npu.bench.b12244.d0.md) | [E5](reports/environments.md#e5) | 4 | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |

### 4.5 Runs without a result

| Test | Status |
|---|---|
| qwen3-8b.npu.bench.retry | started |
| granite-4.2-8b.npu.server | started |
| ministral-3-8b.npu.bench | skipped-unsafe |
| llama-3.2-3b.npu.server | started |
| qwen3-4b-2507.npu.server.rerun | started |
| qwen3-8b.npu.bench.d0 | skipped-unsafe |
| granite-4-h-tiny.npu.bench.d0 | skipped-unsafe |
| qwen3-8b.npu.bench.retry2 | skipped-unsafe |
| qwen3.5-9b.npu.bench.d0 | skipped-unsafe |
| gemma-4-e4b.npu.bench.d0 | skipped-unsafe |
| granite-4.2-8b.npu.bench.d0 | skipped-unsafe |
| qwen3-vl-8b.npu.server.vfix2 | hung |
| ministral-3-8b.npu.server.vfix2 | skipped-hung |
| gemma-4-e4b.npu.server.vfix2 | skipped-hung |
| qwen3-8b.npu.server.tr | hung (NPU wedged on the first request, board reset by hand) |
| qwen3-8b.npu.server.tr2 | hung after tool case 5 of 7 (NPU wedged, sysrq reset); [partial transcript](results/transcripts/qwen3-8b.npu.server.tr2.transcript.jsonl) |

### 4.6 llama.cpp build comparison

Table 4. Same model and device on the original build (`7fe450e`, 2026-10-02) and a newer upstream build
(`b12244` / `d5bbcd1`, 2026-11-10, built with the Snapdragon toolchain `arm64-linux:v0.8`). Best run per build.
🟢 better by 3% or more, 🔴 worse by 3% or more, ⚪ within 3%.

| Model | Device | Metric | `7fe450e` | `d5bbcd1` | Change |
|---|---|---|---:|---:|---:|
| gemma-4-e4b | npu | llamabench | ❌ | ❌ [gemma-4-e4b.npu.bench.b12244.d0](reports/gemma-4-e4b.npu.bench.b12244.d0.md) | |
| gemma-4-e4b | npu | server | ok | ❌ [gemma-4-e4b.npu.server.b12244](reports/gemma-4-e4b.npu.server.b12244.md) | |
| lfm2-8b-a1b | npu | pp512_d0 | [555.4](reports/lfm2-8b-a1b.npu.bench.md) | [595.55](reports/lfm2-8b-a1b.npu.bench.b12244.md) | 🟢 +7% |
| lfm2-8b-a1b | npu | tg128_d0 | [24.9](reports/lfm2-8b-a1b.npu.bench.md) | [24.26](reports/lfm2-8b-a1b.npu.bench.b12244.md) | ⚪ -3% |
| lfm2-8b-a1b | npu | pp512_d2048 | [536.24](reports/lfm2-8b-a1b.npu.bench.md) | [562.52](reports/lfm2-8b-a1b.npu.bench.b12244.md) | 🟢 +5% |
| lfm2-8b-a1b | npu | tg128_d2048 | [22.39](reports/lfm2-8b-a1b.npu.bench.md) | [22.39](reports/lfm2-8b-a1b.npu.bench.b12244.md) | ⚪ +0% |
| lfm2-8b-a1b | npu | Gen t/s | [23.97](reports/lfm2-8b-a1b.npu.server.tr.md) | [24.23](reports/lfm2-8b-a1b.npu.server.b12244.md) | ⚪ +1% |
| lfm2-8b-a1b | npu | Prefill t/s | [511.4](reports/lfm2-8b-a1b.npu.server.tr.md) | [550.86](reports/lfm2-8b-a1b.npu.server.b12244.md) | 🟢 +8% |
| lfm2-8b-a1b | npu | Tools | 6/7 | 5/7 | |
| lfm2-8b-a1b | npu | Quiz | 10/12 | 10/12 | |
| lfm2-8b-a1b | npu | Peak RAM MB | [6597](reports/lfm2-8b-a1b.npu.server.tr.md) | [6480](reports/lfm2-8b-a1b.npu.server.b12244.md) | ⚪ -2% |
| lfm2.5-1.2b | npu | pp512_d0 | [1438.99](reports/lfm2.5-1.2b.npu.bench.md) | [1461.56](reports/lfm2.5-1.2b.npu.bench.b12244.md) | ⚪ +2% |
| lfm2.5-1.2b | npu | tg128_d0 | [29.47](reports/lfm2.5-1.2b.npu.bench.md) | [30.31](reports/lfm2.5-1.2b.npu.bench.b12244.md) | ⚪ +3% |
| lfm2.5-1.2b | npu | pp512_d2048 | [1261.92](reports/lfm2.5-1.2b.npu.bench.md) | [1270.59](reports/lfm2.5-1.2b.npu.bench.b12244.md) | ⚪ +1% |
| lfm2.5-1.2b | npu | tg128_d2048 | [25.74](reports/lfm2.5-1.2b.npu.bench.md) | [27.23](reports/lfm2.5-1.2b.npu.bench.b12244.md) | 🟢 +6% |
| lfm2.5-1.2b | npu | Gen t/s | [29.13](reports/lfm2.5-1.2b.npu.server.md) | [29.88](reports/lfm2.5-1.2b.npu.server.b12244.md) | ⚪ +3% |
| lfm2.5-1.2b | npu | Prefill t/s | [1263.86](reports/lfm2.5-1.2b.npu.server.md) | [1317.85](reports/lfm2.5-1.2b.npu.server.b12244.md) | 🟢 +4% |
| lfm2.5-1.2b | npu | Tools | 6/7 | 6/7 | |
| lfm2.5-1.2b | npu | Quiz | 10/12 | 10/12 | |
| lfm2.5-1.2b | npu | Peak RAM MB | [2504](reports/lfm2.5-1.2b.npu.server.md) | [2382](reports/lfm2.5-1.2b.npu.server.b12244.md) | 🟢 -5% |
| ministral-3-8b | npu | server | ok | ❌ [ministral-3-8b.npu.server.b12244](reports/ministral-3-8b.npu.server.b12244.md) | |
| qwen3-4b-2507 | cpu | pp512_d0 | [33.59](reports/qwen3-4b-2507.cpu.bench.md) | [30.57](reports/qwen3-4b-2507.cpu.bench.b12244.md) | 🔴 -9% |
| qwen3-4b-2507 | cpu | tg128_d0 | [10.2](reports/qwen3-4b-2507.cpu.bench.md) | [10.22](reports/qwen3-4b-2507.cpu.bench.b12244.md) | ⚪ +0% |
| qwen3-4b-2507 | cpu | pp512_d2048 | [20.77](reports/qwen3-4b-2507.cpu.bench.md) | [20.48](reports/qwen3-4b-2507.cpu.bench.b12244.md) | ⚪ -1% |
| qwen3-4b-2507 | cpu | tg128_d2048 | [5.1](reports/qwen3-4b-2507.cpu.bench.md) | [5.08](reports/qwen3-4b-2507.cpu.bench.b12244.md) | ⚪ -0% |
| qwen3-4b-2507 | cpu | Gen t/s | [10.0](reports/qwen3-4b-2507.cpu.server.tr.md) | [9.84](reports/qwen3-4b-2507.cpu.server.b12244.md) | ⚪ -2% |
| qwen3-4b-2507 | cpu | Prefill t/s | [27.81](reports/qwen3-4b-2507.cpu.server.tr.md) | [22.02](reports/qwen3-4b-2507.cpu.server.b12244.md) | 🔴 -21% |
| qwen3-4b-2507 | cpu | Tools | 7/7 | 7/7 | |
| qwen3-4b-2507 | cpu | Quiz | 11/12 | 11/12 | |
| qwen3-4b-2507 | cpu | Peak RAM MB | [4482](reports/qwen3-4b-2507.cpu.server.tr.md) | [4290](reports/qwen3-4b-2507.cpu.server.b12244.md) | 🟢 -4% |
| qwen3-4b-2507 | npu | pp512_d0 | [441.41](reports/qwen3-4b-2507.npu.bench.md) | [445.23](reports/tops.t1.qwen3-4b-q4.hmx.md) | ⚪ +1% |
| qwen3-4b-2507 | npu | tg128_d0 | [12.99](reports/qwen3-4b-2507.npu.bench.md) | [13.13](reports/tops.t1.qwen3-4b-q4.hmx.md) | ⚪ +1% |
| qwen3-4b-2507 | npu | pp512_d2048 | [330.31](reports/qwen3-4b-2507.npu.bench.md) | ❌ |  |
| qwen3-4b-2507 | npu | tg128_d2048 | [9.19](reports/qwen3-4b-2507.npu.bench.md) | ❌ |  |
| qwen3-4b-2507 | npu | Gen t/s | [12.79](reports/qwen3-4b-2507.npu.server.tr.md) | [12.71](reports/qwen3-4b-2507.npu.server.b12244.md) | ⚪ -1% |
| qwen3-4b-2507 | npu | Prefill t/s | [395.46](reports/qwen3-4b-2507.npu.server.tr.md) | [402.2](reports/qwen3-4b-2507.npu.server.b12244.md) | ⚪ +2% |
| qwen3-4b-2507 | npu | Tools | 7/7 | 7/7 | |
| qwen3-4b-2507 | npu | Quiz | 12/12 | 12/12 | |
| qwen3-4b-2507 | npu | Peak RAM MB | [5405](reports/qwen3-4b-2507.npu.server.tr.md) | [5287](reports/qwen3-4b-2507.npu.server.b12244.md) | ⚪ -2% |
| qwen3-4b-2507-q8 | npu | llamabench | ❌ | ❌ [tops.t4.qwen3-4b-q8.hmx](reports/tops.t4.qwen3-4b-q8.hmx.md) | |
| qwen3-8b | npu | pp512_d0 | ❌ | [269.82](reports/qwen3-8b.npu.bench.b12244.d0.md) |  |
| qwen3-8b | npu | tg128_d0 | ❌ | [7.99](reports/qwen3-8b.npu.bench.b12244.d0.md) |  |
| qwen3-8b | npu | Gen t/s | [7.64](reports/qwen3-8b.npu.server.md) | ❌ |  |
| qwen3-8b | npu | Prefill t/s | [250.26](reports/qwen3-8b.npu.server.md) | ❌ |  |
| qwen3-8b | npu | Tools | 7/7 | — | |
| qwen3-8b | npu | Quiz | 10/12 | — | |
| qwen3-8b | npu | Peak RAM MB | [7370](reports/qwen3-8b.npu.server.md) | ❌ |  |
| qwen3-vl-8b | npu | pp512_d0 | [263.45](reports/qwen3-vl-8b.npu.bench.md) | ❌ |  |
| qwen3-vl-8b | npu | tg128_d0 | [7.79](reports/qwen3-vl-8b.npu.bench.md) | ❌ |  |
| qwen3-vl-8b | npu | pp512_d2048 | [218.88](reports/qwen3-vl-8b.npu.bench.md) | ❌ |  |
| qwen3-vl-8b | npu | tg128_d2048 | [6.25](reports/qwen3-vl-8b.npu.bench.md) | ❌ |  |
| qwen3-vl-8b | npu | server | ok | ❌ [qwen3-vl-8b.npu.server.b12244](reports/qwen3-vl-8b.npu.server.b12244.md) | |
| qwen3.5-4b | npu | pp512_d0 | [159.97](reports/qwen3.5-4b.npu.bench.md) | [398.98](reports/qwen3.5-4b.npu.bench.b12244.md) | 🟢 +149% |
| qwen3.5-4b | npu | tg128_d0 | [8.79](reports/qwen3.5-4b.npu.bench.md) | [11.09](reports/qwen3.5-4b.npu.bench.b12244.md) | 🟢 +26% |
| qwen3.5-4b | npu | pp512_d2048 | [153.63](reports/qwen3.5-4b.npu.bench.md) | [383.81](reports/qwen3.5-4b.npu.bench.b12244.md) | 🟢 +150% |
| qwen3.5-4b | npu | tg128_d2048 | [8.51](reports/qwen3.5-4b.npu.bench.md) | [10.36](reports/qwen3.5-4b.npu.bench.b12244.md) | 🟢 +22% |
| qwen3.5-4b | npu | Gen t/s | [8.59](reports/qwen3.5-4b.npu.server.md) | [10.6](reports/qwen3.5-4b.npu.server.b12244.md) | 🟢 +23% |
| qwen3.5-4b | npu | Prefill t/s | [151.21](reports/qwen3.5-4b.npu.server.md) | [372.61](reports/qwen3.5-4b.npu.server.b12244.md) | 🟢 +146% |
| qwen3.5-4b | npu | Tools | 7/7 | 7/7 | |
| qwen3.5-4b | npu | Quiz | 11/12 | 11/12 | |
| qwen3.5-4b | npu | Vision | 3/4 | 3/4 | |
| qwen3.5-4b | npu | Peak RAM MB | [9557](reports/qwen3.5-4b.npu.server.md) | [8890](reports/qwen3.5-4b.npu.server.b12244.md) | 🟢 -7% |

### 4.7 40 TOPS tests

The vendor advertises "up to 40 dense TOPS of NPU acceleration for vision models, LLMs, and multi-modal AI
inference" ([sources](docs/sources.md)). These llama-bench runs (llama.cpp `d5bbcd1`, 4 NPU sessions, Q4_0) measure
how much of that an LLM workload reaches. Effective TOPS = prompt tokens/s × 2 × parameters, the usual estimate
for a transformer's forward pass. Generation is memory-bound and does not use the TOPS; see §4.1 and §6.

Table 5. Prompt throughput (t/s) by prompt size, with the matrix engine (HMX) on or off and two power modes.

| Test | Model | Matrix engine (HMX) | Power mode | pp128 | pp512 | pp2048 | tg128 | Effective TOPS (pp512) | Share of 40 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| [tops.t1.qwen3-4b-q4.hmx](reports/tops.t1.qwen3-4b-q4.hmx.md) | qwen3-4b-2507 | on | burst (default) | 386.97 | 445.23 | 401.2 | 13.13 | 3.58 | 9% |
| [tops.t2.qwen3-4b-q4.nohmx](reports/tops.t2.qwen3-4b-q4.nohmx.md) | qwen3-4b-2507 | off | burst (default) | 27.99 | 24.81 | 16.97 | 12.99 | 0.2 | 0% |
| [tops.t3.qwen3-4b-q4.balanced](reports/tops.t3.qwen3-4b-q4.balanced.md) | qwen3-4b-2507 | on | balanced | 383.86 | 444.99 | 400.59 | 12.86 | 3.58 | 9% |
| ❌ [tops.t4.qwen3-4b-q8.hmx](reports/tops.t4.qwen3-4b-q8.hmx.md) | qwen3-4b-2507-q8 | on | burst (default) | — | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mm… |
| [tops.t5.lfm2.5-1.2b.hmx](reports/tops.t5.lfm2.5-1.2b.hmx.md) | lfm2.5-1.2b | on | burst (default) | 1191.64 | 1463.7 | 1383.25 | 20.73 | 3.43 | 9% |
| [tops.t5b.lfm2.5-1.2b.nohmx](reports/tops.t5b.lfm2.5-1.2b.nohmx.md) | lfm2.5-1.2b | off | burst (default) | 106.49 | 104.24 | 89.84 | 28.91 | 0.24 | 1% |

Findings:

- **The matrix engine does all the prompt work.** Turning it off (`GGML_HEXAGON_NHMX=0`) drops Qwen3-4B prompt
  reading from 445 to 25 t/s (18× slower, below the 4 CPU cores at 28 t/s) and LFM2.5-1.2B from 1464 to 104 t/s.
- **Prompt throughput hits the same ceiling of about 3.5 TOPS on both models** (1.2B and 4B), and it does not
  grow with prompt size. A fixed ceiling across models points at the execution path rather than the model: Q4_0
  weights are unpacked on the vector units and fed to the matrix engine at 16-bit precision, while the 40 TOPS
  figure is the matrix engine's dense 8-bit integer rate.
- **Power mode makes no difference** (`burst` vs `balanced`: 445 vs 445 t/s), so clock and bus votes are not the
  limit.
- **The 8-bit model (Q8_0), the closest format to the 40 TOPS precision, cannot be tested**: at 4.3 GB it fails to
  map on the NPU (`fastrpc_mmap failed`), the same limit as the 8B models.
- **Generation is unaffected by the matrix engine** (Qwen3-4B 13.1 vs 13.0 t/s). For LFM2.5-1.2B this llama-bench
  run measured lower generation with HMX on (20.7 vs 28.9 t/s), but the same build's earlier bench measured 30.3
  t/s with HMX on, so that difference is not reliable from one run.
- **Qualcomm's own runtime gets about 3× further.** Genie (QNN) read Qwen3-4B prompts at about 1290 t/s
  (~2770 tokens in 2.15 s to first token), which is **~10.4 TOPS, 26% of 40**
  ([raw](results/probes/genie_prefill_qwen3-4b.txt), [script](suite/probes/genie_prefill.py)). Token counts are
  from the Qwen3 tokenizer, since Genie's stream does not report them. The test prompts repeat one filler
  paragraph; each request used a fresh Genie session, so prefix reuse is unlikely but not ruled out.
- **Result: with llama.cpp, LLM prompt processing reaches about 9% of the advertised 40 TOPS; with Qualcomm's
  Genie about 26%.** Neither comes close to 40 TOPS for an LLM.

### 4.8 Memory bandwidth

Table 6. CPU memory bandwidth measured on the board with a STREAM-style test
([source](suite/probes/bw.c), [raw](results/probes/memory_bandwidth.txt)), 256 MB per thread.

| Cores | Read GB/s | Copy GB/s |
|---|---:|---:|
| 1× Cortex-A78 | 16.7 | 24.7 |
| 2× Cortex-A78 | 27.8 | 30.2 |
| 4× Cortex-A78 | 26.1 | 27.2 |
| 4× Cortex-A55 | 5.7 | 8.7 |
| All 8 | 28.4 | 29.6 |

The usable memory bandwidth is **about 28-30 GB/s**, well below the ~51 GB/s that the product brief's
"4x16 LPDDR5/5x @ 3200 MHz" implies, and two CPU cores already saturate it. LLM generation reads every weight
once per token, so this is the ceiling for generation speed on any engine. Measured against it, NPU generation
is already at the limit: Qwen3-4B at 12.8 t/s reads ~2.4 GB per token, about 31 GB/s, and Qwen3-8B at 7.6 t/s
about 34 GB/s (the NPU may see slightly more bandwidth than the CPU cluster). This is why the CPU nearly matches
the NPU for generation while the NPU is 14× faster at reading prompts.

### 4.9 Combination tests

Table 7. Using the NPU and CPU together (llama.cpp; C1, C2 on `7fe450e`, the rest on `d5bbcd1`).

| Test | Setup | Result |
|---|---|---|
| [C1](reports/combo.c1.qwen3-8b.ngl28.md) | Qwen3-8B, 28 layers on NPU (4 sessions), rest on CPU | ❌ crashed after 30 min (connection reset) |
| [C2](reports/combo.c2.qwen3-8b.ngl20.md) | Qwen3-8B, 20 layers on NPU (3 sessions), rest on CPU | ✅ 7/7 tools, 10/12 quiz, but **0.89 t/s** generation, 25 t/s prefill |
| [C3](reports/combo.c3.qwen3-4b.spec4.md) | Qwen3-4B on NPU + Qwen3-0.6B draft on CPU, 4-token drafts | ✅ 7/7, 12/12, **12.5 t/s** (no gain over 12.7 without a draft) |
| [C4](reports/combo.c4.qwen3-4b.spec8.md) | Same, 8-token drafts | ❌ answered 7 quiz questions correctly, then hung and crashed (timeouts, connection refused) |
| [Parallel](results/probes/combo_parallel.jsonl) | Qwen3-4B on NPU (host threads on A55) + LFM2-8B-A1B on CPU (A78), both generating at once ([script](suite/probes/combo_parallel.py)) | NPU 10.9 → 10.3 t/s, CPU 26.4 → **15.4 t/s**, total **25.7 t/s**, 9.4 GB RAM |

Findings:

- **Splitting a model between NPU and CPU does not get around the NPU mapping limit usefully**: with more layers on
  the NPU it crashes, with fewer it works but is 8× slower than running it on the NPU alone.
- **Speculative decoding gives nothing here.** The draft model guesses essay text poorly, and every speculation
  step still has to read the full 4B model's weights; with 8-token drafts the server hung.
- **Running two models at once does not add throughput.** Both compete for the same ~30 GB/s; together they
  produce less than the CPU model alone. It is still useful when two different models must be available at once.
- Driving the NPU from the slow A55 cores costs about 15% generation speed (10.9 vs 12.7 t/s from the A78s).

## 5. Stability findings

All fixes and workarounds that kept the board running (firmware rollback, leak guards, watchdog, sysrq
reboots, the never-kill procedure, the stall watcher and the Genie fixes) are collected with their exact
configuration in [docs/stability-fixes.md](docs/stability-fixes.md).

- The NPU wedges at random (Llama 3.2 3B, Qwen3-4B rerun, Qwen3-VL-8B twice); runs that wedged are listed in the
  detail tables but excluded above. See [docs/board-notes.md](docs/board-notes.md) for the freeze history and mitigations.
- One NPU session can't map a 4B model on this llama.cpp build (`fastrpc_mmap`), so all NPU runs use 4 sessions.
- Vision image encoders run on CPU (`--no-mmproj-offload`); on the NPU they fail to map.
- Genie needs: streaming only (non-streaming kills its LLM process), one session per request, and
  `HISTORY_EVICTION_THRESHOLD=100` (history eviction's facts pass crashes it). See [`suite/genie-compose.yaml`](suite/genie-compose.yaml).
- The two late CPU reruns (Qwen3-4B 3.3 t/s, LFM2-8B 7.8 t/s) were slowed by something else on the CPU; the
  original CPU numbers stand.

The NPU wedges are consistent with open fastrpc driver bugs (context leak and hang on a signal-interrupted invoke)
that were not fixed in the newest kernel available for the board at the time (6.8.0-1089-qcom). The full incident
log, watchdog configuration and recovery procedure are in [docs/board-notes.md](docs/board-notes.md).

## 6. Limitations and open items

- Accuracy tests are small (7 tool cases, 12 quiz questions, 4 images). They separate usable from unusable
  models but are not a substitute for standard benchmarks; differences of one point should not be over-read.
- Most configurations were run once, so no variance is reported. Four were rerun on 2026-11-10 to capture
  transcripts (`*.tr`): Qwen3-4B (NPU, CPU) and LFM2-8B-A1B (NPU, CPU). Every tools, quiz, JSON and needle
  result matched the original run exactly, and throughput was within 2%. Qwen3-8B was rerun twice and wedged
  the NPU both times (on the first request, then mid-way through the tool tests), so it still has pass/fail
  results only; the second attempt's partial transcript is kept.
- Everything ran on one board. Two llama.cpp builds were tested (`7fe450e`, `d5bbcd1`); the newer one did not
  change the NPU mapping limit, the 8B instability or generation speed (§4.6).
- Genie prompt speed was measured once, with repeated filler text (§4.7).
- Not measured: Qwen3-VL-8B vision (NPU wedged in 2 of 3 attempts), Gemma 4 E4B (failed to load).
- The original early runs predate transcript capture; their pages show pass/fail only (see the `*.tr` reruns).

## 7. Reproducibility

| Path | Content |
|---|---|
| [`results/results.jsonl`](results/results.jsonl) | One JSON object per test run (all metrics) |
| [`results/transcripts/`](results/transcripts/) | Every request and response, per run |
| [`results/queue.json`](results/queue.json), [`results/state.json`](results/state.json), [`results/driver.log`](results/driver.log) | Test queue, run status, runner log |
| [`reports/`](reports/index.md) | Generated per-run pages and cross-model matrices |
| [`suite/suite.py`](suite/suite.py) | Test runner |
| [`suite/genie-compose.yaml`](suite/genie-compose.yaml) | Working Genie configuration |
| [`tools/build_docs.py`](tools/build_docs.py) | Regenerates `reports/` and the tables in this README |
| [`reports/environments.md`](reports/environments.md) | Environment profiles (kernel, firmware, packages, engine build) and their runs |
| [`results/probes/`](results/probes/), [`suite/probes/`](suite/probes/) | Memory bandwidth, Genie prompt speed and two-model results, with their scripts and the stall watcher |
| [`docs/sources.md`](docs/sources.md) | Vendor claims under test, with Wayback Machine snapshots |
| [`docs/stability-fixes.md`](docs/stability-fixes.md) | Every crash fix and workaround, with config and verification status |
| [`docs/board-notes.md`](docs/board-notes.md) | Board setup, kernel and firmware notes, incident log |

## License and citation

Code (`suite/`, `tools/`) is under the MIT license; results, transcripts and documentation are under CC BY 4.0.
See [LICENSE](LICENSE). Citation metadata is in [CITATION.cff](CITATION.cff).
