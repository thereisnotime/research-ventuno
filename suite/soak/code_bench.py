#!/usr/bin/env python3
"""Coding test: a fixed subset of HumanEval, in two variants, against a running OpenAI-compatible server.

hidden    The model gets the function signature and docstring and writes the function. It is then run against
          HumanEval's own unit tests, which the model never sees. Score: tasks whose hidden tests pass.
selftest  The model writes the function and its own assert-based tests. Three things are measured:
          - own pass:   its asserts pass on its own function (does it believe its code works?)
          - assert ok:  its asserts pass on the reference solution (are its tests actually correct?)
          - hidden:     the hidden tests pass on its function (does the code really work?)
          A task where own pass is true but hidden fails is a confident wrong answer.

Model code runs in a separate python3 -I process with a 10 s timeout and memory and process limits."""
import ast, json, os, re, resource, subprocess, sys, tempfile, time, urllib.request

CURRENT = None                         # (variant, task) being asked, for the caller's watchdog
HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = [json.loads(l) for l in open(os.path.join(HERE, "HumanEval.jsonl"))][::4]      # 41 tasks, fixed

HIDDEN_PROMPT = """Complete this Python function. Reply with the full function, including the signature and any imports,
in a single ```python code block. Do not include tests or example usage.

```python
{prompt}```"""

SELFTEST_PROMPT = """Implement this Python function, then test it.

```python
{prompt}```

Reply with exactly two ```python code blocks:
1. The full function, including the signature and any imports.
2. Your tests: at least 5 `assert` statements that call `{entry}` with concrete inputs and expected outputs,
   including edge cases. Work out each expected value from the specification, not by running the code."""

# Runs each top-level statement of the test block on its own, so one wrong assert does not hide the others
HARNESS = r'''
import ast, json, sys
src, tests = open(sys.argv[1]).read(), open(sys.argv[2]).read()
g = {}
exec(compile(src, "solution", "exec"), g)
res = {"asserts": 0, "passed": 0, "errors": []}
for node in ast.parse(tests).body:
    code = compile(ast.Module([node], []), "tests", "exec")
    if isinstance(node, ast.Assert):
        res["asserts"] += 1
        try:
            exec(code, g); res["passed"] += 1
        except Exception as e:
            res["errors"].append(f"{type(e).__name__}: {ast.unparse(node)[:120]}")
    else:
        try:
            exec(code, g)
        except Exception as e:
            res["errors"].append(f"setup {type(e).__name__}: {ast.unparse(node)[:120]}")
print(json.dumps(res))
'''


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    os.setsid()


def run_py(files, argv, timeout=10):
    with tempfile.TemporaryDirectory() as d:
        for name, text in files.items():
            open(os.path.join(d, name), "w").write(text)
        try:
            p = subprocess.run(["python3", "-I", *argv], cwd=d, capture_output=True, text=True, timeout=timeout,
                               preexec_fn=limits)
            return p.returncode, p.stdout, p.stderr[-300:]
        except subprocess.TimeoutExpired:
            return None, "", "timeout"


def hidden_pass(task, solution):
    prog = solution + "\n\n" + task["test"] + f"\n\ncheck({task['entry_point']})\n"
    rc, _, err = run_py({"t.py": prog}, ["t.py"])
    return rc == 0, err if rc != 0 else ""


def own_tests(solution, tests):
    rc, out, err = run_py({"h.py": HARNESS, "s.py": solution, "x.py": tests}, ["h.py", "s.py", "x.py"])
    try:
        return json.loads(out.strip().splitlines()[-1])
    except Exception:
        return {"asserts": 0, "passed": 0, "errors": [f"harness: {err or 'no output'}"]}


def blocks(text):
    return [b.strip() + "\n" for b in re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)]


def chat(port, model, engine, prompt, max_tokens):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens,
            "temperature": 0, "stream": True, "user": f"code-{time.time_ns()}"}
    if engine != "genie":
        body["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    out, n = [], 0
    with urllib.request.urlopen(req, timeout=300) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            for c in json.loads(line[5:]).get("choices") or []:
                t = (c.get("delta") or {}).get("content")
                if t:
                    out.append(t); n += 1
    return "".join(out), n


def run(port, model, engine, log, done=()):
    """Log one row per (variant, task) via log(); tasks already in `done` are skipped (resume after a reset)."""
    for variant in ("hidden", "selftest"):
        for t in TASKS:
            if (variant, t["task_id"]) in done:
                continue
            p = (HIDDEN_PROMPT if variant == "hidden" else SELFTEST_PROMPT).format(prompt=t["prompt"],
                                                                                 entry=t["entry_point"])
            global CURRENT
            CURRENT = (variant, t["task_id"])
            s = time.time()
            text, chunks = chat(port, model, engine, p, 768 if variant == "hidden" else 1280)
            row = {"variant": variant, "task": t["task_id"], "lat_s": round(time.time() - s, 1), "chunks": chunks}
            b = blocks(text)
            sol = b[0] if b else text
            if t["entry_point"] not in sol:            # model returned only the body: put the signature back
                sol = t["prompt"] + sol
            row["hidden"], row["hidden_err"] = hidden_pass(t, sol)
            if variant == "selftest":
                tests = b[1] if len(b) > 1 else ""
                own = own_tests(sol, tests)
                ref = own_tests(t["prompt"] + t["canonical_solution"], tests)
                row.update(asserts=own["asserts"], own_passed=own["passed"],
                           own_pass=own["asserts"] > 0 and own["passed"] == own["asserts"],
                           ref_passed=ref["passed"],
                           asserts_correct=ref["asserts"] > 0 and ref["passed"] == ref["asserts"],
                           own_errors=own["errors"][:3], ref_errors=ref["errors"][:3])
            row["reply"] = text[:4000]
            log(row)


if __name__ == "__main__":
    # Standalone: code_bench.py <port> <model> <engine> <out.jsonl>
    port, model, engine, out = sys.argv[1:5]
    run(int(port), model, engine, lambda r: print(json.dumps(r), file=open(out, "a")))
