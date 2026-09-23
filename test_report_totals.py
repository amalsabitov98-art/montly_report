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

    def test_august_keeps_unpaid_bookings_but_defers_their_profit(self):
        data = json.loads((ROOT / "august-data.json").read_text())
        self.assertEqual(data["excludedBookingIds"], [])
        august = section(self.html, 7)
        for expected in (
            "$157 422", "37 / 124", "$4 255", "$144 300,20", "$12 847",
            "$155 405", "$2 017",
        ):
            self.assertIn(expected, august)
        for stale in ("$153 688", "35 / 120", "$4 391", "$140 841"):
            self.assertNotIn(stale, august)
        self.assertIn("37 бронирований · 124 туриста", section(self.html, 8))

    def test_july_booking_metrics_are_corrected(self):
        july = section(self.html, 5)
        for expected in (
            "$208 751", "163", "$13 001", "$4 014", "+122,2%", "+91,8%", "+15,4%",
            "$194 847", "$206 651", "$181 785", "$2 100", "$13 062",
            "$79 635", "$2 900", "$16 244", "$61 775", "$29 615", "$22 590",
        ):
            self.assertIn(expected, july)
        for stale in ("$206 271", "$13 144", "$3 967", "+119,6%", "+96,5%"):
            self.assertNotIn(stale, july)
        self.assertNotIn(">167<", july)
        self.assertIn("Прибыль $903 по июльским бронированиям получена и учтена в августе", july)
        self.assertNotIn("нетто-стоимость и прибыль не подтверждены", july)

    def test_july_summary_matches_corrected_dashboard(self):
        july_summary = section(self.html, 6)
        for expected in ("ИТОГИ ИЮЛЯ", "$208 751", "163 туриста", "$13 001"):
            self.assertIn(expected, july_summary)

    def test_months_reconcile_to_cover(self):
        bookings = [26, 27, 52, 37]
        tourists = [95, 85, 163, 124]
        sales = [127_732, 93_949, 208_751, 157_422]
        profit = [8_152, 5_417, 13_001, 13_750]
        self.assertEqual(sum(bookings), 142)
        self.assertEqual(sum(tourists), 467)
        self.assertEqual(sum(sales), 587_854)
        self.assertEqual(sum(profit), 40_320)

    def test_cover_is_rendered_from_current_totals(self):
        cover = section(self.html, 0)
        for expected in ("142", "467", "$587 854", "$40 320", "$86,34"):
            self.assertIn(expected, cover)
        self.assertNotIn("visualArtwork", cover)

    def test_cover_identifies_gross_profit_and_profit_per_tourist(self):
        cover = section(self.html, 0)
        self.assertIn("Отчёт Turon Tour по продажам и валовой прибыли", cover)
        self.assertIn("$40 320 валовой прибыли", cover)
        self.assertIn("$86,34 валовой прибыли с туриста", cover)
        self.assertIn(
            "<title>Turon Tour — Отчёт по продажам и валовой прибыли, май–август 2026</title>",
            self.html,
        )

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
