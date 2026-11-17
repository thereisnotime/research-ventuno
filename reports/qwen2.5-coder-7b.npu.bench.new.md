# qwen2.5-coder-7b.npu.bench.new

[← README](../README.md) · [all runs](index.md)

llama-bench, model `qwen2.5-coder-7b`, device `npu`, NPU sessions `4`, started 2026-11-17 12:47:27.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

Extra environment: `GGML_HEXAGON_MBUF=256,256`

| Test | t/s |
|---|---:|
| pp512_d0 | 301.37 |
| tg128_d0 | 8.42 |
| pp512_d2048 | 262.54 |
| tg128_d2048 | 7.52 |

Peak RAM 6695 MB, peak pinned 5496 MB.
