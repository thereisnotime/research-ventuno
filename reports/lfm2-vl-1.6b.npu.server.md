# lfm2-vl-1.6b.npu.server

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `lfm2-vl-1.6b`, engine `llama`, device `npu`, NPU sessions `—`, started 2026-11-08 22:14:47, finished 2026-11-08 22:16:16.

**Environment [E1](environments.md#e1)** (inferred from the package and boot history; this run predates environment capture): Kernel `6.8.0-1089-qcom`, Extra kernel args `—`, NPU firmware (cdsp0.mbn) `dragonwing 20260612 (restored)`, linux-firmware `20240318.git3b128b60-0ubuntu2.27`, qcom-fastrpc1 (libcdsprpc) `1.0.15+repack2`, Engine `llama.cpp`, Engine build `7fe450e`

Raw transcript: [lfm2-vl-1.6b.npu.server.transcript.jsonl](../results/transcripts/lfm2-vl-1.6b.npu.server.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 4.0 |
| Cold TTFT s | 0.183 |
| Gen t/s | 29.51 |
| Prefill t/s (~1.7k tokens) | 1233.42 |
| Long TTFT s | 1.54 |
| Peak RAM MB | 3976 |
| Peak pinned MB | 2736 |
| Tools | 2/7 |
| Quiz | 10/12 |
| Vision | 3/4 |
| s/image | 5.1 |
| Needle | ✅ |
| JSON schema | ✅ |

## Speed prompt reply

> A home router is a device that connects your home network to the internet and manages the flow of data between your devices and the internet. It uses a combination of NAT, DHCP, DNS, and firewall to ensure that your network is secure and efficient. NAT (Network Address Translation) is a process that allows multiple devices on a network to share a single public IP address. When a device on your network wants to access the internet, the router translates its private IP address to the public IP address. This allows other devices on the internet to communicate with your devices on your network. DH…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

✅ reply: `4417`

<a id="tools"></a>
## Tools (2/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ❌ | I'm sorry, but I don't have real-time data access to provide the current weather conditions in Sofia, Bulgaria, or any other specific location. However, you can easily find the current weather in Sofia by using a weather… |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ❌ | I'm sorry, but I can't assist with that. It's important to note that I can't provide real-time or future flight information. However, I can help you find flights from London to Tokyo on 24 December 2026. You might want t… |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ❌ | The product of 1234 and 5678 is 7000002. |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ❌ | Subject: Lunch Hi Bob, I hope you're doing well. I'm 10 minutes late for our lunch meeting. I'll be there in 5 minutes. Best, [Your Name] |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ✅ | Why don't cats make good scientists? Because they always land on their feet. |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | Paris: The weather in Paris is currently 15°C with a chance of rain. It's a typical spring day with a mix of clouds and sunshine. Berlin: The weather in Berlin is currently 12°C with a chance of rain. It's a typical spri… |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ✅ | The weather in Oslo is currently light rain with a temperature of 7°C. |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

✅ reply: `{ "name": "Maria", "age": 34, "hobbies": ["climbing", "chess", "baking"] }`

<a id="quiz"></a>
## Quiz (10/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ✅ | 391 |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ✅ | The train leaves at 14:40 and takes 2 hours 35 minutes. Adding this to the departure time, the train arrives at 17:15. |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ✅ | The capital of Australia is Canberra. |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ✅ | The letter 'r' appears 3 times in the word 'strawberry'. |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ✅ | 1, 2, 5, 9 |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ✅ | Carol is the youngest. |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ✅ | Buenos días. |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ❌ | 44 |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ✅ | Au |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ✅ | Let's break this down. We know the bat and ball together cost $1.10, and the bat costs $1.00 more than the ball. If we let the cost of the ball be x cents, then the cost of the bat would be x + $1.00. Since the total cos… |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ✅ | 1945 |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ❌ | ssset |

<a id="vision"></a>
## Vision (3/4, 5.1 s/image)

| # | Question | Image | Expected | Pass | Model answer |
|---|---|---|---|---|---|
| <a id="v1"></a>1 | What text is written in this image? | image of the text `VENI 7429` | VENI 7429 | ✅ | VENI 7429 |
| <a id="v2"></a>2 | How many green circles are in this image? | 5 green circles | 5 | ❌ | 4 |
| <a id="v3"></a>3 | What colour is the square and what colour is the circle? | red square, blue circle | red and blue | ✅ | The square is red and the circle is blue. |
| <a id="v4"></a>4 | Is the arrow pointing left or right? | arrow pointing right | right | ✅ | Right |

