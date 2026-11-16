#!/usr/bin/env python3
"""Check whether mission-runtime telemetry is actually recording.

Silent failure is the danger with hook-based capture: hooks can be disabled by
settings, skipped in bare mode, or never installed for a host, and the only
symptom is an empty store that looks identical to "you haven't run anything
yet". This distinguishes those cases.

    python3 scripts/mr_doctor.py
"""

from __future__ import annotations

import datetime as _dt
import argparse
import glob
import json
import os
import subprocess
import sys
from mr_record import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
RECORDER = os.path.join(HERE, "mr_record.py")

OK, WARN, BAD = "ok  ", "warn", "FAIL"


def store_root() -> str:
    override = os.environ.get("MISSIONRUNTIME_HOME")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.join(os.path.expanduser("~"), ".missionruntime")


def line(status: str, label: str, detail: str = "") -> None:
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true",
                        help="send a local probe only when telemetry is explicitly enabled")
    args = parser.parse_args()
    problems = 0
    root = store_root()
    effective = load_config(root)

    print(f"mission-runtime telemetry doctor\nplugin: {PLUGIN_ROOT}\n")

    # 1. Interpreter
    line(OK, "python", sys.version.split()[0])

    # 2. Recorder present and runnable
    if not os.path.isfile(RECORDER):
        line(BAD, "recorder", f"missing at {RECORDER}")
        problems += 1
    elif args.probe and effective["enabled"]:
        try:
            probe = subprocess.run(
                [sys.executable, RECORDER, "--event", "DoctorProbe",
                 "--host", "doctor"],
                input='{"session_id":"mr-doctor-probe","cwd":"' +
                      PLUGIN_ROOT.replace("\\", "/") + '"}',
                text=True, capture_output=True, timeout=20,
                env=dict(os.environ))
            if probe.returncode == 0:
                line(OK, "recorder", "ran and exited 0")
            else:
                line(BAD, "recorder", f"exit {probe.returncode}")
                problems += 1
        except Exception as exc:
            line(BAD, "recorder", f"could not run: {exc}")
            problems += 1
    else:
        line(OK, "recorder", "present; active probe requires --probe and enabled telemetry")

    # 3. Config and switches
    cfg_path = os.path.join(root, "config.json")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as fh:
                cfg = json.load(fh)
            line(OK, "config", f"loaded {cfg_path}")
        except Exception as exc:
            line(WARN, "config", f"{cfg_path} unreadable ({exc}); using defaults")
    else:
        line(OK, "config", f"none at {cfg_path}; using defaults")

    if not effective["enabled"]:
        line(OK, "switch", "recording is OFF")
    else:
        line(OK, "switch", "recording enabled")

    # 4. Claude Code hook config
    hooks_json = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
    if os.path.isfile(hooks_json):
        try:
            with open(hooks_json, encoding="utf-8") as fh:
                data = json.load(fh)
            events = sorted(data.get("hooks", {}))
            line(OK, "claude hooks", f"{len(events)} events: {', '.join(events)}")
        except Exception as exc:
            line(BAD, "claude hooks", f"{hooks_json} invalid JSON: {exc}")
            problems += 1
    else:
        line(BAD, "claude hooks", f"missing {hooks_json}")
        problems += 1

    # 5. Other hosts — installed or not
    for host, target in (("cursor", "~/.cursor/hooks.json"),
                         ("copilot", "~/.copilot/hooks/mission-runtime.json"),
                         ("codex", "~/.codex/hooks.json")):
        path = os.path.expanduser(target)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                if "mr_record.py" in text:
                    line(OK, f"{host} hooks", path)
                else:
                    line(WARN, f"{host} hooks",
                         f"{path} exists but does not reference mr_record.py")
            except Exception:
                line(WARN, f"{host} hooks", f"{path} unreadable")
        else:
            line(WARN, f"{host} hooks", "not installed "
                 f"(python3 scripts/mr_install_hooks.py --host {host} --apply)")

    # 6. Store contents and freshness — the real proof capture is working
    files = glob.glob(os.path.join(root, "sessions", "*", "*.jsonl"))
    if not files:
        line(WARN, "store", f"{root} has no records yet")
    else:
        newest = max(files, key=os.path.getmtime)
        age = _dt.datetime.now() - _dt.datetime.fromtimestamp(
            os.path.getmtime(newest))
        total = 0
        for path in files:
            try:
                with open(path, encoding="utf-8") as fh:
                    total += sum(1 for _ in fh)
            except OSError:
                pass
        hours = age.total_seconds() / 3600.0
        detail = (f"{len(files)} session file(s), {total} record(s), "
                  f"newest {hours:.1f}h old")
        line(OK if hours < 72 else WARN, "store", detail)

    err = os.path.join(root, "recorder.err")
    if os.path.isfile(err) and os.path.getsize(err) > 0:
        line(WARN, "recorder errors", f"see {err}")
    else:
        line(OK, "recorder errors", "none")

    print()
    if problems:
        print(f"{problems} problem(s) found.")
        return 1
    if not effective["enabled"]:
        print("Telemetry is disabled. No recording was activated.")
        return 0
    print("Telemetry checks finished. If the store stays empty after a session, "
          "the host is probably not loading plugin hooks\n(Claude Code: check "
          "`disableAllHooks`, and note that `--bare` skips hook discovery).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
