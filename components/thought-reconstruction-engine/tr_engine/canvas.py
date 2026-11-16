"""Canvas stage: validate every object, emit data.js, copy canvas assets.

data.js is a JS file (not JSON) so the canvas opens from file:// without a
server and with zero network requests.
"""
import datetime
import json
import os
import shutil

from .validate import validate_object


def canvas_source_dir():
    # thought-reconstruction/canvas/ next to the code; another component owns
    # its contents, we only copy them.
    return os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                        "canvas")


def write_canvas(objects, work):
    """Validate all objects (hard fail on any invalid one — the canvas
    contract is binding), then write canvas/data.js and copy assets."""
    bad = []
    for obj in objects:
        errors = validate_object(obj)
        if errors:
            bad.append((obj.get("id", "<no id>"), errors))
    if bad:
        lines = ["%s: %s" % (oid, "; ".join(errs)) for oid, errs in bad]
        raise SystemExit("canvas: %d invalid object(s):\n" % len(bad)
                         + "\n".join(lines[:20]))

    out_dir = os.path.join(work, "canvas")
    os.makedirs(out_dir, exist_ok=True)
    generated = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    payload = json.dumps({"generated": generated, "objects": objects},
                         ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.TR_DATA = %s;\n" % payload)

    src = canvas_source_dir()
    copied = 0
    if os.path.isdir(src):
        for name in sorted(os.listdir(src)):
            sp = os.path.join(src, name)
            if os.path.isfile(sp):
                shutil.copy2(sp, os.path.join(out_dir, name))
                copied += 1
    return out_dir, copied
