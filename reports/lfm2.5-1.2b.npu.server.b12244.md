# lfm2.5-1.2b.npu.server.b12244

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `lfm2.5-1.2b`, engine `llama`, device `npu`, NPU sessions `4`, started 2026-11-10 11:55:33, finished 2026-11-10 11:56:35.

**Environment [E5](environments.md#e5)**: Kernel `6.8.0-1089-qcom`, Extra kernel args `watchdog.stop_on_reboot=0`, NPU firmware (cdsp0.mbn) `dragonwing 20260612 (restored)`, linux-firmware `20240318.git3b128b60.0ubuntu3.1`, qcom-fastrpc1 (libcdsprpc) `1.0.15+repack2`, Engine `llama.cpp`, Engine build `d5bbcd1`

Raw transcript: [lfm2.5-1.2b.npu.server.b12244.transcript.jsonl](../results/transcripts/lfm2.5-1.2b.npu.server.b12244.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 2.0 |
| Cold TTFT s | 0.126 |
| Gen t/s | 29.88 |
| Prefill t/s (~1.7k tokens) | 1317.85 |
| Long TTFT s | 1.442 |
| Peak RAM MB | 2382 |
| Peak pinned MB | 1287 |
| Tools | 6/7 |
| Quiz | 10/12 |
| Needle | ✅ |
| JSON schema | ✅ |

## Speed prompt reply

> A home router is a critical device that manages network traffic between your home network and the internet. It handles several essential services to ensure your devices can communicate effectively. Here's a detailed breakdown of how a home router manages **NAT (Network Address Translation)**, **DHCP (Dynamic Host Configuration Protocol)**, **DNS (Domain Name System)**, and **firewall**: --- ## 1. **NAT (Network Address Translation)** ### **What is NAT?** NAT is a protocol that allows multiple devices on a private network to share a single public IP address when accessing the internet. It trans…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

✅ reply: `4417`

<a id="tools"></a>
## Tools (6/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ✅ | `get_weather({"city":"Sofia","unit":"celsius"})` |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ✅ | `search_flights({"origin":"London","destination":"Tokyo","date":"2026-12-24"})` |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ✅ | `calculator({"expression":"1234 * 5678"})` |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ✅ | `send_email({"to":"bob@example.com","subject":"Lunch","body":"I'm 10 minutes late."})` |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ✅ | I don't have a tool to generate jokes, but here's one for you: Why don't cats play poker? Because four is the wrong number! 😺 |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | `get_weather({"city":"Paris","unit":"celsius"})` |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ✅ | The current weather in Oslo is 7°C with light rain. Let me know if you'd like additional details! |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

✅ reply: `{ "name": "Maria", "age": 34, "hobbies": ["climbing", "chess", "baking"] }`

<a id="quiz"></a>
## Quiz (10/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ✅ | 17 * 23 = 391 |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ✅ | The train departs at 14:40 and travels for 2 hours 35 minutes. Adding that to 14:40 gives a arrival time of **17:15**. |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ✅ | The capital of Australia is Canberra. |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ✅ | The letter "r" appears 3 times in "strawberry." |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ✅ | The numbers in ascending order are: 1, 2, 5, 9. |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ✅ | Carol is the youngest. |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ✅ | "Buenos días". |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ✅ | The pattern increases by doubling the previous number: 2→6 (+4), 6→12 (+6), 12→20 (+8), 20→30 (+10). Next difference is +12, so 30 + 12 = 42. Answer: 42 |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ✅ | The chemical symbol for gold is **Au**. |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ❌ | The ball costs 10 cents. |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ✅ | World War II ended in 1945. |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ❌ | Stressed is read the same backwards. |

