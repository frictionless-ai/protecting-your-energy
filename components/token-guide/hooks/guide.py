#!/usr/bin/env python3
"""token-guide: nudge a session away from token-wasting habits.

Runs as a Claude Code hook (PostToolUse, UserPromptSubmit). Reads the hook
payload on stdin and, when a known wasteful pattern shows up, returns one
short hint as `additionalContext`. It never blocks, never denies a tool call,
and never changes permissions: the only output is a suggestion the model may
ignore. Each hint has a cooldown per session so it stays quiet.

Patterns are heuristic observations of session workflow (see README.md):
  batch      one tool call per turn on a large context
  compact    context past a size where every turn is expensive
  research   repeated research subagents re-grounding the same code
  bigread    whole-file or huge-range reads of large files
  poll       sleep/until/while loops and repeated status curls
  refdoc     large skill/reference docs pulled into the main context
  ceremony   planning ceremony after the user asked to start building
  packet     debate protocols or oversized prompts in worker packets
  image      screenshots and image reads when text would do
  bigout     a single tool result dumped tens of KB into the main context
  persisted  re-reading a whole persisted (overflowed) tool output
  notify     several background agents launched one by one; each completion is a full-context turn
  fanout     workflow scripts with a fixed multi-vote verify per item
  skillchain a skill loaded on a large context pulls its reference docs into every later turn
  model      routine subagents pinned to the strongest model instead of the default worker model
  dualreview two review agents launched on the same change
  timeout    a foreground command hit the tool timeout and needed an extra turn to collect
  longlines  output with multi-kilobyte lines (JSON logs, minified code)
  ugrep      grep is ugrep here and rejected a GNU-style pattern
  selfkill   pkill/pgrep -f whose pattern also matches the shell running it
  compound   long multi-part commands that trip the auto-mode safety check
  placement  scripts written to disk before checking where the tool reads them
  toc        one big file read in many chunks instead of its index first
  branches   branches inspected one call at a time instead of one pass
  envfirst   searching the disk for tools/skills/folders before checking the environment
  fixedblock the same large block of text pasted into several agent prompts

Also handles PostToolUseFailure (hints on the error) and PermissionDenied
(records the denial; the hint rides on the next tool result, because that
event cannot carry context).
"""
import hashlib
import json
import os
import re
import sys
import tempfile
import time

COOLDOWN = {  # seconds between repeats of the same hint in one session
    "batch": 900, "compact": 1800, "research": 1800, "bigread": 600,
    "poll": 900, "refdoc": 1200, "ceremony": 3600, "packet": 1200, "image": 900,
    "bigout": 900, "persisted": 900, "notify": 1800, "fanout": 3600, "skillchain": 1800,
    "serial": 3600, "rerun": 3600, "model": 3600, "dualreview": 1800, "timeout": 900, "longlines": 1200, "ugrep": 3600, "selfkill": 3600,
    "compound": 900, "placement": 1800, "toc": 900, "branches": 1800, "envfirst": 1200, "fixedblock": 1800,
}
COMPOUND_PARTS = 5        # top-level && || ; segments that make a command "long"
COMPOUND_CHARS = 600
COMPOUND_GIT = 3          # git subcommands in one command
CHUNKED_READS = 3         # chunked reads of one file before the index hint
BRANCH_CALLS = 4          # distinct branches inspected in separate calls
SEARCH_MISSES = 3         # empty disk searches before the environment hint
REPEAT_BLOCK_CHARS = 1500 # prompt text repeated from earlier agent prompts
def configured_threshold(name, default):
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


BIG_CONTEXT = configured_threshold("TOKEN_GUIDE_BIG_CONTEXT", 200000)
HUGE_CONTEXT = configured_threshold("TOKEN_GUIDE_HUGE_CONTEXT", 600000)
BIG_FILE_LINES = 800
BIG_RANGE_LINES = 300
BIG_REF_BYTES = 20000
BIG_OUTPUT_CHARS = configured_threshold("TOKEN_GUIDE_BIG_OUTPUT", 25000)
BG_AGENT_BURST = 3  # background agents in one window that trigger the notify hint
BG_WINDOW = 1200    # seconds
STRONG_MODELS = {"opus", "fable"}
STRONG_AFTER = 2    # strong-model subagents in a session before the model hint
REVIEW_WINDOW = 1800  # seconds in which two reviews of one change count as a pair
LONG_LINE = 2000    # chars
STREAK = 8          # look-back window
STREAK_SINGLES = 6  # single-call turns in that window that trigger the hint

HINTS = {
    "batch": ("Most recent turns ran a single tool call while the context is ~{ctx}k tokens. "
              "Every turn re-reads that context. Put independent reads, greps and status checks "
              "in one message as parallel calls."),
    "compact": ("Context is ~{ctx}k tokens, so each turn costs that much again. At the next natural "
                "break, compact or hand remaining work to a fresh subagent with a short packet."),
    "research": ("This is research subagent #{n} this session. If earlier agents or dossiers already "
                 "covered this code, pass their report paths and the specific path:line ranges "
                 "instead of re-grounding from scratch."),
    "bigread": ("That read pulled ~{lines} lines of {name}. Next time, `grep -n` for the symbol and read "
                "a ~60-line range around the hit."),
    "poll": ("This looks like polling. Run one background command that waits for the condition "
             "(run_in_background, or Monitor with an until-loop) and do other work until it wakes you."),
    "refdoc": ("A {kb}KB reference doc is now in the main context and will ride along on every later turn. "
               "Prefer reading only the section you need (grep the heading, then a range), "
               "or read it inside a subagent."),
    "ceremony": ("The user asked to start building. Build from the requirements that already exist. "
                 "Skip ideation, brainstorm and plan-reference reads unless a real blocker comes up."),
    "packet": ("Worker prompts work best as a plain task packet: goal, files, constraints, how to verify, "
               "short return, and a line asking it to batch independent calls. {why}"),
    "model": ("Subagent #{n} this session is pinned to {model}. If the user or memory names a default worker "
              "model, routine implement, fixture and review work usually runs fine on it; keep {model} for "
              "hard integration fixes or disputed calls."),
    "dualreview": ("A second review agent is reading the same change ({sha}). For a small or test-only diff, one "
                   "reviewer covering spec and quality, or checking the diff and test output yourself, usually "
                   "settles it. Keep separate passes for large or risky changes."),
    "timeout": ("That command ran past the foreground timeout, so collecting it costs another turn. For scans over "
                "many repos or worktrees, slow disks, fetches or test suites, start with run_in_background, or "
                "bound the work (timeout, head, per-item limits)."),
    "longlines": ("That output had lines of ~{kb}KB each (JSON logs or minified code). Cut them "
                  "(`cut -c1-300`) or pull only the fields you need with jq or a short python script."),
    "ugrep": ("grep here is ugrep, which rejects some GNU regex forms (for example a bracket class holding an "
              "escaped backslash inside a counted repeat). Use `grep -E` with simpler classes, `rg`, or a python "
              "one-liner."),
    "selfkill": ("`{cmd} -f` also matches the shell that runs it, because the pattern is in its own command "
                 "line; that can kill the tool call itself. Use the bracket trick (`pgrep -f '[f]oo'`), or "
                 "kill PIDs recorded at launch."),
    "bigout": ("That result put ~{kb}KB into the main context, and it rides along on every later turn. "
               "Next time, extract only what the next step needs (grep, head, or a short python summary "
               "that prints counts and the few matching lines)."),
    "persisted": ("That output was saved to a file because it was too large. Instead of reading it whole, "
                  "grep it or parse it with a short script and print only the fields you need."),
    "serial": ("The previous implementer was launched {m} min ago. Check whether independent units can run "
               "together with appropriate file ownership or isolation, while the main loop handles useful work."),
    "rerun": ("This long background command already ran {m} min ago. If the fix since then touched only the files "
              "that failed, consider the targeted check appropriate to that change before repeating broad checks."),
    "notify": ("{n} background agents were launched separately in a short window. Each one that finishes wakes "
               "the main loop for a full-context turn. For independent parallel work, prefer one parallel "
               "batch in a single message, or one workflow that returns a single combined result."),
    "fanout": ("This workflow gives every item a fixed multi-vote verification. Consider scaling votes to "
               "the stakes: one verifier per item, and extra votes only where the first vote is close or "
               "disagrees with the proposer."),
    "skillchain": ("A skill was loaded on a ~{ctx}k-token context. Its reference docs will ride along on every "
                   "later turn. Read only the phase owner you need, or run the skill's heavy phases in a "
                   "subagent and keep the result, not the references."),
    "image": ("Screenshots cost many tokens each time the context is re-read. For text and structure, "
              "prefer read_page, get_page_text or find. Keep screenshots for visual layout checks."),
    "compound": ("{why}Long multi-part commands can trip the auto-mode safety check and cost a retry. Split "
                 "independent steps into separate parallel Bash calls, one purpose each, especially git."),
    "placement": ("{why}Check where the consuming tool reads files before writing them. Workflow takes its "
                  "script inline and saves a copy itself; pass scriptPath only for that saved copy."),
    "toc": ("{name} has now been read in {n} chunks. Get its index first (`grep -n '^#'` or its table of "
            "contents), then read only the section you need."),
    "branches": ("Branches are being inspected one call at a time ({n} so far). Settle it in one pass: "
                 "`git branch --no-merged <default>`, then `git cherry -v <default> <branch>` for each in a "
                 "single loop."),
    "envfirst": ("{why}Check the environment before searching the disk: the session's skill and agent lists, "
                 "the known roots in AGENTS.md (for example ~/.agents), `command -v`, and env vars."),
    "fixedblock": ("About {k}k chars of this agent prompt repeat text from an earlier prompt. Put the shared "
                   "text in a file and pass its path; inline text is paid for on every agent call."),
}

START_CODING = re.compile(
    r"\b(start (writing|coding|building|implementing|developing)|actually start|just (build|code|implement)"
    r"|implement (it|this|now)|stop planning|write the code)\b", re.I)
RESEARCH_PROMPT = re.compile(
    r"\b(read-only|research|gather evidence|grounding|investigate|survey|dossier|explore the)\b", re.I)
PROTOCOL_BLOCK = re.compile(r"AGENT-TO-AGENT PROTOCOL|PROTOCOL \(prove-the-effort\)|grill-me handshake", re.I)
IMPLEMENT_PROMPT = re.compile(r"\b(implement|build|fix|edit only|apply|write the code)\b", re.I)
POLL_CMD = re.compile(r"\bsleep ([3-9]|\d\d)|\bwatch -n\b", re.S)  # a loop only polls if it waits
REF_PATH = re.compile(r"(/skills/|/references/|plugins/cache/|SKILL\.md|FRONTEND_INTENT|AGENTS\.md)")
READ_CMD = re.compile(r"(?:^|[;&|]\s*)(?:cat|less|more)\s+([^\s|;&>]+)|sed -n '?(\d+),(\d+)p'?\s+([^\s|;&>]+)")
BROWSER_SHOT = re.compile(r"(computer|screenshot)$")
REVIEW_PROMPT = re.compile(r"\b(review(er)?|re-review|audit|verify the (commit|change|diff))\b", re.I)
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
SELF_MATCH = re.compile(r"\b(pkill|pgrep)\b[^|;&\n]*?\s-\w*f\w*\s+(['\"]?)([^'\"\s|;&]+)\2")
TIMED_OUT = re.compile(r"did not complete within its \d+s timeout|moved to the background")
UGREP_ERR = re.compile(r"^ugrep: error", re.M)
WORKFLOW_SCRIPT = re.compile(r"export\s+const\s+meta\s*=\s*\{")
GIT_SUB = re.compile(r"\bgit\s+(?:-C\s+\S+\s+|-c\s+\S+\s+)*([a-z][a-z-]+)")
BRANCH_REF = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(?:log|diff|rev-list|cherry|merge-base|show-branch)\b([^\n;&|]*)")
REF_TOKEN = re.compile(r"(?:^|\s|\.\.\.?)((?:origin/)?[A-Za-z][A-Za-z0-9._/-]*)")
BROAD_FIND = re.compile(r"\bfind\s+(/|~|\$HOME)(\s|$)|\blocate\s")
SEARCH_CMD = re.compile(r"^\s*(find|locate|which|command -v|ls|test -[edf]|type)\b")
MISS_TEXT = re.compile(r"No such file or directory|not found|cannot access", re.I)
DENIAL = re.compile(r"auto mode|classifier|safety check|permission .*denied|denied.*permission", re.I)
SEPARATORS = re.compile(r"&&|\|\||;")
GIT_WORDS = {"log", "diff", "status", "add", "commit", "push", "pull", "fetch", "merge", "rebase", "checkout",
             "switch", "branch", "cherry", "rev-list", "rev-parse", "show", "stash", "reset", "tag", "worktree",
             "merge-base", "cherry-pick", "restore", "rm", "mv", "remote", "config"}
GIT_OPTS_WORDS = {"oneline", "stat", "short", "porcelain", "format", "all", "graph", "no-merged", "merged"}


def top_level_parts(cmd):
    """Count && || ; separators outside quotes and heredoc bodies."""
    body = re.sub(r"'[^']*'|\"[^\"]*\"", "", cmd.split("<<", 1)[0])
    return len(SEPARATORS.findall(body)) + 1


def big_paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) >= 300]


def now_ts():
    """Wall clock; TOKEN_GUIDE_NOW overrides it so the smoke driver can replay time gaps."""
    return float(os.environ.get("TOKEN_GUIDE_NOW") or time.time())


def strip_heredocs(cmd):
    """Drop heredoc bodies so code or data inside them is not read as shell commands."""
    return re.sub(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\b", "<<heredoc", cmd, flags=re.S)


def task_text(prompt):
    """The prompt minus a pasted debate block, so the task itself is what gets classified."""
    m = PROTOCOL_BLOCK.search(prompt)
    if not m:
        return prompt
    rest = prompt[m.end():]
    cut = re.search(r"\n-{3,}\s*\n|\n\s*confidence:[^\n]*\n\s*```\s*\n", rest)
    if not cut:
        return prompt
    return (prompt[:m.start()] + rest[cut.end():]).strip()


def resp_text(resp):
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict) and isinstance(resp.get("file"), dict):  # Read results nest the text
        return resp["file"].get("content") or ""
    if isinstance(resp, dict):
        parts = [resp.get(k) for k in ("stdout", "stderr", "output", "content") if isinstance(resp.get(k), str)]
        if parts:
            return "\n".join(parts)
    return json.dumps(resp) if resp is not None else ""


def state_path(session):
    state_home = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    root = os.environ.get("TOKEN_GUIDE_STATE_DIR") or os.path.join(state_home, "protecting-your-energy", "token-guide")
    root = os.path.expanduser(root)
    os.makedirs(root, mode=0o700, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session or "nosession")
    return os.path.join(root, safe + ".json")


def load_state(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"last": {}, "counts": {}, "curls": {}}


def save_state(path, st):
    fd, tmp = tempfile.mkstemp(prefix=".token-guide-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(st, fh)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def recent_turns(transcript, limit=12, tail_bytes=600000):
    """Return [(tool_count, context_tokens)] for the latest assistant messages."""
    if not transcript or not os.path.exists(transcript):
        return []
    try:
        with open(transcript, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - tail_bytes))
            raw = fh.read().decode("utf-8", "replace")
    except OSError:
        return []
    msgs = {}
    order = []
    for line in raw.splitlines()[1:] if len(raw) >= tail_bytes else raw.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant":
            continue
        m = d.get("message") or {}
        mid = m.get("id")
        if mid not in msgs:
            order.append(mid)
            msgs[mid] = [0, 0]
        u = m.get("usage") or {}
        ctx = (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) + (u.get("input_tokens") or 0)
        msgs[mid][1] = max(msgs[mid][1], ctx)
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                msgs[mid][0] += 1
    return [tuple(msgs[i]) for i in order[-limit:]]


def count_lines(path):
    try:
        if os.path.getsize(path) > 50_000_000:
            return 0
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def detect_post(p, st):
    """Yield (hint_id, fields) for a PostToolUse payload."""
    tool = p.get("tool_name") or ""
    ti = p.get("tool_input") or {}
    turns = recent_turns(p.get("transcript_path"))
    ctx = turns[-1][1] if turns else 0

    if len(turns) >= STREAK and ctx >= BIG_CONTEXT and sum(1 for n, _ in turns[-STREAK:] if n == 1) >= STREAK_SINGLES:
        yield "batch", {"ctx": ctx // 1000}
    if ctx >= HUGE_CONTEXT:
        yield "compact", {"ctx": ctx // 1000}

    if tool in ("Agent", "Task"):
        prompt = ti.get("prompt") or ""
        if RESEARCH_PROMPT.search(task_text(prompt)[:600]):
            n = st["counts"].get("research", 0) + 1
            st["counts"]["research"] = n
            if n >= 3:
                yield "research", {"n": n}
        why = []
        head = task_text(prompt)[:1500]
        if PROTOCOL_BLOCK.search(prompt) and IMPLEMENT_PROMPT.search(head):
            why.append("Debate protocols belong only to agents assessing complex plans, not builders.")
        elif PROTOCOL_BLOCK.search(prompt) and REVIEW_PROMPT.search(head):
            why.append("A routine review needs the diff, the spec and the evidence paths; keep the debate block "
                       "for disputed or high-risk plans.")
        if len(prompt) > 7000:
            why.append(f"This prompt is {len(prompt) // 1000}k chars; send the unit text and evidence paths, not whole reports.")
        if why:
            yield "packet", {"why": " ".join(why)}
        model = (ti.get("model") or "").lower()
        if model in STRONG_MODELS:
            n = st["counts"].get("strong", 0) + 1
            st["counts"]["strong"] = n
            if n >= STRONG_AFTER:
                yield "model", {"n": n, "model": model}
        if REVIEW_PROMPT.search(head):
            now = time.time()
            seen = {k: v for k, v in st.setdefault("reviews", {}).items() if now - v < REVIEW_WINDOW}
            shas = [s for s in SHA.findall(head) if re.search(r"[a-f]", s) and re.search(r"\d", s)]
            if shas:  # the first hash names the change under review; later ones are usually parents
                key = shas[0][:7]
                hit = key in seen
                seen[key] = now
                if hit:
                    yield "dualreview", {"sha": key}
            st["reviews"] = seen
        seen_blocks = set(st.setdefault("blocks", []))
        paras = big_paragraphs(prompt)
        digests = [hashlib.sha1(x.encode()).hexdigest()[:12] for x in paras]
        repeated = sum(len(x) for x, d in zip(paras, digests) if d in seen_blocks)
        st["blocks"] = list(seen_blocks.union(digests))[-400:]
        if repeated >= REPEAT_BLOCK_CHARS:
            yield "fixedblock", {"k": max(1, repeated // 1000)}

    if tool == "Read":
        fp = ti.get("file_path") or ""
        if re.search(r"\.(png|jpe?g|gif|webp)$", fp, re.I):
            yield "image", {}
        elif not ti.get("limit"):
            lines = count_lines(fp)
            if REF_PATH.search(fp) and os.path.exists(fp) and os.path.getsize(fp) >= BIG_REF_BYTES:
                yield "refdoc", {"kb": os.path.getsize(fp) // 1000}
            elif lines >= BIG_FILE_LINES:
                yield "bigread", {"lines": lines, "name": os.path.basename(fp)}
        elif int(ti.get("limit") or 0) >= BIG_RANGE_LINES * 2:
            yield "bigread", {"lines": ti.get("limit"), "name": os.path.basename(fp)}
        if ti.get("offset") or ti.get("limit"):
            yield from chunk_read(st, fp)

    if tool in ("Write", "Edit"):
        body = (ti.get("content") or "") + (ti.get("new_string") or "")
        if WORKFLOW_SCRIPT.search(body):
            yield "placement", {"why": "That file holds a workflow script. "}

    if st.get("denied"):
        yield "compound", {"why": "The last denied call looked like a safety-check rejection. "}
        st["denied"] = ""

    if tool == "Bash":
        cmd = strip_heredocs(ti.get("command") or "")
        if ti.get("run_in_background"):
            key = re.sub(r"\b[0-9a-f]{7,40}\b|\d+", "#", cmd)[:200]
            now = now_ts()
            runs = st.setdefault("bgcmd", {})
            if key in runs and now - runs[key] < 3600:
                yield "rerun", {"m": int((now - runs[key]) // 60)}
            runs[key] = now
            return
        yield from bash_shape(st, cmd, resp_text(p.get("tool_response")))
        if POLL_CMD.search(cmd):
            yield "poll", {}
        for url in re.findall(r"curl[^\n|;&]*?(https?://[^\s'\"]+|localhost:\d+[^\s'\"]*)", cmd):
            key = re.sub(r"[?#].*", "", url)
            st["curls"][key] = st["curls"].get(key, 0) + 1
            if st["curls"][key] >= 4:
                yield "poll", {}
        for m in READ_CMD.finditer(cmd):
            fp = m.group(1) or m.group(4)
            if not fp or fp.startswith("-"):
                continue
            fp = os.path.expanduser(fp)
            if m.group(2):
                span = int(m.group(3)) - int(m.group(2))
                if span >= BIG_RANGE_LINES:
                    yield "bigread", {"lines": span, "name": os.path.basename(fp)}
                yield from chunk_read(st, fp)
                continue
            if REF_PATH.search(fp) and os.path.isfile(fp) and os.path.getsize(fp) >= BIG_REF_BYTES:
                yield "refdoc", {"kb": os.path.getsize(fp) // 1000}
            elif os.path.isfile(fp) and count_lines(fp) >= BIG_FILE_LINES:
                yield "bigread", {"lines": count_lines(fp), "name": os.path.basename(fp)}

    resp = p.get("tool_response")
    size = len(resp) if isinstance(resp, str) else len(json.dumps(resp)) if resp is not None else 0
    if tool in ("Bash", "Read") and size >= BIG_OUTPUT_CHARS:
        yield "bigout", {"kb": size // 1000}
    if tool in ("Bash", "Read") and size >= 3 * LONG_LINE:
        text = resp_text(resp)
        longest = max((len(line) for line in text.splitlines()), default=0)
        if longest >= LONG_LINE:
            yield "longlines", {"kb": max(1, longest // 1000)}
    if tool == "Bash":
        text = resp_text(resp)[-4000:]
        if TIMED_OUT.search(text):
            yield "timeout", {}
        if UGREP_ERR.search(text):
            yield "ugrep", {}
        m = SELF_MATCH.search(strip_heredocs(ti.get("command") or ""))
        if m and not m.group(3).startswith("["):
            yield "selfkill", {"cmd": m.group(1)}
    if tool == "Read" and "/tool-results/" in (ti.get("file_path") or "") and not ti.get("limit"):
        yield "persisted", {}

    if tool in ("Agent", "Task") and ti.get("run_in_background") is not False:
        task = task_text(ti.get("prompt") or "")[:1500]
        if IMPLEMENT_PROMPT.search(task) and not REVIEW_PROMPT.search(task[:300]):
            now = now_ts()
            impl = [x for x in st.setdefault("impl", []) if now - x < 7200]
            if impl and 240 < now - impl[-1] < 3600:
                st["counts"]["serial"] = st["counts"].get("serial", 0) + 1
                if st["counts"]["serial"] >= 1:
                    yield "serial", {"m": int((now - impl[-1]) // 60)}
            st["impl"] = impl + [now]
        now = time.time()
        recent = [t for t in st.setdefault("bg", []) if now - t < BG_WINDOW] + [now]
        st["bg"] = recent
        if len(recent) >= BG_AGENT_BURST:
            yield "notify", {"n": len(recent)}

    if tool == "Workflow":
        script = ti.get("script") or ""
        if re.search(r"\.map\([^)]*=>[\s\S]{0,400}(Array\.from\(\{\s*length:\s*[3-9]|\[0,\s*1,\s*2)", script):
            yield "fanout", {}

    if tool == "Skill" and ctx >= BIG_CONTEXT:
        yield "skillchain", {"ctx": ctx // 1000}

    if tool.startswith("mcp__") and BROWSER_SHOT.search(tool):
        if (ti.get("action") in ("screenshot", "zoom")) or tool.endswith("screenshot"):
            yield "image", {}
    if tool.endswith("browser_batch"):
        acts = ti.get("actions") or []
        if sum(1 for a in acts if (a.get("input") or {}).get("action") == "screenshot") >= 2:
            yield "image", {}


def chunk_read(st, fp):
    if not fp:
        return
    chunks = st.setdefault("chunks", {})
    chunks[fp] = chunks.get(fp, 0) + 1
    if chunks[fp] >= CHUNKED_READS:
        yield "toc", {"name": os.path.basename(fp), "n": chunks[fp]}


def bash_shape(st, cmd, out):
    """Hints about how a command is shaped: length, git fan-out, branch walking, disk searches."""
    subs = [s for s in GIT_SUB.findall(cmd) if s in GIT_WORDS]
    if (top_level_parts(cmd) >= COMPOUND_PARTS and len(cmd) >= COMPOUND_CHARS) or len(subs) >= COMPOUND_GIT:
        yield "compound", {"why": ""}
    refs = set()
    for m in BRANCH_REF.finditer(cmd):
        for r in REF_TOKEN.findall(m.group(1)):
            if r not in ("HEAD", "origin") and r not in GIT_OPTS_WORDS and not r.startswith("-"):
                refs.add(r)
    if 0 < len(refs) <= 2:
        seen = set(st.setdefault("branches", [])) | refs
        st["branches"] = sorted(seen)[-200:]
        if len(seen) >= BRANCH_CALLS:
            yield "branches", {"n": len(seen)}
    if BROAD_FIND.search(cmd):
        yield "envfirst", {"why": "A search over the whole disk or home is slow and usually unnecessary. "}
    elif SEARCH_CMD.search(cmd) and (not out.strip() or MISS_TEXT.search(out[-2000:])):
        st["misses"] = st.get("misses", 0) + 1
        if st["misses"] >= SEARCH_MISSES:
            st["misses"] = 0
            yield "envfirst", {"why": "Several disk searches came back empty. "}


def detect_failure(p, st):
    """Yield hints for a PostToolUseFailure payload (the tool errored)."""
    tool = p.get("tool_name") or ""
    ti = p.get("tool_input") or {}
    err = str(p.get("error") or "")
    if DENIAL.search(err):
        yield "compound", {"why": "That call was rejected by the auto-mode check. "}
    if tool == "Workflow" and re.search(r"script|path|not found|no such", err, re.I):
        yield "placement", {"why": "The workflow could not load its script. "}
    if tool == "Bash":
        yield from bash_shape(st, ti.get("command") or "", err)
    if tool == "Read" and MISS_TEXT.search(err):
        st["misses"] = st.get("misses", 0) + 1
        if st["misses"] >= SEARCH_MISSES:
            st["misses"] = 0
            yield "envfirst", {"why": "Several paths did not exist. "}


def detect_prompt(p, st):
    if START_CODING.search(p.get("prompt") or ""):
        yield "ceremony", {}


def main():
    if os.environ.get("TOKEN_GUIDE_OFF"):
        return 0
    try:
        p = json.load(sys.stdin)
    except ValueError:
        return 0
    event = p.get("hook_event_name") or ""
    path = state_path(p.get("session_id"))
    st = load_state(path)
    for key in ("last", "counts", "curls", "bg"):
        st.setdefault(key, {})
    now = time.time()
    if event == "PermissionDenied":  # cannot carry context; remember it for the next tool result
        if DENIAL.search(str(p.get("reason") or "")) or p.get("tool_name") == "Bash":
            st["denied"] = str(p.get("reason") or "denied")[:200]
        try:
            save_state(path, st)
        except OSError:
            pass
        return 0
    detector = {"UserPromptSubmit": detect_prompt, "PostToolUseFailure": detect_failure}.get(event, detect_post)
    hints = []
    for hid, fields in detector(p, st):
        if now - st["last"].get(hid, 0) < COOLDOWN.get(hid, 900):
            continue
        if any(h[0] == hid for h in hints):
            continue
        st["last"][hid] = now
        hints.append((hid, HINTS[hid].format(**fields)))
    try:
        save_state(path, st)
    except OSError:
        pass
    if os.environ.get("TOKEN_GUIDE_OFF") or not hints:
        return 0
    text = "token-guide (suggestion, not a rule): " + " ".join(h[1] for h in hints[:2])
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event or "PostToolUse", "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # a guide must never break the session
        sys.exit(0)
