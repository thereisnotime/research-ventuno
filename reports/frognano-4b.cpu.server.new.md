# frognano-4b.cpu.server.new

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `frognano-4b`, engine `llama`, device `cpu`, NPU sessions `0`, started 2026-11-17 12:34:16, finished 2026-11-17 12:41:21.

**Environment [E5](environments.md#e5)**: Kernel `6.8.0-1089-qcom`, Extra kernel args `watchdog.stop_on_reboot=0`, NPU firmware (cdsp0.mbn) `dragonwing 20260612 (restored)`, linux-firmware `20240318.git3b128b60.0ubuntu3.1`, qcom-fastrpc1 (libcdsprpc) `1.0.15+repack2`, Engine `llama.cpp`, Engine build `d5bbcd1`

Raw transcript: [frognano-4b.cpu.server.new.transcript.jsonl](../results/performance/transcripts/frognano-4b.cpu.server.new.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 8.0 |
| Cold TTFT s | 1.121 |
| Gen t/s | 8.13 |
| Prefill t/s (~1.7k tokens) | 29.92 |
| Long TTFT s | 58.683 |
| Peak RAM MB | 5953 |
| Peak pinned MB | 64 |
| Tools | 7/7 |
| Quiz | 11/12 |
| Needle | ✅ |
| JSON schema | ✅ |

## Speed prompt reply

> A home router acts as the central traffic controller for your local network (LAN) connecting it to the internet (WAN). It performs four critical functions simultaneously: **DHCP** (assigning identities), **NAT** (hiding internal addresses), **DNS** (translating names to IPs), and **Firewall** (filtering traffic). Here is a detailed breakdown of how each mechanism works within the router's architecture. --- ### 1. DHCP (Dynamic Host Configuration Protocol) **Purpose:** To automatically assign IP addresses, subnet masks, default gateways, and DNS servers to devices on your local network. #### Ho…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

✅ reply: `4417`

<a id="tools"></a>
## Tools (7/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ✅ | `get_weather({"city":"Sofia","unit":"celsius"})` |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ✅ | `search_flights({"origin":"London","destination":"Tokyo","date":"2026-12-24"})` |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ✅ | `calculator({"expression":"1234 * 5678"})` |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ✅ | `send_email({"to":"bob@example.com","subject":"Lunch","body":"Hi Bob,\n\nI'm 10 minutes late for lunch. Sorry about that!\n\nBest,\n[Your Name]"})` |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ✅ | Why don't cats like to sing in the shower? Because they always feel like they're **purr-fectly** out of tune! 🐱🚿 |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ✅ | `get_weather({"city":"Paris"})` `get_weather({"city":"Berlin"})` |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ✅ | The weather in Oslo is currently 7°C with light rain. |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

✅ reply: `{ "name": "Maria","age": 34,"hobbies": ["climbing", "chess", "baking"] }`

<a id="quiz"></a>
## Quiz (11/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ✅ | 391 |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ✅ | 17:15 |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ✅ | There is no single capital for Australia. The **capital city** is **Canberra**, which serves as the seat of the federal government. However, the country's capital **territory** is the **Australian Capital Territory (ACT)… |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ✅ | The letter "r" appears **3** times in the word "strawberry". Breakdown: s-t-**r**-a-w-b-e-**r**-**r**-y |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ❌ | 2, 5, 9, 1 |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ✅ | Carol is the youngest. |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ✅ | Buenos días |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ✅ | 42 |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ✅ | Au |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ✅ | The ball costs **5 cents**. **Reasoning:** Let the ball cost $x$ cents. The bat costs $x + 100$ cents. Total cost: $x + (x + 100) = 110$ $2x = 10$ $x = 5$ |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ✅ | World War II ended in **1945**. |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ✅ | desserts |

