# Stability fixes

[← README](../README.md) · [board notes](board-notes.md) · [environments](../reports/environments.md)

Everything changed on the board, in the runner and in Genie to make the benchmark survive the NPU's failure modes,
in the order the problems were found. Each entry gives the symptom, the root cause as far as it is known, the fix
with its exact configuration, and whether the fix has been seen working.

The underlying problem is not fixed by any of this. The Hexagon NPU path (kernel `fastrpc` driver plus
`libcdsprpc`) leaks pinned memory and occasionally wedges; the fixes below contain the damage and recover from it
without someone pressing the power button. See [§5 of the README](../README.md#5-stability-findings).

## Summary

| # | Problem | Fix | Layer | Verified |
|---|---|---|---|---|
| 1 | Newer NPU firmware breaks memory mapping | Roll back `cdsp0.mbn` to 20260612, hold the package | Firmware | ✅ every run uses it |
| 2 | Failed NPU loads leak pinned DMA memory | Refuse to start above 1.5 GB pinned; suite reboots above 1.2 GB | Service, runner | ✅ 34+ planned reboots |
| 3 | Crash-looping NPU service leaks until the board freezes | Restart cap on the NPU service | systemd | ✅ no loop since |
| 4 | Kernel hangs leave the board dead | Hardware watchdog while running; hangs become panics | systemd, sysctl | ⚠️ configured, no real hang caught yet |
| 5 | Reboot hangs while tearing down the NPU | Keep the watchdog armed through reboot | Kernel cmdline | ⚠️ active, no real hang caught yet |
| 6 | `systemctl reboot` itself hangs on fastrpc teardown | Reboot with sysrq (`s`, `u`, `b`) | Runner | ✅ every reboot since 2026-11-09 |
| 7 | Killing a wedged NPU process froze the board | Never SIGKILL: pause the runner (SIGSTOP), then sysrq | Procedure | ✅ 6 wedges recovered |
| 8 | A wedge stalls the queue for hours | Stall watcher: no progress for 8 min → pause + sysrq, continue the queue | Runner | ✅ |
| 9 | llama-bench can hang forever | 900 s timeout; on timeout disable the runner instead of killing | Runner | ✅ |
| 10 | Crash evidence lost on reset | EFI pstore for panic dumps | Kernel module | ⚠️ not yet seen persisting |
| 11 | Model too big for one NPU session | Split over 4 sessions | Runner | ✅ |
| 11b | Random `fastrpc_mmap failed` at load | `GGML_HEXAGON_MBUF=256,256` | llama.cpp env | ✅ Q8_0 and 8B load; ❌ 8B freezes mid-generation |
| 12 | Vision encoder fails to map on the NPU | Run the image encoder on CPU | Runner | ✅ |
| 13 | Genie crashes or returns empty replies | Streaming only, one session per request, eviction off, real call ids | Genie, runner | ✅ |

## 1. NPU firmware regression

- **Symptom:** after upgrading `linux-firmware-dragonwing` to 20260825 (new `cdsp0.mbn` and `fastrpc_shell_3`),
  even a 4B model failed to map on the NPU.
- **Fix:** the 20260612 firmware files were restored from a backup into `/lib/firmware/updates/` and the
  initramfs rebuilt. The package is on hold so apt does not reinstall the new files.
- **Caveat:** dpkg still reports 20260825 because the old `.deb` is no longer in the archive. The firmware hash
  recorded per run (`9ef6c8dc39d866a1…`) is the reliable record; see [environments](../reports/environments.md).
- A one-shot boot guard (`fw-guard.service`) rolled the firmware back automatically if the board did not come
  back on the network after the upgrade; it disarmed itself on the first good boot.

## 2. Leaked NPU memory

- **Symptom:** after a failed or killed NPU load, DMA buffers stay pinned (up to 7.4 GB seen in
  `/sys/kernel/debug/dma_buf/bufinfo` with nothing running). Later loads fail with `fastrpc_mmap failed`.
- **Cause:** fastrpc driver leak. Several fixes are already in kernel `6.8.0-1089-qcom`; this one is not.
  Only a reboot gives the memory back.
- **Fix, service side:** `/usr/local/sbin/npu-precheck.sh` runs before the NPU service starts:

  ```sh
  LIMIT_MB=${NPU_DMABUF_LIMIT_MB:-1500}
  bytes=$(sed -n 's/^Total [0-9]* objects, \([0-9]*\) bytes$/\1/p' /sys/kernel/debug/dma_buf/bufinfo)
  mb=$(( ${bytes:-0} / 1048576 ))
  [ "$mb" -gt "$LIMIT_MB" ] && { echo "npu-precheck: ${mb} MB pinned, reboot first" >&2; exit 1; }
  ```

- **Fix, runner side:** before each test the suite checks pinned memory and reboots if it is above 1200 MB
  (`REBOOT_MB` in [`suite.py`](../suite/suite.py)). Items marked `fresh` need less than 200 MB. If the board is
  still over the limit right after a reboot, the item is skipped instead of looping. Reboots are capped at 60.

## 3. Crash-looping NPU service

- **Symptom:** a llama-server that crashed on load was restarted by systemd again and again, leaking more memory
  each time, until the board froze during reboot.
- **Fix:** in `llama-server.service`: `ExecStartPre=+/usr/local/sbin/npu-precheck.sh`, `RestartSec=30`, and
  `StartLimitIntervalSec=300` / `StartLimitBurst=2` in `[Unit]`. An NPU service must never restart without a cap.
  `-c 4096`, because 8192 runs out of NPU-mappable memory.

## 4. Hardware watchdog and panic on hang

`/etc/systemd/system.conf.d/10-watchdog.conf`:

```ini
[Manager]
# qcom_wdt resets the board if PID 1 stops petting it (frozen kernel)
RuntimeWatchdogSec=30s
# force the reset when shutdown hangs on unkillable NPU processes
RebootWatchdogSec=2min
```

`/etc/sysctl.d/90-hang-panic.conf`:

```ini
# Turn hangs into panics: the oops lands in EFI pstore, then the board reboots
kernel.panic = 10
kernel.softlockup_panic = 1
kernel.hung_task_timeout_secs = 120
kernel.hung_task_panic = 1
```

`hung_task_timeout_secs` was 300 until 2026-11-09; lowered so a task stuck in the driver panics and reboots
sooner.

## 5. Watchdog disarmed during reboot

- **Symptom:** a reboot started by the suite hung with no output; `RebootWatchdogSec` never fired, and the board
  needed a power cycle.
- **Cause:** the kernel's watchdog core defaults to `stop_on_reboot=Y` and disarms `qcom_wdt` as soon as a reboot
  begins, so a hang during shutdown is never reset.
- **Fix:** `/etc/default/grub.d/99-zz-watchdog-reboot.cfg`:

  ```sh
  GRUB_CMDLINE_LINUX="${GRUB_CMDLINE_LINUX} watchdog.stop_on_reboot=0"
  ```

  Confirmed via `/sys/module/watchdog/parameters/stop_on_reboot` = 0. Recorded per run in the environment
  (column "Extra kernel args").

## 6. Reboot via sysrq

- **Symptom:** `systemctl reboot` tears down services first, and tearing down a process with an open fastrpc
  session can hang forever.
- **Fix:** the runner reboots by writing `s` (sync), `u` (remount read-only) and `b` (reboot) to
  `/proc/sysrq-trigger`. Ubuntu's default `kernel.sysrq = 176` already allows exactly these three. Used for every
  planned reboot since 2026-11-09 (reboots 12 to 34+) without a single hang.
- When sending it over SSH, send `b` in the same foreground command. A backgrounded `(sleep 1; echo b > …) &`
  was killed when the SSH session closed and the reboot never happened (2026-11-10).

## 7. Never kill a wedged NPU process

- **Symptom:** Granite 4.2 8B wedged the NPU (`dspqueue wait_signal_locked` timeouts). Killing it with SIGKILL
  appeared to work, but the board hard-froze about 15 s into the next load, and the watchdog did not recover it.
- **Procedure since then:**
  1. Do not kill `llama-server` or `llama-bench`.
  2. Pause the runner (`kill -STOP` on the suite processes) so it does not start anything new.
  3. Mark the item as hung in `state.json`.
  4. `sync`, then sysrq `s`, `u`, `b`.
- The suite never restarts an item that is already marked as started, so after the reset it continues with the
  next item.

## 8. Stall watcher

A wedged server request otherwise blocks until the client timeout (600 s per request, so hours for a full test).
An external watcher polls the board every 30 s. If neither the current transcript nor the driver log grows for
8 minutes during a server test, it applies the procedure from §7 and lets the queue continue. It gives up after
3 wedges in one batch. A planned reboot (runner briefly inactive) is not a stall; only a disabled runner stops the
watcher. Script: [`suite/probes/watch.sh`](../suite/probes/watch.sh).

Three bugs in earlier versions, all fixed:

- It found the runner with `pgrep -f suite.py`, which also matched the watcher's own SSH shell (its command line
  contains "suite.py"). It paused itself, that SSH call never returned, and the reset after it never ran
  (2026-11-10, twice). It now pauses only systemd's `MainPID` of the runner.
- It now checks the board's uptime after the reset and stops if the reset did not happen, instead of assuming it.

## 9. llama-bench timeout

`run_llamabench` starts llama-bench with a 900 s timeout. On timeout it does **not** kill the process (see §7). It
disables the runner and exits, so the next step is a manual sysrq reset.

## 10. Crash dumps

`efi_pstore` is loaded at boot (`/etc/modules-load.d/efi-pstore.conf`), and `systemd-pstore` archives panic dumps
to `/var/lib/systemd/pstore/`. It is not yet proven that this board's UEFI keeps the variables across a reset.
Wi-Fi cannot do netconsole; the serial console is `ttyMSM0` at 115200.

## 11. NPU sessions

One NPU session offers about 3.1 GiB of address space (3134 MiB, printed as `vmem` when the session opens), and a
process can open four. A 4B Q4_0 model does not fit one session with its KV cache and compute buffers (fails at
about 3.05 GB pinned, on every build and with any buffer setting), so NPU runs split the model over sessions:
`GGML_HEXAGON_DEVICES=4` and `-dev HTP0,HTP1,HTP2,HTP3` for llama-server (comma-separated; llama-bench uses `/`).
The layers run in sequence across sessions; this makes models fit, it is not a speed-up. Arduino's App Lab runner
computes the session count per model instead and keeps each session under 85% of its address space.

## 11b. NPU buffer chunk size

- **Symptom:** `fastrpc_mmap failed` at load, at random, for models well inside four sessions' address space
  (Qwen3-4B Q8_0, Qwen3-8B in llama-bench).
- **Cause:** llama.cpp's Hexagon backend maps NPU memory in chunks of 512 MiB (compute buffers) and 1 GiB (weights
  and KV cache) by default, and mapping a chunk that large fails at random. Arduino's App Lab runner notes the same:
  "3 loads in 5 for gemma-4-E4B, 0 in 9 once MBUF was 256".
- **Fix:** `GGML_HEXAGON_MBUF=256,256` (256 MiB chunks for both). With it, Qwen3-4B Q8_0 and Qwen3-8B load
  reliably in llama-bench; Qwen3-4B speed and scores are unchanged (12.8 t/s, 7/7, 12/12). See
  [§4.10](../README.md#410-arduino-app-lab-path-gemma-4-e4b). The main result tables predate this fix.
- **Not fixed by it:** one session for a 4B model (§11), Gemma 4 E4B on plain llama.cpp, Qwen3-8B as a server,
  and freezes during generation: Ministral 3 8B and Qwen3-VL-8B both froze mid-answer with MBUF 256
  ([§4.11](../README.md#411-mbuf-rerun-of-the-main-picks)). Qwen3-4B froze twice in a 12-hour soak with MBUF 256
  (1766 requests, no leak, no throttling), so a freeze detector with a sysrq reset is still required.
- **Side effect:** Qwen3-VL-4B's image tests passed (3/4) on the first run with MBUF 256; with the defaults they
  needed a separate fix run.

## 12. Vision encoder on CPU

The multimodal projector (`mmproj`, about 800 MB) fails to map on the NPU. The suite passes
`--no-mmproj-offload` with `--mmproj`, so the image encoder runs on the CPU while the language model stays on
the NPU.

## 13. Genie

| Symptom | Cause | Fix |
|---|---|---|
| Non-streaming request kills the LLM process; re-init then fails with SDK error 14003 until a reboot | Genie service bug | Send every request with `stream: true`; the runner rebuilds the OpenAI response from the stream |
| Replies empty or mixed up between tests | Genie groups sessions by user plus messages | Unique `user` per request |
| Process crashes after a few requests | History eviction runs a "facts" extraction pass that crashes | `HISTORY_EVICTION_THRESHOLD=100` in [`genie-compose.yaml`](../suite/genie-compose.yaml) |
| Tool result request times out (408) | Genie tracks pending tool calls server-side | Answer with the model's own call id, never a made-up one |
| HTTP 400 on every request | Wrong model name | Use the short names (`qwen3_4b_instruct_2507`, `qwen3_vl_8b_instruct`) |

Not fixed: Genie ignores `response_format` (no JSON-schema output), and Genie Qwen3-VL-8B hangs on a ~1.7k-token
prompt.

## What did not help

- **Newer kernel:** `6.8.0-1089-qcom` is the newest kernel for this board and already has the known fastrpc
  fixes (including CVE-2025-68252). The remaining hang matches an unmerged upstream patch ("misc: fastrpc: fix
  context leak and hang on signal-interrupted invoke").
- **Newer llama.cpp alone:** `d5bbcd1` (2026-11-10) behaves the same as `7fe450e` for single-session mapping and 8B
  loading; see [§4.6](../README.md#46-llamacpp-build-comparison).
- **Docker:** the leak is in the kernel driver, which containers share.
- **Splitting 8B models between NPU and CPU** (`-ngl` below the layer count): 28 NPU layers crashed, 20 worked at
  0.89 t/s; see [§4.9](../README.md#49-combination-tests).
- **Speculative decoding with 8-token drafts** made the server hang and crash mid-test.
