#!/usr/bin/env python3
"""sdd_metrics_migrate.py — metrics.jsonl schema versioning (F4). Rows without `v` are legacy (v=0): this tags them
explicitly instead of letting them be silently reinterpreted under the current semantics. Corrupt lines are counted,
never dropped silently. Dry-run by default; --apply rewrites the file after saving metrics.jsonl.bak-v0.
Usage: python3 scripts/sdd_metrics_migrate.py [--apply] [path]
"""
import json, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
path = args[0] if args else os.path.join(ROOT, "src/.sdd/logs/metrics.jsonl")
out, legacy, current, corrupt = [], 0, 0, 0
for line in open(path):
    if not line.strip():
        continue
    try:
        d = json.loads(line)
    except ValueError:
        corrupt += 1
        out.append(line.rstrip("\n"))
        continue
    if "v" in d:
        current += 1
        out.append(line.rstrip("\n"))
    else:
        legacy += 1
        out.append(json.dumps({"v": 0, **d}))
print(f"rows: legacy(v=0)={legacy} versioned={current} corrupt_lines={corrupt}")
if "--apply" in sys.argv:
    shutil.copy(path, path + ".bak-v0")
    open(path, "w").write("\n".join(out) + "\n")
    print("applied; backup at " + path + ".bak-v0")
else:
    print("dry-run (use --apply to rewrite)")
