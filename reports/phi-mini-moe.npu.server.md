# phi-mini-moe.npu.server

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `phi-mini-moe`, engine `llama`, device `npu`, NPU sessions `—`, started 2026-11-09 17:53:18, finished 2026-11-09 17:56:02.

Raw transcript: [phi-mini-moe.npu.server.transcript.jsonl](../results/transcripts/phi-mini-moe.npu.server.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 8.0 |
| Cold TTFT s | 0.381 |
| Gen t/s | 18.63 |
| Prefill t/s (~1.7k tokens) | 352.77 |
| Long TTFT s | 6.341 |
| Peak RAM MB | 7306 |
| Peak pinned MB | 5602 |
| Tools | 1/7 |
| Quiz | 8/12 |
| Needle | ❌ |
| JSON schema | ❌ |

## Speed prompt reply

> A home router is a device that connects multiple devices to the internet and provides various networking services. Here's how it handles NAT (Network Address Translation), DHCP (Dynamic Host Configuration Protocol), DNS (Domain Name System), and its firewall: 1. NAT (Network Address Translation): NAT is a technique used to translate private IP addresses to public IP addresses. This allows multiple devices to share a single public IP address. When a device connects to the internet, its private IP address is translated to a public IP address assigned by the router. This public IP address is then…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

❌ reply: `*(empty)*`

<a id="tools"></a>
## Tools (1/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ❌ | As of my last update, I cannot provide real-time weather information. However, I can tell you that the typical weather in Sofia, Bulgaria, can vary greatly depending on the season. In the winter, temperatures can drop be… |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ❌ | I'm sorry for any inconvenience, but as Phibert, I'm unable to access real-time flight data. However, I can provide you with a general idea of how to find flights from London to Tokyo on 24 December 2026. 1. Use a flight… |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ❌ | To compute 1234 * 5678 using a calculator, you would enter the numbers as follows: 1234 * 5678 The result of this multiplication is: 7006652 So, 1234 multiplied by 5678 equals 7006652. |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ❌ | Subject: Lunch Dear Bob, I hope this email finds you well. I wanted to inform you that I am currently 10 minutes late for our scheduled lunch meeting today. I apologize for any inconvenience this may cause and I apprecia… |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ✅ | Why don' anybody like cats? Because they're always purr-fect! |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | As of my last update in early 2023, I cannot provide real-time weather information. However, I can give you a general idea of the typical weather patterns in Paris and Berlin based on historical data. Paris typically exp… |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ❌ | *(empty)* |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

❌ reply: `(no reply: {"error": "HTTP Error 400: Bad Request"})`
 ⚠️ `HTTP Error 400: Bad Request`

<a id="quiz"></a>
## Quiz (8/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ✅ | 391. |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ✅ | 17:15 |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ✅ | Canberra. |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ❌ | The letter r appears 2 times in the word strawberry. |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ❌ | 2, 5, 9, 1 |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ✅ | Carol is the youngest. |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ✅ | Buenos días. |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ✅ | 42. The pattern is increasing by 4, 6, 8, 10, 12, so the next increment is 14. |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ✅ | Au. |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ❌ | The ball costs 10 cents. |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ✅ | World War II ended in 1945. |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ❌ | dessed |

