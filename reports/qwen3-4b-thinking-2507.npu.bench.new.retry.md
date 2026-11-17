# qwen3-4b-thinking-2507.npu.bench.new.retry

[← README](../README.md) · [all runs](index.md)

llama-bench, model `qwen3-4b-thinking-2507`, device `npu`, NPU sessions `4`, started 2026-11-17 21:31:02.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

Extra environment: `GGML_HEXAGON_MBUF=256,256`

| Test | t/s |
|---|---:|
| pp512_d0 | 443.73 |
| tg128_d0 | 12.6 |
| pp512_d2048 | 333.89 |
| tg128_d2048 | 9.0 |

Peak RAM 4911 MB, peak pinned 3719 MB.
