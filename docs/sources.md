# Vendor claims and sources

[← README](../README.md)

The manufacturer's public claims this research tests, archived in the Internet Archive's Wayback Machine on
2026-11-10 so they stay citable if the pages change. Each snapshot was checked to contain the real page content.

## Claims under test

From the Arduino Store product page ([archived](https://web.archive.org/web/20261110132750/https://store.arduino.cc/products/ventuno-q)):

> "The AI brain with pre-loaded Linux delivers up to 40 dense TOPS of NPU acceleration for vision models, LLMs,
> and multi-modal AI inference"

> "Running LLMs and agentic AI offline, with 40 dense TOPS of NPU acceleration"

> "Hexagon Tensor AI Processor (NPU): up to 40 Dense TOPS"

> "The current library includes: Qwen 3 4B LLM; Qwen 2.5 7B and Qwen 3 4B VLM; …"

No source gives a tokens-per-second figure. Memory bandwidth (the limit for LLM generation) is not stated on the
Arduino pages; Qualcomm's product brief lists "4x16 LPDDR5/5x @ 3200 MHz".

What this repository measured against those claims: [§4](../README.md#4-results) and the 40 TOPS tests.

## Archived pages

| Source | Original | Wayback snapshot |
|---|---|---|
| Arduino Store product page | [store.arduino.cc](https://store.arduino.cc/products/ventuno-q) | [2026-11-10](https://web.archive.org/web/20261110132750/https://store.arduino.cc/products/ventuno-q) |
| Arduino product page | [arduino.cc](https://www.arduino.cc/product-ventuno-q) | [2026-11-10](https://web.archive.org/web/20261110132829/https://www.arduino.cc/product-ventuno-q) |
| Arduino docs | [docs.arduino.cc](https://docs.arduino.cc/hardware/ventuno-q) | [2026-11-10](https://web.archive.org/web/20261110132906/https://docs.arduino.cc/hardware/ventuno-q) |
| Arduino launch blog (2026-03-09) | [blog.arduino.cc](https://blog.arduino.cc/2026/03/09/introducing-arduino-ventuno-q-your-new-ai-robotics-and-actuation-platform/) | [2026-11-10](https://web.archive.org/web/20261110132936/https://blog.arduino.cc/2026/03/09/introducing-arduino-ventuno-q-your-new-ai-robotics-and-actuation-platform/) |
| Arduino availability blog (2026-08-25) | [blog.arduino.cc](https://blog.arduino.cc/2026/08/25/the-age-of-physical-ai-is-here-and-it-runs-on-the-arduino-ventuno-q-board/) | [2026-11-10](https://web.archive.org/web/20261110133007/https://blog.arduino.cc/2026/08/25/the-age-of-physical-ai-is-here-and-it-runs-on-the-arduino-ventuno-q-board/) |
| Qualcomm IQ8 series page | [qualcomm.com](https://www.qualcomm.com/internet-of-things/products/iq8-series) | [2026-11-10](https://web.archive.org/web/20261110133219/https://www.qualcomm.com/internet-of-things/products/iq8-series) |
| Qualcomm IQ8 product brief (PDF) | [docs.qualcomm.com](https://docs.qualcomm.com/doc/87-83839-1/87-83839-1_REV_A_Qualcomm_IQ8_Series_Product_Brief.pdf) | [2026-11-10](https://web.archive.org/web/20261110133249/https://docs.qualcomm.com/doc/87-83839-1/87-83839-1_REV_A_Qualcomm_IQ8_Series_Product_Brief.pdf) |
| Qualcomm IQ-8275 LPDDR memory docs | [dragonwingdocs.qualcomm.com](https://dragonwingdocs.qualcomm.com/Linux/devices/iq8275-evk/peripherals-interfaces/LPDDR_memory) | [2026-11-10](https://web.archive.org/web/20261110133309/https://dragonwingdocs.qualcomm.com/Linux/devices/iq8275-evk/peripherals-interfaces/LPDDR_memory) |
| Arduino press release (Edge AI and Vision Alliance) | [edge-ai-vision.com](https://www.edge-ai-vision.com/2026/03/arduino-announces-arduino-ventuno-q-powered-by-qualcomm-dragonwing-iq8-series/) | [2026-11-10](https://web.archive.org/web/20261110133341/https://www.edge-ai-vision.com/2026/03/arduino-announces-arduino-ventuno-q-powered-by-qualcomm-dragonwing-iq8-series/) |

## Not from the advertising

The Genie bundles tested here (`qwen3_4b_instruct_2507`, `qwen3_8b`, `qwen3_vl_8b_instruct`, built for
`qualcomm_qcs8275`) were offered for this board through `arduino-app-cli`, not named in the product pages above.
