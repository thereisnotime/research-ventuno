# mbuf.m4.qwen3-4b-q8.bench

[← README](../README.md) · [all runs](index.md)

llama-bench, model `qwen3-4b-2507-q8`, device `npu`, NPU sessions `4`, started 2026-11-10 16:08:47.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

Extra environment: `GGML_HEXAGON_MBUF=256,256`

| Test | t/s |
|---|---:|
| pp128_d0 | 384.98 |
| pp512_d0 | 439.51 |
| pp2048_d0 | 398.24 |
| tg128_d0 | 8.45 |
| pp128_d2048 | 303.9 |
| pp512_d2048 | 332.34 |
| pp2048_d2048 | 306.7 |
| tg128_d2048 | 6.65 |

Peak RAM 7269 MB, peak pinned 5877 MB.
