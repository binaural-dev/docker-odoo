import json, sys
from collections import defaultdict

a = json.load(open(sys.argv[1]))  # 17
b = json.load(open(sys.argv[2]))  # 19
TOL = 0.011


def walk(x, y, path, diffs, only):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in y:
                only["solo_17"].add(k)
            elif k not in x:
                only["solo_19"].add(k)
            else:
                walk(x[k], y[k], f"{path}.{k}", diffs, only)
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            diffs.append((path, f"len {len(x)}", f"len {len(y)}"))
        for i, (u, v) in enumerate(zip(x, y)):
            walk(u, v, f"{path}[{i}]", diffs, only)
    elif isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
        if abs(x - y) > TOL:
            diffs.append((path, x, y))
    elif x != y:
        diffs.append((path, x, y))


def numbers(x):
    """Suma de todos los números del resultado: huella rápida del monto del reporte."""
    if isinstance(x, dict):
        return sum(numbers(v) for v in x.values())
    if isinstance(x, list):
        return sum(numbers(v) for v in x)
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return x
    return 0


summary = defaultdict(lambda: defaultdict(int))
for comp in sorted(set(a) | set(b)):
    for rep in sorted(set(a.get(comp, {})) | set(b.get(comp, {}))):
        x, y = a.get(comp, {}).get(rep), b.get(comp, {}).get(rep)
        if not isinstance(x, dict) or not isinstance(y, dict):
            continue
        kind = rep.rsplit("_", 2)[0] if rep.startswith(("inces", "mpppst", "faov", "horas")) else rep
        if not x["ok"] or not y["ok"]:
            print(f"[ERROR ] {comp} | {rep} | 17: {'ok' if x['ok'] else x['error'][:90]} | 19: {'ok' if y['ok'] else y['error'][:90]}")
            continue
        diffs, only = [], defaultdict(set)
        walk(x["result"], y["result"], "", diffs, only)
        n17, n19 = numbers(x["result"]), numbers(y["result"])
        status = "IGUAL " if not diffs else "DIFIERE"
        print(f"[{status}] {comp} | {rep} | Σnúmeros 17={n17:,.2f} 19={n19:,.2f} | difs={len(diffs)}"
              + (f" | solo17={sorted(only['solo_17'])[:6]}" if only["solo_17"] else "")
              + (f" | solo19={sorted(only['solo_19'])[:6]}" if only["solo_19"] else ""))
        for d in diffs[:4]:
            print(f"          {d[0][:90]}: 17={str(d[1])[:60]!r} 19={str(d[2])[:60]!r}")
