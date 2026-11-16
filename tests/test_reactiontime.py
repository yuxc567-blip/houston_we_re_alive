import json
from pathlib import Path
import tempfile
import unittest
from sleep.reactiontime import ReactionTrial, load_results, process_reaction_times, save_results

class ReactionTimeTests(unittest.TestCase):
    def test_early_click_and_monotonic_timing(self):
        trial = ReactionTrial()
        self.assertEqual(trial.press(1), ("ignored", None))
        trial.wait()
        self.assertEqual(trial.press(2), ("early", None))
        trial.signal(3)
        self.assertEqual(trial.press(4), ("ignored", None))
        trial.wait(); trial.signal(10)
        outcome, value = trial.press(10.25)
        self.assertEqual(outcome, "valid")
        self.assertAlmostEqual(value, 250)
        self.assertEqual(trial.press(11), ("ignored", None))

    def test_slowdown_and_recovery_use_actual_days(self):
        rows = process_reaction_times([1,3,6], [250,300,275], 250)
        self.assertIsNone(rows[0]["error_rate"])
        self.assertEqual(rows[1]["deviation"], 50)
        self.assertAlmostEqual(rows[1]["error"], .2)
        self.assertAlmostEqual(rows[1]["error_rate"], .1)
        self.assertAlmostEqual(rows[2]["error_rate"], -.1/3)
        self.assertAlmostEqual(rows[2]["accumulated_error"], .65)
        self.assertNotIn("urgency_level", rows[1])

    def test_invalid_inputs_and_cancel(self):
        for days, values, baseline in [([], [], 250), ([1],[250],0), ([1],[float("nan")],250), ([1],[float("inf")],250), ([1],[-2],250), ([True],[250],250), ([1.5],[250],250), ([1,1],[250,260],250), ([2,1],[250,260],250), ([1],[250,260],250)]:
            with self.subTest(days=days, values=values):
                with self.assertRaises(ValueError): process_reaction_times(days, values, baseline)
        trial=ReactionTrial(); trial.wait(); trial.signal(1); trial.cancel()
        self.assertEqual(trial.press(2), ("ignored",None))

    def test_persistence_and_malformed_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"results.json"
            self.assertEqual(load_results(path), {"baseline":None,"sessions":[]})
            data={"baseline":{"mean_ms":250,"trials_ms":[240,260]},"sessions":[{"day":1,"mean_ms":300}]}
            save_results(path,data)
            self.assertEqual(load_results(path),data)
            path.write_text("broken")
            with self.assertRaises(json.JSONDecodeError): load_results(path)
            self.assertEqual(path.read_text(), "broken")
