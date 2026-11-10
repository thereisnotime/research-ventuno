# gemma-3-4b.npu.server

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `gemma-3-4b`, engine `llama`, device `npu`, NPU sessions `—`, started 2026-11-08 22:02:26, finished 2026-11-08 22:07:27.

**Environment [E1](environments.md#e1)** (inferred from the package and boot history; this run predates environment capture): Kernel `6.8.0-1089-qcom`, Extra kernel args `—`, NPU firmware (cdsp0.mbn) `dragonwing 20260612 (restored)`, linux-firmware `20240318.git3b128b60-0ubuntu2.27`, qcom-fastrpc1 (libcdsprpc) `1.0.15+repack2`, Engine `llama.cpp`, Engine build `7fe450e`

Raw transcript: [gemma-3-4b.npu.server.transcript.jsonl](../results/transcripts/gemma-3-4b.npu.server.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 18.1 |
| Cold TTFT s | 0.404 |
| Gen t/s | 13.26 |
| Prefill t/s (~1.7k tokens) | 445.78 |
| Long TTFT s | 4.035 |
| Peak RAM MB | 7048 |
| Peak pinned MB | 4460 |
| Tools | 1/7 |
| Quiz | 12/12 |
| Vision | 4/4 |
| s/image | 27.7 |
| Needle | ✅ |
| JSON schema | ✅ |

## Speed prompt reply

> Okay, let's break down how a home router handles NAT, DHCP, DNS, and its firewall – these are the core functions that make your home network work. It's a surprisingly complex process happening behind a simple interface! **1. NAT (Network Address Translation)** * **The Problem:** Traditionally, each device on a network needed its own unique IP address (like 192.168.1.100). The internet uses a different system (IPv4) where addresses are globally unique. IPv4 addresses are running out, and we're moving to IPv6 which uses a different addressing scheme. * **NAT's Solution:** NAT allows multiple dev…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

✅ reply: `4417`

<a id="tools"></a>
## Tools (1/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ❌ | Okay, let's check the weather in Sofia, Bulgaria. As of 1:53 PM PST on November 2, 2023, the weather in Sofia is: * **Temperature:** 12°C (54°F) * **Feels Like:** 12°C (54°F) * **Condition:** Partly cloudy * **Wind:** 13… |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ❌ | Okay, let's look for flights from London to Tokyo on December 24, 2026. This is a long way out, so availability and pricing are *highly* speculative at this point. Here's what I can tell you based on current trends and w… |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ❌ | 1234 * 5678 = 7006652 |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ❌ | Subject: Lunch Hi Bob, Just wanted to let you know I'm about 10 minutes late. Sorry about that! Best, [Your Name] --- Would you like me to add anything else to the email, like a reason for the delay or an apology? |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ✅ | Why did the cat sit on the computer? ...To keep an eye on the mouse! 😄 --- Would you like to hear another joke? |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | Okay, here's the weather forecast for Paris and Berlin as of November 3, 2023, at 1:30 PM PST: **Paris, France** * **Current Temperature:** 11°C (52°F) * **Feels Like:** 11°C (52°F) * **Conditions:** Overcast * **Wind:**… |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ❌ | (no reply: {"error": "HTTP Error 400: Bad Request"}) ⚠️ `HTTP Error 400: Bad Request` |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

✅ reply: `{ "name": "Maria", "age": 34, "hobbies": ["climbing", "chess", "baking"] }`

<a id="quiz"></a>
## Quiz (12/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ✅ | 391 |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ✅ | 17:15 |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ✅ | Canberra |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ✅ | Three times. |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ✅ | 1, 2, 5, 9 |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ✅ | Carol. |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ✅ | Buenos días. |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ✅ | 42 |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ✅ | Au |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ✅ | 5 cents. |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ✅ | 1945 |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ✅ | desserts |

<a id="vision"></a>
## Vision (4/4, 27.7 s/image)

| # | Question | Image | Expected | Pass | Model answer |
|---|---|---|---|---|---|
| <a id="v1"></a>1 | What text is written in this image? | image of the text `VENI 7429` | VENI 7429 | ✅ | VENI 7429 |
| <a id="v2"></a>2 | How many green circles are in this image? | 5 green circles | 5 | ✅ | 5 |
| <a id="v3"></a>3 | What colour is the square and what colour is the circle? | red square, blue circle | red and blue | ✅ | The square is red and the circle is blue. |
| <a id="v4"></a>4 | Is the arrow pointing left or right? | arrow pointing right | right | ✅ | Right |

