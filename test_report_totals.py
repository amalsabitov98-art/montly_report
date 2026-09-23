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
    body = re.sub(r'src="data:image/[^\"]+"', 'src="[embedded-image]"', match.group(1))
    return body.replace("&nbsp;", " ")


class ReportTotalsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = {**os.environ, "PYTHONUTF8": "1"}
        subprocess.run(["python", "build_august.py"], cwd=ROOT, check=True, env=env)
        cls.html = (ROOT / "Turon_Tour_August_2026_FINAL.html").read_text(encoding="utf-8")

    def test_august_matches_the_current_workbook(self):
        data = json.loads((ROOT / "august-data.json").read_text())
        self.assertEqual(data["excludedBookingIds"], [])
        august = section(self.html, 7)
        for expected in (
            "$166 788", "39 / 127", "$4 277", "$153 038", "$13 750",
            "$166 788", "$0",
        ):
            self.assertIn(expected, august)
        for stale in ("$157 422", "37 / 124", "$4 255", "$144 300,20", "$12 847"):
            self.assertNotIn(stale, august)
        self.assertIn("39 бронирований · 127 туристов", section(self.html, 8))
        self.assertNotIn("$903", august + section(self.html, 8))

    def test_july_booking_metrics_are_corrected(self):
        july = section(self.html, 5)
        for expected in (
            "$192 751", "154", "$12 901", "$4 101", "+105,2%", "+81,2%", "+17,9%",
            "$179 850", "$192 751", "$168 788", "$0", "$11 062",
        ):
            self.assertIn(expected, july)
        for stale in ("$208 751", "$13 001", "$4 014", "+122,2%", "+91,8%"):
            self.assertNotIn(stale, july)
        self.assertNotIn("$903", july)

    def test_july_summary_matches_corrected_dashboard(self):
        july_summary = section(self.html, 6)
        for expected in ("ИТОГИ ИЮЛЯ", "$192 751", "154 туриста", "$12 901"):
            self.assertIn(expected, july_summary)

    def test_months_reconcile_to_cover(self):
        bookings = [26, 27, 47, 39]
        tourists = [95, 85, 154, 127]
        sales = [127_732, 93_949, 192_751, 166_788]
        profit = [8_152, 5_417, 12_901, 13_750]
        self.assertEqual(sum(bookings), 139)
        self.assertEqual(sum(tourists), 461)
        self.assertEqual(sum(sales), 581_220)
        self.assertEqual(sum(profit), 40_220)

    def test_cover_uses_the_original_branded_artwork(self):
        cover = section(self.html, 0)
        self.assertIn("visualFrame", cover)
        self.assertIn("visualArtwork", cover)
        self.assertIn("cover-gross-profit-per-tourist-may-august-2026-v3.png", cover)
        self.assertNotIn("reportCover", cover)

    def test_cover_identifies_gross_profit_and_profit_per_tourist(self):
        cover = section(self.html, 0)
        self.assertIn("Отчёт Turon Tour по продажам и валовой прибыли", cover)
        self.assertIn("$40 220 валовой прибыли", cover)
        self.assertIn("$87,25 валовой прибыли с туриста", cover)
        self.assertIn(
            "<title>Turon Tour — Отчёт по продажам и валовой прибыли, май–август 2026</title>",
            self.html,
        )
        self.assertNotIn("ЧИСТАЯ ПРИБЫЛЬ", self.html)
        self.assertNotIn("Чистая прибыль", self.html)

    def test_august_does_not_show_office_remainder(self):
        august = section(self.html, 7)
        august_summary = section(self.html, 8)
        for screen in (august, august_summary):
            self.assertNotRegex(screen, r"(?i)остаток\s+офису")

    def test_plain_url_starts_on_cover(self):
        self.assertIn(
            'const startScreen={"#august":7,"#august-summary":8}[location.hash]??0;go(startScreen);',
            self.html,
        )
        self.assertNotIn(
            'go(location.hash === "#august-summary" ? 8 : location.hash === "#cover" ? 0 : 7);',
            self.html,
        )


if __name__ == "__main__":
    unittest.main()
