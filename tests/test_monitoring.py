import unittest

from sleep.monitoring import assess_series, linear_regression, monitoring_summary
from sleep.reactiontime import process_reaction_times
from sleep.sleep_duration import analyze_sleep


class MonitoringTests(unittest.TestCase):
    def assess_sleep(self, hours, days=None):
        rows = analyze_sleep(hours, days)["records"]
        return assess_series(rows, "relative_error", "error_rate_per_day", "accumulated_relative_error_days")

    def test_exact_linear_fit_with_actual_irregular_days(self):
        result = linear_regression([2, 5, 9], [.02, .05, .09])
        self.assertEqual(result["status"], "fitted")
        self.assertAlmostEqual(result["slope"], .01)
        self.assertAlmostEqual(result["intercept"], 0)
        self.assertAlmostEqual(result["r_squared"], 1)
        self.assertAlmostEqual(result["rmse"], 0)

    def test_short_constant_and_invalid_regression_inputs(self):
        self.assertEqual(linear_regression([1, 2], [.1, .2])["status"], "insufficient_data")
        self.assertEqual(linear_regression([1, 1, 1], [.1, .2, .3])["status"], "no_predictor_variation")
        flat = linear_regression([1, 2, 3], [.25, .25, .25])
        self.assertAlmostEqual(flat["slope"], 0)
        self.assertIsNone(flat["r_squared"])
        for xs, ys in [([1],[1,2]),([1,2,3],[0,.1,float("nan")]),([True,2,3],[0,.1,.2])]:
            with self.assertRaises(ValueError): linear_regression(xs,ys)

    def test_status_boundaries_and_direction(self):
        self.assertEqual(self.assess_sleep([8])["status"], "NORMAL")
        self.assertEqual(self.assess_sleep([7.6])["status"], "WATCH OUT")
        self.assertEqual(self.assess_sleep([7.2])["status"], "ACTION NEEDED")
        self.assertEqual(self.assess_sleep([10])["status"], "NORMAL")
        self.assertIsNone(self.assess_sleep([8])["latest_derivative_per_day"])

    def test_fast_improvement_is_not_high_urgency(self):
        result = self.assess_sleep([7.2, 7.6, 8])
        self.assertEqual(result["status"], "NORMAL")
        self.assertEqual(result["urgency"], "LOW")
        self.assertAlmostEqual(result["latest_derivative_per_day"], -.05)
        self.assertAlmostEqual(result["signed_integral_fraction_days"], .1)
        self.assertEqual(result["worsening_rate_used_per_day"], 0)

    def test_derivative_and_regression_forecast_can_raise_demo_urgency(self):
        interval = self.assess_sleep([8, 7.52])
        self.assertEqual(interval["status"], "WATCH OUT")
        self.assertEqual(interval["urgency"], "HIGH")
        self.assertEqual(interval["trend"]["status"], "insufficient_data")
        forecast = self.assess_sleep([8, 7.88, 7.76])
        self.assertEqual(forecast["status"], "NORMAL")
        self.assertEqual(forecast["urgency"], "HIGH")
        self.assertAlmostEqual(forecast["trend"]["slope"], .015)
        self.assertAlmostEqual(forecast["trend"]["forecast_error"], .135)
        self.assertEqual(forecast["trend"]["forecast_day"], 10)

    def test_paired_association_is_separate_from_urgency(self):
        sleep = analyze_sleep([8,7.6,7.2])["records"]
        reaction = process_reaction_times([1,2,3], [250,275,300], 250)
        result = monitoring_summary(sleep,reaction)
        fit = result["association"]
        self.assertAlmostEqual(fit["slope"], 2)
        self.assertAlmostEqual(fit["r_squared"], 1)
        self.assertIn("not used to assign urgency", fit["description"])
        self.assertEqual(result["sleep"]["urgency"], monitoring_summary(sleep,[])["sleep"]["urgency"])

    def test_missing_data_is_not_normal_and_sources_are_traceable(self):
        result = monitoring_summary([],[])
        self.assertEqual(result["sleep"]["status"], "NOT ASSESSED")
        self.assertEqual(result["reaction"]["urgency"], "NOT ASSESSED")
        self.assertIn("unvalidated",result["settings"]["classification_basis"])
        self.assertEqual(len(result["evidence"]),5)
        self.assertTrue(all(item["url"].startswith("https://humanresearchroadmap.nasa.gov/") for item in result["evidence"]))
