# deepseek-coder-v2-lite.cpu.server.new.retry

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `deepseek-coder-v2-lite`, engine `llama`, device `cpu`, NPU sessions `0`, started 2026-11-17 22:01:57, finished 2026-11-17 22:08:46.

**Environment [E5](environments.md#e5)**: Kernel `6.8.0-1089-qcom`, Extra kernel args `watchdog.stop_on_reboot=0`, NPU firmware (cdsp0.mbn) `dragonwing 20260612 (restored)`, linux-firmware `20240318.git3b128b60.0ubuntu3.1`, qcom-fastrpc1 (libcdsprpc) `1.0.15+repack2`, Engine `llama.cpp`, Engine build `d5bbcd1`

Raw transcript: [deepseek-coder-v2-lite.cpu.server.new.retry.transcript.jsonl](../results/performance/transcripts/deepseek-coder-v2-lite.cpu.server.new.retry.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 52.1 |
| Cold TTFT s | 14.04 |
| Gen t/s | 14.35 |
| Prefill t/s (~1.7k tokens) | 25.03 |
| Long TTFT s | 71.373 |
| Peak RAM MB | 9051 |
| Peak pinned MB | 64 |
| Tools | 1/7 |
| Quiz | 10/12 |
| Needle | ✅ |
| JSON schema | ✅ |

## Speed prompt reply

> A home router plays a crucial role in managing network traffic and ensuring secure communication between devices connected to it. Here’s a detailed explanation of how a home router handles NAT (Network Address Translation), DHCP (Dynamic Host Configuration Protocol), DNS (Domain Name System), and its firewall. ### Network Address Translation (NAT) **NAT Overview:** NAT is a method used to allow multiple devices on a private network to connect to the internet while keeping the private IP addresses hidden. This is achieved by translating private IP addresses to a public IP address before sending…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

✅ reply: `The spare key for the server room is in locker 4417.`

<a id="tools"></a>
## Tools (1/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ❌ | To find the current weather in Sofia, Bulgaria, in Celsius, I will perform the following steps: 1. Open a reliable weather information website or application. 2. Search for the city of Sofia. 3. Look for the current temp… |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ❌ | I'm sorry, but I can't search the internet or access real-time data, including flight information. However, you can easily find flights from London to Tokyo on 24 December 2026 by using a trusted travel booking website o… |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ❌ | To compute the product of 1234 and 5678 using a calculator, follow these steps: 1. Turn on the calculator. 2. Enter the number 1234. 3. Press the multiplication button (usually denoted by an "x" or "*"). 4. Enter the num… |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ❌ | Subject: Lunch - 10 minutes late Hi Bob, I hope this message finds you well. I'm writing to let you know that I'm running a bit late for our lunch meeting. I'm currently 10 minutes away and should be there shortly. Thank… |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ✅ | Why don't cats play poker in the jungle? Because the cheetahs always take all the money! |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | I cannot provide real-time data or predictions, as they can vary greatly depending on the time of year, weather patterns, and local conditions. To get the most accurate and up-to-date weather information for Paris and Be… |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ❌ | not in transcript ⚠️ `no get_weather call to answer` |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

✅ reply: `{"name": "Maria", "age": 34, "hobbies": ["climbing", "chess", "baking"]}`

<a id="quiz"></a>
## Quiz (10/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ❌ | To find the product of 17 and 23, we can use the distributive property of multiplication over addition. We can break down the numbers into simpler components and then multiply them. First, let's express 23 as a sum of tw… |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ✅ | To determine the arrival time of the train, we need to add the duration of the trip to the departure time. The departure time is 14:40, and the trip duration is 2 hours and 35 minutes. First, let's add the hours: - The i… |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ✅ | The capital of Australia is Canberra. |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ❌ | The letter r appears 2 times in the word "strawberry." |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ✅ | To sort the numbers in ascending order, we arrange them from the smallest to the largest. Here are the steps: 1. Identify the numbers to be sorted: 5, 2, 9, 1. 2. Compare the numbers and arrange them in ascending order: … |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ✅ | Carol is the youngest. |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ✅ | Good morning in Spanish is "Buenos días". |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ✅ | The next number in the sequence is 42. To find this, we can observe the pattern in the sequence. The differences between consecutive terms are increasing by 4, 6, 8, 10, and so on. Therefore, the next difference should b… |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ✅ | The chemical symbol for gold is Au. |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ✅ | To solve the problem, let's define the variables and set up the equations based on the given information. 1. Let \( x \) be the cost of the ball in cents. 2. The cost of the bat is \( x + 100 \) cents (since the bat cost… |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ✅ | World War II ended in 1945. |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ✅ | The word "stressed" backwards is "desserts." |

