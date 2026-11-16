from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .cli import register
from .tools import LAYERS, TOOLS, Tool

SKILLS = ("reverse-anything", "re-match", "re-observe", "re-recover", "re-verify", "re-export")
Result = dict[str, Any]


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:60]
    return ""


def _run(cmd: str | list[str], timeout: int, shell: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)


def _json_version(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    ident = data.get("identity")
    v = data.get("version") or (ident.get("version") if isinstance(ident, dict) else None)
    return str(v) if v else ""


def _probe(spec: str) -> tuple[bool, str, str, Any]:
    kind, _, arg = spec.partition(":")
    if kind == "cmd":
        r = _run(arg, 5, shell=True)
        if r.returncode == 0:
            return True, _first_line(r.stdout) or _first_line(r.stderr), "", None
        missing = r.returncode == 127 or "not found" in r.stderr
        return False, "", "not on PATH" if missing else "", None
    if kind == "python":
        if importlib.util.find_spec(arg) is None:
            return False, "", "", None
        try:
            return True, importlib.metadata.version(arg), "", None
        except importlib.metadata.PackageNotFoundError:
            return True, "", "", None
    if kind == "env":
        var, _, rel = arg.partition("/")
        if var not in os.environ:
            return False, "", "", None
        path = Path(os.environ[var]) / rel
        return path.exists(), "", str(path), None
    if kind == "file":
        return Path(arg).expanduser().exists(), "", "", None
    if spec == "rea":
        cmd = ["rea", "doctor", "--json"] if shutil.which("rea") else ["npx", "-y", "rea-agents@latest", "doctor", "--json"]
        r = _run(cmd, 60 if cmd[0] == "rea" else 45)
        try:
            data = json.loads(r.stdout)
        except ValueError:
            return False, "", _first_line(r.stderr), None
        if not isinstance(data, dict):
            return False, "", _first_line(r.stderr), None
        return True, _json_version(data), "healthy" if data.get("healthy") else "unhealthy", data
    if spec == "reagent":
        try:
            r = _run(["re-agent", "doctor"], 30)
        except FileNotFoundError:
            return False, "", "not on PATH", None
        if r.returncode != 0:
            return False, "", "", None
        try:
            v = _first_line(_run(["re-agent", "--version"], 10).stdout)
        except Exception:
            v = ""
        return True, v, "", None
    raise ValueError(f"unknown detect spec: {spec}")


def _rea_line(row: Result | None, data: Any) -> str:
    if row is None:
        return ""
    if row["status"] != "found":
        return "rea: missing"
    if data.get("healthy"):
        return "rea: found (healthy)"
    bad = next((c for c in data.get("scope_checks") or [] if isinstance(c, dict) and not c.get("ok")), None)
    why = f": {bad.get('name')} {bad.get('classification', '')}".rstrip() if bad else ""
    return f"rea: found (unhealthy{why})"


def _check(tool: Tool) -> Result:
    row: Result = {
        "name": tool.name, "layer": tool.layer, "status": "bench", "version": "",
        "detail": "", "detect": tool.detect, "install_hint": tool.install_hint,
        "url": tool.url, "_data": None,
    }
    spec = tool.detect
    if spec is None:
        return row
    if spec.startswith("config:"):
        row["status"], row["detail"] = "n/a", f"needs {spec[7:]}"
        return row
    if spec.partition(":")[0] not in ("cmd", "python", "env", "file") and spec not in ("rea", "reagent"):
        raise ValueError(f"unknown detect spec: {spec}")
    try:
        ok, version, detail, data = _probe(spec)
    except subprocess.TimeoutExpired:
        row["status"], row["detail"] = "missing", "timeout"
        return row
    except Exception as exc:
        row["status"], row["detail"] = "missing", type(exc).__name__
        return row
    row["status"] = "found" if ok else "missing"
    row["version"], row["detail"], row["_data"] = version, detail, data
    return row


def _skill_dirs() -> list[Path]:
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    claude = Path(cfg).expanduser() if cfg else Path.home() / ".claude"
    return [Path.home() / ".agents" / "skills", claude / "skills"]


def _skills() -> list[Result]:
    out = []
    for d in _skill_dirs():
        if d.is_dir():
            present = [s for s in SKILLS if (d / s).exists()]
            out.append({"path": str(d), "present": present, "missing": [s for s in SKILLS if s not in present]})
    return out


def _clients(rea: Any) -> list[str]:
    if not isinstance(rea, dict):
        return []
    for key in ("clients", "agents"):
        val = rea.get(key)
        if isinstance(val, list):
            return [str(c.get("name", c)) if isinstance(c, dict) else str(c) for c in val]
    return []


def _add_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="print one JSON object")
    p.add_argument("--layer", choices=LAYERS, help="check one layer only")
    p.add_argument("--require", metavar="NAME[,NAME...]", help="exit 1 unless these tools are found")


def _run_doctor(args: argparse.Namespace) -> int:
    tools = [t for t in TOOLS if args.layer in (None, t.layer)]
    if args.require:
        wanted = [n.strip() for n in args.require.split(",") if n.strip()]
        known = {t.name.lower(): t.name for t in TOOLS}
        unknown = [n for n in wanted if n.lower() not in known]
        if unknown:
            print(f"unknown tool: {', '.join(unknown)}", file=sys.stderr)
            return 2
        shown = {t.name.lower() for t in tools}
        for n in wanted:
            if n.lower() not in shown:
                print(f"{n} is not in layer {args.layer}", file=sys.stderr)
                return 2
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(_check, tools))
    rea = next((r["_data"] for r in rows if r["detect"] == "rea" and r["_data"] is not None), None)
    install_dir = os.environ.get("GHIDRA_INSTALL_DIR")
    skills = _skills()
    for r in rows:
        r.pop("_data")
    if args.json:
        headless = bool(install_dir) and (Path(install_dir) / "support" / "analyzeHeadless").exists()
        print(json.dumps({
            "version": __version__,
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tools": rows, "rea": rea,
            "ghidra": {"install_dir": install_dir, "analyze_headless": headless},
            "skills": skills,
        }, indent=2))
    else:
        for r in rows:
            detail = r["version"] or r["detail"]
            if r["status"] == "missing" and not r["detail"]:
                detail = r["install_hint"]
            print(f"{r['name']:<24} {r['layer']:<13} {r['status']:<8} {detail}".rstrip())
        rea_row = next((r for r in rows if r["detect"] == "rea"), None)
        if rea_row:
            print(_rea_line(rea_row, rea))
            clients = _clients(rea)
            if clients:
                print(f"rea clients: {', '.join(clients)}")
        print(f"ghidra: {install_dir or 'unset'}")
        for s in skills:
            print(f"skills: {len(s['present'])}/{len(SKILLS)} at {s['path']}")
    if args.require:
        by_name = {r["name"].lower(): r["status"] for r in rows}
        return 1 if any(by_name.get(n.lower()) != "found" for n in wanted) else 0
    return 0


register("doctor", _add_parser, _run_doctor, "check which tools and skills are installed")
