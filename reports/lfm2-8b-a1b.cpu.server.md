# lfm2-8b-a1b.cpu.server

[← README](../README.md) · [all runs](index.md) · [quiz matrix](quiz.md) · [tools matrix](tools.md)

Model `lfm2-8b-a1b`, engine `llama`, device `cpu`, NPU sessions `—`, started 2026-11-08 21:27:08, finished 2026-11-08 21:30:07.

No transcript was recorded for this run (it ran before the suite saved transcripts), so only pass/fail is known.

## Numbers

| Metric | Value |
|---|---|
| Load s | 8.0 |
| Cold TTFT s | 0.683 |
| Gen t/s | 24.54 |
| Prefill t/s (~1.7k tokens) | 49.22 |
| Long TTFT s | 38.389 |
| Peak RAM MB | 5492 |
| Peak pinned MB | 500 |
| Tools | 6/7 |
| Quiz | 10/12 |
| Needle | ✅ |
| JSON schema | ✅ |

<a id="needle"></a>
## Needle

A secret code (4417) buried in a ~1.7k-token filler log; the model is asked to return it.

✅ reply: `—`

<a id="tools"></a>
## Tools (6/7)

| # | Case | Prompt | Expected | Pass | Model output |
|---|---|---|---|---|---|
| <a id="tool-weather"></a>1 | weather | What's the weather in Sofia right now, in celsius? | get_weather(city=Sofia, unit=celsius) | ✅ | — |
| <a id="tool-flights"></a>2 | flights | Find me flights from London to Tokyo on 24 December 2026. | search_flights(London, Tokyo, 2026-12-24) | ✅ | — |
| <a id="tool-calculator"></a>3 | calculator | Use the calculator to compute 1234 * 5678. | calculator(expression has 1234 and 5678) | ✅ | — |
| <a id="tool-email"></a>4 | email | Email bob@example.com with subject 'Lunch' and tell him I'm 10 minutes late. | send_email(to=bob@example.com, subject has Lunch) | ✅ | — |
| <a id="tool-no_tool"></a>5 | no_tool | Tell me a short joke about cats. | plain text, no tool call | ✅ | — |
| <a id="tool-parallel"></a>6 | parallel | What's the weather in Paris and in Berlin? | get_weather for both Paris and Berlin | ❌ | — |
| <a id="tool-use_result"></a>7 | use_result | What is the weather in Oslo? (then the tool result) | after tool result {temp_c: 7, light rain}: answer mentions 7 and rain, no new call | ✅ | — |

<a id="json"></a>
## JSON schema

Prompt: Extract the person: Maria is 34 and loves climbing, chess and baking.

✅ reply: `—`

<a id="quiz"></a>
## Quiz (10/12)

| # | Question | Expected (regex) | Pass | Model answer |
|---|---|---|---|---|
| <a id="q1"></a>1 | What is 17 * 23? | `\b391\b` | ✅ | — |
| <a id="q2"></a>2 | A train leaves at 14:40 and the trip takes 2 hours 35 minutes. What time does it arrive (HH:MM)? | `17:15` | ✅ | — |
| <a id="q3"></a>3 | What is the capital of Australia? | `canberra` | ✅ | — |
| <a id="q4"></a>4 | How many times does the letter r appear in the word strawberry? | `\b(3\|three)\b` | ❌ | — |
| <a id="q5"></a>5 | Sort these numbers ascending: 5, 2, 9, 1 | `1\D+2\D+5\D+9` | ✅ | — |
| <a id="q6"></a>6 | Alice is older than Bob. Bob is older than Carol. Who is the youngest? | `carol` | ✅ | — |
| <a id="q7"></a>7 | Translate 'good morning' into Spanish. | `buenos d[ií]as` | ✅ | — |
| <a id="q8"></a>8 | What number comes next: 2, 6, 12, 20, 30, ? | `\b42\b` | ✅ | — |
| <a id="q9"></a>9 | What is the chemical symbol for gold? | `\bau\b` | ✅ | — |
| <a id="q10"></a>10 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How many cents does the ball cost? | `\b(5\|five)\b` | ✅ | — |
| <a id="q11"></a>11 | In what year did World War II end? | `1945` | ✅ | — |
| <a id="q12"></a>12 | Write the word 'stressed' backwards. | `desserts` | ❌ | — |

