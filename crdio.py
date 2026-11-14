#!/usr/bin/env python3
"""Cardiovascular deviation-monitor prototype; Python 3.9+, standard library only.

Run: python3 cardiovascular_monitor.py
     python3 cardiovascular_monitor.py --demo-thresholds
     python3 cardiovascular_monitor.py --self-test

Research averages are context, not individual targets or medical thresholds.
This calculates P/I/D-like features, not closed-loop treatment control.
Input measurements must already be acquired; this does not interpret raw ECG.
Filtered QRS requires specialized ECG processing, not ordinary wearable QRS.
"""
import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from enum import Enum

RESEARCH_REFERENCES = {
    'awake_hr': dict(unit='bpm', preflight=70.5, early_inflight=65., late_inflight=64.,
                     source='NASA cardiovascular evidence report (2022), Figure 5, printed p.16',
                     graph_estimate=True, condition='awake, not necessarily resting'),
    'awake_systolic_bp': dict(unit='mmHg', preflight=127., early_inflight=122., late_inflight=125.,
                     source='NASA cardiovascular evidence report (2022), Figure 5, printed p.16',
                     graph_estimate=True, condition='awake'),
    'awake_diastolic_bp': dict(unit='mmHg', preflight=72., early_inflight=66., late_inflight=66.,
                     source='NASA cardiovascular evidence report (2022), Figure 5, printed p.16',
                     graph_estimate=True, condition='awake'),
    'filtered_qrs': dict(unit='ms', preflight=84.5, preflight_reported_plus_minus=8.2,
                     inflight_maximum=90.5, inflight_reported_plus_minus=12.1,
                     source='Hastings et al. 2013, Circulation Abstract A18904; 12 astronauts, 4-6 months',
                     url='https://doi.org/10.1161/circ.128.suppl_22.a18904',
                     verification='Numbers retrieved from indexed abstract; publisher access blocked.',
                     graph_estimate=False, condition='specialized filtered QRS; maximum across flight'),
}


def finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + ' must be a finite number')
    return float(value)


class Deviation:
    """Signed baseline minus current value (not an absolute magnitude)."""
    def __init__(self, std, current):
        self.std = finite(std, 'baseline')
        self.current = finite(current, 'reading')
        if self.std <= 0:
            raise ValueError('Baseline must be positive')

    def calculate(self):
        return self.std - self.current


class Error(Deviation):
    def __init__(self, std, current, direction='both'):
        super().__init__(std, current)
        if direction not in ('both', 'low', 'high'):
            raise ValueError('Direction must be both, low, or high')
        self.direction = direction

    def calculate(self):
        change = (self.current - self.std) / self.std
        return {'both': abs(change), 'low': max(-change, 0.),
                'high': max(change, 0.)}[self.direction]


class AccumulatedError:
    """Trapezoidal integral, clipped to window; never bridges long data gaps.

    Errors supplied by Error are nonnegative. Integral units: fraction-days.
    Missing intervals are excluded, not treated as healthy observations.
    """
    def __init__(self, window_days=30, max_gap_days=2):
        self.window_days = finite(window_days, 'window_days')
        self.max_gap_days = finite(max_gap_days, 'max_gap_days')
        if min(self.window_days, self.max_gap_days) <= 0:
            raise ValueError('Window and maximum gap must be positive')
        self.history = []
        self.coverage_days = 0.

    def update(self, timestamp, error):
        if self.history and timestamp <= self.history[-1][0]:
            raise ValueError('Timestamp must increase')
        self.history.append((timestamp, max(finite(error, 'error'), 0.)))
        cutoff = timestamp - timedelta(days=self.window_days)
        # Retain one preceding sample for interpolation at the cutoff.
        while len(self.history) > 2 and self.history[1][0] <= cutoff:
            self.history.pop(0)

    def calculate(self):
        self.coverage_days = 0.
        if len(self.history) < 2:
            return 0.
        cutoff = self.history[-1][0] - timedelta(days=self.window_days)
        total = 0.
        for (t1, e1), (t2, e2) in zip(self.history, self.history[1:]):
            duration = (t2 - t1).total_seconds() / 86400
            if duration > self.max_gap_days or t2 <= cutoff:
                continue
            start = max(t1, cutoff)
            start_error = e1 + (e2 - e1) * ((start-t1).total_seconds()/86400) / duration
            days = (t2-start).total_seconds()/86400
            total += (start_error + e2) * days / 2
            self.coverage_days += days
        return total


class DeteriorationRate:
    """Rate of monitoring error, not a clinical determination of deterioration."""
    def __init__(self, max_gap_days=2):
        self.previous_error = self.previous_time = None
        self.max_gap_days = max_gap_days

    def calculate(self, timestamp, error):
        rate = None
        if self.previous_time is not None:
            days = (timestamp-self.previous_time).total_seconds()/86400
            if days <= 0:
                raise ValueError('Timestamp must increase')
            if days <= self.max_gap_days:
                rate = (error-self.previous_error)/days
        self.previous_error, self.previous_time = error, timestamp
        return rate


class Status(Enum):
    NO_DEVIATION_FLAG = 'NO_DEVIATION_FLAG'
    WATCH = 'WATCH'
    ACTION_REVIEW = 'ACTION_REVIEW'


class InterventionStatus:
    def __init__(self, warning, critical):
        self.warning = finite(warning, 'warning')
        self.critical = finite(critical, 'critical')
        if not 0 < self.warning < self.critical:
            raise ValueError('Require 0 < warning < critical')

    def evaluate(self, error):
        if error >= self.critical:
            return Status.ACTION_REVIEW
        return Status.WATCH if error >= self.warning else Status.NO_DEVIATION_FLAG


class Urgency:
    """Experimental score; not calibrated medical urgency."""
    def __init__(self, critical, rate_scale, accumulated_scale, weights=(.5, .25, .25)):
        self.critical, self.rate_scale, self.accumulated_scale = [
            finite(v, 'scale') for v in (critical, rate_scale, accumulated_scale)]
        if min(self.critical, self.rate_scale, self.accumulated_scale) <= 0:
            raise ValueError('Scales must be positive')
        self.weights = tuple(finite(w, 'weight') for w in weights)
        if len(self.weights) != 3 or min(self.weights) < 0 or not math.isclose(sum(self.weights), 1.):
            raise ValueError('Three nonnegative weights must sum to one')

    def evaluate(self, error, rate, accumulated):
        if rate is None:
            return dict(score=None, level='INSUFFICIENT_TREND_DATA')
        features = (min(error/self.critical, 1.),
                    min(max(rate, 0.)/self.rate_scale, 1.),
                    min(accumulated/self.accumulated_scale, 1.))
        score = 100 * sum(w*f for w, f in zip(self.weights, features))
        level = ('CRITICAL' if error >= self.critical else 'HIGH' if score >= 70
                 else 'MODERATE' if score >= 40 else 'LOW')
        return dict(score=round(score, 2), level=level)


class HealthController:
    def __init__(self, std, warning=None, critical=None, window_days=30,
                 rate_scale=.001, accumulated_scale=1., direction='both', max_gap_days=2):
        self.std = Error(std, std, direction).std
        self.direction = direction
        if (warning is None) != (critical is None):
            raise ValueError('Supply both thresholds or neither')
        self.accumulated = AccumulatedError(window_days, max_gap_days)
        self.deterioration = DeteriorationRate(max_gap_days)
        self.status = None if warning is None else InterventionStatus(warning, critical)
        self.urgency = None if warning is None else Urgency(critical, rate_scale, accumulated_scale)

    def process(self, timestamp, current_value):
        if not isinstance(timestamp, datetime) or timestamp.utcoffset() is None:
            raise ValueError('Use a timezone-aware datetime')
        value = finite(current_value, 'reading')
        if value <= 0:
            raise ValueError('Reading must be positive')
        previous = self.deterioration.previous_time
        if previous is not None and timestamp <= previous:
            raise ValueError('Timestamp must increase')
        error = Error(self.std, value, self.direction).calculate()
        rate = self.deterioration.calculate(timestamp, error)
        self.accumulated.update(timestamp, error)
        accumulated = self.accumulated.calculate()
        urgency = (dict(score=None, level='NOT_ASSESSED') if self.urgency is None
                   else self.urgency.evaluate(error, rate, accumulated))
        return dict(timestamp=timestamp.isoformat(), current_value=value,
                    personal_baseline=self.std, deviation=self.std-value,
                    change_from_baseline_pct=100*(value-self.std)/self.std,
                    monitoring_error=error, accumulated_error_fraction_days=accumulated,
                    covered_days=self.accumulated.coverage_days,
                    error_change_per_day=rate,
                    intervention_status='NOT_ASSESSED' if self.status is None else self.status.evaluate(error).value,
                    urgency_score=urgency['score'], urgency_level=urgency['level'])


def run_demo(demo_thresholds=False):
    # FICTIONAL personal baselines and readings. Match acquisition conditions.
    baselines = dict(awake_hr=70., awake_systolic_bp=120., awake_diastolic_bp=80., filtered_qrs=85.)
    # Optional thresholds/scales are arbitrary software demonstrations only.
    settings = dict(warning=.15, critical=.30, rate_scale=.05, accumulated_scale=.5) if demo_thresholds else {}
    monitors = {name: HealthController(value, direction='high' if name == 'filtered_qrs' else 'both',
                                       **settings) for name, value in baselines.items()}
    rows = [(65., 115., 75., 90.), (66., 116., 76., 91.), (80., 140., 95., 100.)]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    output = []
    for day, values in enumerate(rows):
        for (name, monitor), value in zip(monitors.items(), values):
            output.append(dict(indicator=name, unit=RESEARCH_REFERENCES[name]['unit'],
                               **monitor.process(start+timedelta(days=day), value)))
    print(json.dumps(dict(simulation_only=True, demo_thresholds=demo_thresholds,
                         note='Research references are not alert limits. No diagnosis or treatment output.',
                         research_references=RESEARCH_REFERENCES, measurements=output), indent=2, allow_nan=False))


def self_test():
    import unittest
    class Checks(unittest.TestCase):
        def test_direction(self):
            self.assertAlmostEqual(Error(100, 80, 'low').calculate(), .2)
            self.assertEqual(Error(100, 80, 'high').calculate(), 0)
            self.assertAlmostEqual(Error(100, 120).calculate(), .2)
        def test_window_and_gap(self):
            t = datetime(2026, 1, 1, tzinfo=timezone.utc)
            a = AccumulatedError(window_days=1, max_gap_days=3)
            a.update(t, 0); a.update(t+timedelta(days=2), .2)
            self.assertAlmostEqual(a.calculate(), .15)
            b = AccumulatedError(max_gap_days=1)
            b.update(t, .1); b.update(t+timedelta(days=3), .1)
            self.assertEqual(b.calculate(), 0)
        def test_validation_and_first_reading(self):
            t = datetime(2026, 1, 1, tzinfo=timezone.utc)
            m = HealthController(70)
            r = m.process(t, 65)
            self.assertIsNone(r['error_change_per_day'])
            self.assertEqual(r['intervention_status'], 'NOT_ASSESSED')
            for value in (float('nan'), -1, float('inf')):
                with self.assertRaises(ValueError): m.process(t+timedelta(days=1), value)
            with self.assertRaises(ValueError): m.process(t, 70)
            self.assertEqual(len(m.accumulated.history), 1)
        def test_thresholds(self):
            s = InterventionStatus(.1, .2)
            self.assertEqual(s.evaluate(.2), Status.ACTION_REVIEW)
            with self.assertRaises(ValueError): HealthController(70, warning=.1)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo-thresholds', action='store_true', help='Enable arbitrary SIMULATION-ONLY scoring')
    parser.add_argument('--self-test', action='store_true', help='Run built-in verification')
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    run_demo(args.demo_thresholds)
