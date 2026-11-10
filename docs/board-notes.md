# Board setup and stability notes

Arduino VENTUNO Q (Qualcomm QCS8300), Ubuntu image from Arduino. Notes kept while running the benchmark.

> **Historical log.** This is the running log from 2026-11-06 to 11-09, kept as written. Later results supersede
> some of it: the "~4 GB per process" mapping limit was partly llama.cpp's default buffer chunk size (fixed by
> `GGML_HEXAGON_MBUF=256,256`; the real limit is ~3.1 GiB per session, four sessions per process), Gemma 4 E4B runs
> through Arduino's App Lab runner, and the "still queued" items were all run. For current findings see the
> [README](../README.md), [stability fixes](stability-fixes.md) and [environments](../reports/environments.md).

### Canonical telemetry off (2026-11-08)

```bash
sudo systemctl disable --now motd-news.timer apport-autoreport.timer ua-timer.timer \
  apport.service ubuntu-advantage.service pollinate.service kerneloops.service
sudo systemctl mask motd-news.service motd-news.timer apport.service apport-autoreport.timer \
  apport-autoreport.service apport-forward@.service whoopsie.service whoopsie.path \
  pollinate.service ua-timer.timer ua-timer.service ubuntu-advantage.service kerneloops.service
sudo sed -i 's/^ENABLED=1/ENABLED=0/' /etc/default/motd-news
sudo sed -i 's/^enabled=1/enabled=0/' /etc/default/apport
sudo pro config set apt_news=false
```

| What | Called | Now |
|------|--------|-----|
| `motd-news` | login-banner news from Canonical | masked, `ENABLED=0` |
| `apport` / `whoopsie` | crash reports to Canonical | masked, `enabled=0` |
| `kerneloops` | kernel oops reports | masked |
| `pollinate` | entropy from `entropy.ubuntu.com` at boot | masked |
| `ubuntu-advantage` / `ua-timer` | Ubuntu Pro status checks, apt news | masked, `apt_news=false` |

Revert: `systemctl unmask` + `enable` the units and flip the two `/etc/default` flags back.

**Deliberately left on:** apt / `unattended-upgrades`, snapd refresh, `fwupd`, NTP
(`ntp.ubuntu.com`), Arduino's apt repo (`apt-repo.arduino.cc`), `api2.arduino.cc` and
`ghcr.io/arduino` pulls by App CLI. These are the update paths, not telemetry.

### Packages (2026-11-08)

- Booted the already-installed kernel `6.8.0-1089-qcom` (stock image ran `1078`).
- **Arduino Cloud agent blocked**: `arduino-ventunoq` 0.4.0 pulls in `arduino-cloud-connector`,
  so it is pinned to never install. App CLI's NOPASSWD self-update can't pull it in either;
  `arduino-ventunoq` stays on 0.2.0.

  ```
  # /etc/apt/preferences.d/no-arduino-cloud
  Package: arduino-cloud-connector
  Pin: release *
  Pin-Priority: -1
  ```
- `linux-firmware-dragonwing` stays held. Its 20260825 build breaks the NPU (see the LLM
  section); the 20260612 files are what's on disk.

### Desktop off, boots to console (2026-11-08)

GNOME + update-manager + Evolution/tracker held ~800 MB. Stopped and disabled:

```bash
sudo systemctl set-default multi-user.target
sudo systemctl stop gdm
```

Idle RAM used went from ~1.75 GB to ~0.98 GB (14.3 GB available).
Revert: `sudo systemctl set-default graphical.target && sudo systemctl start gdm`.

### Genie LLM API on the LAN (2026-11-08)

`/opt/genie/compose.yaml` runs Qualcomm's `genai-llm-vlm-service:1.5.0` the same way Arduino's
`genie` service does, but bound to `0.0.0.0:9001`, `restart: unless-stopped`, and one model
loaded at a time (`MAX_ACTIVE_MODELS=1`). **No auth, LAN only** (board has no public IP; `ufw`
is inactive).

- Endpoint: `http://<board-ip>:9001/v1` (OpenAI-compatible: `/v1/models`,
  `/v1/chat/completions`, streaming supported)
- Models dir: `/var/lib/arduino-app-cli/models/genai/` (every Genie bundle in there is listed)
- Manage: `docker compose -f /opt/genie/compose.yaml up -d | down | logs -f`

```bash
curl http://<board-ip>:9001/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"qwen3_4b_instruct_2507","messages":[{"role":"user","content":"hi"}]}'
```

Genie bundles are fetched with Arduino's downloader container (needs no AI Hub account):

```bash
docker run --rm -v /var/lib/arduino-app-cli/models/genai:/models \
  -e model_type=genie -e model_name=qwen3_8b -e models_repository=genai \
  -e model_directory=qwen3_8b-genie-w4a16-qualcomm_qcs8275 \
  -e quantization=w4a16 -e chipset=qualcomm-qcs8275 \
  --entrypoint /app/ai_hub/ai_hub_model_downloader.sh \
  ghcr.io/arduino/app-bricks/models-downloader:0.13.2
```

### NPU crash guards (2026-11-08)

After a crash-looping llama-server leaked 7.4 GB of fastrpc DMA-bufs and the board froze on
reboot (no log after `systemd-shutdown` SIGTERM, needed a manual power cycle):

- `/usr/local/sbin/npu-precheck.sh` refuses to start when more than 1500 MB of DMA-buf is already
  pinned (`NPU_DMABUF_LIMIT_MB` overrides). Leaked buffers only come back with a reboot.
- `llama-server.service`: `ExecStartPre=+/usr/local/sbin/npu-precheck.sh`, `-c 4096` (8192 OOMs the
  NPU mapping), `RestartSec=30`, `StartLimitIntervalSec=300` / `StartLimitBurst=2` in `[Unit]`.
  Never auto-restart an NPU service without a cap.
- `/etc/systemd/system.conf.d/10-watchdog.conf`: `RuntimeWatchdogSec=30s`, `RebootWatchdogSec=2min`
  on `qcom_wdt` (stock: 10 min on reboot only).
- `/etc/sysctl.d/90-hang-panic.conf`: `kernel.panic=10`, `softlockup_panic=1`,
  `hung_task_panic=1` with `hung_task_timeout_secs=120` (was 300 until 2026-11-09), so a stuck task panics and reboots.
- Crash logs: `efi_pstore` loaded at boot (`/etc/modules-load.d/efi-pstore.conf`), panic dumps are
  archived by `systemd-pstore` to `/var/lib/systemd/pstore/`. Not proven yet that this UEFI keeps
  the variables. Wi-Fi can't do netconsole; serial is `ttyMSM0` 115200.
- Docker would not help here: the leak is in the kernel driver that containers share.

Second freeze (2026-11-08 22:16 UTC): the suite's 5th self-reboot, with 833 MB still pinned, hung
after journald stopped, same as the first one. It stayed hung until the power cycle the next morning.
There is no RTC, so the boot after that started with the old clock, and the driver log shows a fake
10 h gap until NTP synced at 08:34. The `RebootWatchdogSec` above never fired because the
kernel's watchdog core defaults to `stop_on_reboot=Y` and disarms `qcom_wdt` as the reboot starts.
Fix: `/etc/default/grub.d/99-zz-watchdog-reboot.cfg` adds `watchdog.stop_on_reboot=0`, so a hung
warm reboot now gets reset by the hardware watchdog within about 30 s. Confirmed active after a
reboot (`/sys/module/watchdog/parameters/stop_on_reboot` = 0). Not yet seen rescuing a real hang.
Reboots 1 to 4 that night, at lower pinned memory, were all fine.

## LLM benchmark (2026-11-08)

Two NPU runtimes ship with the board: Arduino's **llama.cpp NPU runner**
(`ghcr.io/arduino/app-bricks/llamacpp-npu-runner:0.13.2`, any GGUF, port 9999) and Qualcomm's
**Genie** service (`genai-llm-vlm-service:1.5.0`, AI Hub pre-compiled models only, OpenAI-style
API on port 9001). Both were run with the same devices, mounts and limits as Arduino's own
compose files (`/var/lib/arduino-app-cli/assets/0.13.2/services/arduino/{llamacpp,genie}/`).
The pre-pulled runner `0.11.2` cannot open an NPU session (`error 0x80000406`); use `0.13.2`.

| Model | Runtime | Device | Prompt t/s | Gen t/s | Peak RAM used |
|-------|---------|--------|-----------:|--------:|--------------:|
| Qwen3-4B Instruct 2507 (w4a16) | Genie | NPU | — (TTFT 0.11 s, 30-token prompt) | **16.5** | ~8.8 GB |
| Qwen3-8B (w4a16, 5 parts, 5.2 GB) | Genie | NPU | fails to load | — | — |
| Qwen3-VL-8B Instruct (w4a16, 6.9 GB) | Genie | NPU | fails to load | — | — |
| Qwen3-8B Q4_0 (bartowski GGUF) | llama.cpp | NPU | fails to load | — | — |
| Qwen3-8B Q4_0 | llama.cpp | CPU (cores 0-3) | 18.5 | 3.8 ± 2.2 | ~6.2 GB |
| Qwen3-14B Q4_0 | llama.cpp | NPU | fails to load | — | — |
| Qwen3-14B Q4_0 | llama.cpp | CPU (cores 0-3) | 9.2 | 2.7 ± 0.5 | ~9.6 GB |

- llama.cpp: `llama-bench -p 512 -n 128 -r 2 -t 4`, `-fa on` for NPU runs. Peak RAM is
  system-wide `used` (baseline ~1.8 GB).
- Genie: 3 streamed requests of 256 tokens; the first one includes the ~23 s model load.
- **llama.cpp's Hexagon backend (marked experimental) runs out of NPU-mappable memory at
  roughly 4 GB** (`rpcmem_alloc failed`). Splitting across two sessions (`GGML_HEXAGON_NDEV=2`)
  fails too. That matches Arduino only listing ≤4B models for llama.cpp on this board.
- **Genie 8B fails the same way**: Qwen3-8B maps 4 of 5 parts, then
  `fastrpc memory map ... length 876609536 failed` / `Could not map shared weights buffer`, and
  the kernel logs `qcom,fastrpc-cb ... compute-cb@N: failed to map buffer`. The NPU's IOMMU
  mapping tops out around 4 GB per process, so Arduino's advertised Qwen 3-VL-8B does not run
  on this board either. Tried on 2026-11-08, none of it helped:
  - kernel `6.8.0-1089-qcom` (now booted, kept): 8B still fails, 4B fine.
  - `linux-firmware-dragonwing` 20260825 (new `cdsp0.mbn` + `fastrpc_shell_3`): **regression**,
    even the 4B fails to map. Rolled back by restoring the 20260612 files from
    `/var/backups/fw-guard/dragonwing-20260612-files.tar` + `update-initramfs -u`.
    **dpkg still records 20260825** (the old .deb is gone from the repo) and the package is on
    hold, so apt won't touch it; just don't `apt-mark unhold` it. The disabled one-shot
    rollback guard is in `/usr/local/sbin/fw-guard.sh` / `fw-guard.service`.
- Genie lists only 8B as its largest build for `qualcomm-qcs8275` (Qwen3-8B, Qwen3-VL-8B);
  Llama / Mistral / Falcon / Granite are licence-gated. GPT-OSS-20B exists only as GenieX
  (llama.cpp).
- **8B does run on the NPU with current upstream llama.cpp split over several sessions**
  (2026-11-08). Prebuilt from [ThinkOffApp/ventuno](https://github.com/ThinkOffApp/ventuno)
  release `v0.1-7fe450e` (`pkg-linux-7fe450e.tgz`, sha256 `3940dbafd8e2…38e7eb`), installed
  without sudo into `~/llama-npu` (its `build/install-on-ventuno.sh` just untars and symlinks
  `libcdsprpc.so`). A socket monitor on every `~/llama-npu` process saw **no network
  connections** during install, device probe or the benchmark. Arduino's runner fails because
  its script sets `GGML_HEXAGON_NDEV`; ggml itself reads `GGML_HEXAGON_DEVICES`.

  ```bash
  D=~/llama-npu; export LD_LIBRARY_PATH=$D/lib ADSP_LIBRARY_PATH=$D/lib
  GGML_HEXAGON_DEVICES=3 taskset -c 0-3 $D/bin/llama-bench -m Qwen_Qwen3-8B-Q4_0.gguf \
    -dev HTP0/HTP1/HTP2 -ngl 99 -t 4 -fa 1 -p 512 -n 128 -r 2
  ```

  | Model | Runtime | Device | Prompt t/s | Gen t/s | Peak RAM used |
  |-------|---------|--------|-----------:|--------:|--------------:|
  | Qwen3-8B Q4_0 (bartowski) | upstream llama.cpp `7fe450e` | NPU, 3 sessions | **266.7** | **7.8** | ~6.5 GB |

  Generation is memory-bandwidth bound (~7-8 t/s for 8B), but prompt reading is 14x the CPU.

  **What "3 sessions" means and what it unlocks:** there is one NPU. The ~3.5 GB cap is per
  fastrpc session, so `GGML_HEXAGON_DEVICES=N` opens N sessions on the same NPU and llama.cpp
  splits the layers across them (HTP0 → HTP1 → HTP2, run in sequence, not in parallel). It is a
  fit fix, not a speed-up. With that, the ceiling becomes RAM: ~14 GB free headless, minus KV
  cache and headroom ≈ **10-11 GB of GGUF max** (a 13.7 GB model OOMs per ThinkOffApp).
  Generation speed scales roughly with bytes read per token: dense 14B Q4_0 (~8.5 GB) should
  land around 4 t/s; MoE models (few active params per token) are the way to get bigger
  without the speed falling off a cliff.
- **NPU buffer leak:** after a failed or killed NPU load, the DMA buffers stay pinned
  (4.9 GB seen in `/sys/kernel/debug/dma_buf/bufinfo` with nothing running) and later loads
  fail to map. Known fastrpc bug, fixed in Toradex's Torizon BSP but not in Ubuntu's `qcom`
  kernel. **Reboot after any crashed NPU load.**
- Takeaway: Genie Qwen3-4B (16.5 t/s) for chat speed; upstream llama.cpp Qwen3-8B (7.8 t/s)
  when quality matters more. CPU-only runs are too slow
  to bother with; the GGUFs were deleted.
- Benchmark scripts and raw results are in `~/llm-bench` on the board.

## Overnight LLM suite (2026-11-08/09, stopped, 31 results)

Full results, raw JSON, request/reply transcripts and the runner live in
[](RESULTS.md). The tables below are the early partial snapshot.

Exact kernel, modules, firmware and llama.cpp/Genie versions are in the results file's
"Test environment" section. No newer kernel exists; 1089 already has the known fastrpc fixes.

Incidents on 2026-11-09 (all NPU, kernel 6.8.0-1089-qcom):
- Granite 4.2 8B llama-bench wedged the NPU (`dspqueue wait_signal_locked` timeouts) for 48 min.
  I SIGKILLed it, the suite's reboot went through fine, then the board hard-froze ~15 s into the
  Granite 4.2 server load. The hardware watchdog did not reset it, so it needed a power cycle.
- Llama 3.2 3B llama-server stalled mid-reply at token 196 (NPU stopped answering). The suite was
  paused before its 30 min guard could kill it, and the board was powered off cleanly.
- Takeaway: the NPU can wedge on any model size, and killing or tearing down a wedged session can
  freeze the box. Only run NPU work when someone can power-cycle it, or behind an HA smart plug,
  until there's a kernel with fastrpc fixes. Skipped NPU benches are marked `skipped-unsafe`.
- Suite reboots now go through sysrq (`s`ync, `u`nmount read-only, re`b`oot) instead of `systemctl reboot`,
  so the kernel never runs the fastrpc teardown that hangs. Likely cause per research: unmerged
  "misc: fastrpc: fix context leak and hang on signal-interrupted invoke" (2026, not in 1089).
- The suite (`veni-bench.service`) is disabled. `suite.py` now stops itself instead of killing a
  llama-bench that runs past 15 min.

`~/llm-bench/suite/suite.py` runs as `veni-bench.service`, one item at a time, and disables itself when
the queue is done. Per model: `llama-bench` (pp512/tg128, empty and 2048-token context, 3 reps)
and a server pass through the OpenAI API. Server pass: load time, generation speed, prefill on a 1.7k-token prompt with a
needle, 7 tool-calling cases (pick tool, args, date format, no-tool, parallel calls, use tool result),
JSON schema output, 12-question quiz, 4 vision images where supported. Qwen3 thinking off.
All llama.cpp runs: upstream `7fe450e`, Q4_0, 4 HTP sessions, `-c 4096`, `-fa on`, `-t 4` on cores
0-3. Reboots when more than 1.2 GB of DMA-buf is pinned. Raw data: `results.jsonl`, request/reply transcripts in
`logs/*.transcript.jsonl`.

Partial results (17 of 51 items, 22:11):

| Model | Dev | Load | Gen t/s | Long-prompt prefill t/s | Tools | JSON | Quiz | Needle | Vision | Peak RAM |
|---|---|---:|---:|---:|---:|:-:|---:|:-:|---:|---:|
| Qwen3-4B-2507 | NPU | 6 s | 12.6 | 395 | 7/7 | ✓ | 12/12 | ✓ | – | 6.3 GB |
| Qwen3-4B-2507 | CPU | 8 s | 9.9 | 28 | 7/7 | ✓ | 11/12 | ✓ | – | 5.4 GB |
| Qwen3-8B | NPU | 58 s | 7.6 | 250 | 7/7 | ✓ | 10/12 | ✓ | – | 7.4 GB |
| LFM2-8B-A1B (MoE) | NPU | 8 s | 23.5 | 511 | 6/7 | ✓ | 10/12 | ✓ | – | 6.7 GB |
| LFM2-8B-A1B (MoE) | CPU | 8 s | 24.5 | 49 | 6/7 | ✓ | 10/12 | ✓ | – | 5.5 GB |
| Phi-4-mini | NPU | 6 s | 14.0 | 457 | 2/7 | ✓ | 9/12 | ✓ | – | 5.4 GB |
| Gemma 3 4B | NPU | 18 s | 13.3 | 446 | 1/7 | ✓ | 12/12 | ✓ | 4/4 | 7.0 GB |
| Granite 4.0 H Tiny | NPU | 54 s | hung on first request (20 min, needed SIGKILL) | | | | | | | 8.6 GB |

llama-bench (t/s):

| Model | Dev | pp512 | tg128 | pp512 @2k ctx | tg128 @2k ctx |
|---|---|---:|---:|---:|---:|
| Qwen3-4B-2507 | NPU | 441 | 13.0 | 330 | 9.2 |
| Qwen3-4B-2507 | CPU | 34 | 10.2 | 21 | 5.1 |
| LFM2-8B-A1B | NPU | 555 | 24.9 | 536 | 22.4 |
| LFM2-8B-A1B | CPU | 51 | 25.1 | 47 | 7.8 |
| Phi-4-mini | NPU | 502 | 13.7 | 398 | 10.5 |
| Qwen3-VL-4B | NPU | 431 | 13.0 | 323 | 9.2 |

Qwen3-8B, Granite H Tiny and Gemma 3 4B failed llama-bench with `fastrpc_mmap failed`. The 2048-depth
run needs more mapping, and their server tests worked. Depth-0 retries on a fresh boot are queued.

Takeaways so far:
- Qwen3-4B-2507 on the NPU is the best all-rounder (perfect tools and quiz, 12.6 t/s, 6 s load) and
  beats Qwen3-8B everywhere.
- LFM2-8B-A1B generates as fast on CPU as on NPU (~24 t/s, memory-bandwidth bound). The NPU wins
  10-14x on prefill and holds speed with 2k context; on CPU, tg drops to 7.8.
- Gemma 3 4B: best vision so far, but it can't do tool calls. Phi-4-mini is weak at tools too.

Still queued: Qwen3-VL-4B/8B, LFM2-VL-1.6B, Qwen3.5-4B/9B, Gemma 4 E4B, Granite 4.2 8B,
Ministral 3 8B, Llama 3.2 3B, LFM2.5-1.2B, Phi-mini-MoE, OLMoE-1B-7B, Genie Qwen3-4B / VL-8B,
transcript reruns, depth-0 retries.

