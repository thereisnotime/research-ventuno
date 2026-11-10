# tops.t3.qwen3-4b-q4.balanced

[← README](../README.md) · [all runs](index.md)

llama-bench, model `qwen3-4b-2507`, device `npu`, NPU sessions `4`, started 2026-11-10 13:17:46.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

Extra environment: `GGML_HEXAGON_POWER_MODE=balanced`

| Test | t/s |
|---|---:|
| pp128_d0 | 383.86 |
| pp512_d0 | 444.99 |
| pp2048_d0 | 400.59 |
| tg128_d0 | 12.86 |

Peak RAM 4838 MB, peak pinned 3665 MB.
