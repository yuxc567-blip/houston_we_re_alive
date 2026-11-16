"""
Run the bone-density monitor over four mission profiles and export the
results for the web page.

Every status, urgency, error and prevention line on the page comes from the
project's own engine:

    control_loop.HealthController(std=100.0, warning=0.05, critical=0.10,
                                  warning_rate=0.01, critical_rate=0.02,
                                  prediction_days=7)
    prevention.Prevention(...).recommend("bone_density", error, urgency)

Those are the same thresholds `test.py` uses for the Unity report, and
`prevention.py` is bundled here unchanged. Only the readings are simulated:
bone density is expressed as a percentage of the crew member's pre-flight
baseline, and the profiles below are invented mission shapes, not measured
astronaut data.

    python -m bones.export_bone_data   -> bones/web/bone-data.js
"""
from __future__ import annotations

import json
import random
import zlib
from datetime import datetime, timedelta
from pathlib import Path

from control_loop import HealthController

try:
    from . import prevention
except ImportError:          # run directly
    import prevention

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'web' / 'bone-data.js'

BASELINE = 100.0
THRESHOLDS = dict(std=BASELINE, warning=0.05, critical=0.10,
                  warning_rate=0.01, critical_rate=0.02, prediction_days=7)

# The canonical case from test.py, kept so the page can show the exact
# report the Unity panel consumes.
REFERENCE = {'date': datetime(2026, 6, 6, 12, 0, 0), 'value': 92.5}


def new_controller():
    return HealthController(**THRESHOLDS)


def prevent(error, urgency):
    database = prevention.PreventionDatabase(':memory:')
    try:
        return prevention.Prevention(database, prevention.PREVENTION_PLANS).recommend(
            'bone_density', error, urgency)
    finally:
        database.close()


def sample(controller, day, when, value):
    result = controller.process(when, value)
    return {
        'day': day,
        'date': when.date().isoformat(),
        'value': round(value, 2),
        'baseline': BASELINE,
        'deviation': round(result['deviation'], 2),
        'error': round(result['error'], 4),
        'error_pct': round(result['error'] * 100, 2),
        'accumulated': round(result['accumulated_error'], 3),
        'rate': round(result['error_rate'], 5),
        'rate_pct_per_day': round(result['error_rate'] * 100, 4),
        'status': result['intervention_status'],
        'urgency': result['urgency_level'],
        'prevention': prevent(result['error'], result['urgency_level']),
    }


def case_reference():
    controller = new_controller()
    when = REFERENCE['date']
    row = sample(controller, 0, when, REFERENCE['value'])
    return {
        'id': 'bone_reference',
        'label': 'The reference reading',
        'note': ('The single sample test.py exports to the Unity panel: baseline '
                 f"{BASELINE:g}, reading {REFERENCE['value']:g} on {when.date().isoformat()}."),
        'source': 'engine output, single sample',
        'cadence_label': 'One measurement',
        'samples': [row],
    }


def series_case(case_id, label, note, days, shape, start=datetime(2026, 1, 1, 12, 0, 0), seed=None):
    controller = new_controller()
    rng = random.Random(zlib.crc32((seed or case_id).encode()) & 0xFFFF)
    samples = []
    for day in range(days + 1):
        value = BASELINE * shape(day) * (1.0 + rng.gauss(0, 0.0015))
        samples.append(sample(controller, day, start + timedelta(days=day), value))
    return {
        'id': case_id,
        'label': label,
        'note': note,
        'source': 'simulated readings, engine output',
        'cadence_label': 'Daily checks',
        'samples': samples,
    }


def slow_loss(day):
    # Weight-bearing bone loses roughly 1-1.5% a month in microgravity.
    return 1.0 - 0.0005 * day


def held_after(day):
    # Loss stops once the exercise and nutrition countermeasure starts.
    return 1.0 - 0.0005 * min(day, 90)


def rapid_loss(day):
    return 1.0 - 0.0012 * day


def main():
    cases = [
        case_reference(),
        series_case('bone_slow', 'Steady loss over six months',
                    'About 1.5% a month, which is the published range for '
                    'weight-bearing bone in microgravity.',
                    days=180, shape=slow_loss),
        series_case('bone_held', 'Countermeasure holds the loss from day 90',
                    'The same decline, but loading exercise and nutrition stop it '
                    'three months in.',
                    days=180, shape=held_after),
        series_case('bone_rapid', 'Fast loss over four months',
                    'Twice the usual rate; this is the profile that reaches the '
                    'critical band.',
                    days=120, shape=rapid_loss),
    ]

    payload = {
        'generated_from': 'control_loop.HealthController + bones/prevention.py',
        'engine': 'HealthController(std=100, warning=0.05, critical=0.10, '
                  'warning_rate=0.01, critical_rate=0.02, prediction_days=7)',
        'thresholds': {'warning': 0.05, 'critical': 0.10},
        'unit': '% of pre-flight baseline',
        'cases': cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('window.BONE_DATA = '
                   + json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
                   + ';\n', encoding='utf-8')
    print(f'wrote {OUT}  ({OUT.stat().st_size / 1024:.1f} KB)')
    for case in cases:
        counts = {}
        for row in case['samples']:
            counts[row['status']] = counts.get(row['status'], 0) + 1
        print(f"  {case['label'][:44]:<46}{counts}")


if __name__ == '__main__':
    main()
