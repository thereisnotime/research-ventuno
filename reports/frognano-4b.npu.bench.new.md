# frognano-4b.npu.bench.new

[← README](../README.md) · [all runs](index.md)

llama-bench, model `frognano-4b`, device `npu`, NPU sessions `4`, started 2026-11-17 12:24:25.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

Extra environment: `GGML_HEXAGON_MBUF=256,256`

| Test | t/s |
|---|---:|
| pp512_d0 | 396.99 |
| tg128_d0 | 11.16 |
| pp512_d2048 | 383.45 |
| tg128_d2048 | 10.52 |

Peak RAM 5303 MB, peak pinned 4133 MB.
