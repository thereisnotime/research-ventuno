# genie-qwen3-vl-8b.server.fix3

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `qwen3_vl_8b_instruct`, engine `genie`, device `None`, NPU sessions `0`, started 2026-11-09 20:54:23, finished 2026-11-09 21:03:50.

**Environment [E4](environments.md#e4)** (inferred from the package and boot history; this run predates environment capture): Kernel `6.8.0-1089-qcom`, Extra kernel args `watchdog.stop_on_reboot=0`, NPU firmware (cdsp0.mbn) `dragonwing 20260612 (restored)`, linux-firmware `20240318.git3b128b60.0ubuntu3.1`, qcom-fastrpc1 (libcdsprpc) `1.0.15+repack2`, Engine `Genie (genai-llm-vlm-service)`, Engine build `1.5.0`

Raw transcript: [genie-qwen3-vl-8b.server.fix3.transcript.jsonl](../results/transcripts/genie-qwen3-vl-8b.server.fix3.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 6.3 |
| Cold TTFT s | 128.688 |
| Peak RAM MB | 9679 |
| Peak pinned MB | 6811 |
| Tools | 0/7 |
| Quiz | 0/12 |
| Vision | 0/4 |
| s/image | 4.2 |
| Needle | ❌ |
| JSON schema | ❌ |

## Speed prompt reply

> *(empty)*

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

❌ reply: `*(empty)*`

<a id="tools"></a>
## Tools (0/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ❌ | *(empty)* |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ❌ | *(empty)* |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ❌ | *(empty)* |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ❌ | *(empty)* |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ❌ | *(empty)* |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | *(empty)* |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ❌ | not in transcript ⚠️ `no get_weather call to answer` |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

❌ reply: `*(empty)*`
 ⚠️ `Expecting value: line 1 column 1 (char 0)`

<a id="quiz"></a>
## Quiz (0/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ❌ | *(empty)* |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ❌ | *(empty)* |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ❌ | *(empty)* |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ❌ | *(empty)* |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ❌ | *(empty)* |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ❌ | *(empty)* |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ❌ | *(empty)* |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ❌ | *(empty)* |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ❌ | *(empty)* |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ❌ | *(empty)* |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ❌ | *(empty)* |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ❌ | *(empty)* |

<a id="vision"></a>
## Vision (0/4, 4.2 s/image)

| # | Question | Image | Expected | Pass | Model answer |
|---|---|---|---|---|---|
| <a id="v1"></a>1 | What text is written in this image? | image of the text `VENI 7429` | VENI 7429 | ❌ | *(empty)* |
| <a id="v2"></a>2 | How many green circles are in this image? | 5 green circles | 5 | ❌ | *(empty)* |
| <a id="v3"></a>3 | What colour is the square and what colour is the circle? | red square, blue circle | red and blue | ❌ | *(empty)* |
| <a id="v4"></a>4 | Is the arrow pointing left or right? | arrow pointing right | right | ❌ | *(empty)* |

