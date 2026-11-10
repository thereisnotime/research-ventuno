# olmoe-1b-7b.npu.server

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `olmoe-1b-7b`, engine `llama`, device `npu`, NPU sessions `—`, started 2026-11-09 17:59:05, finished 2026-11-09 18:01:16.

Raw transcript: [olmoe-1b-7b.npu.server.transcript.jsonl](../results/transcripts/olmoe-1b-7b.npu.server.transcript.jsonl)

## Numbers

| Metric | Value |
|---|---|
| Load s | 8.0 |
| Cold TTFT s | 0.332 |
| Gen t/s | 28.76 |
| Prefill t/s (~1.7k tokens) | 567.83 |
| Long TTFT s | 3.227 |
| Peak RAM MB | 7371 |
| Peak pinned MB | 5583 |
| Tools | 1/7 |
| Quiz | 7/12 |
| Needle | ❌ |
| JSON schema | ✅ |

## Speed prompt reply

> A home router plays a crucial role in managing network traffic and providing security for a home network. It handles several key functions, including Network Address Translation (NAT), Dynamic Host Configuration Protocol (DHCP), Domain Name System (DNS) management, and firewall protection. Here's a detailed explanation of how each of these functions works: 1. Network Address Translation (NAT): NAT is a technique that allows multiple devices on a local network to share a single public IP address. The router assigns a unique private IP address to each device on the network, and when a device sen…

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

❌ reply: `The answer can be found in the maintenance log for the north warehouse, specifically in the entry that notes "Note from the`

<a id="tools"></a>
## Tools (1/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ❌ | I'm sorry, but as an AI language model, I don't have access to real-time weather information. However, you can easily find the current weather in Sofia by searching for "weather in Sofia" on a search engine or a weather … |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ❌ | I'm sorry, but as an AI language model, I am unable to search for flights in real-time or provide you with a specific flight itinerary. However, I can guide you on how to find flights from London to Tokyo on 24 December … |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ❌ | To compute 1234 * 5678 using a calculator, follow these steps: 1. Press the "x" button to clear the display. 2. Enter 1234. 3. Press the "x" button again to clear the display. 4. Enter 5678. 5. Press the "x" button to mu… |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ❌ | Subject: Lunch Hi Bob, I hope this email finds you well. I'm writing to let you know that I'm 10 minutes late for our lunch appointment. I apologize for any inconvenience this may cause and I appreciate your understandin… |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ✅ | Why did the cat join the internet? To find out where all the mice were hiding! (But let's be real, they're probably just lounging on a windowsill somewhere.) |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | As an AI language model, I don't have access to real-time weather data. However, I can provide you with the weather information for Paris and Berlin up until my knowledge cutoff date of September 2021. Paris, France: The… |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ❌ | I'm sorry, but as an AI language model, I don't have access to real-time weather information. The current weather in Oslo, Norway, can be found by checking a weather website or app, or by searching for "Oslo weather" on … |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

✅ reply: `{ "name": "Maria", "age": 34, "hobbies": ["climbing", "chess", "baking"] }`

<a id="quiz"></a>
## Quiz (7/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ❌ | 17 * 23 is equal to 399. This answer can be provided briefly. |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ❌ | To find the arrival time, we need to convert the time from minutes to hours. 2 hours 35 minutes is equal to 2 + 35/60 = 2.5833 hours. Since the train leaves at 14:40, the arrival time is 14:40 + 0.5833 hours. To convert … |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ✅ | The capital of Australia is Canberra. It is the country's largest city and the seat of government. Founded in 1908, Canberra was designed to be a capital that was not tied to any one state or territory, and it is situate… |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ❌ | The letter "r" appears twice in the word "strawberry." |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ✅ | The sorted numbers in ascending order are: 1, 2, 5, 9. So the answer is: 1, 2, 5, 9. |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ✅ | Based on the given information, Carol is the youngest. Since Alice is older than Bob, and Bob is older than Carol, Carol cannot be the youngest. Therefore, Carol is the youngest among Alice, Bob, and Carol. |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ✅ | "Good morning" in Spanish is "Buenos días". |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ❌ | The number that comes next in the sequence 2, 6, 12, 20, 30 is 40. In this sequence, each number is found by multiplying the previous number by 3 and adding 4. So: 2 x 3 + 4 = 6 6 x 3 + 4 = 12 12 x 3 + 4 = 20 20 x 3 + 4 … |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ✅ | The chemical symbol for gold is "Au," which comes from the Latin word "aurum," meaning "gold." Gold is a chemical element with the atomic number 79 and is a dense, soft, yellow, and highly conductive metal. It is highly … |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ❌ | Let's assume the cost of the ball is x cents. According to the given information, the bat costs $1.00 more than the ball, so the cost of the bat is x + $0.10. The total cost of the bat and the ball is $1.10, so we can wr… |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ✅ | The Second World War, commonly known as World War II, ended on May 8, 1945, when Germany signed an unconditional surrender. However, the formal surrender ceremony took place on May 15, 1945, in the British Cabinet Room i… |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ✅ | The word "stressed" spelled backwards is "desserts". A "desserts" is a type of sweet treat, often served after a meal. |

