# Korean Administrative Code Crosswalk (KOSTAT ↔ MOIS)

[![tests](https://github.com/emilioh-GIS/kr-admin-code-crosswalk/actions/workflows/ci.yml/badge.svg)](https://github.com/emilioh-GIS/kr-admin-code-crosswalk/actions/workflows/ci.yml)

A flat, documented, tested lookup table mapping South Korea's **two parallel
administrative code systems** against each other at all three levels — province
(시도), municipality (시군구), and administrative neighbourhood (행정동).

Vintage **2026-07-01** · 16 sido · 256 sigungu · 3,558 dong · standard library only.

## Why this exists

Korea maintains two official code families, and **they do not share numbering**:

- **KOSTAT** (통계청, Statistics Korea) — 8-digit at dong level. Census and SGIS
  statistical products are keyed to these.
- **MOIS** (행정안전부, Ministry of the Interior and Safety) — 10-digit at dong level.
  Resident registration and most other government registers use these.

The problem is not that the numbers differ. It is that **the same number is a valid
code in both systems and means a different place** — at every level:

| Level | Numbers valid in both systems | …that denote different units | Example |
|---|---|---|---|
| Province (2-digit) | 4 | **2** | `26` = Ulsan (KOSTAT) but Busan (MOIS) |
| Municipality (5-digit) | 9 | **9** — all of them | `11110` = Nowon-gu (KOSTAT) but Jongno-gu (MOIS) |
| Dong (8-digit) | 48 | **48** — all of them | |

A join on a truncated code therefore does not fail — it silently attaches Busan's
figures to Ulsan, or Jongno's to Nowon. This table exists so you never have to guess
which family a dataset is keyed to, and never have to hand-build the mapping from a
34 MB GeoJSON.

Only **2 of 16** province codes are identical in both systems:

| KOSTAT | MOIS | Match | Province | English | Sigungu | Dong |
|---|---|---|---|---|---|---|
| 11 | 11 | yes | 서울특별시 | Seoul | 25 | 427 |
| 12 | 12 | yes | 전남광주통합특별시 | Jeonnam-Gwangju | 27 | 393 |
| 21 | 26 | no | 부산광역시 | Busan | 16 | 206 |
| 22 | 27 | no | 대구광역시 | Daegu | 9 | 150 |
| 23 | 28 | no | 인천광역시 | Incheon | 11 | 158 |
| 25 | 30 | no | 대전광역시 | Daejeon | 5 | 82 |
| 26 | 31 | no | 울산광역시 | Ulsan | 5 | 55 |
| 29 | 36 | no | 세종특별자치시 | Sejong | 1 | 24 |
| 31 | 41 | no | 경기도 | Gyeonggi-do | 47 | 602 |
| 32 | 51 | no | 강원특별자치도 | Gangwon-do | 18 | 188 |
| 33 | 43 | no | 충청북도 | Chungcheongbuk-do | 14 | 153 |
| 34 | 44 | no | 충청남도 | Chungcheongnam-do | 16 | 208 |
| 35 | 52 | no | 전북특별자치도 | Jeonbuk-do | 15 | 243 |
| 37 | 47 | no | 경상북도 | Gyeongsangbuk-do | 23 | 321 |
| 38 | 48 | no | 경상남도 | Gyeongsangnam-do | 22 | 305 |
| 39 | 50 | no | 제주특별자치도 | Jeju-do | 2 | 43 |

**Sixteen provinces, not seventeen.** Gwangju Metropolitan City and South Jeolla
Province merged into 전남광주통합특별시 effective 2026-07-01, and every unit in that
region was recoded. Any reference listing 17 provinces predates the merger — which is
also why a crosswalk is only trustworthy for its stated vintage.

## Files

| File | Rows | Contents |
|---|---|---|
| `data/kr_admin_codes_sido.csv` | 16 | Both province codes, `codes_match` flag, names, child counts |
| `data/kr_admin_codes_sigungu.csv` | 256 | Both municipality codes, parent province codes, names, dong count |
| `data/kr_admin_codes_dong.csv` | 3,558 | Both dong codes, all parent codes in both families, names, full path |
| `data/manifest.json` | — | SHA-256 and size of the source file and of every output, row counts, vintage, build timestamp |

All CSVs are UTF-8 (no BOM), comma-delimited, `\n` line endings, header row.

```
dong_kostat,dong_mois,sigungu_kostat,sigungu_mois,sido_kostat,sido_mois,dong_name_ko,dong_name_en,sigungu_name_ko,sido_name_ko,full_name_ko
11010530,1111053000,11010,11110,11,11,사직동,Sajik-dong,종로구,서울특별시,서울특별시 종로구 사직동
```

**Read every code column as text.** They are identifiers, not numbers: treating them
as integers invites accidental arithmetic and breaks joins against any system that
stores them as strings. (None happen to carry leading zeros in this vintage; that is
not a guarantee.)

**Opening in Excel:** double-clicking a UTF-8 CSV shows Korean as mojibake on Windows.
Use *Data → From Text/CSV* and choose UTF-8, or read the files programmatically.

## Using it

```python
import pandas as pd

xw = pd.read_csv("data/kr_admin_codes_dong.csv", dtype=str)

# a statistics table keyed to KOSTAT 8-digit codes, e.g. from SGIS / KOSIS
stats = pd.read_csv("sgis_population_by_dong.csv", dtype=str)

merged = stats.merge(xw, left_on="adm_cd", right_on="dong_kostat", how="left")

# every input row should have found its MOIS code; if not, your stats file is
# keyed to a different vintage (or a different family) than you think
assert merged["dong_mois"].notna().all(), merged[merged["dong_mois"].isna()]
```

## Reproducing it

```bash
python build_crosswalk.py HangJeongDong_ver20260701.geojson ./data
```

The script **validates before it writes anything**, and exits without output if any
check fails:

- every required attribute present on every feature
- KOSTAT and MOIS dong codes each unique, 8 and 10 digits respectively
- KOSTAT ↔ MOIS mapping is **1:1 in both directions** at province and municipality
  level — a many-to-one collapse either way is treated as a defect
- each dong's parent codes agree with its own code prefix in both families

Output is **deterministic**: rows are sorted by code, and identical input produces
byte-identical files (asserted in the test suite). `data/manifest.json` records the
SHA-256 of the input and of every output so a consumer can verify that what they
downloaded is what was built.

## Refreshing for a new vintage

Point the script at a newer release, then compare the old and new dong tables:

```bash
python diff_vintages.py data_old/kr_admin_codes_dong.csv data/kr_admin_codes_dong.csv changes.csv
```

Each unit is classified as `unchanged`, `renamed` (same codes, new name), `recoded`
(same unit, new code — the case that silently breaks anything keyed to the old code),
`removed`, or `added`. Review the report before refreshing anything downstream.

## Tests

```bash
python -m unittest discover -s tests -v
```

27 tests, standard library only, run in CI on every push (`.github/workflows/ci.yml`).
`tests/test_build.py` covers the validator (each failure mode has a test that proves it
is caught), the build, collision detection, and end-to-end determinism against a small
fixture. `tests/test_real_data.py` is a conformance suite against the shipped files:
row counts, code uniqueness, the known province collisions, and that every checksum in
`manifest.json` matches the file on disk.

## Source and provenance

Both code families are published together on every feature of Statistics Korea's SGIS
administrative-dong boundary release, obtained through the maintained redistribution
[vuski/admdongkor](https://github.com/vuski/admdongkor), file
`ver20260701/HangJeongDong_ver20260701.geojson` (34,653,221 bytes; its SHA-256 and
modification time are recorded in `data/manifest.json`).

This repository contains **codes and names only** — no geometry. If you need
boundaries, go to the source.

## Limitations — read before relying on this

- **Vintage-locked.** Korea reorganises administrative units regularly (the 2026
  provincial merger and Incheon's district restructuring are both recent). A crosswalk
  is only valid for its vintage; re-run the script against a current release rather
  than assuming this file stays correct.
- **Administrative dong (행정동), not legal dong (법정동).** These are two different
  unit families and are not interchangeable. Legal dong are what most consumer
  basemaps label; administrative dong are what statistics are published on. If your
  data is keyed to legal dong, this table is the wrong tool.
- **English names are transliterations, not official designations.** Dong and sigungu
  names are machine-transcribed by Revised Romanization (bundled `kr_romanize.py`) with
  the standard sound-change rules; province names come from a curated table of official
  short forms. Individual bodies occasionally publish an English name that differs from
  the transliteration — treat `*_name_en` as a convenience column and the Korean name as
  authoritative.
- **Derived, not authoritative.** This is a convenience extraction of codes the source
  already publishes. Where this table and the source disagree, the source is right.

## Licence

**Data** (`data/`) — derived from a KOGL Type 1 release with CC BY 4.0 additions; the
required attribution is in [`LICENSE-DATA.md`](LICENSE-DATA.md) and must be kept with
any redistribution.

**Code** — MIT, see [`LICENSE`](LICENSE).

---

Built by Emilio Hernandez · Terrain Studio — terrain and site analysis, boundary and
census data engineering.
