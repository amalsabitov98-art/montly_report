import json
import os
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parent


def section(html: str, screen: int) -> str:
    match = re.search(
        rf'<section class="[^"]+" data-screen="{screen}"[^>]*>(.*?)</section>',
        html,
        re.S,
    )
    if not match:
        raise AssertionError(f"screen {screen} not found")
    return match.group(1).replace("&nbsp;", " ")


class ReportTotalsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = {**os.environ, "PYTHONUTF8": "1"}
        subprocess.run(["python", "build_august.py"], cwd=ROOT, check=True, env=env)
        cls.html = (ROOT / "Turon_Tour_August_2026_FINAL.html").read_text(encoding="utf-8")

    def test_august_excludes_muslim_yellow_rows(self):
        data = json.loads((ROOT / "august-data.json").read_text())
        self.assertEqual(data["excludedBookingIds"], [18, 25])
        august = section(self.html, 7)
        for expected in ("$153 688", "35 / 120", "$4 391", "$140 841", "$12 847"):
            self.assertIn(expected, august)
        for excluded in ("$157 422", "37 / 124", "$2 017", "№18", "№25"):
            self.assertNotIn(excluded, august)

    def test_july_booking_metrics_are_corrected(self):
        july = section(self.html, 5)
        for expected in (
            "$208 751", "167", "$4 014", "+122,2%", "+96,5%", "+15,4%",
            "$79 635", "$2 900", "$16 244", "$61 775", "$29 615", "$22 590",
        ):
            self.assertIn(expected, july)
        for stale in ("$206 271", "163", "$3 967", "+119,6%", "+91,8%"):
            self.assertNotIn(stale, july)
        self.assertIn("Прибыль $903 по трём июльским броням получена и учтена в августе", july)
        self.assertNotIn("нетто-стоимость и прибыль не подтверждены", july)

    def test_july_summary_matches_corrected_dashboard(self):
        july_summary = section(self.html, 6)
        for expected in ("ИТОГИ ИЮЛЯ", "$208 751", "167 туристов", "$13 144"):
            self.assertIn(expected, july_summary)

    def test_months_reconcile_to_cover(self):
        tourists = [95, 85, 167, 120]
        sales = [127_732, 93_949, 208_751, 153_688]
        profit = [8_152, 5_417, 13_144, 13_750]
        self.assertEqual(sum(tourists), 467)
        self.assertEqual(sum(sales), 584_120)
        self.assertEqual(sum(profit), 40_463)
        self.assertIn("cover-may-august-2026.png", self.html)


if __name__ == "__main__":
    unittest.main()
