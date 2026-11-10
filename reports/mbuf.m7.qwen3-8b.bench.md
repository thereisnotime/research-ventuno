# mbuf.m7.qwen3-8b.bench

[← README](../README.md) · [all runs](index.md)

llama-bench, model `qwen3-8b`, device `npu`, NPU sessions `4`, started 2026-11-10 16:15:40.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

Extra environment: `GGML_HEXAGON_MBUF=256,256`

| Test | t/s |
|---|---:|
| pp512_d0 | 268.66 |
| tg128_d0 | 7.85 |
| pp512_d2048 | 223.8 |
| tg128_d2048 | 6.27 |

Peak RAM 7431 MB, peak pinned 5985 MB.
