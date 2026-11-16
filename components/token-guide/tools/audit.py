#!/usr/bin/env python3
"""token-guide audit: inspect supplied session usage and estimate workflow costs.

Usage: audit.py <session.jsonl>
Reads the main transcript and, if present, <session>/subagents/*.jsonl.

Every figure is in input-equivalent tokens (IET): the price of one uncached input token.
Cache reads cost 0.1, 1h cache writes 2.0, 5m cache writes 1.25 and output 5.0 IET. These are
historical default accounting ratios. Override them with TG_READ, TG_WRITE_1H, TG_WRITE_5M, TG_OUT.

Why this matters: every turn re-reads the whole context. Anything added to it (a tool result, a
prompt you wrote) is paid again, at the cache-read rate, on every later turn until compaction.
So the waste of a pattern is "extra turns x context" or "extra tokens x turns they ride along".
Each finding below states that mechanism, the measured cost, the cost of the cheaper path, and the fix.
"""
import glob
import json
import os
import re
import sys

READ = float(os.environ.get("TG_READ", 0.1))
W1H = float(os.environ.get("TG_WRITE_1H", 2.0))
W5M = float(os.environ.get("TG_WRITE_5M", 1.25))
OUT = float(os.environ.get("TG_OUT", 5.0))
CAP = 2000          # chars a trimmed result would keep
CHARS_PER_TOKEN = 3.6
NOTIFY = re.compile(r"<task-notification>|agent-message from=|\[Subagent hand-back\]")
TIMED_OUT = re.compile(r"did not complete within its \d+s timeout|moved to the background")
SHELL_ERR = re.compile(r"(?m)^ugrep: error|Exit code 14[34]\b")
REVIEW = re.compile(r"\breview|audit\b", re.I)
PATH = re.compile(r"(?:[\w.-]+/)+[\w.-]+\.(?:mjs|js|ts|py|rs|md|json|css|html|sh)\b")
WORD = re.compile(r"[A-Za-z0-9_./-]{8,}")


def tok(chars):
    return int(chars / CHARS_PER_TOKEN)


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return json.dumps(content) if content is not None else ""


def load(path):
    """Return turns: dicts with ctx, cost, out, calls[(name, input, result_text)], wake(bool)."""
    turns, by_id, pending, wake_next = [], {}, {}, False
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get("message") or {}
        if d.get("type") == "assistant":
            mid = m.get("id")
            if mid not in by_id:
                by_id[mid] = {"ctx": 0, "cost": 0.0, "out": 0, "calls": [], "wake": wake_next, "model": m.get("model")}
                turns.append(by_id[mid])
                wake_next = False
            t = by_id[mid]
            u = m.get("usage") or {}
            cr, cw, inp, out = (u.get("cache_read_input_tokens") or 0), (u.get("cache_creation_input_tokens") or 0), (u.get("input_tokens") or 0), (u.get("output_tokens") or 0)
            cc = u.get("cache_creation") or {}
            w1, w5 = cc.get("ephemeral_1h_input_tokens"), cc.get("ephemeral_5m_input_tokens")
            if w1 is None and w5 is None:
                w1, w5 = cw, 0
            t["ctx"] = max(t["ctx"], cr + cw + inp)
            t["cost"] = cr * READ + (w1 or 0) * W1H + (w5 or 0) * W5M + inp + out * OUT
            t["out"] = max(t["out"], out)
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    call = [b.get("name"), b.get("input") or {}, ""]
                    t["calls"].append(call)
                    pending[b.get("id")] = call
        elif d.get("type") == "user":
            c = m.get("content")
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                        pending[b["tool_use_id"]][2] = text_of(b.get("content"))
                    elif isinstance(b, dict) and b.get("type") == "text" and NOTIFY.search(b.get("text", "")):
                        wake_next = True
            elif isinstance(c, str) and NOTIFY.search(c):
                wake_next = True
    return turns


def remaining(turns, i):
    """Turns after i that still carry what turn i added (stop at a compaction drop)."""
    n, base = 0, turns[i + 1]["ctx"] if i + 1 < len(turns) else 0
    for t in turns[i + 1:]:
        if t["ctx"] < base * 0.6:
            break
        n += 1
    return n


def describe(call):
    name, inp, _ = call
    return (inp.get("description") or inp.get("command") or inp.get("file_path") or inp.get("prompt") or name or "")[:70].replace("\n", " ")


def findings(label, turns):
    out = []
    total = sum(t["cost"] for t in turns)
    calls = sum(len(t["calls"]) for t in turns)

    # 1. Consecutive single-call turns with no data flow from the first result into the second call.
    pairs, save = [], 0.0
    for i in range(len(turns) - 1):
        a, b = turns[i], turns[i + 1]
        if len(a["calls"]) != 1 or len(b["calls"]) != 1 or b["wake"]:
            continue
        (_, ain, ares), (bname, bin_, _) = a["calls"][0], b["calls"][0]
        if bname in ("Edit", "Write") or re.search(r"(?i)error|exit code [1-9]|not found|no such", ares[:600]):
            continue  # edits and retries depend on what the previous result showed
        new = set(WORD.findall(ares)) - set(WORD.findall(json.dumps(ain)))
        btext = json.dumps(bin_)
        if not any(w in btext for w in new):
            pairs.append((i, describe(a["calls"][0]), describe(b["calls"][0])))
            save += b["ctx"] * READ
    if pairs:
        out.append(("Independent calls in separate turns",
                    f"{len(pairs)} times a call ran in its own turn although nothing from the previous result fed into it. "
                    "Each extra turn re-read the whole context.",
                    save, f"Send both calls in one message: {len(pairs)} fewer turns. (Upper bound: a call can still depend on a decision the previous result informed.)",
                    "Batch calls whose inputs you already know. Example pair: " + f"`{pairs[0][1]}` then `{pairs[0][2]}`."))

    # 2. Large results carried on every later turn.
    carried, rows = 0.0, []
    for i, t in enumerate(turns[:-1]):
        size = sum(len(c[2]) for c in t["calls"])
        if size < 8000:
            continue
        n = remaining(turns, i)
        extra = tok(size) - tok(CAP) * len(t["calls"])
        if extra <= 0:
            continue
        cost = extra * n * READ
        carried += cost
        rows.append((cost, size, n, describe(t["calls"][0])))
    if rows:
        rows.sort(reverse=True)
        top = rows[0]
        out.append(("Large tool results carried along",
                    f"{len(rows)} results over 8 KB stayed in context. The biggest ({top[1] // 1000} KB, `{top[3]}`) rode along on {top[2]} later turns.",
                    carried, f"Trimmed to {CAP} chars each, those results cost almost nothing to carry.",
                    "Print only what the next step needs: `| cut -c1-300`, `| tail -5`, `grep -c`, or a python summary."))

    # 3. Wake-up turns caused by background notifications.
    wakes = [t for t in turns if t["wake"]]
    idle = [t for t in wakes if not t["calls"]]
    if wakes:
        out.append(("Background notification wake-ups",
                    f"{len(wakes)} turns were started by a finished background task; {len(idle)} of them made no tool call "
                    "and only acknowledged it. Each re-read the full context.",
                    sum(t["cost"] for t in idle), "One parallel batch that returns together needs one wake-up, not one per agent.",
                    "Launch independent agents in one message and act once they have all returned; skip acknowledgement-only replies."))

    # 4. Timeouts and shell errors that forced a retry or collection turn.
    retry, why = 0.0, []
    for i, t in enumerate(turns[:-1]):
        for c in t["calls"]:
            if TIMED_OUT.search(c[2]) or SHELL_ERR.search(c[2]):
                retry += turns[i + 1]["cost"]
                why.append(describe(c))
    if why:
        out.append(("Timeouts and shell errors",
                    f"{len(why)} calls timed out or hit a shell error, so the next turn was spent collecting or retrying: " + "; ".join(f"`{w}`" for w in why[:3]) + ".",
                    retry, "Started in the background (or with a working pattern), no recovery turn is needed.",
                    "Start slow scans, suites and fetches with run_in_background; use `grep -E`/`rg`; use `pgrep -f '[f]oo'`."))

    # 5. Text repeated at the start of every subagent prompt.
    prompts = [c[1].get("prompt", "") for t in turns for c in t["calls"] if c[0] in ("Agent", "Task")]
    if len(prompts) >= 2:
        prefix = os.path.commonprefix(prompts)
        if len(prefix) >= 800:
            written = tok(len(prefix)) * len(prompts) * OUT
            idx = [i for i, t in enumerate(turns) if any(c[0] in ("Agent", "Task") for c in t["calls"])]
            carried_main = sum(tok(len(prefix)) * remaining(turns, i) * READ for i in idx)
            out.append(("Same block pasted into every subagent prompt",
                        f"{len(prompts)} prompts started with the same {len(prefix)} chars (~{tok(len(prefix))} tokens). "
                        "The main loop wrote it as output each time, then carried every copy on later turns.",
                        written + carried_main, "A one-line file path instead costs about 20 tokens per prompt.",
                        "Save the block once and pass its path, or leave it out of routine worker and review packets."))
    return total, calls, out


def first_prompt(path):
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "user":
            return text_of((d.get("message") or {}).get("content"))
    return ""


def subagent_report(paths):
    rows = []
    for p in sorted(paths):
        turns = load(p)
        task = first_prompt(p)
        cut = re.search(r"\n-{3,}\s*\n", task)
        task = task[cut.end():] if cut and "PROTOCOL" in task[:cut.start()] else task
        if not turns:
            continue
        first = next((t for t in turns if t["calls"]), None)
        files = set()
        for t in turns:
            for c in t["calls"]:
                files |= set(PATH.findall(json.dumps(c[1])))
        rows.append({"name": os.path.basename(p), "turns": len(turns), "single": sum(1 for t in turns if len(t["calls"]) == 1),
                     "cost": sum(t["cost"] for t in turns), "model": turns[0]["model"], "files": files, "first": describe(first["calls"][0]) if first else "", "review": bool(REVIEW.search(task[:400]))})
    return rows


AWAY = 1800  # a gap longer than this is the user being away, not the session working
TASK_ID = re.compile(r"agentId: (\w+)|\bID: (\w+)|<task-id>(\w+)</task-id>")


def timing(path):
    """Wall-clock: where active time went, and which background job the main loop was parked on."""
    ev, launched, open_jobs, parked = [], {}, {}, []
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        t = d.get("timestamp")
        if not t or d.get("type") not in ("user", "assistant"):
            continue
        t = __import__("datetime").datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
        m = d.get("message") or {}
        c = m.get("content") or []
        if d["type"] == "assistant":
            uses = [b for b in c if isinstance(b, dict) and b.get("type") == "tool_use"]
            for b in uses:
                launched[b.get("id")] = (b.get("input") or {}).get("description") or b.get("name")
            ev.append((t, "tool" if uses else "text"))
        else:
            txt = c if isinstance(c, str) else " ".join(
                (text_of(b.get("content")) if b.get("type") == "tool_result" else b.get("text", "")) for b in c if isinstance(b, dict))
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        body = text_of(b.get("content"))
                        if re.search(r"launched successfully|running in background|moved to the background", body):
                            mm = TASK_ID.search(body)
                            if mm:
                                open_jobs[next(g for g in mm.groups() if g)] = (t, launched.get(b.get("tool_use_id"), "background job"))
            for mm in re.finditer(r"<task-id>(\w+)</task-id>|agent-message from=\"(\w+)\"", txt):
                open_jobs.pop(next(g for g in mm.groups() if g), None)
            ev.append((t, "result" if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c) else "input"))
            if ev[-1][1] == "input" and len(ev) >= 2 and ev[-2][1] == "text":
                gap = t - ev[-2][0]
                if 60 < gap < AWAY:
                    parked.append((gap, ev[-2][0], sorted({v[1] for v in open_jobs.values()} | set())))
        # snapshot jobs in flight at each text-only end of turn
        if ev and ev[-1][1] == "text":
            ev[-1] = (ev[-1][0], "text", sorted(v[1] for v in open_jobs.values()))
    active = away = model = tools = 0.0
    for a, b in zip(ev, ev[1:]):
        gap = b[0] - a[0]
        if gap >= AWAY:
            away += gap
            continue
        active += gap
        if b[1] in ("tool", "text"):
            model += gap
        elif b[1] == "result":
            tools += gap
    waits = []
    for a, b in zip(ev, ev[1:]):
        gap = b[0] - a[0]
        if a[1] == "text" and b[1] == "input" and 60 < gap < AWAY:
            waits.append((gap, a[2] if len(a) > 2 else []))
    return active, away, model, tools, waits


def print_timing(path):
    active, away, model, tools, waits = timing(path)
    if not active:
        return
    parked = sum(g for g, _ in waits)
    print("## Where the time went\n")
    print(f"- Active {active / 60:.0f} min (away {away / 60:.0f} min not counted): model {model / 60:.0f} min, tools {tools / 60:.0f} min, "
          f"parked waiting on background work {parked / 60:.0f} min ({100 * parked / active:.0f}%).")
    for g, jobs in sorted(waits, reverse=True)[:6]:
        print(f"  - parked {g / 60:.1f} min on: {', '.join(jobs) if jobs else 'a background job or the user'}")
    if parked > 0.25 * active:
        print("- Bottleneck: the main loop ran one background job at a time and waited for each. Units that touch different "
              "files can run at once in separate worktrees; a review can run while the next unit is built; a suite can run "
              "while reviews run. After a test-only fix, rerun the failed file, not the whole suite.")
    print()


def main():
    if any(value in ("--help", "-h") for value in sys.argv[1:]):
        print(__doc__)
        return 0
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    turns = load(path)
    total, calls, fs = findings("main", turns)
    subs = subagent_report(glob.glob(os.path.splitext(path)[0] + "/subagents/*.jsonl"))
    sub_total = sum(r["cost"] for r in subs)
    print(f"# token-guide audit: {os.path.basename(path)}\n")
    print(f"Main loop: {len(turns)} turns, {calls} tool calls, {total / 1e6:.2f}M IET. Subagents: {len(subs)}, {sub_total / 1e6:.2f}M IET.")
    print(f"IET coefficients: cache read={READ}, 1h write={W1H}, 5m write={W5M}, output={OUT}. Estimates can overlap.\n")
    print_timing(path)
    grand = 0.0
    for title, what, cost, cheaper, fix in fs:
        grand += cost
        print(f"## {title}: {cost / 1e3:.0f}k IET ({100 * cost / max(total, 1):.1f}% of main)\n")
        print(f"- What was wasted: {what}\n- Cheaper path: {cheaper}\n- Fix: {fix}\n")
    if subs:
        print("## Subagents\n")
        print("| agent | model | turns | single-call | IET | first call |\n|---|---|---|---|---|---|")
        for r in subs:
            print(f"| {r['name'][6:14]} | {r['model']} | {r['turns']} | {r['single']} | {r['cost'] / 1e3:.0f}k | {r['first'][:40]} |")
        pairs = []
        for i, a in enumerate(subs):
            for b in subs[i + 1:]:
                if a["review"] and b["review"] and a["files"] and b["files"]:
                    both = a["files"] & b["files"]
                    if len(both) >= 3 and len(both) >= 0.5 * min(len(a["files"]), len(b["files"])):
                        pairs.append((a, b, both))
        if pairs:
            dup = sum(min(a["cost"], b["cost"]) for a, b, _ in pairs)
            grand += dup
            a, b, both = pairs[0]
            print(f"\n## Subagents re-reading the same files: ~{dup / 1e3:.0f}k IET\n")
            print(f"- What was wasted: {len(pairs)} pairs of review agents read mostly the same files (for example {len(both)} shared, "
                  f"incl. `{sorted(both)[0]}`). The second agent of each pair rebuilt context the first already had.")
            print("- Cheaper path: one agent with both checklists costs about the larger of the two, not the sum.")
            print("- Fix: give one reviewer the spec and quality questions together, or send the second a follow-up to the first.")
        strong = [r for r in subs if r["model"] and "opus" in r["model"]]
        if strong:
            print(f"\n## Strong-model subagents\n\n- {len(strong)} of {len(subs)} subagents ran on {strong[0]['model']} "
                  f"({sum(r['cost'] for r in strong) / 1e3:.0f}k IET). The tokens are the same on a cheaper model; the price per "
                  "token is not. Check each against the task: routine fixes and reviews rarely need the strongest model.")
    print(f"\n**Estimated workflow opportunities above: ~{grand / 1e3:.0f}k IET of {(total + sub_total) / 1e3:.0f}k ({100 * grand / max(total + sub_total, 1):.0f}%).**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
