"""Unit tests for build_crosswalk.py - run with:  python -m unittest discover -s tests -v"""
import contextlib, csv, io, json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import build_crosswalk as bc  # noqa: E402


def feat(adm_cd, adm_cd2, sido, sidonm, sggnm, dong):
    return {"adm_cd": adm_cd, "adm_cd2": adm_cd2, "sgg": adm_cd2[:5], "sido": sido,
            "sidonm": sidonm, "sggnm": sggnm, "adm_nm": f"{sidonm} {sggnm} {dong}"}


def clean_rows():
    """Small but realistic fixture. Reproduces the real-world collision on code 26:
    KOSTAT 26 = Ulsan, MOIS 26 = Busan."""
    return [
        feat("11010530", "1111053000", "11", "서울특별시", "종로구", "사직동"),
        feat("11010540", "1111054000", "11", "서울특별시", "종로구", "삼청동"),
        feat("21010510", "2611051000", "26", "부산광역시", "중구", "중앙동"),
        feat("26010510", "3111051000", "31", "울산광역시", "중구", "학성동"),
    ]


class ValidateTests(unittest.TestCase):
    def test_clean_input_passes(self):
        self.assertEqual(bc.validate(clean_rows()), [])

    def test_empty_input_fails(self):
        self.assertTrue(bc.validate([]))

    def test_missing_field_is_reported(self):
        rows = clean_rows(); rows[0]["sggnm"] = ""
        self.assertTrue(any("missing sggnm" in e for e in bc.validate(rows)))

    def test_duplicate_kostat_code_is_reported(self):
        rows = clean_rows(); rows[1]["adm_cd"] = rows[0]["adm_cd"]
        self.assertTrue(any("adm_cd) are not unique" in e for e in bc.validate(rows)))

    def test_duplicate_mois_code_is_reported(self):
        rows = clean_rows(); rows[1]["adm_cd2"] = rows[0]["adm_cd2"]
        self.assertTrue(any("adm_cd2) are not unique" in e for e in bc.validate(rows)))

    def test_wrong_code_length_is_reported(self):
        rows = clean_rows(); rows[0]["adm_cd"] = "1101053"
        self.assertTrue(any("8 digits" in e for e in bc.validate(rows)))

    def test_one_kostat_to_many_mois_is_reported(self):
        rows = clean_rows()
        rows[1]["sido"] = "99"; rows[1]["adm_cd2"] = "9911054000"; rows[1]["sgg"] = "99110"
        errs = bc.validate(rows)
        self.assertTrue(any("one KOSTAT code maps to several MOIS" in e for e in errs), errs)

    def test_many_kostat_to_one_mois_is_reported(self):
        # two different KOSTAT sido (11 and 21) both claiming MOIS sido 11
        rows = clean_rows()
        rows[2]["sido"] = "11"; rows[2]["adm_cd2"] = "1111051000"; rows[2]["sgg"] = "11110"
        errs = bc.validate(rows)
        self.assertTrue(any("one MOIS code maps to several KOSTAT" in e for e in errs), errs)

    def test_prefix_inconsistency_is_reported(self):
        rows = clean_rows(); rows[0]["sgg"] = "11140"        # no longer a prefix of adm_cd2
        self.assertTrue(any("prefix disagrees" in e for e in bc.validate(rows)))


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.sido, self.sigungu, self.dong = bc.build(clean_rows())

    def test_counts(self):
        self.assertEqual((len(self.sido), len(self.sigungu), len(self.dong)), (3, 3, 4))

    def test_output_is_sorted_by_code(self):
        self.assertEqual([d["dong_kostat"] for d in self.dong],
                         sorted(d["dong_kostat"] for d in self.dong))

    def test_codes_match_flag(self):
        flags = {s["sido_kostat"]: s["codes_match"] for s in self.sido}
        self.assertEqual(flags, {"11": "yes", "21": "no", "26": "no"})

    def test_child_counts(self):
        seoul = next(s for s in self.sido if s["sido_kostat"] == "11")
        self.assertEqual((seoul["sigungu_count"], seoul["dong_count"]), (1, 2))

    def test_dong_row_carries_both_families_at_every_level(self):
        d = next(x for x in self.dong if x["dong_kostat"] == "26010510")
        self.assertEqual((d["dong_mois"], d["sigungu_mois"], d["sido_mois"]),
                         ("3111051000", "31110", "31"))

    def test_english_names_are_filled(self):
        self.assertTrue(all(d["dong_name_en"] for d in self.dong))
        self.assertEqual(next(d for d in self.dong if d["dong_name_ko"] == "사직동")["dong_name_en"],
                         "Sajik-dong")

    def test_collision_on_26_is_detected(self):
        coll = bc.collisions(self.sido, self.sigungu, self.dong)
        codes = [c for c, _, _ in coll["sido"]]
        self.assertEqual(codes, ["26"])
        code, kostat_name, mois_name = coll["sido"][0]
        self.assertEqual((kostat_name, mois_name), ("울산광역시", "부산광역시"))


class EndToEndTests(unittest.TestCase):
    def _write_geojson(self, path):
        gj = {"type": "FeatureCollection",
              "features": [{"type": "Feature", "properties": p, "geometry": None}
                           for p in clean_rows()]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(gj, f, ensure_ascii=False)

    def test_main_writes_csvs_and_truthful_manifest_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "HangJeongDong_ver20260701.geojson")
            self._write_geojson(src)
            out1, out2 = os.path.join(tmp, "a"), os.path.join(tmp, "b")
            with contextlib.redirect_stdout(io.StringIO()):
                bc.main(src, out1)
                bc.main(src, out2)
            for name in ("sido", "sigungu", "dong"):
                fn = f"kr_admin_codes_{name}.csv"
                with open(os.path.join(out1, fn), "rb") as fa, open(os.path.join(out2, fn), "rb") as fb:
                    self.assertEqual(fa.read(), fb.read(), f"{fn} not deterministic")
            with open(os.path.join(out1, "manifest.json"), encoding="utf-8") as f:
                man = json.load(f)
            self.assertEqual(man["source"]["sha256"], bc.sha256_of(src))
            self.assertEqual(man["source"]["vintage"], "2026-07-01")
            for fn, meta in man["outputs"].items():
                self.assertEqual(meta["sha256"], bc.sha256_of(os.path.join(out1, fn)))
                with open(os.path.join(out1, fn), encoding="utf-8") as f:
                    self.assertEqual(sum(1 for _ in csv.DictReader(f)), meta["rows"])
            self.assertEqual(man["summary"]["collisions"]["sido"], 1)

    def test_main_refuses_to_write_on_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "bad.geojson")
            rows = clean_rows(); rows[1]["adm_cd"] = rows[0]["adm_cd"]
            with open(src, "w", encoding="utf-8") as f:
                json.dump({"type": "FeatureCollection",
                           "features": [{"type": "Feature", "properties": p} for p in rows]}, f,
                          ensure_ascii=False)
            out = os.path.join(tmp, "out")
            with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
                bc.main(src, out)
            self.assertFalse(os.path.exists(os.path.join(out, "kr_admin_codes_dong.csv")))


if __name__ == "__main__":
    unittest.main()
