# qwen3-vl-8b.npu.server.vfix3

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `qwen3-vl-8b`, engine `llama`, device `npu`, NPU sessions `4`, started 2026-11-09 21:03:30, finished 2026-11-09 21:35:15.

Raw transcript: [qwen3-vl-8b.npu.server.vfix3.transcript.jsonl](../results/transcripts/qwen3-vl-8b.npu.server.vfix3.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 99.0 |
| Cold TTFT s | 0.341 |
| Gen t/s | 7.54 |
| Prefill t/s (~1.7k tokens) | 246.7 |
| Long TTFT s | 7.125 |
| Peak RAM MB | 8469 |
| Peak pinned MB | 5584 |
| Tools | 2/7 |
| Quiz | 0/12 |
| Vision | 0/4 |
| Needle | ✅ |
| JSON schema | ❌ |

## Speed prompt reply

> A home router is the central networking device in most residential environments, acting as a gateway between your local network (LAN) and the wider internet (WAN). It performs several critical functions: **NAT (Network Address Translation)**, **DHCP (Dynamic Host Configuration Protocol)**, **DNS (Domain Name System)** resolution, and **firewall** protection. Let’s break down each component in detail. --- ## 1. NAT (Network Address Translation) ### What is NAT? NAT is a method used to map multiple private IP addresses (used internally on your LAN) to a single public IP address (assigned by your…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

✅ reply: `4417`

<a id="tools"></a>
## Tools (2/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ✅ | `get_weather({"city": "Sofia", "unit": "celsius"})` |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ✅ | `search_flights({"origin": "London", "destination": "Tokyo", "date": "2026-12-24"})` |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ❌ | (no reply: {"error": "timed out"}) ⚠️ `timed out` |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ❌ | (no reply: {"error": "timed out"}) ⚠️ `timed out` |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ❌ | (no reply: {"error": "Remote end closed connection without response"}) ⚠️ `Remote end closed connection without response` |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | (no reply: {"error": "[Errno 104] Connection reset by peer"}) ⚠️ `[Errno 104] Connection reset by peer` |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ❌ | not in transcript ⚠️ `first call: <urlopen error [Errno 111] Connection refused>` |

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

