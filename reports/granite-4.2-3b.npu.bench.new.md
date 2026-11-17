# granite-4.2-3b.npu.bench.new

[← README](../README.md) · [all runs](index.md)

llama-bench, model `granite-4.2-3b`, device `npu`, NPU sessions `4`, started 2026-11-17 11:52:45.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

Extra environment: `GGML_HEXAGON_MBUF=256,256`

| Test | t/s |
|---|---:|
| pp512_d0 | 471.36 |
| tg128_d0 | 14.97 |
| pp512_d2048 | 333.48 |
| tg128_d2048 | 11.28 |

Peak RAM 3962 MB, peak pinned 2801 MB.
