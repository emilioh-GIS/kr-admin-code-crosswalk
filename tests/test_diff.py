"""Unit tests for diff_vintages.py"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import diff_vintages as dv  # noqa: E402


def row(kostat, mois, full, sgg="종로구"):
    return {"dong_kostat": kostat, "dong_mois": mois, "full_name_ko": full, "sigungu_name_ko": sgg}


class DiffTests(unittest.TestCase):
    def test_every_change_class_is_classified(self):
        old = [
            row("11010530", "1111053000", "서울특별시 종로구 사직동"),   # unchanged
            row("11010540", "1111054000", "서울특별시 종로구 삼청동"),   # renamed in new
            row("24010510", "2911051000", "광주광역시 동구 충장동", "동구"),   # recoded in new
            row("11010550", "1111055000", "서울특별시 종로구 부암동"),   # removed
        ]
        new = [
            row("11010530", "1111053000", "서울특별시 종로구 사직동"),
            row("11010540", "1111054000", "서울특별시 종로구 삼청신동"),
            row("12010510", "1211051000", "광주광역시 동구 충장동", "동구"),   # same name, new codes
            row("11010560", "1111056000", "서울특별시 종로구 평창동"),   # added
        ]
        counts = {}
        for kind, *_ in dv.classify(old, new):
            counts[kind] = counts.get(kind, 0) + 1
        self.assertEqual(counts, {"unchanged": 1, "renamed": 1, "recoded": 1, "removed": 1, "added": 1})

    def test_recoded_unit_links_old_and_new_code(self):
        old = [row("24010510", "2911051000", "광주광역시 동구 충장동", "동구")]
        new = [row("12010510", "1211051000", "광주광역시 동구 충장동", "동구")]
        ev = dv.classify(old, new)
        self.assertEqual(ev, [("recoded", "24010510", "12010510",
                               "광주광역시 동구 충장동", "광주광역시 동구 충장동")])

    def test_identical_vintages_are_all_unchanged(self):
        rows = [row("11010530", "1111053000", "서울특별시 종로구 사직동")]
        self.assertEqual([e[0] for e in dv.classify(rows, rows)], ["unchanged"])


if __name__ == "__main__":
    unittest.main()
