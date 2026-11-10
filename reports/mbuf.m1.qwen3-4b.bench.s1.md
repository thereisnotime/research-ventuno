# mbuf.m1.qwen3-4b.bench.s1

[← README](../README.md) · [all runs](index.md)

llama-bench, model `qwen3-4b-2507`, device `npu`, NPU sessions `1`, started 2026-11-10 16:01:49.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

> ❌ **Error:** `llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed (see log for details)']`

Extra environment: `GGML_HEXAGON_MBUF=256,256`

| Test | t/s |
|---|---:|
| pp512_d0 | — |
| tg128_d0 | — |
| pp512_d2048 | — |
| tg128_d2048 | — |

Peak RAM 4302 MB, peak pinned 3052 MB.
