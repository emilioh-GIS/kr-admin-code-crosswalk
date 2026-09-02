#!/usr/bin/env python3
"""
diff_vintages.py - what changed between two vintages of the dong crosswalk?

    python diff_vintages.py <old_kr_admin_codes_dong.csv> <new_kr_admin_codes_dong.csv> [report.csv]

Korea reorganises administrative units regularly (mergers, splits, renames,
wholesale recoding of a province). Before refreshing anything keyed to these
codes you want to know exactly which units survived, which were renamed in
place, which kept their identity but got a NEW code, and which are new or gone.

Classification per unit (in this order):
  unchanged  same KOSTAT code, same MOIS code, same full name
  renamed    same KOSTAT code and MOIS code, different full name
  recoded    same full name (and same parent sigungu name), different code(s)
             -> the unit persisted; only its identifier changed. This is the
                case that silently breaks joins if you key on the code alone.
  removed    old code not in new, and no recoded match
  added      new code not in old, and no recoded match

Standard library only.
"""
import csv, sys
from collections import Counter


def read(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def classify(old, new):
    o_by_code = {r["dong_kostat"]: r for r in old}
    n_by_code = {r["dong_kostat"]: r for r in new}
    key = lambda r: (r["full_name_ko"], r["sigungu_name_ko"])
    o_by_name = {key(r): r for r in old}
    n_by_name = {key(r): r for r in new}

    events = []
    seen_new = set()
    for code, o in o_by_code.items():
        n = n_by_code.get(code)
        if n is not None:
            seen_new.add(code)
            if o["dong_mois"] == n["dong_mois"] and o["full_name_ko"] == n["full_name_ko"]:
                events.append(("unchanged", code, code, o["full_name_ko"], n["full_name_ko"]))
            elif o["dong_mois"] == n["dong_mois"]:
                events.append(("renamed", code, code, o["full_name_ko"], n["full_name_ko"]))
            else:
                # same KOSTAT code but MOIS changed - treat as recoded on the MOIS side
                events.append(("recoded", code, code, o["full_name_ko"], n["full_name_ko"]))
            continue
        m = n_by_name.get(key(o))
        if m is not None and m["dong_kostat"] not in o_by_code:
            seen_new.add(m["dong_kostat"])
            events.append(("recoded", code, m["dong_kostat"], o["full_name_ko"], m["full_name_ko"]))
        else:
            events.append(("removed", code, "", o["full_name_ko"], ""))
    for code, n in n_by_code.items():
        if code not in seen_new:
            events.append(("added", "", code, "", n["full_name_ko"]))
    return events


def main(old_path, new_path, report=None):
    old, new = read(old_path), read(new_path)
    events = classify(old, new)
    counts = Counter(e[0] for e in events)
    print(f"old: {len(old)} units   new: {len(new)} units")
    for k in ("unchanged", "renamed", "recoded", "removed", "added"):
        print(f"  {k:<10} {counts.get(k, 0)}")
    interesting = [e for e in events if e[0] != "unchanged"]
    for kind, oc, nc, on, nn in interesting[:25]:
        print(f"  {kind:<8} {oc or '-':>8} -> {nc or '-':<8}  {on or nn}" +
              (f"  ->  {nn}" if kind == "renamed" else ""))
    if len(interesting) > 25:
        print(f"  ... {len(interesting) - 25} more (write a report for the full list)")
    if report:
        with open(report, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["change", "old_kostat", "new_kostat", "old_name", "new_name"])
            w.writerows(events)
        print(f"report: {report} ({len(events)} rows)")
    return counts


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
