# gemma-4-e4b.npu.server

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `gemma-4-e4b`, engine `llama`, device `npu`, NPU sessions `—`, started 2026-11-09 10:57:06, finished 2026-11-09 10:59:23.

**Environment [E1](environments.md#e1)** (inferred from the package and boot history; this run predates environment capture): Kernel `6.8.0-1089-qcom`, Extra kernel args `—`, NPU firmware (cdsp0.mbn) `dragonwing 20260612 (restored)`, linux-firmware `20240318.git3b128b60-0ubuntu2.27`, qcom-fastrpc1 (libcdsprpc) `1.0.15+repack2`, Engine `llama.cpp`, Engine build `7fe450e`

Raw transcript: [gemma-4-e4b.npu.server.transcript.jsonl](../results/transcripts/gemma-4-e4b.npu.server.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 28.1 |
| Cold TTFT s | 0.508 |
| Gen t/s | 10.47 |
| Peak RAM MB | 9007 |
| Peak pinned MB | 5155 |
| Tools | 0/7 |
| Quiz | 0/12 |
| Vision | 0/4 |
| Needle | ❌ |
| JSON schema | ❌ |

## Speed prompt reply

> A home router is a sophisticated piece of networking hardware that performs several critical functions to allow multiple devices on a private local network (LAN) to share a single public IP address provided by the Internet Service Provider (ISP). Here is a detailed breakdown of how a home router handles **NAT, DHCP, DNS, and its Firewall.** --- ## 1. Network Address Translation (NAT) **The Problem:** The public internet uses a limited pool of IPv4 addresses. Your ISP assigns you **one** public IP address. However, you might have 5, 10, or 20 devices (phones, laptops, smart TVs) on your home ne…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

❌ reply: `*(empty)*`

<a id="tools"></a>
## Tools (0/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ❌ | (no reply: {"error": "[Errno 104] Connection reset by peer"}) ⚠️ `[Errno 104] Connection reset by peer` |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) ⚠️ `<urlopen error [Errno 111] Connection refused>` |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) ⚠️ `<urlopen error [Errno 111] Connection refused>` |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) ⚠️ `<urlopen error [Errno 111] Connection refused>` |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) ⚠️ `<urlopen error [Errno 111] Connection refused>` |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) ⚠️ `<urlopen error [Errno 111] Connection refused>` |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) ⚠️ `<urlopen error [Errno 111] Connection refused>` |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

❌ reply: `(no reply: {"error": "<urlopen error [Errno 111] Connection refused>"})`
 ⚠️ `<urlopen error [Errno 111] Connection refused>`

<a id="quiz"></a>
## Quiz (0/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |

<a id="vision"></a>
## Vision (0/4, — s/image)

| # | Question | Image | Expected | Pass | Model answer |
|---|---|---|---|---|---|
| <a id="v1"></a>1 | What text is written in this image? | image of the text `VENI 7429` | VENI 7429 | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="v2"></a>2 | How many green circles are in this image? | 5 green circles | 5 | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="v3"></a>3 | What colour is the square and what colour is the circle? | red square, blue circle | red and blue | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |
| <a id="v4"></a>4 | Is the arrow pointing left or right? | arrow pointing right | right | ❌ | (no reply: {"error": "<urlopen error [Errno 111] Connection refused>"}) |

