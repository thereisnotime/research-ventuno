#!/usr/bin/env python3
"""Grade the Go, Rust and TypeScript coding replies collected on the board (code_bench.py, phases with "langs").

The board has no toolchains, so this runs on any machine with podman (or docker). Every program is compiled and run inside a
throwaway container with no network, a 10 s timeout per program and memory and process limits. Results are written
back into the same .jsonl rows:

  hidden      the model's function passes MultiPL-E's translation of the HumanEval tests (which it never saw)
  own_pass    (selftest) the model's own test program compiles and runs to the end on its own function
  compiles    the model's function compiled at all (a missing or broken code block counts as not compiling)

MultiPL-E has no reference solutions in these languages, so unlike Python there is no "asserts correct" column.
Go is run through goimports first, so missing or unused imports (a compile error in Go) are not counted against the
model; the other two languages are compiled as written.

Usage: grade_multi.py results/coding/multi/<model>.jsonl ...      (needs MultiPL-<lang>.jsonl next to this script)
"""
import json, os, re, shutil, subprocess, sys, tempfile

ENGINE = shutil.which("podman") or shutil.which("docker")

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = {l: {t["task_id"]: t for t in map(json.loads, open(os.path.join(HERE, f"MultiPL-{l}.jsonl")))}
         for l in ("go", "rs", "ts")}
FENCES = {"go": "go|golang", "rs": "rust|rs", "ts": "typescript|ts|javascript|js"}

# Images are built once, with the tools baked in, so the grading containers can run with --network none
IMAGES = {
    "go": ("veni-grade-go", "FROM docker.io/golang:1.23\nRUN go install golang.org/x/tools/cmd/goimports@v0.24.0\n"),
    "rs": ("veni-grade-rs", "FROM docker.io/rust:1.82-slim\n"),
    "ts": ("veni-grade-ts", "FROM docker.io/node:22-slim\nRUN npm install -g typescript@5.6.3\n"),
}

# Runs every job directory in /w inside the container; each writes its own result file
RUNNER = {
    "go": r'''
cd /w; export HOME=/tmp GOCACHE=/tmp/gocache GOFLAGS=-mod=mod CGO_ENABLED=0
for d in */; do d=${d%/}; ( cd $d
  printf 'module t\ngo 1.23\n' > go.mod
  goimports -w *.go 2>/dev/null
  if [ -f main_test.go ]; then timeout 60 go test ./... > out.txt 2>&1; else timeout 60 go run . > out.txt 2>&1; fi
  echo $? > rc ) ; done''',
    "rs": r'''
cd /w; for d in */; do d=${d%/}; ( cd $d
  if timeout 60 rustc --edition 2021 -O -o prog main.rs > out.txt 2>&1; then timeout 10 ./prog >> out.txt 2>&1; echo $? > rc
  else echo 200 > rc; fi ) ; done''',
    "ts": r'''
cd /w; for d in */; do d=${d%/}; ( cd $d
  if tsc --target es2022 --lib es2022 --module commonjs --noEmitOnError --outDir js main.ts > out.txt 2>&1
  then timeout 10 node js/main.js >> out.txt 2>&1; echo $? > rc; else echo 200 > rc; fi ) ; done''',
}


def blocks(text, lang):
    return [b.strip() + "\n" for b in re.findall(rf"```(?:{FENCES[lang]})?[ \t]*\n(.*?)```", text, re.S | re.I)]


def split_tests(code, lang):
    """Tests written into the function block: split at the first test entry point."""
    m = re.search({"go": r"^func (main|Test\w*)\s*\(", "rs": r"^(fn main\s*\(|#\[cfg\(test\)\])",
                   "ts": r"^(const assert|import .*assert|assert\.|function test)"}[lang], code, re.M)
    return (code[:m.start()], code[m.start():]) if m else (code, "")


def go_parts(code):
    """Split Go source into (imports, rest), dropping the package clause."""
    code = re.sub(r"^package \w+\s*$", "", code, flags=re.M)
    imports = re.findall(r'^import\s+(?:\w+\s+)?"[^"]+"\s*$', code, re.M)
    for block in re.findall(r"^import\s*\((.*?)\)", code, re.M | re.S):
        imports += [f"import {l.strip()}" for l in block.splitlines() if l.strip()]
    code = re.sub(r'^import\s+(?:\w+\s+)?"[^"]+"\s*$', "", code, flags=re.M)
    code = re.sub(r"^import\s*\(.*?\)", "", code, flags=re.M | re.S)
    return imports, code


def programs(t, lang, variant, reply):
    """(function source, {job name: (filename, program)}) for one reply."""
    text = reply.split("</think>")[-1]
    b = blocks(text, lang)
    sol, tests = (b[0] if b else ""), ""
    if variant == "selftest":
        sol, tests = split_tests(sol, lang)
        if len(b) > 1:
            tests = (tests + "\n" + "\n".join(b[1:])).strip() + "\n"
    if lang == "go":
        pkg = re.search(r"^package (\w+)", t["prompt"], re.M).group(1)
        pi, _ = go_parts(t["prompt"])
        mi, body = go_parts(sol)
        imp = "\n".join(dict.fromkeys(pi + mi))
        jobs = {"hidden": ("main_test.go", f"package {pkg}\n\n{imp}\n\n{body}\n\n{t['tests']}")}
        if variant == "selftest":
            ti, tbody = go_parts(tests)
            imp2 = "\n".join(dict.fromkeys(mi + ti))
            jobs["own"] = ("main.go", f"package main\n\n{imp2}\n\n{body}\n\n{tbody}")
    elif lang == "rs":
        hidden_tests = t["tests"].lstrip()[1:] if t["tests"].lstrip().startswith("}") else t["tests"]
        jobs = {"hidden": ("main.rs", f"#![allow(unused)]\n{sol}\n{hidden_tests}")}
        if variant == "selftest":
            own = re.sub(r"#\[cfg\(test\)\]\s*mod \w+\s*\{", "", tests) if "#[cfg(test)]" in tests else tests
            jobs["own"] = ("main.rs", f"#![allow(unused)]\n{sol}\n{own}")
    else:
        hidden_tests = t["tests"]
        jobs = {"hidden": ("main.ts", f"{sol}\n{hidden_tests}")}
        if variant == "selftest":
            own = tests if "declare var require" in tests else "declare var require: any;\n" + tests
            jobs["own"] = ("main.ts", f"{sol}\n{own}")
    return sol, jobs


def build(lang):
    name, dockerfile = IMAGES[lang]
    if subprocess.run([ENGINE, "image", "inspect", name], capture_output=True).returncode != 0:
        subprocess.run([ENGINE, "build", "-q", "-t", name, "-"], input=dockerfile.encode(), check=True)
    return name


def run_jobs(lang, jobs):
    """jobs: {id: (filename, source)} -> {id: (rc, output tail)}"""
    out = {}
    with tempfile.TemporaryDirectory() as d:
        for i, (fname, src) in jobs.items():
            os.makedirs(f"{d}/{i}")
            open(f"{d}/{i}/{fname}", "w").write(src)
        subprocess.run([ENGINE, "run", "--rm", "--name", f"veni-grade-{lang}-{os.getpid()}", "--network", "none", *(["--userns", "keep-id"] if "podman" in ENGINE else ["--user", f"{os.getuid()}:{os.getgid()}"]),
                        "--memory", "4g", "--pids-limit", "512", "-v", f"{d}:/w", build(lang), "sh", "-c", RUNNER[lang]],
                       check=True, capture_output=True)
        for i in jobs:
            try:
                rc = int(open(f"{d}/{i}/rc").read())
            except (OSError, ValueError):
                rc = 999
            out[i] = (rc, open(f"{d}/{i}/out.txt", errors="replace").read()[-400:] if os.path.exists(f"{d}/{i}/out.txt") else "")
    return out


def grade_file(path):
    rows = [json.loads(l) for l in open(path)]
    for lang in ("go", "rs", "ts"):
        jobs, owners = {}, {}
        for n, r in enumerate(rows):
            if r.get("lang") != lang or "reply" not in r:
                continue
            sol, js = programs(TASKS[lang][r["task"]], lang, r["variant"], r["reply"])
            for kind, job in js.items():
                jobs[f"{n}-{kind}"] = job
                owners[f"{n}-{kind}"] = (n, kind)
            r["has_code"] = bool(sol.strip())
        if not jobs:
            continue
        res = run_jobs(lang, jobs)
        for jid, (rc, tail) in res.items():
            n, kind = owners[jid]
            r = rows[n]
            if kind == "hidden":
                r["hidden"] = rc == 0 and r["has_code"]
                r["compiles"] = rc != 200 and r["has_code"] and not ("build failed" in tail or "[setup failed]" in tail)
                r["hidden_err"] = "" if r["hidden"] else tail[-300:]
            else:
                r["own_pass"] = rc == 0 and r["has_code"]
                r["own_err"] = "" if r["own_pass"] else tail[-300:]
        print(f"{path} {lang}: {sum(1 for r in rows if r.get('lang') == lang and r.get('hidden'))} hidden passes")
    open(path, "w").write("".join(json.dumps(r) + "\n" for r in rows))


if __name__ == "__main__":
    if not ENGINE:
        raise SystemExit("needs podman or docker")
    for p in sys.argv[1:]:
        grade_file(p)
