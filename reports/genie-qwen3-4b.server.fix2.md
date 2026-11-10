# genie-qwen3-4b.server.fix2

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `qwen3_4b_instruct_2507`, engine `genie`, device `None`, NPU sessions `0`, started 2026-11-09 19:58:35, finished 2026-11-09 20:02:49.

Raw transcript: [genie-qwen3-4b.server.fix2.transcript.jsonl](../results/transcripts/genie-qwen3-4b.server.fix2.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 6.2 |
| Cold TTFT s | 58.247 |
| Gen t/s | 17.06 |
| Long TTFT s | 1.603 |
| Peak RAM MB | 11508 |
| Peak pinned MB | 8244 |
| Tools | 0/7 |
| Quiz | 0/12 |
| Needle | ✅ |
| JSON schema | ❌ |

## Speed prompt reply

> A home router plays a crucial role in managing internet connectivity for devices on a local network. It handles several key functions including **NAT (Network Address Translation)**, **DHCP (Dynamic Host Configuration Protocol)**, **DNS (Domain Name System)**, and **firewall protection**. Below is a detailed explanation of how each function works within a home router: --- ### 1. **NAT (Network Address Translation)** **What it is**: NAT allows multiple devices on a local network to share a single public IP address when accessing the internet. The router acts as a gateway between the local netwo…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

✅ reply: `4417`

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
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ❌ | (no reply: {"error": "HTTP Error 408: "}) ⚠️ `HTTP Error 408:` |

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

