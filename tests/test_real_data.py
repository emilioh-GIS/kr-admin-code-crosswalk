"""Conformance tests against the shipped data/ files. Skipped if data/ is absent."""
import csv, json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, ROOT)
import build_crosswalk as bc  # noqa: E402

HAVE_DATA = all(os.path.exists(os.path.join(DATA, f)) for f in
                ("kr_admin_codes_sido.csv", "kr_admin_codes_sigungu.csv",
                 "kr_admin_codes_dong.csv", "manifest.json"))


def read(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


@unittest.skipUnless(HAVE_DATA, "data/ not present")
class ShippedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sido, cls.sigungu, cls.dong = read("kr_admin_codes_sido.csv"), \
            read("kr_admin_codes_sigungu.csv"), read("kr_admin_codes_dong.csv")
        with open(os.path.join(DATA, "manifest.json"), encoding="utf-8") as f:
            cls.man = json.load(f)

    def test_row_counts_match_vintage_2026_07_01(self):
        self.assertEqual((len(self.sido), len(self.sigungu), len(self.dong)), (16, 256, 3558))

    def test_manifest_checksums_match_files_on_disk(self):
        for fn, meta in self.man["outputs"].items():
            self.assertEqual(meta["sha256"], bc.sha256_of(os.path.join(DATA, fn)), fn)
            with open(os.path.join(DATA, fn), encoding="utf-8") as f:
                self.assertEqual(sum(1 for _ in csv.DictReader(f)), meta["rows"], fn)

    def test_codes_are_unique_and_well_formed(self):
        self.assertEqual(len({d["dong_kostat"] for d in self.dong}), 3558)
        self.assertEqual(len({d["dong_mois"] for d in self.dong}), 3558)
        self.assertTrue(all(len(d["dong_kostat"]) == 8 and len(d["dong_mois"]) == 10 for d in self.dong))

    def test_known_province_collisions(self):
        coll = bc.collisions(self.sido, self.sigungu, self.dong)
        self.assertEqual([c for c, _, _ in coll["sido"]], ["26", "31"])
        self.assertEqual(sum(1 for s in self.sido if s["codes_match"] == "yes"), 2)

    def test_every_dong_has_an_english_name(self):
        self.assertTrue(all(d["dong_name_en"] for d in self.dong))

    def test_sixteen_provinces_after_2026_merger(self):
        names = {s["name_ko"] for s in self.sido}
        self.assertIn("전남광주통합특별시", names)
        self.assertNotIn("광주광역시", names)
        self.assertNotIn("전라남도", names)


if __name__ == "__main__":
    unittest.main()
