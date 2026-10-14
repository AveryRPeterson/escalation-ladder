"""Evaluation harness: does the escalation ladder beat a fixed cheap model, a fixed strong model,
or a cheap model with an advisor, on tasks with an automated pass/fail check?

Commands (run from anywhere):
  python harness.py validate            reference solutions must pass; starting code must not
  python harness.py setup-ladder        set the ladder's stored policy to `balanced` for arm D
  python harness.py run --arms A,B,C,D --tasks all --reps 1 [--parallel 3] [--out DIR]
  python harness.py summary DIR         table of pass rate, cost and consults per arm

Arms (all start from the same files in a fresh temp directory; the model is told nothing about the hidden tests):
  A  sonnet-5-5, effort low,  advisor opus            (the cheap-executor-plus-advisor pattern)
  B  haiku-4-5,               advisor opus            (cheaper executor, same advisor)
  C  opus-5-5, effort high,   no advisor              (always-strong baseline)
  D  A plus the escalation-ladder mod on `balanced`   (isolates what the ladder adds to A)
"""
import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS_DIR = os.path.join(ROOT, "tasks")
MOD_DIR = r"C:\Users\CycleTranSister\.claude\dev-mods\2beefaee-9e21-4ab2-af56-3ef08da00a0a\escalation-ladder"
WORK_BASE = os.path.join(tempfile.gettempdir(), "ladder-eval", "runs")

ARMS = {
    "A": dict(model="claude-sonnet-5-5", effort="low", advisor="opus", plugin=False),
    "B": dict(model="claude-haiku-4-5-20251001", effort=None, advisor="opus", plugin=False),
    "C": dict(model="claude-opus-5-5", effort="high", advisor=None, plugin=False),
    "D": dict(model="claude-sonnet-5-5", effort="low", advisor="opus", plugin=True),
}
TOOLS = "Read,Write,Edit,Glob,Grep,Bash,PowerShell"
PER_RUN_TIMEOUT = 900

# $/MTok (see hooks/lib/policy.ts PRICES); used only to split total_cost_usd into main vs advisor
PRICES = {
    "claude-haiku-4-5": (1, 5, 0.1, 2),
    "claude-sonnet-5-5": (2, 10, 0.2, 2),
    "claude-opus-5-5": (4, 20, 0.2, 2),
}


def task_names():
    return sorted(d for d in os.listdir(TASKS_DIR) if os.path.isdir(os.path.join(TASKS_DIR, d)))


def pick_tasks(spec):
    names = task_names()
    if spec == "all":
        return names
    want = spec.split(",")
    out = [n for n in names if any(n == w or n.startswith(w + "-") or n.startswith(w) for w in want)]
    if not out:
        raise SystemExit(f"no task matches {spec!r}; have {names}")
    return out


def prepare(task, tag):
    wd = os.path.join(WORK_BASE, f"{datetime.now():%Y%m%d-%H%M%S}-{task}-{tag}")
    shutil.copytree(os.path.join(TASKS_DIR, task, "start"), wd)
    return wd


def hidden_score(task, workdir):
    tdir = os.path.join(TASKS_DIR, task)
    for fn in os.listdir(tdir):
        if fn == "hidden_test.py" or fn.startswith("hidden_"):
            shutil.copy(os.path.join(tdir, fn), os.path.join(workdir, fn))
    try:
        p = subprocess.run([sys.executable, os.path.join(ROOT, "run_hidden.py"), workdir],
                           capture_output=True, text=True, timeout=180, cwd=workdir)
        line = [l for l in p.stdout.splitlines() if l.startswith("{")]
        if not line:
            return {"total": 1, "passed": 0, "units": [{"id": "runner", "ok": False, "error": (p.stderr or p.stdout)[-300:]}]}
        return json.loads(line[-1])
    except subprocess.TimeoutExpired:
        return {"total": 1, "passed": 0, "units": [{"id": "timeout", "ok": False, "error": "hidden tests timed out (hang?)"}]}


def cost_split(usage, main_model):
    """Split a result's usage into (main_usd, advisor_usd) from its iterations, using our price table.
    A `message` iteration carries no model id, so it is priced as the arm's main model."""
    main = adv = 0.0
    for it in (usage or {}).get("iterations") or []:
        m = it.get("model") or main_model
        price = PRICES.get(m) or PRICES.get(m.rsplit("-", 1)[0])
        if it.get("type") == "advisor_message":
            price = price or PRICES["claude-opus-5-5"]
        if not price:
            continue
        i, o, cr, cw = price
        usd = (
            it.get("input_tokens", 0) * i + it.get("output_tokens", 0) * o
            + it.get("cache_read_input_tokens", 0) * cr + it.get("cache_creation_input_tokens", 0) * i * cw / 1.0
        ) / 1e6
        if it.get("type") == "advisor_message":
            adv += usd
        else:
            main += usd
    return main, adv


def run_one(task, arm, rep, outdir):
    cfg = ARMS[arm]
    wd = prepare(task, f"{arm}{rep}")
    with open(os.path.join(TASKS_DIR, task, "prompt.txt"), encoding="utf-8") as f:
        prompt = f.read().strip()
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--no-session-persistence",
           "--permission-mode", "acceptEdits", "--allowedTools", TOOLS, "--model", cfg["model"],
           "--setting-sources", "project,local"]
    if cfg["effort"]:
        cmd += ["--effort", cfg["effort"]]
    settings = {"advisorModel": cfg["advisor"]} if cfg["advisor"] else {}
    cmd += ["--settings", json.dumps(settings)]
    if cfg["plugin"]:
        cmd += ["--plugin-dir", MOD_DIR]
    t0 = time.time()
    rec = {"task": task, "arm": arm, "rep": rep, "workdir": wd, "started": datetime.now().isoformat(timespec="seconds")}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=PER_RUN_TIMEOUT, cwd=wd, encoding="utf-8", errors="replace")
        rec["exit"] = p.returncode
        raw = p.stdout.strip()
        try:
            data = json.loads(raw)
        except Exception:
            data = {"parse_error": True, "stdout_tail": raw[-500:], "stderr_tail": p.stderr[-500:]}
    except subprocess.TimeoutExpired:
        data = {"timeout": True}
        rec["exit"] = None
    rec["wall_s"] = round(time.time() - t0, 1)
    usage = data.get("usage") or {}
    main_usd, adv_usd = cost_split(usage, cfg["model"])
    its = usage.get("iterations") or []
    rec.update({
        "is_error": data.get("is_error"),
        "result_tail": (data.get("result") or "")[-300:],
        "num_turns": data.get("num_turns"),
        "duration_ms": data.get("duration_ms"),
        "total_cost_usd": data.get("total_cost_usd"),
        "est_main_usd": round(main_usd, 4),
        "est_advisor_usd": round(adv_usd, 4),
        "advisor_calls": sum(1 for it in its if it.get("type") == "advisor_message"),
        "output_tokens": usage.get("output_tokens"),
        "cache_creation": usage.get("cache_creation_input_tokens"),
        "cache_read": usage.get("cache_read_input_tokens"),
        "model_usage": data.get("modelUsage"),
        "parse_error": data.get("parse_error"),
        "timeout": data.get("timeout"),
    })
    rec["hidden"] = hidden_score(task, wd)
    rec["pass_units"] = rec["hidden"]["passed"]
    rec["total_units"] = rec["hidden"]["total"]
    rec["all_pass"] = rec["hidden"]["total"] > 0 and rec["hidden"]["passed"] == rec["hidden"]["total"]
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, f"{task}__{arm}__{rep}.json"), "w", encoding="utf-8") as f:
        json.dump({"record": rec, "raw": data}, f, indent=1)
    return rec


def cmd_validate(_):
    ok = True
    for t in task_names():
        wd = prepare(t, "ref")
        ref = os.path.join(TASKS_DIR, t, "reference")
        for fn in os.listdir(ref):
            shutil.copy(os.path.join(ref, fn), os.path.join(wd, fn))
        if os.path.exists(os.path.join(wd, "report.py")):
            subprocess.run([sys.executable, "report.py"], cwd=wd, check=True)
        r = hidden_score(t, wd)
        wd0 = prepare(t, "start")
        s = hidden_score(t, wd0)
        good = r["total"] > 0 and r["passed"] == r["total"] and s["passed"] < s["total"]
        ok &= good
        bad = [u["id"] for u in r["units"] if not u["ok"]][:3]
        print(f"{t:22s} reference {r['passed']}/{r['total']}  start {s['passed']}/{s['total']}  {'OK' if good else 'PROBLEM ' + str(bad)}")
    sys.exit(0 if ok else 1)


def cmd_setup_ladder(_):
    for line in ("/ladder preset balanced", "/ladder status"):
        p = subprocess.run(["claude", "-p", line, "--plugin-dir", MOD_DIR, "--no-session-persistence", "--model", "claude-sonnet-5-5"],
                           capture_output=True, text=True, timeout=180, encoding="utf-8", errors="replace")
        print(f"$ {line}\n{(p.stdout or p.stderr).strip()[:900]}\n")


def cmd_run(a):
    arms = a.arms.split(",")
    tasks = pick_tasks(a.tasks)
    out = a.out or os.path.join(ROOT, "results", datetime.now().strftime("%Y%m%d-%H%M%S"))
    jobs = [(t, arm, r) for t in tasks for arm in arms for r in range(1, a.reps + 1)]
    print(f"{len(jobs)} runs -> {out}", flush=True)
    done = []
    with cf.ThreadPoolExecutor(max_workers=a.parallel) as ex:
        futs = {ex.submit(run_one, t, arm, r, out): (t, arm, r) for t, arm, r in jobs}
        for f in cf.as_completed(futs):
            rec = f.result()
            done.append(rec)
            print(f"{rec['task']:20s} {rec['arm']}{rec['rep']}  {rec['pass_units']}/{rec['total_units']}  "
                  f"${rec['total_cost_usd'] if rec['total_cost_usd'] is not None else float('nan'):.3f}  "
                  f"{rec['wall_s']:.0f}s  adv={rec['advisor_calls']}  turns={rec['num_turns']}", flush=True)
    cmd_summary(argparse.Namespace(dir=out))


def cmd_summary(a):
    recs = []
    for fn in sorted(os.listdir(a.dir)):
        if fn.endswith(".json"):
            recs.append(json.load(open(os.path.join(a.dir, fn), encoding="utf-8"))["record"])
    arms = sorted({r["arm"] for r in recs})
    tasks = sorted({r["task"] for r in recs})
    print(f"\n{'arm':4s}{'runs':>5s}{'units':>9s}{'all-pass':>10s}{'cost $':>9s}{'$/run':>8s}{'sec/run':>9s}{'advisor':>9s}{'adv $':>8s}")
    for arm in arms:
        rs = [r for r in recs if r["arm"] == arm]
        pu = sum(r["pass_units"] for r in rs)
        tu = sum(r["total_units"] for r in rs)
        ap = sum(1 for r in rs if r["all_pass"])
        cost = sum(r["total_cost_usd"] or 0 for r in rs)
        print(f"{arm:4s}{len(rs):5d}{f'{pu}/{tu}':>9s}{f'{ap}/{len(rs)}':>10s}{cost:9.2f}{cost / len(rs):8.2f}"
              f"{sum(r['wall_s'] for r in rs) / len(rs):9.0f}{sum(r['advisor_calls'] for r in rs):9d}{sum(r['est_advisor_usd'] for r in rs):8.2f}")
    print("\nper task (units passed / total, $):")
    print(f"{'task':22s}" + "".join(f"{arm:>16s}" for arm in arms))
    for t in tasks:
        row = f"{t:22s}"
        for arm in arms:
            rs = [r for r in recs if r["task"] == t and r["arm"] == arm]
            if not rs:
                row += f"{'-':>16s}"
                continue
            row += f"{f'{sum(r['pass_units'] for r in rs)}/{sum(r['total_units'] for r in rs)} ${sum(r['total_cost_usd'] or 0 for r in rs):.2f}':>16s}"
        print(row)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    sub.add_parser("setup-ladder").set_defaults(fn=cmd_setup_ladder)
    r = sub.add_parser("run")
    r.add_argument("--arms", default="A,B,C,D")
    r.add_argument("--tasks", default="all")
    r.add_argument("--reps", type=int, default=1)
    r.add_argument("--parallel", type=int, default=3)
    r.add_argument("--out")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("summary")
    s.add_argument("dir")
    s.set_defaults(fn=cmd_summary)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
