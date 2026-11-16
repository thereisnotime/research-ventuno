# Coding test

The same 41 HumanEval tasks (every 4th of the 164) in Python, plus MultiPL-E's translations into Go (38),
Rust (39) and TypeScript (39). Temperature 0, one attempt per task. Results: [`results/coding/`](../../results/coding/),
write-up: README §4.12.

## Two variants

| Variant | The model is asked to | Scored by |
|---|---|---|
| `hidden` | write the function from its signature and docstring | the benchmark's own unit tests, which the model never sees |
| `selftest` | write the function and at least 5 tests of its own | **own pass**: its tests pass on its code. **Hidden**: the hidden tests pass on its code. **Asserts correct** (Python only): its tests pass on the reference solution |

A task where its own tests pass but the hidden tests fail is a *confident wrong answer*: the model believes
broken code works. MultiPL-E ships no reference solutions, so "asserts correct" exists only for Python.

## Files

| File | Role |
|---|---|
| `code_bench.py` | Prompts, the request loop and the Python grader. Runs on the board, against any OpenAI-compatible server |
| `grade_multi.py` | Grades the Go, Rust and TypeScript replies afterwards on a machine with containers (the board has no compilers) |
| `HumanEval.jsonl`, `MultiPL-{go,rs,ts}.jsonl` | Task data, not in the repo: [download commands](../../docs/reproduce.md) |

The runs are scheduled as `"kind": "code"` phases in [`../stability/plan.json`](../stability/plan.json), so each
model starts from a fresh boot and a frozen NPU is reset by the watchdog. `"thinking": true` raises the reply
limit for reasoning models, `"budget"` sets it explicitly, `"langs"` selects the non-Python languages.

## Safety

Model code is untrusted. Python runs in a separate `python3 -I` process with a 10 s timeout and memory and
process limits; Go, Rust and TypeScript run in throwaway containers with no network. Run it on a test machine.
