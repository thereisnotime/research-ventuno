# mbuf.m5.gemma-4-e4b.bench

[← README](../README.md) · [all runs](index.md)

llama-bench, model `gemma-4-e4b`, device `npu`, NPU sessions `4`, started 2026-11-10 16:14:38.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

> ❌ **Error:** `llama-bench rc=-6: [' what(): ggml-hex: fastrpc_mmap failed (see log for details)']`

Extra environment: `GGML_HEXAGON_MBUF=256,256`

| Test | t/s |
|---|---:|
| pp512_d0 | — |
| tg128_d0 | — |
| pp512_d2048 | — |
| tg128_d2048 | — |

Peak RAM 10544 MB, peak pinned 9227 MB.
