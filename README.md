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
run unattended. All raw requests, responses and per-test results are published so every figure can be traced to the
model output it came from.

## 1. Motivation

The VENTUNO Q is marketed as an edge-AI board: eight Arm cores, 16 GB of RAM and a Hexagon NPU at the price of a
small PC. The intended use here is an always-on, LAN-only assistant for home automation that must (a) call tools
reliably, (b) read short text and simple images, and (c) answer at interactive speed, without cloud services or a
discrete GPU. Vendor material does not answer the practical questions this raises:

1. Which model and which engine (Genie or llama.cpp's Hexagon backend) give the best accuracy per unit of latency?
2. How large is the NPU's advantage over the CPU, for prompt processing and for generation?
3. Is the NPU stack stable enough for 24/7 operation, and if not, what are the failure modes and recovery options?

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

| Model | Pick | Engine | Device | Gen t/s | Prefill t/s | Tools | JSON | Quiz | Needle | Vision | s/image | Peak RAM MB |
|---|---|---|---|---:|---:|---|---|---|---|---|---:|---:|
| [lfm2-vl-1.6b](reports/lfm2-vl-1.6b.npu.server.md) |  | llama | npu | 🥇 29.51 | 🥈 1233.42 | [2/7](reports/lfm2-vl-1.6b.npu.server.md#tools) | ✅ | [🥉 10/12](reports/lfm2-vl-1.6b.npu.server.md#quiz) | ✅ | [🥈 3/4](reports/lfm2-vl-1.6b.npu.server.md#vision) | 🥈 5.1 | 🥈 3976 |
| [lfm2.5-1.2b](reports/lfm2.5-1.2b.npu.server.md) | ⚡ fastest useful | llama | npu | 🥈 29.13 | 🥇 1263.86 | [🥈 6/7](reports/lfm2.5-1.2b.npu.server.md#tools) | ✅ | [🥉 10/12](reports/lfm2.5-1.2b.npu.server.md#quiz) | ✅ | — | — | 🥇 2504 |
| [olmoe-1b-7b](reports/olmoe-1b-7b.npu.server.md) | ⚠️ bad at tools | llama | npu | 🥉 28.76 | 🥉 567.83 | [1/7](reports/olmoe-1b-7b.npu.server.md#tools) | ✅ | [7/12](reports/olmoe-1b-7b.npu.server.md#quiz) | ❌ | — | — | 7371 |
| [lfm2-8b-a1b](reports/lfm2-8b-a1b.cpu.server.tr.md) | 🛡️ safe 24/7 | llama | cpu | 24.7 | 49.0 | [🥈 6/7](reports/lfm2-8b-a1b.cpu.server.tr.md#tools) | ✅ | [🥉 10/12](reports/lfm2-8b-a1b.cpu.server.tr.md#quiz) | ✅ | — | — | 5430 |
| [lfm2-8b-a1b](reports/lfm2-8b-a1b.npu.server.tr.md) |  | llama | npu | 23.97 | 511.4 | [🥈 6/7](reports/lfm2-8b-a1b.npu.server.tr.md#tools) | ✅ | [🥉 10/12](reports/lfm2-8b-a1b.npu.server.tr.md#quiz) | ✅ | — | — | 6597 |
| [phi-mini-moe](reports/phi-mini-moe.npu.server.md) | ⚠️ bad at tools | llama | npu | 18.63 | 352.77 | [1/7](reports/phi-mini-moe.npu.server.md#tools) | ❌ | [8/12](reports/phi-mini-moe.npu.server.md#quiz) | ❌ | — | — | 7306 |
| [qwen3_4b_instruct_2507](reports/genie-qwen3-4b.server.fix5.md) | 🚀 fastest 4B | genie | npu (QNN) | 16.45 | — | [🥈 6/7](reports/genie-qwen3-4b.server.fix5.md#tools) | ❌ | [🥉 10/12](reports/genie-qwen3-4b.server.fix5.md#quiz) | ✅ | — | — | 7752 |
| [phi-4-mini](reports/phi-4-mini.npu.server.md) |  | llama | npu | 14.04 | 456.92 | [2/7](reports/phi-4-mini.npu.server.md#tools) | ✅ | [9/12](reports/phi-4-mini.npu.server.md#quiz) | ✅ | — | — | 5429 |
| [gemma-3-4b](reports/gemma-3-4b.npu.server.md) | 🎯 most accurate vision | llama | npu | 13.26 | 445.78 | [1/7](reports/gemma-3-4b.npu.server.md#tools) | ✅ | [🥇 12/12](reports/gemma-3-4b.npu.server.md#quiz) | ✅ | [🥇 4/4](reports/gemma-3-4b.npu.server.md#vision) | 27.7 | 7048 |
| [qwen3-4b-2507](reports/qwen3-4b-2507.npu.server.tr.md) | 🏆 best all-round | llama | npu | 12.79 | 395.46 | [🥇 7/7](reports/qwen3-4b-2507.npu.server.tr.md#tools) | ✅ | [🥇 12/12](reports/qwen3-4b-2507.npu.server.tr.md#quiz) | ✅ | — | — | 5405 |
| [qwen3-vl-4b](reports/qwen3-vl-4b.npu.server.md) |  | llama | npu | 12.55 | 385.69 | [🥇 7/7](reports/qwen3-vl-4b.npu.server.md#tools) | ✅ | [🥈 11/12](reports/qwen3-vl-4b.npu.server.md#quiz) | ✅ | [🥈 3/4](reports/qwen3-vl-4b.npu.server.vfix2.md#vision) | 🥉 9.8 | 6800 |
| [gemma-4-e4b](reports/gemma-4-e4b.npu.server.md) | ⛔ never loaded | llama | npu | 10.47 | — | [0/7](reports/gemma-4-e4b.npu.server.md#tools) | ❌ | [0/12](reports/gemma-4-e4b.npu.server.md#quiz) | ❌ | — | — | 9007 |
| [qwen3-4b-2507](reports/qwen3-4b-2507.cpu.server.tr.md) |  | llama | cpu | 10.0 | 27.81 | [🥇 7/7](reports/qwen3-4b-2507.cpu.server.tr.md#tools) | ✅ | [🥈 11/12](reports/qwen3-4b-2507.cpu.server.tr.md#quiz) | ✅ | — | — | 🥉 4482 |
| [qwen3.5-4b](reports/qwen3.5-4b.npu.server.md) | 👁️ fast vision | llama | npu | 8.59 | 151.21 | [🥇 7/7](reports/qwen3.5-4b.npu.server.md#tools) | ✅ | [🥈 11/12](reports/qwen3.5-4b.npu.server.md#quiz) | ✅ | [🥈 3/4](reports/qwen3.5-4b.npu.server.md#vision) | 🥇 3.9 | 9557 |
| [qwen3-8b](reports/qwen3-8b.npu.server.md) |  | llama | npu | 7.64 | 250.26 | [🥇 7/7](reports/qwen3-8b.npu.server.md#tools) | ✅ | [🥉 10/12](reports/qwen3-8b.npu.server.md#quiz) | ✅ | — | — | 7370 |
| [qwen3-vl-8b](reports/qwen3-vl-8b.npu.server.md) |  | llama | npu | 7.57 | 246.36 | [🥇 7/7](reports/qwen3-vl-8b.npu.server.md#tools) | ✅ | [🥈 11/12](reports/qwen3-vl-8b.npu.server.md#quiz) | ✅ | — | — | 9079 |
| [ministral-3-8b](reports/ministral-3-8b.npu.server.vfix3.md) | 👁️ quality vision | llama | npu | 7.07 | 216.55 | [🥇 7/7](reports/ministral-3-8b.npu.server.vfix3.md#tools) | ✅ | [🥈 11/12](reports/ministral-3-8b.npu.server.vfix3.md#quiz) | ✅ | [🥈 3/4](reports/ministral-3-8b.npu.server.vfix3.md#vision) | 14.3 | 8531 |
| [qwen3.5-9b](reports/qwen3.5-9b.npu.server.md) |  | llama | npu | 5.83 | 99.5 | [🥇 7/7](reports/qwen3.5-9b.npu.server.md#tools) | ✅ | [🥉 10/12](reports/qwen3.5-9b.npu.server.md#quiz) | ✅ | [🥉 2/4](reports/qwen3.5-9b.npu.server.md#vision) | 10.1 | 12188 |
| [granite-4-h-tiny](reports/granite-4-h-tiny.npu.server.md) | ⛔ froze the board | llama | npu | — | — | — | — | — | — | — | — | 8582 |
| [qwen3_4b_instruct_2507-genie-w4a16-qualcomm_qcs8275](reports/genie-qwen3-4b.server.md) |  | genie | npu (QNN) | — | — | — | — | — | — | — | — | 2032 |
| [qwen3_vl_8b_instruct-genie-w4a16-qualcomm_qcs8275](reports/genie-qwen3-vl-8b.server.md) |  | genie | npu (QNN) | — | — | — | — | — | — | — | — | 886 |
| [qwen3_vl_8b_instruct](reports/genie-qwen3-vl-8b.server.fix.md) | ⛔ hangs | genie | npu (QNN) | — | — | [0/7](reports/genie-qwen3-vl-8b.server.fix.md#tools) | ❌ | [0/12](reports/genie-qwen3-vl-8b.server.fix.md#quiz) | ❌ | — | — | 9561 |

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

| Test | htp | Gen t/s | Prefill t/s | Load s | Needle | Tools | JSON | Quiz | Vision | s/image | Peak RAM MB | Note |
|---|---|---:|---:|---:|---|---|---|---|---|---:|---:|---|
| [qwen3-4b-2507.npu.server](reports/qwen3-4b-2507.npu.server.md) | — | 12.55 | 394.97 | 6.1 | ✅ | 7/7 | ✅ | 12/12 | — | — | 6287 |  |
| [qwen3-4b-2507.cpu.server](reports/qwen3-4b-2507.cpu.server.md) | — | 9.93 | 27.88 | 8.0 | ✅ | 7/7 | ✅ | 11/12 | — | — | 5406 |  |
| [qwen3-8b.npu.server](reports/qwen3-8b.npu.server.md) | — | 7.64 | 250.26 | 58.2 | ✅ | 7/7 | ✅ | 10/12 | — | — | 7370 |  |
| [lfm2-8b-a1b.npu.server](reports/lfm2-8b-a1b.npu.server.md) | — | 23.5 | 511.43 | 8.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 6673 |  |
| [lfm2-8b-a1b.cpu.server](reports/lfm2-8b-a1b.cpu.server.md) | — | 24.54 | 49.22 | 8.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 5492 |  |
| ❌ [granite-4-h-tiny.npu.server](reports/granite-4-h-tiny.npu.server.md) | — | — | — | 54.1 | — | — | — | — | — | — | 8582 | [Errno 104] Connection reset by peer |
| [phi-4-mini.npu.server](reports/phi-4-mini.npu.server.md) | — | 14.04 | 456.92 | 6.1 | ✅ | 2/7 | ✅ | 9/12 | — | — | 5429 |  |
| [gemma-3-4b.npu.server](reports/gemma-3-4b.npu.server.md) | — | 13.26 | 445.78 | 18.1 | ✅ | 1/7 | ✅ | 12/12 | 4/4 | 27.7 | 7048 |  |
| [qwen3-vl-4b.npu.server](reports/qwen3-vl-4b.npu.server.md) | — | 12.55 | 385.69 | 6.0 | ✅ | 7/7 | ✅ | 11/12 | 0/4 | — | 6800 |  |
| [lfm2-vl-1.6b.npu.server](reports/lfm2-vl-1.6b.npu.server.md) | — | 29.51 | 1233.42 | 4.0 | ✅ | 2/7 | ✅ | 10/12 | 3/4 | 5.1 | 3976 |  |
| [qwen3-vl-8b.npu.server](reports/qwen3-vl-8b.npu.server.md) | — | 7.57 | 246.36 | 10.2 | ✅ | 7/7 | ✅ | 11/12 | 0/4 | — | 9079 |  |
| [qwen3.5-4b.npu.server](reports/qwen3.5-4b.npu.server.md) | — | 8.59 | 151.21 | 8.1 | ✅ | 7/7 | ✅ | 11/12 | 3/4 | 3.9 | 9557 |  |
| [qwen3.5-9b.npu.server](reports/qwen3.5-9b.npu.server.md) | — | 5.83 | 99.5 | 34.1 | ✅ | 7/7 | ✅ | 10/12 | 2/4 | 10.1 | 12188 |  |
| [gemma-4-e4b.npu.server](reports/gemma-4-e4b.npu.server.md) | — | 10.47 | — | 28.1 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | — | 9007 |  |
| [ministral-3-8b.npu.server](reports/ministral-3-8b.npu.server.md) | — | 6.83 | 216.51 | 8.1 | ✅ | 7/7 | ✅ | 11/12 | 0/4 | — | 8677 |  |
| [lfm2.5-1.2b.npu.server](reports/lfm2.5-1.2b.npu.server.md) | — | 29.13 | 1263.86 | 2.1 | ✅ | 6/7 | ✅ | 10/12 | — | — | 2504 |  |
| [phi-mini-moe.npu.server](reports/phi-mini-moe.npu.server.md) | — | 18.63 | 352.77 | 8.0 | ❌ | 1/7 | ❌ | 8/12 | — | — | 7306 |  |
| [olmoe-1b-7b.npu.server](reports/olmoe-1b-7b.npu.server.md) | — | 28.76 | 567.83 | 8.0 | ❌ | 1/7 | ✅ | 7/12 | — | — | 7371 |  |
| ❌ [genie-qwen3-4b.server](reports/genie-qwen3-4b.server.md) | — | — | — | 10.2 | — | — | — | — | — | — | 2032 | HTTP Error 400: |
| ❌ [genie-qwen3-vl-8b.server](reports/genie-qwen3-vl-8b.server.md) | — | — | — | 4.2 | — | — | — | — | — | — | 886 | HTTP Error 400: |
| [qwen3-4b-2507.cpu.server.rerun](reports/qwen3-4b-2507.cpu.server.rerun.md) | 1 | 3.33 | 27.75 | 14.1 | ✅ | 7/7 | ✅ | 11/12 | — | — | 4225 |  |
| ❌ [qwen3-8b.npu.server.rerun](reports/qwen3-8b.npu.server.rerun.md) | 1 | — | — | — | — | — | — | — | — | — | 6341 | server did not become healthy |
| ❌ [lfm2-8b-a1b.npu.server.rerun](reports/lfm2-8b-a1b.npu.server.rerun.md) | 1 | — | — | — | — | — | — | — | — | — | 5820 | server did not become healthy |
| [lfm2-8b-a1b.cpu.server.rerun](reports/lfm2-8b-a1b.cpu.server.rerun.md) | 1 | 7.81 | 49.06 | 4.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 6163 |  |
| ❌ [qwen3-4b-2507.npu.server.s1](reports/qwen3-4b-2507.npu.server.s1.md) | 1 | — | — | — | — | — | — | — | — | — | 4274 | server did not become healthy |
| [genie-qwen3-4b.server.fix](reports/genie-qwen3-4b.server.fix.md) | 0 | 17.31 | — | 4.2 | ✅ | 0/7 | ❌ | 0/12 | — | — | 11785 |  |
| [genie-qwen3-vl-8b.server.fix](reports/genie-qwen3-vl-8b.server.fix.md) | 0 | — | — | 6.2 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | — | 9561 |  |
| ❌ [qwen3-vl-4b.npu.server.vfix](reports/qwen3-vl-4b.npu.server.vfix.md) | 1 | — | — | — | — | — | — | — | — | — | 4311 | server did not become healthy |
| ❌ [qwen3-vl-8b.npu.server.vfix](reports/qwen3-vl-8b.npu.server.vfix.md) | 4 | — | — | — | — | — | — | — | — | — | 892 | server did not become healthy |
| ❌ [ministral-3-8b.npu.server.vfix](reports/ministral-3-8b.npu.server.vfix.md) | 4 | — | — | — | — | — | — | — | — | — | 886 | server did not become healthy |
| ❌ [gemma-4-e4b.npu.server.vfix](reports/gemma-4-e4b.npu.server.vfix.md) | 1 | — | — | — | — | — | — | — | — | — | 6878 | server did not become healthy |
| [genie-qwen3-4b.server.fix2](reports/genie-qwen3-4b.server.fix2.md) | 0 | 17.06 | — | 6.2 | ✅ | 0/7 | ❌ | 0/12 | — | — | 11508 |  |
| [genie-qwen3-vl-8b.server.fix2](reports/genie-qwen3-vl-8b.server.fix2.md) | 0 | — | — | 4.2 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | 4.2 | 9730 |  |
| [qwen3-vl-4b.npu.server.vfix2](reports/qwen3-vl-4b.npu.server.vfix2.md) | 4 | 12.27 | 386.42 | 6.1 | ✅ | 7/7 | ✅ | 11/12 | 3/4 | 9.8 | 6418 |  |
| [genie-qwen3-4b.server.fix3](reports/genie-qwen3-4b.server.fix3.md) | 0 | 16.3 | — | 6.2 | ✅ | 0/7 | ❌ | 0/12 | — | — | 11347 |  |
| [genie-qwen3-vl-8b.server.fix3](reports/genie-qwen3-vl-8b.server.fix3.md) | 0 | — | — | 6.3 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | 4.2 | 9679 |  |
| [qwen3-vl-8b.npu.server.vfix3](reports/qwen3-vl-8b.npu.server.vfix3.md) | 4 | 7.54 | 246.7 | 99.0 | ✅ | 2/7 | ❌ | 0/12 | 0/4 | — | 8469 |  |
| [ministral-3-8b.npu.server.vfix3](reports/ministral-3-8b.npu.server.vfix3.md) | 4 | 7.07 | 216.55 | 10.1 | ✅ | 7/7 | ✅ | 11/12 | 3/4 | 14.3 | 8531 |  |
| ❌ [gemma-4-e4b.npu.server.vfix3](reports/gemma-4-e4b.npu.server.vfix3.md) | 4 | — | — | — | — | — | — | — | — | — | 8090 | server did not become healthy |
| [genie-qwen3-4b.server.fix4](reports/genie-qwen3-4b.server.fix4.md) | 0 | 16.33 | — | 6.2 | ✅ | 0/7 | ❌ | 0/12 | — | — | 11601 |  |
| [genie-qwen3-vl-8b.server.fix4](reports/genie-qwen3-vl-8b.server.fix4.md) | 0 | — | — | 4.2 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | 4.3 | 9703 |  |
| [genie-qwen3-4b.server.fix5](reports/genie-qwen3-4b.server.fix5.md) | 0 | 16.45 | — | 76.6 | ✅ | 6/7 | ❌ | 10/12 | — | — | 7752 |  |
| [genie-qwen3-vl-8b.server.fix5](reports/genie-qwen3-vl-8b.server.fix5.md) | 0 | — | — | 6.3 | ❌ | 0/7 | ❌ | 0/12 | 0/4 | 4.0 | 9704 |  |
| [qwen3-4b-2507.npu.server.tr](reports/qwen3-4b-2507.npu.server.tr.md) | 4 | 12.79 | 395.46 | 6.1 | ✅ | 7/7 | ✅ | 12/12 | — | — | 5405 |  |
| [qwen3-4b-2507.cpu.server.tr](reports/qwen3-4b-2507.cpu.server.tr.md) | 0 | 10.0 | 27.81 | 4.0 | ✅ | 7/7 | ✅ | 11/12 | — | — | 4482 |  |
| [lfm2-8b-a1b.npu.server.tr](reports/lfm2-8b-a1b.npu.server.tr.md) | 4 | 23.97 | 511.4 | 8.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 6597 |  |
| [lfm2-8b-a1b.cpu.server.tr](reports/lfm2-8b-a1b.cpu.server.tr.md) | 0 | 24.7 | 49.0 | 10.0 | ✅ | 6/7 | ✅ | 10/12 | — | — | 5430 |  |

### 4.4 llama-bench

Table 3. `pp512` / `tg128` throughput in tokens/s at context depth 0 and 2048.

| Test | htp | pp512 | tg128 | pp512 @2k | tg128 @2k | Note |
|---|---|---:|---:|---:|---:|---|
| [qwen3-4b-2507.npu.bench](reports/qwen3-4b-2507.npu.bench.md) | — | 441.41 | 12.99 | 330.31 | 9.19 |  |
| [qwen3-4b-2507.cpu.bench](reports/qwen3-4b-2507.cpu.bench.md) | — | 33.59 | 10.2 | 20.77 | 5.1 |  |
| ❌ [qwen3-8b.npu.bench](reports/qwen3-8b.npu.bench.md) | — | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [lfm2-8b-a1b.npu.bench](reports/lfm2-8b-a1b.npu.bench.md) | — | 555.4 | 24.9 | 536.24 | 🥉 22.39 |  |
| [lfm2-8b-a1b.cpu.bench](reports/lfm2-8b-a1b.cpu.bench.md) | — | 50.52 | 25.09 | 46.72 | 7.82 |  |
| ❌ [granite-4-h-tiny.npu.bench](reports/granite-4-h-tiny.npu.bench.md) | — | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [phi-4-mini.npu.bench](reports/phi-4-mini.npu.bench.md) | — | 502.45 | 13.73 | 398.25 | 10.51 |  |
| ❌ [gemma-3-4b.npu.bench](reports/gemma-3-4b.npu.bench.md) | — | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| [qwen3-vl-4b.npu.bench](reports/qwen3-vl-4b.npu.bench.md) | — | 430.88 | 13.0 | 323.27 | 9.16 |  |
| [lfm2-vl-1.6b.npu.bench](reports/lfm2-vl-1.6b.npu.bench.md) | — | 🥇 1440.54 | 🥉 27.87 | 🥈 1254.22 | 🥇 26.59 |  |
| [qwen3-vl-8b.npu.bench](reports/qwen3-vl-8b.npu.bench.md) | — | 263.45 | 7.79 | 218.88 | 6.25 |  |
| [qwen3.5-4b.npu.bench](reports/qwen3.5-4b.npu.bench.md) | — | 159.97 | 8.79 | 153.63 | 8.51 |  |
| ❌ [qwen3.5-9b.npu.bench](reports/qwen3.5-9b.npu.bench.md) | — | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |
| ❌ [gemma-4-e4b.npu.bench](reports/gemma-4-e4b.npu.bench.md) | — | — | — | — | — | llama-bench rc=-6: ['warning: 360\t../csu/libc-start.c: No s… |
| ❌ [granite-4.2-8b.npu.bench](reports/granite-4.2-8b.npu.bench.md) | — | — | — | — | — | llama-bench rc=-9: ['ggml-hex: device 3: HTP3 (phys=0, virt=… |
| [llama-3.2-3b.npu.bench](reports/llama-3.2-3b.npu.bench.md) | — | 593.74 | 16.54 | 467.02 | 12.58 |  |
| [lfm2.5-1.2b.npu.bench](reports/lfm2.5-1.2b.npu.bench.md) | — | 🥈 1438.99 | 🥈 29.47 | 🥇 1261.92 | 🥈 25.74 |  |
| [phi-mini-moe.npu.bench](reports/phi-mini-moe.npu.bench.md) | — | 411.07 | 18.35 | 326.34 | 11.82 |  |
| [olmoe-1b-7b.npu.bench](reports/olmoe-1b-7b.npu.bench.md) | — | 🥉 639.39 | 🥇 30.45 | 🥉 583.62 | 17.61 |  |
| ❌ [gemma-3-4b.npu.bench.d0](reports/gemma-3-4b.npu.bench.d0.md) | 1 | — | — | — | — | llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed … |

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

## 5. Stability findings

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
- Everything ran on one board with one llama.cpp build (`7fe450e`). Newer llama.cpp builds change the Hexagon
  memory layout and may change both the single-session limits and the stability results.
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
| [`docs/board-notes.md`](docs/board-notes.md) | Board setup, kernel and firmware notes, incident log |

## License and citation

Code (`suite/`, `tools/`) is under the MIT license; results, transcripts and documentation are under CC BY 4.0.
See [LICENSE](LICENSE). Citation metadata is in [CITATION.cff](CITATION.cff).
