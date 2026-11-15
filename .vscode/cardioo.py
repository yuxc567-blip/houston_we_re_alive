#!/usr/bin/env python3
"""Daily cardiovascular research comparison. Python 3.9+, no dependencies.
Run: python3 cardiovascular_daily_reference.py
Test: python3 cardiovascular_daily_reference.py --self-test

Reference: Balali et al. (2025), Tables 1-2,
https://doi.org/10.1038/s41526-025-00522-8
This is a separate study, NOT the NASA 2022 evidence report.
17 ISS cosmonauts; seated preflight group medians; nominal flight days
6 +/- 2, 37 +/- 4, 159 +/- 4. Linear interpolation estimates unmeasured days.
Applying group relative changes to an individual is a prototype assumption.
No individual experimental ranges or clinical thresholds are established.
QRS excluded: no dated QRS trajectory is available in the cited data.
P/I/D-like monitoring features; no automatic treatment or closed-loop PID.
"""
import argparse
import math
from datetime import datetime, timedelta, timezone
from enum import Enum
# ============================================================
# REFERENCE DATA — USED IN SECTIONS 8–10
# ============================================================

EXPERIMENTS = {'heart_rate': {'unit': 'bpm', 'preflight': 66.0, 'points': [(6, 61.0), (37, 62.0), (159, 61.0)]}, 'systolic_bp': {'unit': 'mmHg', 'preflight': 127.0, 'points': [(6, 121.0), (37, 116.0), (159, 117.0)]}, 'diastolic_bp': {'unit': 'mmHg', 'preflight': 87.0, 'points': [(6, 78.0), (37, 72.0), (159, 72.0)]}}

def number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (not math.isfinite(value)):
        raise ValueError(name + ' must be finite')
    if positive and value <= 0:
        raise ValueError(name + ' must be positive')
    return float(value)

def check_time(t):
    if not isinstance(t, datetime) or t.utcoffset() is None:
        raise ValueError('Use a timezone-aware datetime')

# ============================================================
# 1. DEVIATION
# ============================================================

class Deviation:

    def __init__(self, std, current):
        self.std = number(std, 'reference', True)
        self.current = number(current, 'reading', True)

    def calculate(self):
        return self.std - self.current

# ============================================================
# 2. ERROR
# ============================================================

class Error(Deviation):
    # Both higher and lower readings can differ from the research reference.

    def calculate(self):
        return abs(super().calculate() / self.std)

# ============================================================
# 3. ACCUMULATED ERROR
# ============================================================

class AccumulatedError:
    """Integral of nonnegative error; exclude gaps over max_gap_days.
    Total covers observed intervals only, not the entire mission.
    """

    def __init__(self, max_gap_days=2):
        self.previous_error = self.previous_time = None
        self.total = self.covered_days = 0.0
        self.max_gap_days = number(max_gap_days, 'max_gap_days', True)

    def calculate(self, timestamp, error):
        if self.previous_time is not None:
            dt = (timestamp - self.previous_time).total_seconds() / 86400
            if dt <= 0:
                raise ValueError('Timestamp must increase')
            if dt <= self.max_gap_days:
                self.total += (self.previous_error + error) / 2 * dt
                self.covered_days += dt
        self.previous_error, self.previous_time = (error, timestamp)
        return self.total

# ============================================================
# 4. DETERIORATION RATE
# ============================================================

class DeteriorationRate:
    """Change in distance from modeled reference, not medical deterioration."""

    def __init__(self, max_gap_days=2):
        self.previous_error = self.previous_time = None
        self.max_gap_days = max_gap_days

    def calculate(self, timestamp, error):
        rate = None
        if self.previous_time is not None:
            dt = (timestamp - self.previous_time).total_seconds() / 86400
            if dt <= 0:
                raise ValueError('Timestamp must increase')
            if dt <= self.max_gap_days:
                rate = (error - self.previous_error) / dt
        self.previous_error, self.previous_time = (error, timestamp)
        return rate

# ============================================================
# 5. INTERVENTION STATUS (SIMULATION LABELS)
# ============================================================

class Status(Enum):
    # NORMAL means below fictional demo tolerance, not medically healthy.
    NORMAL = 'NORMAL'
    WATCH = 'WATCH'
    ACTION_REVIEW = 'ACTION_REVIEW'

class InterventionStatus:

    def __init__(self, warning, critical):
        self.warning = number(warning, 'warning', True)
        self.critical = number(critical, 'critical', True)
        if warning >= critical:
            raise ValueError('Warning must be below critical')

    def evaluate(self, error):
        if error >= self.critical:
            return Status.ACTION_REVIEW
        return Status.WATCH if error >= self.warning else Status.NORMAL

# ============================================================
# 6. URGENCY (SIMULATION ONLY)
# ============================================================

class UrgencyLevel(Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'

class Urgency:
    """Unvalidated simulation rules, including linear extrapolation of error."""

    def __init__(self, warning, critical, warning_rate, critical_rate, prediction_days=7):
        InterventionStatus(warning, critical)
        self.warning, self.critical = (warning, critical)
        self.warning_rate = number(warning_rate, 'warning_rate', True)
        self.critical_rate = number(critical_rate, 'critical_rate', True)
        self.prediction_days = number(prediction_days, 'prediction_days', True)
        if warning_rate >= critical_rate:
            raise ValueError('Warning rate must be below critical rate')

    def evaluate(self, error, rate):
        if rate is None:
            return {'level': 'INSUFFICIENT_TREND_DATA', 'predicted_error': None}
        predicted = max(0.0, error + rate * self.prediction_days)
        magnitude = abs(rate)
        if error >= self.critical or predicted >= self.critical or magnitude >= self.critical_rate:
            level = UrgencyLevel.HIGH.value
        elif error >= self.warning or predicted >= self.warning or magnitude >= self.warning_rate:
            level = UrgencyLevel.MEDIUM.value
        else:
            level = UrgencyLevel.LOW.value
        return {'level': level, 'predicted_error': predicted}

# ============================================================
# 7. GENERAL HEALTH CONTROLLER
# ============================================================

class HealthController:

    def __init__(self, std, warning, critical, warning_rate, critical_rate, prediction_days=7, max_gap_days=2):
        self.std = number(std, 'reference', True)
        self.accumulated = AccumulatedError(max_gap_days)
        self.deterioration = DeteriorationRate(max_gap_days)
        self.status = InterventionStatus(warning, critical)
        self.urgency = Urgency(warning, critical, warning_rate, critical_rate, prediction_days)

    def process(self, timestamp, current_value, reference_value=None):
        check_time(timestamp)
        value = number(current_value, 'reading', True)
        reference = self.std if reference_value is None else number(reference_value, 'reference', True)
        previous = self.deterioration.previous_time
        if previous is not None and timestamp <= previous:
            raise ValueError('Timestamp must increase')
        # 1. Calculate relative deviation from the changing reference.
        error = Error(reference, value).calculate()
        self.std = reference
        # 2. Integrate the deviation over observed time.
        accumulated = self.accumulated.calculate(timestamp, error)
        # 3. Calculate how quickly the deviation changes.
        rate = self.deterioration.calculate(timestamp, error)
        # 4. Evaluate simulation urgency using fictional thresholds.
        urgency = self.urgency.evaluate(error, rate)
        return dict(deviation=reference - value, error=error, accumulated_error=accumulated, intervention_status=self.status.evaluate(error).value, urgency_level=urgency['level'], accumulated_error_fraction_days=accumulated, covered_days=self.accumulated.covered_days, error_rate=rate, demo_comparison_status=self.status.evaluate(error).value, demo_urgency_level=urgency['level'], demo_predicted_error=urgency['predicted_error'])

# ============================================================
# 8. DAILY EXPERIMENTAL REFERENCE
# ============================================================

def experimental_reference(indicator, flight_day):
    if indicator not in EXPERIMENTS:
        raise ValueError('Unknown indicator: ' + str(indicator))
    day = number(flight_day, 'flight_day')
    if not 6 <= day <= 159:
        raise ValueError('No reference outside nominal flight days 6-159; no extrapolation')
    study = EXPERIMENTS[indicator]
    for (d1, v1), (d2, v2) in zip(study['points'], study['points'][1:]):
        if d1 <= day <= d2:
            slope = (v2 - v1) / (d2 - d1)
            value = v1 + slope * (day - d1)
            return dict(study_value=value, ratio_to_preflight=value / study['preflight'], estimated_study_change_per_day=slope, estimated_study_change_pct_points_per_day=100 * slope / study['preflight'])
    raise ValueError('Reference could not be interpolated')

# ============================================================
# 9. CONNECT CARDIOVASCULAR INDICATORS
# ============================================================

# ============================================================
# HEALTH GUIDANCE — SUPPORTS REVIEW, DOES NOT DIAGNOSE
# ============================================================

class HealthGuidance:
    EMERGENCY_SYMPTOMS = {
        "chest_pain", "severe_shortness_of_breath", "fainting",
        "new_confusion", "stroke_like_symptoms",
    }
    REVIEW_SYMPTOMS = {
        "dizziness", "near_fainting", "weakness", "palpitations",
        "blurred_vision", "unusual_fatigue", "shortness_of_breath",
    }
    SOURCES = [
        "https://www.heart.org/en/health-topics/arrhythmia/about-arrhythmia/tachycardia--fast-heart-rate",
        "https://www.heart.org/en/health-topics/arrhythmia/about-arrhythmia/bradycardia--slow-heart-rate",
        "https://www.heart.org/en/health-topics/high-blood-pressure/the-facts-about-high-blood-pressure/low-blood-pressure-when-blood-pressure-is-too-low",
        "https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings/monitoring-your-blood-pressure-at-home",
        "https://www.nasa.gov/reference/fundamentals-of-human-health/",
    ]

    def evaluate(self, result, symptoms=None, persistent=False,
                 signal_quality=True):
        # Supply explicit symptom names; None means not assessed.
        if symptoms is not None and not isinstance(symptoms, (list, tuple, set)):
            raise ValueError("Symptoms must be a list of symptom names or None.")
        symptoms = None if symptoms is None else set(symptoms)
        if symptoms is not None:
            unknown = symptoms - self.EMERGENCY_SYMPTOMS - self.REVIEW_SYMPTOMS
            if unknown:
                raise ValueError("Unknown symptom names: " + str(sorted(unknown)))
        symptom_set = symptoms or set()
        indicator = result["indicator"]
        difference = result["current_value"] - result["modeled_personal_reference"]
        direction = "higher" if difference > 0 else "lower" if difference < 0 else "equal"
        flagged = result["demo_comparison_status"] != "NORMAL"
        concerns = []
        advice = []
        action = "CONTINUE_SCHEDULED_MONITORING"

        if flagged:
            action = "REPEAT_AND_CHECK_CONTEXT"
            if indicator == "heart_rate":
                if direction == "higher":
                    concerns = ["Recent exercise or stress", "Dehydration or fever",
                                "Medication effect or abnormal rhythm"]
                    advice = ["Confirm resting conditions and sensor contact; repeat the reading.",
                              "Record recent activity, temperature, symptoms, and prescribed fluid intake."]
                else:
                    concerns = ["Sleep or fitness-related variation", "Medication effect",
                                "Possible slowed electrical conduction"]
                    advice = ["Confirm awake/asleep state and repeat the reading.",
                              "Report new weakness, dizziness, fatigue, or reduced exercise tolerance."]
            elif direction == "higher":
                concerns = ["Cuff/measurement error", "Recent exertion or stress",
                            "Medication effect or elevated blood pressure"]
                advice = ["Check cuff size and placement; use the mission measurement procedure.",
                          "If no urgent symptoms, rest quietly for five minutes; take two readings one minute apart."]
            else:
                concerns = ["Fluid-volume adaptation or dehydration", "Medication effect",
                            "Possible impaired pressure regulation"]
                advice = ["Repeat BP and check for dizziness, weakness, blurred vision, or near-fainting.",
                          "Review fluid intake against the prescribed plan; do not self-prescribe extra salt or fluids."]
            if persistent:
                action = "MEDICAL_REVIEW"
                advice.append("Persistent unexplained changes need medical review.")
        else:
            advice = ["Continue scheduled measurements; a value near the model does not establish health."]

        if symptom_set & self.REVIEW_SYMPTOMS:
            action = "MEDICAL_REVIEW"
            advice.append("Symptoms need medical assessment even when the model score is low.")
        if symptoms is None:
            advice.append("Complete the symptom check; symptoms have not been assessed.")
        if not signal_quality:
            if action != "MEDICAL_REVIEW":
                action = "REPEAT_MEASUREMENT"
            advice.append("Poor signal: check the equipment and repeat; numerical comparison is unreliable.")
        if symptom_set & self.EMERGENCY_SYMPTOMS:
            action = "URGENT_ASSESSMENT"
            advice = ["Stop activity, alert a crewmate, and activate the onboard emergency medical protocol.",
                      "Do not wait for a scheduled repeat reading or a response from Earth."]

        return {
            "action": action,
            "direction_from_reference": direction,
            "symptoms_assessed": symptoms is not None,
            "possible_concerns": concerns,
            "advice": advice,
            "note": "Possible explanations, not diagnoses. Reference tolerances are fictional; no validated individual range is available.",
            "sources": self.SOURCES,
        }


class CardiovascularMonitor:

    def __init__(self, personal_baselines, launch_time):
        check_time(launch_time)
        self.launch_time = launch_time
        self.baselines = {name: number(personal_baselines[name], name + ' baseline', True) for name in EXPERIMENTS}
        self.controllers = {name: HealthController(base, 0.15, 0.3, 0.02, 0.05) for name, base in self.baselines.items()}

    def process(self, indicator, timestamp, current_value, symptoms=None,
                persistent=False, signal_quality=True):
        # Validate symptoms before updating monitor history.
        if symptoms is not None:
            if not isinstance(symptoms, (list, tuple, set)):
                raise ValueError("Symptoms must be a list or None")
            unknown = set(symptoms) - HealthGuidance.EMERGENCY_SYMPTOMS - HealthGuidance.REVIEW_SYMPTOMS
            if unknown:
                raise ValueError("Unknown symptom names: " + str(sorted(unknown)))
        check_time(timestamp)
        value = number(current_value, 'reading', True)
        day = (timestamp - self.launch_time).total_seconds() / 86400
        study = experimental_reference(indicator, day)
        baseline = self.baselines[indicator]
        # Scale this astronaut's baseline by the study's interpolated ratio.
        reference = baseline * study['ratio_to_preflight']
        result = self.controllers[indicator].process(timestamp, value, reference)
        personal_change = 100 * (value / baseline - 1)
        study_change = 100 * (study['ratio_to_preflight'] - 1)
        output = dict(indicator=indicator, unit=EXPERIMENTS[indicator]['unit'], timestamp=timestamp.isoformat(), flight_day=day, current_value=value, personal_preflight_baseline=baseline, modeled_personal_reference=reference, personal_change_pct=personal_change, experimental_change_pct=study_change, difference_percentage_points=personal_change - study_change, experimental_daily_rate=study['estimated_study_change_per_day'], medical_intervention_status='NOT_ASSESSED', within_experimental_individual_range='NOT_ESTABLISHED', **result)
        output["guidance"] = HealthGuidance().evaluate(
            output, symptoms, persistent, signal_quality
        )
        return output

# ============================================================
# 10. FICTIONAL READINGS AND DISPLAY
# ============================================================

def demo():
    launch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monitor = CardiovascularMonitor(dict(heart_rate=70.0, systolic_bp=120.0, diastolic_bp=80.0), launch)
    samples = [(20, (65.0, 112.0, 70.0)), (21, (66.0, 113.0, 71.0)), (22, (80.0, 140.0, 95.0))]
    print('SIMULATION: fictional personal readings and alert tolerances.')
    print('Published group trajectories are interpolated; no clinical normal range is established.')
    print('Rapid change in either direction can trigger the experimental urgency rule.\n')
    for day, values in samples:
        print('FLIGHT DAY', day)
        for name, value in zip(EXPERIMENTS, values):
            r = monitor.process(name, launch + timedelta(days=day), value, symptoms=[])
            print(f"  {name}: {value:.2f} {r['unit']} | modeled reference {r['modeled_personal_reference']:.2f}")
            print(f"    Personal change {r['personal_change_pct']:+.2f}% | study change {r['experimental_change_pct']:+.2f}% | difference {r['difference_percentage_points']:+.2f} percentage points")
            print(f"    Demo status {r['demo_comparison_status']} | demo urgency {r['demo_urgency_level']}")
            print("    Suggested action:", r["guidance"]["action"])
            for message in r["guidance"]["advice"]:
                print("      -", message)
        print()

# ============================================================
# 11. BUILT-IN CHECKS
# ============================================================

def self_test():
    import unittest

    class Checks(unittest.TestCase):

        def test_anchors(self):
            for name, study in EXPERIMENTS.items():
                for day, value in study['points']:
                    self.assertAlmostEqual(experimental_reference(name, day)['study_value'], value)

        def test_interpolation(self):
            self.assertAlmostEqual(experimental_reference('heart_rate', 20)['study_value'], 61 + 14 / 31)

        def test_bounds(self):
            for day in (0, 5, 160, float('nan')):
                with self.assertRaises(ValueError):
                    experimental_reference('heart_rate', day)

        def test_personal_scaling(self):
            t = datetime(2026, 1, 1, tzinfo=timezone.utc)
            m = CardiovascularMonitor(dict(heart_rate=70.0, systolic_bp=120.0, diastolic_bp=80.0), t)
            r = m.process('heart_rate', t + timedelta(days=20), 65.0)
            self.assertAlmostEqual(r['modeled_personal_reference'], 70 * (61 + 14 / 31) / 66)
            self.assertIsNone(r['error_rate'])
            with self.assertRaises(ValueError):
                m.process('heart_rate', t + timedelta(days=20), 66.0)
            self.assertEqual(m.controllers['heart_rate'].accumulated.total, 0)

        def test_integral_gap(self):
            t = datetime(2026, 1, 1, tzinfo=timezone.utc)
            a = AccumulatedError()
            a.calculate(t, 0.1)
            self.assertAlmostEqual(a.calculate(t + timedelta(days=1), 0.2), 0.15)
            self.assertAlmostEqual(a.calculate(t + timedelta(days=5), 0.2), 0.15)

        def test_guidance(self):
            g = HealthGuidance()
            base = dict(indicator="heart_rate", current_value=65.,
                        modeled_personal_reference=65., demo_comparison_status="NORMAL")
            self.assertEqual(g.evaluate(base, ["chest_pain"], signal_quality=False)["action"], "URGENT_ASSESSMENT")
            self.assertEqual(g.evaluate(base, ["dizziness"])["action"], "MEDICAL_REVIEW")
            self.assertFalse(g.evaluate(base)["symptoms_assessed"])
            high = dict(base, current_value=90., demo_comparison_status="WATCH")
            self.assertEqual(g.evaluate(high, [], persistent=True)["action"], "MEDICAL_REVIEW")
            self.assertEqual(g.evaluate(high, [], signal_quality=False)["action"], "REPEAT_MEASUREMENT")
            self.assertEqual(g.evaluate(high, [])["direction_from_reference"], "higher")

        def test_validation(self):
            with self.assertRaises(ValueError):
                Error(0, 1)
            with self.assertRaises(ValueError):
                Error(70, float('nan'))
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    return 0 if outcome.wasSuccessful() else 1
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    demo()
