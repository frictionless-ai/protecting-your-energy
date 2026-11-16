"""tr — Thought Reconstruction pipeline CLI.

Stages as subcommands: connect, normalize, extract, cluster, reconstruct,
rank, canvas, run. Each stage reads its predecessor's output from
<repo-root>/thought-reconstruction-work/ and writes its own there.
"""
import argparse
import json
import os
import sys

from . import canvas as canvas_mod
from . import cluster as cluster_mod
from . import extract as extract_mod
from . import normalize as normalize_mod
from . import rank as rank_mod
from . import reconstruct as reconstruct_mod
from . import paths

FRAGMENTS = "fragments.jsonl"
EXTRACTED = "extracted.jsonl"
CLUSTERED = "clustered.jsonl"
RECONSTRUCTED = "reconstructed.jsonl"
RANKED = "ranked.jsonl"


def _read_jsonl(path):
    if not os.path.exists(path):
        raise SystemExit("missing %s — run the previous stage first" % path)
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _setup(args):
    root = paths.find_repo_root(args.repo_root)
    work = os.path.realpath(args.work_dir or paths.work_dir(root))
    archive_root = os.environ.get('THOUGHT_RECONSTRUCTION_ARCHIVE_ROOT')
    raw = os.path.realpath(os.path.expanduser(archive_root)) if archive_root else None
    if raw and (work == raw or work.startswith(raw + os.sep)):
        raise SystemExit('output belongs outside the raw archive; pass --work-dir')
    if os.path.isdir(os.path.join(root, 'archive', 'corpus')) and (work == root or work.startswith(root + os.sep)):
        raise SystemExit('output belongs outside the raw archive; pass --work-dir')
    sources = paths.resolve_sources(root, args.source)
    return root, work, sources


def cmd_connect(args):
    _, _, sources = _setup(args)
    if not sources:
        print("no sources found")
        return 1
    total = 0
    for label, path in sources:
        n = len(normalize_mod.fragments_for(label, path))
        total += n
        print("%6d  %s" % (n, label))
    print("%6d  total (pre-dedup)" % total)
    return 0


def cmd_normalize(args):
    _, work, sources = _setup(args)
    frags = normalize_mod.normalize(sources)
    out = os.path.join(work, FRAGMENTS)
    _write_jsonl(out, frags)
    print("normalize: %d fragments -> %s" % (len(frags), out))
    return 0


def cmd_extract(args):
    _, work, _ = _setup(args)
    frags = _read_jsonl(os.path.join(work, FRAGMENTS))
    recs = extract_mod.extract(frags, use_llm=not args.no_llm,
                               batch_size=args.batch_size)
    out = os.path.join(work, EXTRACTED)
    _write_jsonl(out, recs)
    print("extract: %d candidates -> %s" % (len(recs), out))
    return 0


def cmd_cluster(args):
    _, work, _ = _setup(args)
    recs = _read_jsonl(os.path.join(work, EXTRACTED))
    recs = cluster_mod.cluster(recs, threshold=args.threshold)
    if not args.no_llm:
        recs = cluster_mod.refine_llm(recs)
    out = os.path.join(work, CLUSTERED)
    _write_jsonl(out, recs)
    n_clusters = len({r["cluster"] for r in recs})
    print("cluster: %d records in %d clusters -> %s" % (len(recs), n_clusters, out))
    return 0


def cmd_reconstruct(args):
    _, work, _ = _setup(args)
    recs = _read_jsonl(os.path.join(work, CLUSTERED))
    objs = reconstruct_mod.reconstruct(recs, use_llm=not args.no_llm)
    out = os.path.join(work, RECONSTRUCTED)
    _write_jsonl(out, objs)
    print("reconstruct: %d thought objects -> %s" % (len(objs), out))
    return 0


def cmd_rank(args):
    _, work, _ = _setup(args)
    objs = _read_jsonl(os.path.join(work, RECONSTRUCTED))
    objs = rank_mod.rank(objs, use_llm=not args.no_llm,
                         batch_size=args.batch_size)
    out = os.path.join(work, RANKED)
    _write_jsonl(out, objs)
    print("rank: scored %d objects -> %s" % (len(objs), out))
    return 0


def cmd_canvas(args):
    _, work, _ = _setup(args)
    objs = _read_jsonl(os.path.join(work, RANKED))
    out_dir, copied = canvas_mod.write_canvas(objs, work)
    print("canvas: %d objects -> %s/data.js (%d asset file(s) copied)"
          % (len(objs), out_dir, copied))
    return 0


def cmd_run(args):
    for step in (cmd_connect, cmd_normalize, cmd_extract, cmd_cluster,
                 cmd_reconstruct, cmd_rank, cmd_canvas):
        rc = step(args)
        if rc:
            return rc
    return 0


def _add_common(p):
    p.add_argument("--repo-root", default=None,
                   help="repo root (default: walk up from the tool to the dir containing y2/)")
    p.add_argument("--source", action="append", default=[],
                   help="extra source path/glob (repeatable); archive partitions are opt-in via this")
    p.add_argument('--work-dir', help='output outside the raw archive')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'library':
        from .library import main as library_main
        return library_main(argv[1:])
    parser = argparse.ArgumentParser(prog="tr",
                                     description="Thought Reconstruction pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    handlers = {}

    def add(name, fn, help_text, llm=False, threshold=False):
        p = sub.add_parser(name, help=help_text)
        _add_common(p)
        if llm:
            p.set_defaults(no_llm=True)
            p.add_argument("--no-llm", action="store_true",
                           help="use offline heuristics instead of claude -p")
            p.add_argument("--hosted-llm", dest="no_llm", action="store_false",
                           help="explicitly send selected fragments to the hosted Claude service")
            p.add_argument("--batch-size", type=int, default=20)
        if threshold:
            p.add_argument("--threshold", type=float, default=0.35,
                           help="Jaccard threshold for merging (default 0.35)")
        handlers[name] = fn
        return p

    add("connect", cmd_connect, "list configured sources with fragment counts")
    add("normalize", cmd_normalize, "parse sources into fragments.jsonl")
    add("extract", cmd_extract, "type/title candidate thought objects", llm=True)
    add("cluster", cmd_cluster, "group candidates by token overlap",
        llm=True, threshold=True)
    add("reconstruct", cmd_reconstruct, "merge clusters into thought objects", llm=True)
    add("rank", cmd_rank, "score the eight dimensions", llm=True)
    add("canvas", cmd_canvas, "validate objects and emit canvas/data.js")
    run_p = add("run", cmd_run, "full pipeline", llm=True, threshold=True)
    del run_p

    args = parser.parse_args(argv)
    # Stages without LLM/threshold flags still share code paths that read them.
    if not hasattr(args, "no_llm"):
        args.no_llm = True
    if not hasattr(args, "batch_size"):
        args.batch_size = 20
    if not hasattr(args, "threshold"):
        args.threshold = 0.35
    return handlers[args.command](args)
