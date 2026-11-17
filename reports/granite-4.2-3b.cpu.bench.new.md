# granite-4.2-3b.cpu.bench.new

[← README](../README.md) · [all runs](index.md)

llama-bench, model `granite-4.2-3b`, device `cpu`, NPU sessions `0`, started 2026-11-17 12:09:02.

Environment [E5](environments.md#e5): llama.cpp `d5bbcd1`.

Extra environment: `GGML_HEXAGON_MBUF=256,256`

| Test | t/s |
|---|---:|
| pp512_d0 | 42.63 |
| tg128_d0 | 12.35 |
| pp512_d2048 | 27.44 |
| tg128_d2048 | 7.7 |

Peak RAM 3224 MB, peak pinned 0 MB.
