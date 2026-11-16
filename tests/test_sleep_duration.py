import json
from pathlib import Path
import subprocess
import sys
import unittest
from sleep.sleep_duration import analyze_sleep

class SleepAnalysisTests(unittest.TestCase):
    def test_reference_deficit_and_improvement(self):
        rows = analyze_sleep([8, 6, 7])["records"]
        self.assertIsNone(rows[0]["error_rate_per_day"])
        self.assertIsNone(rows[0]["change_from_previous_hours"])
        self.assertEqual(rows[1]["deviation_hours"], 2)
        self.assertEqual(rows[1]["deviation_percent"], 25)
        self.assertEqual(rows[1]["change_from_previous_hours"], -2)
        self.assertAlmostEqual(rows[2]["error_rate_per_day"], -0.125)
        self.assertAlmostEqual(rows[2]["accumulated_relative_error_days"], 0.3125)

    def test_actual_elapsed_days_and_signed_integration(self):
        rows = analyze_sleep([6, 10], [2, 6])["records"]
        self.assertAlmostEqual(rows[1]["error_rate_per_day"], -0.125)
        self.assertAlmostEqual(rows[1]["accumulated_relative_error_days"], 0)
        self.assertEqual(rows[1]["deviation_hours"], -2)

    def test_validation(self):
        for values, days, baseline in [([], None, 8), ([float("nan")], None, 8),
            ([float("inf")], None, 8), ([-1], None, 8), ([25], None, 8),
            ([True], None, 8), ([8], None, 0), ([8], None, 25),
            ([8,7], [2,2], 8), ([8,7], [2,1], 8), ([8], [1,2], 8),
            ([8], [1.5], 8), ([8], [True], 8), ([8], [0], 8)]:
            with self.subTest(values=values, days=days, baseline=baseline):
                with self.assertRaises(ValueError): analyze_sleep(values, days, baseline)
        self.assertEqual(analyze_sleep([0])["records"][0]["relative_error"], 1)

    def test_json_entry_point_from_another_directory(self):
        script = Path(__file__).resolve().parents[1] / "sleep/sleep_duration.py"
        result = subprocess.run([sys.executable, "-B", str(script), "--hours", "6", "7", "--days", "2", "4", "--json"], cwd=script.parent, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["observed_start_day"], 2)
        self.assertAlmostEqual(data["records"][-1]["error_rate_per_day"], -0.0625)
        self.assertNotIn("urgency_level", data["records"][-1])
