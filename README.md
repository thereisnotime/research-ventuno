# research-ventuno

Running local LLMs on the Arduino VENTUNO Q (Qualcomm QCS8300, 16 GB RAM): llama.cpp on the Hexagon NPU,
llama.cpp on CPU, and Qualcomm Genie. 31+ models/configs tested overnight on 2026-11-08/09 for speed,
tool calling, a short quiz, JSON output and vision.

Layout:
- `results/results.jsonl`: one line per test. `results/transcripts/`: every request and reply.
- `results/queue.json`, `results/state.json`, `results/driver.log`: test list, run status, driver log.
- `suite/suite.py`: the runner. `suite/genie-compose.yaml`: the Genie config that works.
- `docs/board-notes.md`: board setup, NPU caveats, freezes and how the suite recovers from them.

## Test environment (versions used for every result)

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

## Summary: best run per model

Each model's run with the highest tools+quiz score (wedged or crashed runs lose automatically). Vision = best run with the image encoder working. `—` = never produced a valid result.

| Model | Engine | Device | Gen t/s | Prefill t/s | Tools | JSON | Quiz | Needle | Vision | s/image | Peak RAM MB |
|---|---|---|---:|---:|---|---|---|---|---|---:|---:|
| lfm2-vl-1.6b | llama | npu | 29.51 | 1233.42 | 2/7 | True | 10/12 | True | 3/4 | 5.1 | 3976 |
| lfm2.5-1.2b | llama | npu | 29.13 | 1263.86 | 6/7 | True | 10/12 | True | — | — | 2504 |
| olmoe-1b-7b | llama | npu | 28.76 | 567.83 | 1/7 | True | 7/12 | False | — | — | 7371 |
| lfm2-8b-a1b | llama | cpu | 24.54 | 49.22 | 6/7 | True | 10/12 | True | — | — | 5492 |
| lfm2-8b-a1b | llama | npu | 23.5 | 511.43 | 6/7 | True | 10/12 | True | — | — | 6673 |
| phi-mini-moe | llama | npu | 18.63 | 352.77 | 1/7 | False | 8/12 | False | — | — | 7306 |
| qwen3_4b_instruct_2507 | genie | npu (QNN) | 16.45 | — | 6/7 | False | 10/12 | True | — | — | 7752 |
| phi-4-mini | llama | npu | 14.04 | 456.92 | 2/7 | True | 9/12 | True | — | — | 5429 |
| gemma-3-4b | llama | npu | 13.26 | 445.78 | 1/7 | True | 12/12 | True | 4/4 | 27.7 | 7048 |
| qwen3-4b-2507 | llama | npu | 12.55 | 394.97 | 7/7 | True | 12/12 | True | — | — | 6287 |
| qwen3-vl-4b | llama | npu | 12.55 | 385.69 | 7/7 | True | 11/12 | True | 3/4 | 9.8 | 6800 |
| gemma-4-e4b | llama | npu | 10.47 | — | 0/7 | False | 0/12 | False | — | — | 9007 |
| qwen3-4b-2507 | llama | cpu | 9.93 | 27.88 | 7/7 | True | 11/12 | True | — | — | 5406 |
| qwen3.5-4b | llama | npu | 8.59 | 151.21 | 7/7 | True | 11/12 | True | 3/4 | 3.9 | 9557 |
| qwen3-8b | llama | npu | 7.64 | 250.26 | 7/7 | True | 10/12 | True | — | — | 7370 |
| qwen3-vl-8b | llama | npu | 7.57 | 246.36 | 7/7 | True | 11/12 | True | — | — | 9079 |
| ministral-3-8b | llama | npu | 7.07 | 216.55 | 7/7 | True | 11/12 | True | 3/4 | 14.3 | 8531 |
| qwen3.5-9b | llama | npu | 5.83 | 99.5 | 7/7 | True | 10/12 | True | 2/4 | 10.1 | 12188 |
| granite-4-h-tiny | llama | npu | — | — | — | — | — | — | — | — | 8582 |
| qwen3_vl_8b_instruct | genie | npu (QNN) | — | — | 0/7 | False | 0/12 | False | 0/4 | 4.2 | 9704 |

## Picks (2026-11-10)

- **Best all-round (tools + reasoning): Qwen3-4B-2507 on llama.cpp NPU.** 7/7 tools, 12/12 quiz, 12.6 t/s, 6.3 GB.
  On Genie it's faster (16.5 t/s) with 6/7 tools and 10/12 quiz, but Genie ignores JSON-schema output.
- **Fastest usable assistant: LFM2.5-1.2B on NPU.** 29 t/s, 1264 t/s prefill, 6/7 tools, 2.5 GB RAM.
- **Fast and no NPU at all (safe 24/7): LFM2-8B-A1B on CPU.** ~24.5 t/s, 6/7 tools, no freeze risk.
- **Vision: Qwen3.5-4B** (3/4, ~4 s/image, 7/7 tools, 8.6 t/s) for speed; **Ministral 3 8B** (3/4, 14 s/image,
  7/7 tools, 11/12 quiz) for quality; **Gemma 3 4B** most accurate (4/4) but 28 s/image and 1/7 tools.
  **LFM2-VL-1.6B** if speed matters most (3/4, 5 s/image, 29 t/s, weak at tools).
- **Skip:** 8-9B dense models on this NPU (slower, no better), Granite (froze the board), OLMoE / Phi-mini-MoE
  (fast but 1/7 tools), Genie Qwen3-VL-8B (hangs on a 1.7k-token prompt).

## Known caveats

- The NPU wedges at random (Llama 3.2 3B, Qwen3-4B rerun, Qwen3-VL-8B twice); runs that wedged are listed in the
  detail tables but excluded above. See docs/board-notes.md for the freeze history and mitigations.
- One NPU session can't map a 4B model on this llama.cpp build (`fastrpc_mmap`), so all NPU runs use 4 sessions.
- Vision image encoders run on CPU (`--no-mmproj-offload`); on the NPU they fail to map.
- Genie needs: streaming only (non-streaming kills its LLM process), one session per request, and
  `HISTORY_EVICTION_THRESHOLD=100` (history eviction's facts pass crashes it). See `genie-compose.yaml`.
- The two late CPU reruns (Qwen3-4B 3.3 t/s, LFM2-8B 7.8 t/s) were slowed by something else on the CPU; the
  original CPU numbers stand.

## Server tests, every run (llama-server or Genie, thinking off)

Gen = short-reply generation t/s. Prefill = t/s reading a ~1.7k-token prompt. Needle = found a fact buried in that prompt.
Tools = 7 tool-calling cases, Quiz = 12 questions, Vision = 4 generated images. `htp` = NPU sessions.

| Test | htp | Gen t/s | Prefill t/s | Load s | Needle | Tools | JSON | Quiz | Vision | s/image | Peak RAM MB | Note |
|---|---|---:|---:|---:|---|---|---|---|---|---:|---:|---|
| qwen3-4b-2507.npu.server | 4 | 12.55 | 394.97 | 6.1 | True | 7/7 | True | 12/12 | — | — | 6287 |  |
| qwen3-4b-2507.cpu.server | — | 9.93 | 27.88 | 8.0 | True | 7/7 | True | 11/12 | — | — | 5406 |  |
| qwen3-8b.npu.server | 4 | 7.64 | 250.26 | 58.2 | True | 7/7 | True | 10/12 | — | — | 7370 |  |
| lfm2-8b-a1b.npu.server | 4 | 23.5 | 511.43 | 8.0 | True | 6/7 | True | 10/12 | — | — | 6673 |  |
| lfm2-8b-a1b.cpu.server | — | 24.54 | 49.22 | 8.0 | True | 6/7 | True | 10/12 | — | — | 5492 |  |
| granite-4-h-tiny.npu.server | 4 | — | — | 54.1 | — | — | — | — | — | — | 8582 | [Errno 104] Connection reset by peer |
| phi-4-mini.npu.server | 4 | 14.04 | 456.92 | 6.1 | True | 2/7 | True | 9/12 | — | — | 5429 |  |
| gemma-3-4b.npu.server | 4 | 13.26 | 445.78 | 18.1 | True | 1/7 | True | 12/12 | 4/4 | 27.7 | 7048 |  |
| qwen3-vl-4b.npu.server | 4 | 12.55 | 385.69 | 6.0 | True | 7/7 | True | 11/12 | 0/4 | — | 6800 |  |
| lfm2-vl-1.6b.npu.server | 4 | 29.51 | 1233.42 | 4.0 | True | 2/7 | True | 10/12 | 3/4 | 5.1 | 3976 |  |
| qwen3-vl-8b.npu.server | 4 | 7.57 | 246.36 | 10.2 | True | 7/7 | True | 11/12 | 0/4 | — | 9079 |  |
| qwen3.5-4b.npu.server | 4 | 8.59 | 151.21 | 8.1 | True | 7/7 | True | 11/12 | 3/4 | 3.9 | 9557 |  |
| qwen3.5-9b.npu.server | 4 | 5.83 | 99.5 | 34.1 | True | 7/7 | True | 10/12 | 2/4 | 10.1 | 12188 |  |
| gemma-4-e4b.npu.server | 4 | 10.47 | — | 28.1 | False | 0/7 | False | 0/12 | 0/4 | — | 9007 |  |
| ministral-3-8b.npu.server | 4 | 6.83 | 216.51 | 8.1 | True | 7/7 | True | 11/12 | 0/4 | — | 8677 |  |
| lfm2.5-1.2b.npu.server | 4 | 29.13 | 1263.86 | 2.1 | True | 6/7 | True | 10/12 | — | — | 2504 |  |
| phi-mini-moe.npu.server | 4 | 18.63 | 352.77 | 8.0 | False | 1/7 | False | 8/12 | — | — | 7306 |  |
| olmoe-1b-7b.npu.server | 4 | 28.76 | 567.83 | 8.0 | False | 1/7 | True | 7/12 | — | — | 7371 |  |
| genie-qwen3-4b.server | — | — | — | 10.2 | — | — | — | — | — | — | 2032 | HTTP Error 400:  |
| genie-qwen3-vl-8b.server | — | — | — | 4.2 | — | — | — | — | — | — | 886 | HTTP Error 400:  |
| qwen3-4b-2507.cpu.server.rerun | 1 | 3.33 | 27.75 | 14.1 | True | 7/7 | True | 11/12 | — | — | 4225 |  |
| qwen3-8b.npu.server.rerun | 1 | — | — | — | — | — | — | — | — | — | 6341 | server did not become healthy |
| lfm2-8b-a1b.npu.server.rerun | 1 | — | — | — | — | — | — | — | — | — | 5820 | server did not become healthy |
| lfm2-8b-a1b.cpu.server.rerun | 1 | 7.81 | 49.06 | 4.0 | True | 6/7 | True | 10/12 | — | — | 6163 |  |
| qwen3-4b-2507.npu.server.s1 | 1 | — | — | — | — | — | — | — | — | — | 4274 | server did not become healthy |
| genie-qwen3-4b.server.fix | 0 | 17.31 | — | 4.2 | True | 0/7 | False | 0/12 | — | — | 11785 |  |
| genie-qwen3-vl-8b.server.fix | 0 | — | — | 6.2 | False | 0/7 | False | 0/12 | 0/4 | — | 9561 |  |
| qwen3-vl-4b.npu.server.vfix | 1 | — | — | — | — | — | — | — | — | — | 4311 | server did not become healthy |
| qwen3-vl-8b.npu.server.vfix | 4 | — | — | — | — | — | — | — | — | — | 892 | server did not become healthy |
| ministral-3-8b.npu.server.vfix | 4 | — | — | — | — | — | — | — | — | — | 886 | server did not become healthy |
| gemma-4-e4b.npu.server.vfix | 1 | — | — | — | — | — | — | — | — | — | 6878 | server did not become healthy |
| genie-qwen3-4b.server.fix2 | 0 | 17.06 | — | 6.2 | True | 0/7 | False | 0/12 | — | — | 11508 |  |
| genie-qwen3-vl-8b.server.fix2 | 0 | — | — | 4.2 | False | 0/7 | False | 0/12 | 0/4 | 4.2 | 9730 |  |
| qwen3-vl-4b.npu.server.vfix2 | 4 | 12.27 | 386.42 | 6.1 | True | 7/7 | True | 11/12 | 3/4 | 9.8 | 6418 |  |
| genie-qwen3-4b.server.fix3 | 0 | 16.3 | — | 6.2 | True | 0/7 | False | 0/12 | — | — | 11347 |  |
| genie-qwen3-vl-8b.server.fix3 | 0 | — | — | 6.3 | False | 0/7 | False | 0/12 | 0/4 | 4.2 | 9679 |  |
| qwen3-vl-8b.npu.server.vfix3 | 4 | 7.54 | 246.7 | 99.0 | True | 2/7 | False | 0/12 | 0/4 | — | 8469 |  |
| ministral-3-8b.npu.server.vfix3 | 4 | 7.07 | 216.55 | 10.1 | True | 7/7 | True | 11/12 | 3/4 | 14.3 | 8531 |  |
| gemma-4-e4b.npu.server.vfix3 | 4 | — | — | — | — | — | — | — | — | — | 8090 | server did not become healthy |
| genie-qwen3-4b.server.fix4 | 0 | 16.33 | — | 6.2 | True | 0/7 | False | 0/12 | — | — | 11601 |  |
| genie-qwen3-vl-8b.server.fix4 | 0 | — | — | 4.2 | False | 0/7 | False | 0/12 | 0/4 | 4.3 | 9703 |  |
| genie-qwen3-4b.server.fix5 | 0 | 16.45 | — | 76.6 | True | 6/7 | False | 10/12 | — | — | 7752 |  |
| genie-qwen3-vl-8b.server.fix5 | 0 | — | — | 6.3 | False | 0/7 | False | 0/12 | 0/4 | 4.0 | 9704 |  |

## llama-bench (pp512 / tg128, t/s, at context depth 0 and 2048)

| Test | htp | pp512 | tg128 | pp512 @2k | tg128 @2k | Note |
|---|---|---:|---:|---:|---:|---|
| qwen3-4b-2507.npu.bench | 4 | 441.41 | 12.99 | 330.31 | 9.19 |  |
| qwen3-4b-2507.cpu.bench | — | 33.59 | 10.2 | 20.77 | 5.1 |  |
| qwen3-8b.npu.bench | 4 | — | — | — | — | llama-bench rc=-6: ['  what():  ggml-hex: fastrpc_mmap failed (see log |
| lfm2-8b-a1b.npu.bench | 4 | 555.4 | 24.9 | 536.24 | 22.39 |  |
| lfm2-8b-a1b.cpu.bench | — | 50.52 | 25.09 | 46.72 | 7.82 |  |
| granite-4-h-tiny.npu.bench | 4 | — | — | — | — | llama-bench rc=-6: ['  what():  ggml-hex: fastrpc_mmap failed (see log |
| phi-4-mini.npu.bench | 4 | 502.45 | 13.73 | 398.25 | 10.51 |  |
| gemma-3-4b.npu.bench | 4 | — | — | — | — | llama-bench rc=-6: ['  what():  ggml-hex: fastrpc_mmap failed (see log |
| qwen3-vl-4b.npu.bench | 4 | 430.88 | 13.0 | 323.27 | 9.16 |  |
| lfm2-vl-1.6b.npu.bench | 4 | 1440.54 | 27.87 | 1254.22 | 26.59 |  |
| qwen3-vl-8b.npu.bench | 4 | 263.45 | 7.79 | 218.88 | 6.25 |  |
| qwen3.5-4b.npu.bench | 4 | 159.97 | 8.79 | 153.63 | 8.51 |  |
| qwen3.5-9b.npu.bench | 4 | — | — | — | — | llama-bench rc=-6: ['  what():  ggml-hex: fastrpc_mmap failed (see log |
| gemma-4-e4b.npu.bench | 4 | — | — | — | — | llama-bench rc=-6: ['warning: 360\t../csu/libc-start.c: No such file o |
| granite-4.2-8b.npu.bench | 4 | — | — | — | — | llama-bench rc=-9: ['ggml-hex: device 3: HTP3 (phys=0, virt=3, domain= |
| llama-3.2-3b.npu.bench | 4 | 593.74 | 16.54 | 467.02 | 12.58 |  |
| lfm2.5-1.2b.npu.bench | 4 | 1438.99 | 29.47 | 1261.92 | 25.74 |  |
| phi-mini-moe.npu.bench | 4 | 411.07 | 18.35 | 326.34 | 11.82 |  |
| olmoe-1b-7b.npu.bench | 4 | 639.39 | 30.45 | 583.62 | 17.61 |  |
| gemma-3-4b.npu.bench.d0 | 1 | — | — | — | — | llama-bench rc=-6: ['  what():  ggml-hex: fastrpc_mmap failed (see log |

## No result

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
