#!/usr/bin/env python3
"""
build_crosswalk.py - build the Korean administrative code crosswalk (KOSTAT <-> MOIS).

Korea maintains two parallel administrative code systems that do NOT share
numbering. This script extracts both, side by side, from the official
Statistics Korea (SGIS) administrative-dong boundary release and writes three
flat CSVs (sido / sigungu / dong) plus a build manifest with checksums.

    python build_crosswalk.py <HangJeongDong_verYYYYMMDD.geojson> <out_dir>

Design:
  * validate-then-write - every structural check runs BEFORE any output is
    produced; a failing input yields no files and a non-zero exit.
  * deterministic - rows are sorted by code; identical input gives byte-
    identical output (verified in tests/).
  * traceable - data/manifest.json records the input file's SHA-256, size and
    vintage, and the SHA-256 and row count of every output, with a UTC
    build timestamp.

Standard library only. Romanisation uses the bundled kr_romanize.py.
"""
import csv, hashlib, json, os, re, sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from kr_romanize import romanize, SIDO_EN
except ImportError:                          # still usable, just without English names
    romanize, SIDO_EN = (lambda s: ""), {}
    print("WARNING: kr_romanize.py not found - English names will be blank")

SCRIPT_VERSION = "1.1.0"
SOURCE_URL = "https://github.com/vuski/admdongkor"
FIELDS = {
    "sido":    ["sido_kostat", "sido_mois", "codes_match", "name_ko", "name_en",
                "sigungu_count", "dong_count"],
    "sigungu": ["sigungu_kostat", "sigungu_mois", "sido_kostat", "sido_mois",
                "name_ko", "name_en", "dong_count"],
    "dong":    ["dong_kostat", "dong_mois", "sigungu_kostat", "sigungu_mois",
                "sido_kostat", "sido_mois", "dong_name_ko", "dong_name_en",
                "sigungu_name_ko", "sido_name_ko", "full_name_ko"],
}


# --------------------------------------------------------------------------- io
def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    with open(path, encoding="utf-8") as f:
        return [ft["properties"] for ft in json.load(f)["features"]]


def vintage_from_name(path):
    m = re.search(r"ver(\d{8})", os.path.basename(path))
    return f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}" if m else None


# ------------------------------------------------------------------- validation
def validate(rows):
    """Return a list of error strings. Empty list == input is fit to build from."""
    errs = []
    n = len(rows)
    if n == 0:
        return ["no features in input"]
    for field in ("adm_cd", "adm_cd2", "sgg", "sido", "sidonm", "sggnm", "adm_nm"):
        missing = sum(1 for r in rows if not r.get(field))
        if missing:
            errs.append(f"{missing} rows missing {field}")
    if errs:                                   # later checks assume fields exist
        return errs
    if len({r["adm_cd"] for r in rows}) != n:
        errs.append("KOSTAT dong codes (adm_cd) are not unique")
    if len({r["adm_cd2"] for r in rows}) != n:
        errs.append("MOIS dong codes (adm_cd2) are not unique")
    if any(not re.fullmatch(r"\d{8}", r["adm_cd"]) for r in rows):
        errs.append("adm_cd is not 8 digits everywhere")
    if any(not re.fullmatch(r"\d{10}", r["adm_cd2"]) for r in rows):
        errs.append("adm_cd2 is not 10 digits everywhere")
    if any(not re.fullmatch(r"\d{5}", r["sgg"]) for r in rows):
        errs.append("sgg is not 5 digits everywhere")
    if any(not re.fullmatch(r"\d{2}", r["sido"]) for r in rows):
        errs.append("sido is not 2 digits everywhere")
    # the two families must map 1:1 onto each other at both parent levels,
    # IN BOTH DIRECTIONS (a many-to-one collapse either way is a defect)
    levels = (("sido",    lambda r: r["adm_cd"][:2], lambda r: r["sido"]),
              ("sigungu", lambda r: r["adm_cd"][:5], lambda r: r["sgg"]))
    for lvl, k_key, m_key in levels:
        fwd, rev = defaultdict(set), defaultdict(set)
        for r in rows:
            fwd[k_key(r)].add(m_key(r))
            rev[m_key(r)].add(k_key(r))
        bad_f = {k: sorted(v) for k, v in fwd.items() if len(v) != 1}
        bad_r = {k: sorted(v) for k, v in rev.items() if len(v) != 1}
        if bad_f:
            errs.append(f"{lvl}: one KOSTAT code maps to several MOIS codes: {bad_f}")
        if bad_r:
            errs.append(f"{lvl}: one MOIS code maps to several KOSTAT codes: {bad_r}")
    # a dong's parents must be consistent with its own code prefix
    if any(r["adm_cd2"][:5] != r["sgg"] for r in rows):
        errs.append("adm_cd2 prefix disagrees with sgg on some rows")
    if any(r["sgg"][:2] != r["sido"] for r in rows):
        errs.append("sgg prefix disagrees with sido on some rows")
    return errs


# ------------------------------------------------------------------------ build
def build(rows):
    sido, sigungu, dong = {}, {}, []
    for r in rows:
        k_sido, k_sgg, k_dong = r["adm_cd"][:2], r["adm_cd"][:5], r["adm_cd"]
        dong_ko = r["adm_nm"].split()[-1]
        sido.setdefault(k_sido, {
            "sido_kostat": k_sido, "sido_mois": r["sido"],
            "name_ko": r["sidonm"], "name_en": SIDO_EN.get(k_sido, ""),
            "sigungu_count": 0, "dong_count": 0})
        sigungu.setdefault(k_sgg, {
            "sigungu_kostat": k_sgg, "sigungu_mois": r["sgg"],
            "sido_kostat": k_sido, "sido_mois": r["sido"],
            "name_ko": r["sggnm"], "name_en": romanize(r["sggnm"]), "dong_count": 0})
        sigungu[k_sgg]["dong_count"] += 1
        sido[k_sido]["dong_count"] += 1
        dong.append({
            "dong_kostat": k_dong, "dong_mois": r["adm_cd2"],
            "sigungu_kostat": k_sgg, "sigungu_mois": r["sgg"],
            "sido_kostat": k_sido, "sido_mois": r["sido"],
            "dong_name_ko": dong_ko, "dong_name_en": romanize(dong_ko),
            "sigungu_name_ko": r["sggnm"], "sido_name_ko": r["sidonm"],
            "full_name_ko": r["adm_nm"]})
    for s in sigungu.values():
        sido[s["sido_kostat"]]["sigungu_count"] += 1
    for s in sido.values():
        s["codes_match"] = "yes" if s["sido_kostat"] == s["sido_mois"] else "no"
    return (sorted(sido.values(), key=lambda r: r["sido_kostat"]),
            sorted(sigungu.values(), key=lambda r: r["sigungu_kostat"]),
            sorted(dong, key=lambda r: r["dong_kostat"]))


def collisions(sido, sigungu, dong):
    """Numbers that are valid codes in BOTH systems but denote DIFFERENT units.

    These are the reason a join on a truncated code corrupts data silently.
    Returns {level: [(code, kostat_name, mois_name), ...]}.
    """
    out = {}
    specs = (("sido",    sido,    "sido_kostat",    "sido_mois",    "name_ko"),
             ("sigungu", sigungu, "sigungu_kostat", "sigungu_mois", "name_ko"),
             ("dong",    dong,    "dong_kostat",    "dong_mois",    "full_name_ko"))
    for lvl, rows, kf, mf, nf in specs:
        by_k = {r[kf]: r[nf] for r in rows}
        # compare at the KOSTAT code's length: a MOIS dong code is 10 digits, so
        # the naive "same number" join uses its first 8
        width = len(next(iter(by_k)))
        by_m = {r[mf][:width]: r[nf] for r in rows}
        out[lvl] = [(c, by_k[c], by_m[c]) for c in sorted(set(by_k) & set(by_m))
                    if by_k[c] != by_m[c]]
    return out


# ------------------------------------------------------------------------ write
def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(src, out):
    rows = load(src)
    print(f"source: {os.path.basename(src)}  features: {len(rows)}  "
          f"vintage: {vintage_from_name(src) or 'unknown'}")

    errs = validate(rows)
    if errs:
        for e in errs:
            print(f"  *** {e}")
        raise SystemExit("VALIDATION FAILED - nothing written")
    print("validation: PASS (fields present, codes unique and well-formed, "
          "KOSTAT<->MOIS 1:1 in both directions at sido and sigungu, prefixes consistent)")

    sido, sigungu, dong = build(rows)
    os.makedirs(out, exist_ok=True)
    outputs = {}
    for name, table in (("sido", sido), ("sigungu", sigungu), ("dong", dong)):
        path = os.path.join(out, f"kr_admin_codes_{name}.csv")
        write_csv(path, table, FIELDS[name])
        outputs[os.path.basename(path)] = {"rows": len(table), "sha256": sha256_of(path),
                                           "bytes": os.path.getsize(path)}
        print(f"  wrote {os.path.basename(path)}: {len(table)} rows")

    coll = collisions(sido, sigungu, dong)
    matched = sum(1 for s in sido if s["codes_match"] == "yes")
    print(f"\nsido codes identical in both systems: {matched} of {len(sido)}")
    for lvl in ("sido", "sigungu", "dong"):
        print(f"silent collisions at {lvl} level: {len(coll[lvl])}")
        for c, a, b in coll[lvl][:5]:
            print(f"  {c}: KOSTAT={a}  MOIS={b}")
        if len(coll[lvl]) > 5:
            print(f"  ... {len(coll[lvl]) - 5} more")

    manifest = {
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": os.path.basename(__file__), "script_version": SCRIPT_VERSION,
        "source": {"file": os.path.basename(src), "sha256": sha256_of(src),
                   "bytes": os.path.getsize(src), "vintage": vintage_from_name(src),
                   "file_mtime_utc": datetime.fromtimestamp(os.path.getmtime(src), timezone.utc)
                                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "features": len(rows), "url": SOURCE_URL,
                   "licence": "KOGL Type 1 (SGIS) + CC BY 4.0 (admdongkor) - see LICENSE-DATA.md"},
        "outputs": outputs,
        "summary": {"sido": len(sido), "sigungu": len(sigungu), "dong": len(dong),
                    "sido_codes_identical": matched,
                    "collisions": {k: len(v) for k, v in coll.items()}},
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nmanifest.json written (source sha256 {manifest['source']['sha256'][:12]}...)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2])
