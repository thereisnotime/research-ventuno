# phi-4-mini.npu.server

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `phi-4-mini`, engine `llama`, device `npu`, NPU sessions `—`, started 2026-11-08 21:57:18, finished 2026-11-08 21:59:35.

Raw transcript: [phi-4-mini.npu.server.transcript.jsonl](../results/transcripts/phi-4-mini.npu.server.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 6.1 |
| Cold TTFT s | 0.193 |
| Gen t/s | 14.04 |
| Prefill t/s (~1.7k tokens) | 456.92 |
| Long TTFT s | 3.85 |
| Peak RAM MB | 5429 |
| Peak pinned MB | 3500 |
| Tools | 2/7 |
| Quiz | 9/12 |
| Needle | ✅ |
| JSON schema | ✅ |

## Speed prompt reply

> A home router is a crucial component of a home network, managing the flow of data between the internet and the devices connected to your home network. It handles several key functions, including Network Address Translation (NAT), Dynamic Host Configuration Protocol (DHCP), Domain Name System (DNS), and firewall protection. Let's break down each of these functions in detail: ### 1. Network Address Translation (NAT) NAT is a method used by routers to remap IP addresses on incoming packets. This is essential because most home networks use a single public IP address provided by the Internet Servic…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

✅ reply: `4417`

<a id="tools"></a>
## Tools (2/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ❌ | I'm sorry, but I can't provide real-time weather updates. You can check the current weather in Sofia by visiting a weather website like Weather.com, AccuWeather, or by using a weather app on your smartphone. These platfo… |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ❌ | I'm sorry, but I can't assist with that. I recommend checking popular travel websites like Skyscanner, Google Flights, or booking directly through airlines for the most accurate and up-to-date information. |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ❌ | The result of 1234 multiplied by 5678 is 7006652. |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ❌ | I'm sorry, but I can't assist with that. How about I help you draft an email instead? Here's a suggestion: --- Subject: I'm Running Late for Lunch Hi Bob, I hope you're having a great day so far. I wanted to let you know… |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ✅ | Why don't cats play poker in the jungle? Too many cheetahs! |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | I'm sorry, but I can't provide real-time weather updates. You can check the latest weather conditions for Paris and Berlin by visiting a weather website like Weather.com, AccuWeather, or using a weather app on your smart… |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ✅ | The current weather in Oslo is 7 degrees Celsius with light rain. Please note that weather conditions can change rapidly, so it's always a good idea to check a reliable weather service for the most up-to-date information… |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

✅ reply: `{ "name": "Maria", "age": 34, "hobbies": ["climbing", "chess", "baking"] }`

<a id="quiz"></a>
## Quiz (9/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ✅ | The product of 17 and 23 is 391. |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ❌ | 15:15 |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ✅ | Canberra |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ❌ | Four. |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ✅ | Sorted in ascending order: 1, 2, 5, 9. |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ✅ | Carol is the youngest. |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ✅ | Buenos días. |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ❌ | The pattern involves adding consecutive even numbers to the previous term: 2 (2+4), 6 (6+2+4), 12 (12+6+2+4), 20 (20+12+6+2+4), 30 (30+20+12+6+2+4). The next number would be 30 + 30 = 60. So, the next number in the seque… |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ✅ | Au |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ✅ | The ball costs 50 cents. Here's the reasoning: 1. Let the cost of the ball be x cents. 2. The cost of the bat is x + 100 cents (since it's $1.00 more). 3. The total cost is x + (x + 100) = 110 cents (since $1.10 is 110 c… |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ✅ | 1945 |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ✅ | desserts |

